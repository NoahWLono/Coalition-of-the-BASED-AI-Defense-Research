"""Explicit adapter from privacy-filtered API extracts to the accounting contract."""
from __future__ import annotations
import re
from copy import deepcopy


def item_input(item: dict, version: str) -> dict:
    unit = item.get('unit', {})
    code, name = unit.get('code', ''), unit.get('name', '').lower()
    result = {'id': item.get('id', ''), 'description': item.get('description', ''),
              'quantity': str(item['quantity']) if item.get('quantity') is not None else None,
              'unit': 'unresolved', 'unit_code': code, 'unit_name': name,
              'quantity_version': version, 'pack_size_reviewed': False}
    # Codes and names must agree. In particular H87 never becomes a pack.
    if code == 'PK' and name in ('пачка', 'пачок', 'пачки', 'pack'):
        result['unit'] = 'pack'
        description = item.get('description', '')
        ambiguous = re.search(r'\b\d+\s*[-–]\s*\d|\b\d+[.,]\d+\s*(?:арк|sheet)|\b\d+\s+\d+\s*(?:арк|sheet)|не\s+менше|не\s+більше|щонайменше|at least|up to|[<>≥≤]', description, re.I)
        sizes = set() if ambiguous else set(re.findall(r'\b(\d+)\s*(?:арк\.?|аркуш\w*|sheets?)', description, re.I))
        if len(sizes) == 1:
            result['sheets_per_pack'] = sizes.pop()
            result['pack_size_reviewed'] = True
            result['pack_size_review_method'] = 'assistant_rule_explicit_description_only'
    elif name in ('аркуш', 'аркуші', 'аркушів', 'sheet') and code == 'ST':
        result['unit'] = 'sheet'
    return result


def _observation(obj: dict, stage: str, version: str, item_ids: list, linked: bool) -> dict:
    v = obj.get('value', {})
    return {'id': obj.get('id', stage), 'stage': stage, 'amount': str(v['amount']) if v.get('amount') is not None else None,
            'currency': v.get('currency'), 'vat_included': v.get('valueAddedTaxIncluded'), 'amount_net': v.get('amountNet'),
            'status': obj.get('status', 'observed'), 'item_ids': item_ids,
            'quantity_version': version, 'quantity_link_reviewed': linked,
            'amendment_reconciled': not bool(obj.get('changes')),
            'date': obj.get('dateSigned', obj.get('date')), 'changes': obj.get('changes', [])}


def adapt(extract: dict) -> dict:
    t = extract['tender']; p = extract['provenance']
    lots = t.get('lots', []); lot_id = lots[0]['id'] if len(lots) == 1 else 'single'
    source = p['url']
    contracts = deepcopy(t.get('contracts', []))
    detail_urls = {}
    current_unavailable = any(x.get('contract') is None for x in extract.get('contract_details', []))
    for detail in extract.get('contract_details', []):
        c = detail.get('contract')
        if not c: continue
        contracts = [x for x in contracts if x.get('id') != c.get('id')]
        contracts.append(c)
        detail_urls[c['id']] = detail['provenance'].get('url')
    # A unique contract's own item set is authoritative for arithmetic. Reconciliation
    # still fails closed if amendments have not been separately reviewed.
    chosen = contracts[0] if len(contracts) == 1 and contracts[0].get('items') else None
    version = 'contract:' + chosen['id'] if chosen else 'tender:' + t['id']
    raw_items = chosen['items'] if chosen else t.get('items', [])
    refs = [i.get('relatedLot') for i in t.get('items', []) + raw_items]
    refs += [a.get('lotID') for a in t.get('awards', [])]
    refs += [c.get('lotID') for c in contracts]
    lot_conflict = any(ref is not None and ref != lot_id for ref in refs)
    lot_conflict = lot_conflict or len(lots) > 1
    items = [item_input(x, version) for x in raw_items]
    observations = []
    estimate = lots[0] if len(lots) == 1 else t
    observations.append(_observation(estimate, 'estimate', 'tender:' + t['id'], [x.get('id') for x in t.get('items', [])], True))
    for bid in t.get('bids', []):
        if bid.get('lotValues'):
            for lv in bid['lotValues']:
                if lv.get('relatedLot') == lot_id:
                    observations.append(_observation({**bid, 'value': lv.get('value', {})}, 'bid', 'unknown', [], False))
        else:
            observations.append(_observation(bid, 'bid', 'unknown', [], False))
    for award in t.get('awards', []):
        observations.append(_observation(award, 'award', 'unknown', [], False))
    for c in contracts:
        has_items = bool(c.get('items'))
        v = 'contract:' + c['id'] if has_items else 'unknown'
        ids = [x.get('id') for x in c.get('items', [])]
        stage = 'amended_contract' if c.get('changes') else 'contract_current'
        o = _observation(c, stage, v, ids, has_items and not lot_conflict and not current_unavailable)
        o['source_url'] = detail_urls.get(c['id'], source)
        observations.append(o)
        if 'amountPaid' in c:
            payment = _observation({**c, 'id': c['id'] + ':amountPaid', 'value': c['amountPaid']}, 'payment_observed', 'unknown', [], False)
            payment['payment_evidence_kind'] = 'reported_aggregate_amountPaid_not_cash_reconciled'
            observations.append(payment)
        for tx in c.get('implementation', {}).get('transactions', []):
            payment = _observation(tx, 'payment_observed', 'unknown', [], False)
            payment['payment_evidence_kind'] = 'published_transaction_not_independently_reconciled'
            observations.append(payment)
    selected_value = chosen.get('value', {}) if chosen else (contracts[0].get('value', {}) if len(contracts) == 1 else {})
    return {'tender_id': t['id'], 'tenderID': t.get('tenderID'), 'lot_id': lot_id, 'source_kind': extract.get('source_kind', 'real'),
            'status': lots[0].get('status', t.get('status')) if lots else t.get('status'),
            'lot_link_conflict': lot_conflict, 'current_contract_state_unavailable': current_unavailable,
            'publication_date': t.get('dateCreated'), 'publication_date_basis': 'API dateCreated, checked against public tenderID date',
            'source_modified': t.get('dateModified'), 'title': t.get('title'),
            'items': items, 'observations': observations,
            'review': {'annotator_type': 'assistant', 'reviewed': False, 'evidence': [source], 'evidence_by_gate': {},
                       'vat_included': selected_value.get('valueAddedTaxIncluded'),
                       'net_gross_scope': None, 'spec_key': None, 'fiscal_key': None, 'delivery_key': None, 'payment_key': None},
            'source_url': source, 'public_url': 'https://prozorro.gov.ua/uk/tender/' + t.get('tenderID', ''),
            'retrieved_at': p.get('retrieved_at'), 'response_sha256': p.get('response_sha256'),
            'attribution': p.get('attribution', 'Prozorro'), 'cancellations': t.get('cancellations', []),
            'contract_count': len(contracts), 'documents': t.get('documents', []),
            'contract_documents': [{'contract_id': c['id'], 'source_url': detail_urls.get(c['id']), 'documents': c.get('documents', [])} for c in contracts]}
