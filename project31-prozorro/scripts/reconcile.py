#!/usr/bin/env python3
"""Independent Fraction arithmetic and bounded assistant source inspection.

No package code is imported. The checker reads privacy-filtered source extracts
and independently reconstructs quotients from the contract snapshot's own item
quantity. A terminated contract's quotient is arithmetic only. It is never fed
back into screening or promoted to a comparable purchase price.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys


STRATA = (
    'ordinary_single_item', 'bundle', 'missing_numeric_quantity',
    'unresolved_sheet_quantity', 'amendment', 'cancelled', 'status_mismatch',
    'arithmetic_range_endpoint',
)


def source_number(raw):
    """Exact source-decimal conversion using integer digits, independently of Decimal."""
    if not isinstance(raw, str) or len(raw) > 200:
        raise ValueError('source number must be a bounded decimal string')
    text = raw.strip()
    if not re.fullmatch(r'[0-9]+(?:[.,][0-9]+)?', text):
        raise ValueError('not an ungrouped source decimal')
    pieces = text.replace(',', '.').split('.')
    if len(pieces) == 1:
        value = Fraction(int(pieces[0]), 1)
    else:
        value = Fraction(int(pieces[0] + pieces[1]), 10 ** len(pieces[1]))
    if value <= 0:
        raise ValueError('nonpositive source number')
    return value


def fraction_json(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def fraction_from_json(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sheet_count(item):
    """Recognize only explicit sheets or unambiguous PK plus written sheet count."""
    unit = item.get('unit', {})
    name = unit.get('name', '').strip().casefold()
    if unit.get('code') == 'ST' and name in {'sheet', 'аркуш', 'аркуші', 'аркушів'}:
        return Fraction(1), 'Explicit sheet unit, code and name agree.'
    if unit.get('code') != 'PK' or name not in {'pack', 'пачка', 'пачки', 'пачок'}:
        return None, 'Declared unit does not establish sheets or a reviewed pack.'
    description = item.get('description', '').casefold()
    # Read the integer immediately before a literal sheet word. Do not use
    # slash shorthand, a bare 500, piece quantities, or a product name as proof.
    counts = set()
    for token in re.finditer(r'(?<![0-9])([0-9]+)\s*(?:арк(?:уш[а-яіїєґ]*)?\.?|sheets?)\b', description):
        counts.add(int(token.group(1)))
    if len(counts) != 1 or next(iter(counts)) <= 0:
        return None, 'PK is explicit, but an unambiguous sheet count is absent.'
    count = next(iter(counts))
    return Fraction(count), f'PK/name agree and the description explicitly states {count} sheets.'


def contract_snapshots(extract):
    """Retain both embedded and detail evidence; prefer each fetched detail for its ID."""
    tender = extract['tender']
    current = {}
    embedded = {}
    for index, contract in enumerate(tender.get('contracts', [])):
        ident = contract.get('id')
        if not ident or ident in embedded:
            raise ValueError('missing or duplicate embedded contract ID')
        embedded[ident] = {'status': contract.get('status'),
                           'field_path': f'/tender/contracts/{index}/status'}
        current[ident] = (contract, f'/tender/contracts/{index}', extract['provenance']['url'])
    seen_details = set()
    for index, detail in enumerate(extract.get('contract_details', [])):
        contract = detail.get('contract')
        if not contract:
            continue
        ident = contract.get('id')
        if not ident or ident in seen_details:
            raise ValueError('missing or duplicate detailed contract ID')
        seen_details.add(ident)
        current[ident] = (contract, f'/contract_details/{index}/contract', detail['provenance']['url'])
    return [(ident, *current[ident], embedded.get(ident)) for ident in sorted(current)]


def source_profile(path, root):
    extract = json.loads(path.read_text())
    tender = extract['tender']
    lots = tender.get('lots', [])
    if len(lots) > 1:
        raise ValueError('independent checker refuses unresolved multi-lot extracts')
    lot_id = lots[0]['id'] if lots else 'single'
    key = tender['id'] + '/' + lot_id
    contracts = []
    for ident, contract, base, url, embedded in contract_snapshots(extract):
        items = contract.get('items', [])
        entry = {
            'contract_id': ident, 'source_url': url, 'field_path': base,
            'status': contract.get('status'),
            'stage': 'amended_contract_snapshot' if contract.get('changes') else 'contract_snapshot',
            'embedded_status_evidence': embedded,
            'status_mismatch': bool(embedded and embedded['status'] != contract.get('status')),
            'value': contract.get('value', {}), 'amount_paid_observed': contract.get('amountPaid'),
            'amount_paid_interpretation': 'Reported aggregate only; not a reconciled cash transaction.',
            'item_count': len(items),
            'items': [{'id': item.get('id'), 'description': item.get('description'),
                       'quantity': item.get('quantity'), 'unit': item.get('unit'),
                       'field_path': f'{base}/items/{index}'} for index, item in enumerate(items)],
            'changes_count': len(contract.get('changes', [])),
            'changes': contract.get('changes', []),
            'declared_unit_quotient': None, 'sheet_quotient': None,
            'quantity_sheets': None, 'arithmetic_issue': None,
            'eligible_for_purchase_comparison': False,
        }
        if len(items) != 1:
            entry['arithmetic_issue'] = 'No allocation of a contract total across multiple or absent item lines.'
        else:
            try:
                amount = source_number(contract.get('value', {}).get('amount'))
                quantity = source_number(items[0].get('quantity'))
                entry['declared_unit_quotient'] = fraction_json(amount / quantity)
                factor, note = sheet_count(items[0])
                entry['sheet_conversion_note'] = note
                if factor is not None:
                    entry['quantity_sheets'] = fraction_json(quantity * factor)
                    entry['sheet_quotient'] = fraction_json(amount / (quantity * factor))
                entry['arithmetic_evidence'] = [base + '/value/amount', base + '/items/0/quantity',
                                                base + '/items/0/unit', base + '/items/0/description']
            except ValueError as exc:
                entry['arithmetic_issue'] = str(exc)
        contracts.append(entry)
    statuses = [tender.get('status')] + [lot.get('status') for lot in lots]
    flags = []
    if any(len(c['items']) > 1 for c in contracts):
        flags.append('bundle')
    if not contracts or any(not c['items'] for c in contracts):
        flags.append('missing_numeric_quantity')
    else:
        for c in contracts:
            for item in c['items']:
                try:
                    source_number(item.get('quantity'))
                except ValueError:
                    if 'missing_numeric_quantity' not in flags:
                        flags.append('missing_numeric_quantity')
    if any(c['item_count'] == 1 and c['sheet_quotient'] is None for c in contracts):
        flags.append('unresolved_sheet_quantity')
    if any(c['changes_count'] for c in contracts):
        flags.append('amendment')
    if any(x in {'cancelled', 'canceled', 'unsuccessful'} for x in statuses) or tender.get('cancellations'):
        flags.append('cancelled')
    if any(c['status_mismatch'] for c in contracts):
        flags.append('status_mismatch')
    if len(contracts) == 1 and contracts[0]['sheet_quotient'] is not None and not contracts[0]['changes_count']:
        flags.append('ordinary_single_item')
    return {
        'key': key, 'tenderID': tender.get('tenderID'),
        'source_file': str(path.relative_to(root)), 'extract_sha256': digest(path),
        'source_url': extract['provenance']['url'],
        'tender_status': tender.get('status'), 'tender_item_count': len(tender.get('items', [])),
        'tender_item_evidence': [{'id': item.get('id'), 'description': item.get('description'),
                                  'quantity': item.get('quantity'), 'unit': item.get('unit'),
                                  'field_path': f'/tender/items/{index}'}
                                 for index, item in enumerate(tender.get('items', []))],
        'cancellations': tender.get('cancellations', []),
        'contracts': contracts, 'strata': flags,
    }


def compare_normalized(profiles, normalized):
    by_key = {profile['key']: profile for profile in profiles}
    seen = set()
    checks = []
    errors = []
    for record in normalized:
        key = record.get('key')
        if key in seen:
            errors.append({'key': key, 'issue': 'duplicate_normalized_lot'})
            continue
        seen.add(key)
        if key not in by_key:
            errors.append({'key': key, 'issue': 'normalized_lot_has_no_source_extract'})
            continue
        if record.get('unit_price') is None:
            continue
        candidates = [c for c in by_key[key]['contracts'] if c['contract_id'] == record.get('selected_observation_id')]
        check = {'key': key, 'selected_observation_id': record.get('selected_observation_id'),
                 'core_unit_price_fraction': record.get('unit_price_fraction'), 'matched': False}
        if len(candidates) != 1:
            check['issue'] = 'cannot_find_unique_source_contract'
        else:
            source = candidates[0]
            check['source_url'] = source['source_url']
            check['field_paths'] = source.get('arithmetic_evidence', [])
            check['independent_unit_price_fraction'] = source['sheet_quotient']
            check['independent_quantity_sheets_fraction'] = source['quantity_sheets']
            if source['sheet_quotient'] is None:
                check['issue'] = 'source_does_not_independently_establish_sheet_arithmetic'
            elif source['status'] != 'active' or source['changes_count']:
                check['issue'] = 'strict_core_price_selected_inactive_or_unreconciled_snapshot'
            else:
                try:
                    price_match = fraction_from_json(source['sheet_quotient']) == fraction_from_json(record['unit_price_fraction'])
                    quantity_match = fraction_from_json(source['quantity_sheets']) == source_number(record['quantity_sheets'])
                    amount_match = source_number(source['value']['amount']) == source_number(record['amount'])
                    check['matched'] = price_match and quantity_match and amount_match
                    if not check['matched']:
                        check['issue'] = 'exact_price_quantity_or_amount_mismatch'
                except (KeyError, ValueError, TypeError, ZeroDivisionError):
                    check['issue'] = 'invalid_normalized_exact_arithmetic'
        checks.append(check)
        if not check['matched']:
            errors.append(check)
    missing = sorted(set(by_key) - seen)
    if missing:
        errors.append({'issue': 'source_extracts_missing_from_normalized_report', 'keys': missing})
    return checks, errors


def inspection_notes(profile):
    notes = []
    for contract in profile['contracts']:
        base = contract['field_path']
        if contract['item_count'] > 1:
            notes.append({'issue': 'mixed_or_multiple_item_total', 'evidence_paths': [base + '/value', base + '/items'],
                          'observation': f"The snapshot has {contract['item_count']} item lines and one total. No paper-line price is allocated.",
                          'proposed_action': 'Exclude until separately priced equivalent goods are reconciled.'})
        if contract['status_mismatch']:
            notes.append({'issue': 'embedded_and_detail_status_differ',
                          'evidence_paths': [contract['embedded_status_evidence']['field_path'], base + '/status'],
                          'observation': f"Embedded contract status is {contract['embedded_status_evidence']['status']}; detailed contract status is {contract['status']}.",
                          'proposed_action': 'Retain both observations and use fetched detail for current state. Do not call it an active purchase.'})
        if contract['changes_count']:
            notes.append({'issue': 'amendment_needs_reconciliation', 'evidence_paths': [base + '/changes', base + '/items', base + '/value'],
                          'observation': f"The source contains {contract['changes_count']} contract change entries. Their original signed quantities and economic effect have not been independently reconciled.",
                          'proposed_action': 'Keep the amendment stage separate and exclude current-price screening pending review.'})
        if contract['item_count'] == 1:
            item = contract['items'][0]
            notes.append({'issue': 'declared_quantity_and_unit',
                          'evidence_paths': [item['field_path'] + '/quantity', item['field_path'] + '/unit', item['field_path'] + '/description', base + '/value'],
                          'observation': 'Source quantity, unit, description, tax flag and total are copied in the contract evidence. '
                                         + contract.get('sheet_conversion_note', contract.get('arithmetic_issue') or 'No sheet conversion established.'),
                          'proposed_action': 'Keep a declared-unit quotient as arithmetic only. Do not assume a piece is a pack or assume missing pack size.'})
    if 'arithmetic_range_endpoint' in profile['strata']:
        notes.append({'issue': 'arithmetic_endpoint_selected_for_inspection',
                      'evidence_paths': [p for c in profile['contracts'] for p in c.get('arithmetic_evidence', [])],
                      'observation': 'Selected because its explicit-sheet quotient is a minimum or maximum among the retained snapshot quotients. The underlying contracts are not established as economically comparable.',
                      'proposed_action': 'Treat only as a source-check candidate; no economic-outlier or wrongdoing claim follows.'})
    notes.append({'issue': 'comparability_unvalidated', 'evidence_paths': ['/tender/items', '/contract_details'],
                  'observation': 'This is assistant inspection of API extract fields. Document contents, equivalent quality, tax scope, delivery inclusions, payment terms and independent human judgments remain unverified.',
                  'proposed_action': 'Retain all real screening exclusions and obtain independent evidence-linked review before comparison.'})
    return notes


def run(root, normalized_path, reconciliation_path, review_path):
    paths = sorted((root / 'data/extracts').glob('*.json'))
    profiles = [source_profile(path, root) for path in paths]
    keys = [p['key'] for p in profiles]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate source lot identity')
    normalized = json.loads(normalized_path.read_text())
    checks, errors = compare_normalized(profiles, normalized)
    ranked = []
    for profile in profiles:
        if len(profile['contracts']) == 1 and profile['contracts'][0]['sheet_quotient'] is not None:
            ranked.append((fraction_from_json(profile['contracts'][0]['sheet_quotient']), profile['key']))
    ranked.sort()
    endpoints = {ranked[0][1], ranked[-1][1]} if ranked else set()
    for profile in profiles:
        if profile['key'] in endpoints:
            profile['strata'].append('arithmetic_range_endpoint')
    pools = {stratum: [p['key'] for p in profiles if stratum in p['strata']] for stratum in STRATA}
    # Include every strict core-computable record first, then up to two from
    # each stratum, then deterministic source-order fill to the bounded 14.
    selected = []
    for key in [c['key'] for c in checks]:
        if key not in selected and len(selected) < 14:
            selected.append(key)
    for stratum in ('amendment', 'cancelled', 'missing_numeric_quantity', 'arithmetic_range_endpoint',
                    'bundle', 'unresolved_sheet_quantity', 'status_mismatch', 'ordinary_single_item'):
        for key in pools[stratum][:2]:
            if key not in selected and len(selected) < 14:
                selected.append(key)
    for key in keys:
        if key not in selected and len(selected) < 14:
            selected.append(key)
    selected_set = set(selected)
    strata = [{'stratum': s, 'observed_count': len(pools[s]),
               'selected_count': len(selected_set.intersection(pools[s])),
               'status': 'observed' if pools[s] else 'absent_in_retained_real_sample',
               'selected_keys': sorted(selected_set.intersection(pools[s]))} for s in STRATA]
    review = {
        'schema_version': 1, 'annotator': 'assistant', 'independent_human': False,
        'review_scope': 'Retained public API extract fields only; no document contents reviewed.',
        'selection': 'Deterministic bounded stratified convenience subset; no random or representative sampling claim.',
        'maximum_review_records': 14, 'sample_lot_count': len(profiles), 'selected_count': len(selected),
        'strata': strata,
        'records': [dict(profile, annotator='assistant', independent_human=False,
                         inspection_notes=inspection_notes(profile))
                    for profile in profiles if profile['key'] in selected_set],
        'human_validation_gate': 'unmet',
        'limitations': ['Assistant notes are provisional, not holdout truth labels.',
                        'An absent observed stratum was not filled with invented real data.',
                        'Termination is a source status, not proof of cancellation or failure.',
                        'No document contents or private evidence were inspected.'],
    }
    snapshots = [c for p in profiles for c in p['contracts']]
    report = {
        'schema_version': 1,
        'method': 'Independent integer-digit Fraction arithmetic on saved source extracts; core and adapter are not imported.',
        'checker_independence': 'Separate arithmetic implementation by the same assistant; not an independent human review.',
        'input_normalized_sha256': digest(normalized_path),
        'input_extract_hashes': {p['source_file']: p['extract_sha256'] for p in profiles},
        'counts': {'source_lots': len(profiles), 'normalized_lots': len(normalized),
                   'contract_snapshots': len(snapshots),
                   'declared_unit_quotients': sum(c['declared_unit_quotient'] is not None for c in snapshots),
                   'explicit_sheet_quotients': sum(c['sheet_quotient'] is not None for c in snapshots),
                   'terminated_declared_unit_quotients': sum(c['status'] == 'terminated' and c['declared_unit_quotient'] is not None for c in snapshots),
                   'core_exact_checks': len(checks), 'core_exact_matches': sum(c['matched'] for c in checks),
                   'mismatches_or_coverage_errors': len(errors), 'assistant_reviewed_records': len(selected)},
        'core_exact_checks': checks, 'errors': errors, 'passed': not errors,
        'snapshot_arithmetic': [{'key': p['key'], 'source_file': p['source_file'], 'contracts': p['contracts']} for p in profiles],
        'review_strata': strata,
        'limitations': ['A snapshot quotient is total divided by the same snapshot item quantity, not a cross-purchase price comparison.',
                        'Terminated snapshots are not substituted for active contract observations in the analyzer.',
                        'amountPaid is separate reported aggregate evidence; absent payments are unknown.',
                        'Exact arithmetic cannot validate specifications, tax, delivery, payments or human judgments.',
                        'The checker accepts only ungrouped source decimal strings and explicit recognized units.'],
    }
    for path, value in [(reconciliation_path, report), (review_path, review)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report['counts'], sort_keys=True))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--normalized', type=Path)
    parser.add_argument('--reconciliation', type=Path)
    parser.add_argument('--assistant-review', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    return run(root, args.normalized or root / 'output/real/normalized.json',
               args.reconciliation or root / 'evidence/reconciliation.json',
               args.assistant_review or root / 'data/assistant-review.json')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Reconciliation failed: {error}', file=sys.stderr)
        sys.exit(2)
