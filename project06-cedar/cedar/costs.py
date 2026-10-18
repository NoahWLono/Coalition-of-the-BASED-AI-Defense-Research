"""Quoted CAD amounts and explicit planning assumptions, using decimal arithmetic."""
from decimal import Decimal, ROUND_HALF_UP
from .ingest import current_assertions, undated_assertions

DEFAULTS = {'years':3, 'replacements_per_aircraft_per_year':1, 'include_optional':False}
CATEGORIES = {'C_aircraft':'Aircraft × 6','C_ground':'Shared ground equipment',
    'C_software':'Required software / year','C_training':'Initial training',
    'C_support':'Fleet support / year','C_battery':'Replacement battery / unit',
    'C_optional':'Optional equipment','C_escalation':'Annual recurring escalation',
    'C_required':'Required additional components'}


def money(x):
    return float(x.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def calculate_cost(assertions, assumptions, as_of):
    assumptions = dict(DEFAULTS, **assumptions)
    years = assumptions['years']; rate = Decimal(str(assumptions['replacements_per_aircraft_per_year']))
    active = current_assertions(assertions,as_of)
    quoted, lines, exposures = {}, [], []
    for key,label in CATEGORIES.items():
        evidence = [a for a in active if a['key']==key]
        values = {str(a['value']) for a in evidence}
        good = evidence and not [a for a in undated_assertions(assertions) if a['key']==key] and len(values)==1 and all(isinstance(a['value'],(float,int)) and a['value']>=0
            and a['normalized_unit']==('pct' if key=='C_escalation' else 'CAD')
            and a['evidence_type']=='quotation' and not a['unresolved_interpretation'] for a in evidence)
        if good:
            quoted[key] = Decimal(str(evidence[0]['value']))
        elif key!='C_optional' or assumptions['include_optional']:
            exposures.append({'key':key,'label':label,'reason':'Missing, conflicting, expired or uninterpretable quoted value; amount is open.',
                'assertions':[a['id'] for a in assertions if a['key']==key]})
        lines.append({'key':key,'label':label,'quoted_value':float(quoted[key]) if key in quoted else None,
            'unit':'pct' if key=='C_escalation' else 'CAD','assertions':[a['id'] for a in evidence]})
    get = lambda k: quoted.get(k,Decimal(0))
    fixed = 6*get('C_aircraft')+get('C_ground')+get('C_training')+get('C_required')
    recurring = get('C_software')+get('C_support')
    # With unknown escalation, only the first year's recurring amount is known.
    annual = [recurring*(1+get('C_escalation')/100)**t for t in range(years)] if 'C_escalation' in quoted else [recurring]
    replacements=Decimal(6*years)*rate*get('C_battery')
    total=fixed+sum(annual)+replacements+(get('C_optional') if assumptions['include_optional'] else 0)
    return dict(currency='CAD',known_total=money(total),upper_total=None if exposures else money(total),
        open_exposures=exposures,lines=lines,assumptions=assumptions,
        breakdown={'initial':money(fixed),'recurring_by_year':[money(x) for x in annual],
                   'replacement_assumption':money(replacements),'optional':money(get('C_optional')) if assumptions['include_optional'] else 0},
        interpretation='Undiscounted, pre-tax known subtotal. Open exposures have no finite upper bound. Replacement quantity is an illustrative planning assumption; escalation is quoted.')
