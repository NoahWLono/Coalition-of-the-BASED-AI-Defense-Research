"""Conservative, offline accounting and review-gated procurement screening.

InputLot is an adapter contract, not the Prozorro API schema. All accounting
numbers arrive as strings. See ``example_lot()`` for a complete synthetic
example. Raw item and stage observations survive normalization. Only one active
``contract_current`` observation with explicit reviewed quantity linkage can
supply a purchase price; estimates, bids, awards and payments are not extra
purchases. A computed price is not evidence of economic comparability.

The caller is responsible for the truth of review assertions and evidence.
This module checks their explicit presence, not the source documents' meaning.
Human holdout labels are separate inputs and are never used in screening.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import json
import math
import re
from typing import Any, Literal, TypedDict


class Item(TypedDict, total=False):
    id: str
    description: str
    quantity: str | None
    unit: Literal['sheet', 'thousand_sheet', 'pack', 'thousand_pack'] | str
    unit_code: str | None
    unit_name: str | None
    unit_conflict: bool
    sheets_per_pack: str | None
    pack_size_reviewed: bool
    quantity_version: str | None
    bundled_services: bool


class Observation(TypedDict, total=False):
    id: str
    stage: Literal['estimate', 'bid', 'award', 'contract_current',
                   'amended_contract', 'payment_observed']
    amount: str | None
    currency: str | None
    status: str
    item_ids: list[str]
    quantity_version: str | None
    quantity_link_reviewed: bool
    amendment_reconciled: bool
    source_reference: str | None


class Review(TypedDict, total=False):
    annotator_type: Literal['assistant', 'independent_human', 'synthetic_fixture_author']
    reviewed: bool
    evidence: list[str]
    evidence_by_gate: dict[str, list[str]]
    spec_key: str | None
    fiscal_key: str | None
    delivery_key: str | None
    payment_key: str | None
    vat_included: bool | None
    net_gross_scope: Literal['net', 'gross'] | None


class InputLot(TypedDict, total=False):
    tender_id: str
    lot_id: str
    source_kind: Literal['real', 'synthetic']
    status: str
    publication_date: str | None
    items: list[Item]
    observations: list[Observation]
    review: Review
    source_url: str | None
    retrieved_at: str | None
    response_sha256: str | None
    extract_sha256: str | None


class HoldoutLabel(TypedDict, total=False):
    key: str
    annotator_type: Literal['independent_human', 'assistant', 'synthetic_fixture_author']
    evidence: list[str]
    comparable: bool
    unusual: bool | None


CONTRACT_VERSION = '1'
DECIMAL_PRECISION = 50
MIN_GROUP_SIZE = 5
MAD_THRESHOLD = Decimal('3.5')
RATIO_THRESHOLD = Decimal('1.5')
MODIFIED_Z_SCALE = Decimal('0.6744897501960817')
GATES = ('spec', 'quantity', 'fiscal', 'delivery', 'payment', 'stage')
# The optional spaces are thousands separators, never an alternative decimal mark.
_NUMBER = re.compile(r'^(?:[0-9]+|[0-9]{1,3}(?: [0-9]{3})+)(?:[.,][0-9]+)?$')


def example_lot() -> InputLot:
    """Return a fixture, explicitly not a real procurement or human review."""
    return {
        'tender_id': 'synthetic-example', 'lot_id': 'single',
        'source_kind': 'synthetic', 'status': 'active', 'publication_date': '2025-01-08',
        'items': [{'id': 'paper', 'description': 'A4 80 gsm 500-sheet pack',
                   'quantity': '100', 'unit': 'pack', 'sheets_per_pack': '500',
                   'pack_size_reviewed': True, 'quantity_version': 'current-v1'}],
        'observations': [{'id': 'contract-1', 'stage': 'contract_current',
                          'amount': '10000', 'currency': 'UAH', 'status': 'active',
                          'item_ids': ['paper'], 'quantity_version': 'current-v1',
                          'quantity_link_reviewed': True, 'amendment_reconciled': True}],
        'review': {'annotator_type': 'synthetic_fixture_author', 'reviewed': True,
                   'evidence': ['fixture:example'],
                   'evidence_by_gate': {gate: ['fixture:example'] for gate in GATES},
                   'spec_key': 'A4-80gsm-reviewed-grade-A', 'fiscal_key': 'gross-VAT20',
                   'vat_included': True, 'net_gross_scope': 'gross',
                   'delivery_key': 'delivered-terms-A', 'payment_key': 'postpay-30d'},
    }


def parse_decimal(value: Any) -> Decimal:
    """Parse a strictly positive decimal string without binary-float coercion."""
    if not isinstance(value, str):
        raise ValueError('accounting number must be an original decimal string')
    text = value.strip().replace('\u00a0', ' ').replace('\u202f', ' ')
    if len(text) > 200 or not _NUMBER.fullmatch(text):
        raise ValueError('invalid or ambiguous decimal')
    try:
        result = Decimal(text.replace(' ', '').replace(',', '.'))
    except InvalidOperation as exc:
        raise ValueError('invalid decimal') from exc
    if not result.is_finite() or result <= 0:
        raise ValueError('number must be positive and finite')
    return result


def _decimal_text(value: Decimal) -> str:
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _known(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in {
        '', 'unknown', 'unresolved', 'unspecified', 'none', 'null', 'n/a', '?'
    }


def _evidence(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_known(x) for x in value)


def _unique_ids(rows: list[dict], kind: str) -> None:
    seen: set[str] = set()
    for row in rows:
        ident = row.get('id')
        if not _known(ident):
            raise ValueError(f'{kind} id is required')
        if ident in seen:
            raise ValueError(f'duplicate {kind} id: {ident}')
        seen.add(ident)


def normalize_lot(lot: InputLot) -> dict[str, Any]:
    """Preserve source observations, compute safe arithmetic, then apply gates.

    ``comparison_eligible`` means the explicit review fields satisfy the
    contract; it does not itself certify independent real-world validation.
    ``unit_price`` uses Decimal at 50 significant digits. The accompanying
    numerator/denominator retains the exact rational price even for recurring
    decimal quotients. Exclusions are stable machine-readable reason codes.
    """
    if not _known(lot.get('tender_id')) or not _known(lot.get('lot_id')):
        raise ValueError('tender_id and lot_id are required')
    items = lot.get('items', [])
    observations = lot.get('observations', [])
    _unique_ids(items, 'item')
    _unique_ids(observations, 'observation')
    reasons: list[str] = []
    def reject(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    result: dict[str, Any] = deepcopy(lot)
    result.update({
        'contract_version': CONTRACT_VERSION,
        'key': lot['tender_id'] + '/' + lot['lot_id'],
        'items': deepcopy(items), 'observations': deepcopy(observations),
        'quantity_sheets': None, 'amount': None, 'currency': None,
        'unit_price': None, 'unit_price_fraction': None,
        'selected_observation_id': None, 'selected_stage': None,
        'comparison_eligible': False, 'group_key': None,
        'arithmetic_status': 'unavailable', 'review_status': 'unreviewed',
        'exclusion_reasons': reasons,
    })
    source_kind = lot.get('source_kind')
    if lot.get('lot_link_conflict') is True:
        reject('lot_link_conflict')
    if lot.get('current_contract_state_unavailable') is True:
        reject('current_contract_state_unavailable')
    if source_kind not in {'real', 'synthetic'}:
        reject('source_kind_unknown')
    status = lot.get('status')
    if status in {'cancelled', 'canceled', 'unsuccessful'}:
        reject('lot_cancelled')
    elif status not in {'active', 'complete', 'completed'}:
        reject('lot_status_unknown')

    item: Item | None = None
    quantity: Decimal | None = None
    if len(items) != 1:
        reject('multiple_items' if len(items) > 1 else 'items_missing')
    else:
        item = items[0]
        if item.get('bundled_services') is True:
            reject('bundled_services')
        unit = item.get('unit')
        try:
            raw_quantity = parse_decimal(item.get('quantity'))
        except ValueError:
            raw_quantity = None
            reject('quantity_invalid')
        factor: Decimal | None = None
        if item.get('unit_conflict') is True:
            reject('unit_conflict')
        elif unit == 'sheet':
            factor = Decimal('1')
        elif unit == 'thousand_sheet':
            factor = Decimal('1000')
        elif unit in {'pack', 'thousand_pack'}:
            if item.get('pack_size_reviewed') is not True:
                reject('pack_size_unreviewed')
            else:
                try:
                    factor = parse_decimal(item.get('sheets_per_pack'))
                    if factor != factor.to_integral_value():
                        raise ValueError('pack size must be whole sheets')
                    if unit == 'thousand_pack':
                        with localcontext() as ctx:
                            ctx.prec = 500
                            factor *= Decimal('1000')
                except ValueError:
                    factor = None
                    reject('pack_size_invalid')
        else:
            reject('unit_unresolved')
        if raw_quantity is not None and factor is not None:
            # Input digit limits bound the exact product precision requirement.
            with localcontext() as ctx:
                ctx.prec = 500
                quantity = raw_quantity * factor
            result['quantity_sheets'] = _decimal_text(quantity)

    active = [obs for obs in observations if obs.get('stage') == 'contract_current'
              and obs.get('status') == 'active']
    selected: Observation | None = None
    amount: Decimal | None = None
    linkage_ok = False
    if len(active) != 1:
        reject('multiple_active_current_contracts' if active else 'no_active_current_contract')
    else:
        selected = active[0]
        result['selected_observation_id'] = selected['id']
        result['selected_stage'] = selected['stage']
        result['currency'] = selected.get('currency')
        try:
            amount = parse_decimal(selected.get('amount'))
            result['amount'] = _decimal_text(amount)
        except ValueError:
            reject('amount_invalid')
        linkage_ok = True
        if lot.get('lot_link_conflict') or lot.get('current_contract_state_unavailable'):
            linkage_ok = False
        if item is None or selected.get('item_ids') != [item['id']]:
            reject('item_link_unresolved')
            linkage_ok = False
        if selected.get('quantity_link_reviewed') is not True:
            reject('quantity_link_unreviewed')
            linkage_ok = False
        if item is None or not _known(item.get('quantity_version')) or not _known(selected.get('quantity_version')):
            reject('quantity_version_unknown')
            linkage_ok = False
        elif item['quantity_version'] != selected['quantity_version']:
            reject('quantity_version_mismatch')
            linkage_ok = False
        if selected.get('amendment_reconciled') is not True:
            reject('amendment_unreconciled')
            linkage_ok = False
        if item is not None and item.get('bundled_services') is True:
            linkage_ok = False
        if amount is not None and quantity is not None and linkage_ok:
            with localcontext() as ctx:
                ctx.prec = DECIMAL_PRECISION
                unit_price = amount / quantity
            exact = Fraction(amount) / Fraction(quantity)
            result['unit_price'] = _decimal_text(unit_price)
            result['unit_price_fraction'] = {'numerator': str(exact.numerator),
                                             'denominator': str(exact.denominator)}
            result['arithmetic_status'] = 'computed'

    review: Review = lot.get('review') or {}
    if selected is not None and isinstance(selected.get('vat_included'), bool) and selected['vat_included'] != review.get('vat_included'):
        reject('fiscal_source_conflict')
    annotator = review.get('annotator_type')
    if review.get('reviewed') is not True:
        reject('review_unapproved')
    if source_kind == 'real':
        if annotator != 'independent_human':
            reject('independent_human_review_required')
            result['review_status'] = 'provisional' if annotator == 'assistant' else 'unreviewed'
        else:
            result['review_status'] = 'independent_human_asserted'
    elif source_kind == 'synthetic':
        if annotator != 'synthetic_fixture_author':
            reject('synthetic_fixture_review_required')
        else:
            result['review_status'] = 'synthetic_expectation'
    evidence_by_gate = review.get('evidence_by_gate') or {}
    for gate in GATES:
        if not _evidence(evidence_by_gate.get(gate)):
            reject(f'{gate}_evidence_missing')
    for field, reason in [('spec_key', 'specification_unknown'), ('delivery_key', 'delivery_unknown'),
                          ('payment_key', 'payment_unknown')]:
        if not _known(review.get(field)):
            reject(reason)
    if not _known(review.get('fiscal_key')) or not isinstance(review.get('vat_included'), bool) or review.get('net_gross_scope') not in {'net', 'gross'}:
        reject('fiscal_unknown')
    currency = result['currency']
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
        reject('currency_unknown')
    elif source_kind == 'real' and currency != 'UAH':
        reject('currency_out_of_scope')
    publication_month = None
    try:
        publication = lot.get('publication_date')
        if not isinstance(publication, str):
            raise ValueError('publication date is missing')
        publication_month = date.fromisoformat(publication[:10]).isoformat()[:7]
    except (ValueError, TypeError):
        reject('publication_date_unknown')
    result['publication_month'] = publication_month
    if quantity is None:
        volume_band = None
    elif quantity < Decimal('50000'):
        volume_band = 'lt_50000'
    elif quantity < Decimal('500000'):
        volume_band = '50000_to_499999'
    else:
        volume_band = 'gte_500000'
    result['volume_band'] = volume_band
    if result['unit_price'] is None:
        reject('price_unavailable')
    if not reasons:
        result['comparison_eligible'] = True
        result['group_key'] = {
            'source_kind': source_kind, 'spec_key': review['spec_key'], 'currency': currency,
            'fiscal_key': review['fiscal_key'], 'vat_included': review['vat_included'],
            'net_gross_scope': review['net_gross_scope'], 'delivery_key': review['delivery_key'],
            'payment_key': review['payment_key'], 'stage': result['selected_stage'],
            'publication_month': publication_month, 'volume_band': volume_band,
        }
    return result


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / Decimal('2')


def _check_record_keys(records: list[dict]) -> None:
    seen: set[str] = set()
    for record in records:
        key = record.get('key')
        if not _known(key):
            raise ValueError('normalized lot key is required')
        if key in seen:
            raise ValueError(f'duplicate lot key: {key}')
        seen.add(key)


def _run_screen(records: list[dict], z_threshold: Decimal, ratio_threshold: Decimal) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record.get('comparison_eligible') is True:
            if not record.get('group_key') or record.get('unit_price') is None:
                raise ValueError('eligible normalized record lacks group or price')
            # Source kind is an independent isolation boundary, even for imported records.
            grouping = dict(record['group_key'], source_kind=record.get('source_kind'))
            grouped[json.dumps(grouping, ensure_ascii=False, sort_keys=True)].append(record)
    groups, leads = [], []
    statuses: dict[str, dict] = {record['key']: {'status': 'excluded', 'is_lead': False} for record in records}
    screened_count = 0
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        for signature in sorted(grouped):
            group_records = sorted(grouped[signature], key=lambda record: record['key'])
            prices = [parse_decimal(record['unit_price']) for record in group_records]
            med = _median(prices)
            mad = _median([abs(value - med) for value in prices])
            group = {'group_key': json.loads(signature), 'size': len(group_records),
                     'keys': [record['key'] for record in group_records],
                     'median': _decimal_text(med), 'mad': _decimal_text(mad),
                     'mad_degenerate': mad == 0,
                     'status': 'screened' if len(group_records) >= MIN_GROUP_SIZE else 'too_small'}
            groups.append(group)
            for record, price in zip(group_records, prices):
                if len(group_records) < MIN_GROUP_SIZE:
                    statuses[record['key']] = {'status': 'too_small', 'is_lead': False}
                    continue
                screened_count += 1
                ratio = price / med
                score = abs(MODIFIED_Z_SCALE * (price - med) / mad) if mad != 0 else None
                ratio_extreme = ratio > ratio_threshold or ratio < Decimal('1') / ratio_threshold
                is_lead = ratio_extreme and (mad == 0 or score > z_threshold)
                finding = {'key': record['key'], 'status': 'screened', 'is_lead': is_lead,
                           'unit_price': _decimal_text(price), 'median': _decimal_text(med),
                           'mad': _decimal_text(mad), 'ratio_to_median': _decimal_text(ratio),
                           'modified_z': _decimal_text(score) if score is not None else None,
                           'method': 'zero_mad_ratio_only' if mad == 0 else 'median_mad_and_ratio',
                           'direction': ('high' if price > med else 'low') if is_lead else None,
                           'source_kind': record.get('source_kind')}
                statuses[record['key']] = finding
                if is_lead:
                    leads.append(finding)
    return {'groups': groups, 'leads': sorted(leads, key=lambda value: value['key']),
            'records': [dict(deepcopy(record), screening=statuses[record['key']])
                        for record in sorted(records, key=lambda value: value['key'])],
            'counts': {'unique_lots': len(records),
                       'arithmetic_computable': sum(record.get('unit_price') is not None for record in records),
                       'comparison_eligible': sum(record.get('comparison_eligible') is True for record in records),
                       'excluded_lots': sum(record.get('comparison_eligible') is not True for record in records),
                       'screened_lots': screened_count, 'leads': len(leads),
                       'real_leads': sum(lead['source_kind'] == 'real' for lead in leads),
                       'synthetic_leads': sum(lead['source_kind'] == 'synthetic' for lead in leads)}}


def screen(records: list[dict]) -> dict[str, Any]:
    """Screen normalized records. A lead is a review prompt, never corruption.

    A group needs at least five distinct lot keys. For positive MAD, both
    |0.6744897501960817 * (price - median) / MAD| > 3.5 and a strict price ratio
    > 1.5 or < 1/1.5 are required. With zero MAD only the same strict ratio
    threshold applies, explicitly labeled as a degenerate baseline. Threshold
    equality does not flag. Sensitivity reports all nine specified pairs.
    """
    _check_record_keys(records)
    result = _run_screen(records, MAD_THRESHOLD, RATIO_THRESHOLD)
    result['algorithm'] = {
        'minimum_group_size': MIN_GROUP_SIZE, 'modified_z_threshold': str(MAD_THRESHOLD),
        'ratio_threshold': str(RATIO_THRESHOLD), 'two_sided': True,
        'threshold_comparison': 'strict', 'zero_mad_policy': 'ratio_only_labeled_degenerate',
        'decimal_precision': DECIMAL_PRECISION,
        'interpretation': 'Review leads only; no inference of corruption or fraud.',
    }
    result['sensitivity'] = []
    for z in ['3', '3.5', '4']:
        for ratio in ['1.3', '1.5', '2']:
            rerun = _run_screen(records, Decimal(z), Decimal(ratio))
            result['sensitivity'].append({'modified_z_threshold': z, 'ratio_threshold': ratio,
                                          'lead_count': len(rerun['leads']),
                                          'lead_keys': [row['key'] for row in rerun['leads']]})
    return result


def _binomial_metric(numerator: int, denominator: int) -> dict:
    if denominator == 0:
        return {'numerator': numerator, 'denominator': 0, 'estimate': None, 'wilson_95': None}
    # Statistical intervals are dimensionless, not monetary accounting.
    p = numerator / denominator
    z = 1.959963984540054
    z2 = z * z
    divisor = 1 + z2 / denominator
    center = (p + z2 / (2 * denominator)) / divisor
    radius = z * math.sqrt((p * (1 - p) + z2 / (4 * denominator)) / denominator) / divisor
    return {'numerator': numerator, 'denominator': denominator, 'estimate': p,
            'wilson_95': [max(0.0, center - radius), min(1.0, center + radius)]}


def evaluate(records: list[dict], labels: list[HoldoutLabel]) -> dict[str, Any]:
    """Evaluate independent real holdout labels without feeding them to screen.

    Precision: true unusual comparable leads / all independently labeled leads.
    False-lead proportion: labeled leads that are ordinary OR incomparable / all
    labeled leads. FPR: flagged ordinary comparable records / screened ordinary
    comparable records. False exclusion: gate-excluded comparable records / all
    human-labeled comparable records. Small groups are unscreened, not exclusions.
    Labels for synthetic data or without independent human evidence are ignored.
    Wilson intervals describe these labeled records; convenience sampling does
    not make them representative population estimates.
    """
    screened = screen(records)
    by_key = {record['key']: record for record in screened['records']}
    seen: set[str] = set()
    accepted, ignored = [], []
    for label in labels:
        key = label.get('key')
        if key not in by_key:
            raise ValueError(f'holdout label references unknown lot: {key}')
        if key in seen:
            raise ValueError(f'duplicate holdout label: {key}')
        seen.add(key)
        record = by_key[key]
        if record.get('source_kind') != 'real':
            ignored.append({'key': key, 'reason': 'synthetic_not_real_validation'})
        elif label.get('annotator_type') != 'independent_human' or not _evidence(label.get('evidence')):
            ignored.append({'key': key, 'reason': 'independent_evidence_required'})
        elif not isinstance(label.get('comparable'), bool) or (label['comparable'] and not isinstance(label.get('unusual'), bool)):
            ignored.append({'key': key, 'reason': 'label_incomplete'})
        else:
            accepted.append((record, label))
    labeled_leads = [(r, label) for r, label in accepted if r['screening']['is_lead']]
    true_leads = sum(label['comparable'] and label.get('unusual') is True for _, label in labeled_leads)
    screened_ordinary = [(r, label) for r, label in accepted
                         if r['screening']['status'] == 'screened'
                         and label['comparable'] and label.get('unusual') is False]
    comparable = [(r, label) for r, label in accepted if label['comparable']]
    metrics = {
        'precision': _binomial_metric(true_leads, len(labeled_leads)),
        'false_lead_proportion': _binomial_metric(len(labeled_leads) - true_leads, len(labeled_leads)),
        'false_positive_rate': _binomial_metric(sum(r['screening']['is_lead'] for r, _ in screened_ordinary), len(screened_ordinary)),
        'false_exclusion_rate': _binomial_metric(sum(r.get('comparison_eligible') is not True for r, _ in comparable), len(comparable)),
    }
    return {'accepted_label_count': len(accepted), 'ignored_labels': ignored,
            'metrics': metrics,
            'validation_gate_met': bool(accepted) and all(value['denominator'] > 0 for value in metrics.values()),
            'validation_scope': 'Labeled holdout records only; no representative population claim.',
            'limitations': ['Independent human labels are required for empirical error rates.',
                            'Synthetic expectations and assistant reviews do not validate real comparability.',
                            'Wilson intervals do not correct selection bias or reviewer error.'],
            'counts': {'labeled_leads': len(labeled_leads), 'labeled_comparable': len(comparable),
                       'labeled_screened_ordinary': len(screened_ordinary)}}
