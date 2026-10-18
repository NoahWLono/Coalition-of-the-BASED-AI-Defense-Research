"""Deterministic documentary assessment; no model has policy or approval authority."""
from collections import Counter
from .ingest import ledger, current_assertions, undated_assertions
from .costs import calculate_cost, DEFAULTS
from .scoring import normalize_score, score_package, sensitivity, dominance, PROFILES
from .assurance import software_assurance


def assess(requirement, assertions, package_id, as_of):
    r=requirement
    all_a=[a for a in assertions if a['key']==r['id'] and a['package_id']==package_id]
    result={'requirement_id':r['id'],'state':'unresolved','reason':'No matching evidence supplied.',
        'assertions':[a['id'] for a in all_a], 'score_low':0,'score_high':100}
    def state(s,reason):
        result.update(state=s,reason=reason);return result
    if '*' not in r['applies_to'] and package_id not in r['applies_to']:
        return state('not_applicable',r.get('na_reason') or 'Configuration is outside the requirement applicability list.')
    if r['effective']>as_of or (r.get('expires') and r['expires']<as_of):
        return state('stale','Requirement is not effective on the declared evaluation date.')
    active=current_assertions(all_a,as_of)
    if not active:
        rejected=[a for a in all_a if a['review_status']=='rejected']
        if rejected:return state('unresolved','Relevant evidence was rejected by a technical reviewer; replacement evidence required.')
        if any(a['unresolved_interpretation'] for a in all_a):return state('unresolved','Evidence cannot be interpreted safely.')
        return state('stale' if all_a else 'unresolved','All matching evidence is expired, future-dated or superseded.' if all_a else 'No matching evidence supplied.')
    known=[a for a in active if a['value'] is not None and not a['unresolved_interpretation']]
    values={(str(a['value']),a['normalized_unit']) for a in known}
    if len(values)>1:
        return state('conflicting','Current sources disagree; a reviewer must reconcile them before relying on this value.')
    if len(known)!=len(active) or undated_assertions(all_a):
        return state('unresolved','At least one current assertion has an unresolved value or interpretation.')
    accepted=[a for a in known if a['evidence_type'] in r['evidence_types']]
    if not accepted:
        return state('unresolved','Supplier assertion does not provide the required evidence type: '+', '.join(r['evidence_types'])+'.')
    if any(a['normalized_unit']!=r['unit'] for a in accepted):
        return state('unresolved',f'Unit is ambiguous or incompatible; requirement uses {r["unit"]}.')
    value=accepted[0]['value']
    comparator=r['comparator']
    if comparator in {'gte','lte'} and not isinstance(value,(int,float)):
        return state('unresolved','A numeric comparison requires an interpretable numeric value.')
    if comparator=='present': passed=value is not None and str(value).strip()!=''
    elif comparator=='gte': passed=value>=r['target']
    elif comparator=='lte': passed=value<=r['target']
    elif comparator=='eq': passed=value==r['target']
    else:raise ValueError('Unsupported comparator')
    if r['mode']=='scored' and r.get('scoring') and isinstance(value,(int,float)):
        score=normalize_score(value,r);result.update(score_low=score,score_high=score)
    result['value']=value
    return state('supported' if passed else 'not_satisfied',
        'Required documentary evidence supports the stated comparison. This is not a field-performance certification.' if passed else f'Documented value {value} does not satisfy {comparator} {r["target"]}.')


def evaluate(inputs, assumptions=None, profile='balanced', as_of='2026-10-17', reviews=None):
    if profile not in PROFILES:raise ValueError('Unknown preference profile')
    requirements=inputs['requirements']
    assertions=ledger(inputs,reviews)
    suppliers={s['id']:s['name'] for s in inputs['suppliers']}
    packages=[];questions=[]
    for p in sorted(inputs['packages'],key=lambda x:x['id']):
        aa=[a for a in assertions if a['package_id']==p['id']]
        assessments=[assess(r,aa,p['id'],as_of) for r in requirements]
        required=[a for a,r in zip(assessments,requirements) if r['mode']=='mandatory']
        eligible=all(a['state'] in {'supported','not_applicable'} for a in required)
        costs=calculate_cost(aa,assumptions or {},as_of)
        package=dict(p,supplier_name=suppliers[p['supplier_id']],eligible=eligible,
            mandatory_counts=dict(Counter(a['state'] for a in required)),assessments=assessments,
            cost=costs,score=score_package(requirements,assessments,profile),assurance=software_assurance(inputs,p['id'],aa,as_of))
        packages.append(package)
        for a,r in zip(assessments,requirements):
            if a['state'] in {'supported','not_applicable'}:continue
            questions.append(dict(id=f'{p["id"]}-{r["id"]}',package_id=p['id'],supplier_id=p['supplier_id'],
                requirement_id=r['id'],priority=1 if r['mode']=='mandatory' else 3,
                question=f'Please provide or reconcile {r["wording"]}',missing=a['reason'],
                consequence='Prevents unconditional documentary eligibility.' if r['mode']=='mandatory' else 'Could change the preference interval or informational completeness.',
                assertions=a['assertions']))
        for exposure in costs['open_exposures']:
            questions.append(dict(id=f'{p["id"]}-{exposure["key"]}',package_id=p['id'],supplier_id=p['supplier_id'],
                requirement_id=exposure['key'],priority=2,question='Please provide a firm CAD quotation for '+exposure['label']+'.',
                missing=exposure['reason'],consequence='Known subtotal is incomplete and has no finite upper bound.',assertions=exposure['assertions']))
        for issue in package['assurance']:
            if issue['disposition'] in {'affected','unresolved'}:
                questions.append(dict(id=f'{p["id"]}-{issue["id"]}',package_id=p['id'],supplier_id=p['supplier_id'],
                    requirement_id=issue['id'],priority=2,question='Please resolve '+issue.get('title',issue['id'])+' and supply application exposure evidence.',
                    missing=issue['reason'],consequence=issue['consequence'],assertions=issue.get('assertions',[])))
    return dict(as_of=as_of,requirements=requirements,packages=packages,assertions=assertions,
        documents=[{k:v for k,v in d.items() if k!='content'} for d in sorted(inputs['documents'],key=lambda d:d['id'])],
        clarifications=sorted(questions,key=lambda q:(q['priority'],q['id'])),
        sensitivity=sensitivity(packages,requirements),dominance=dominance(packages),profiles=PROFILES,
        profile=profile,assumptions=dict(DEFAULTS,**(assumptions or {})),
        limitations=['All supplier data, test reports and advisories are synthetic.',
        'Documentary eligibility is eligibility for further consideration, not purchase authorization or verified field capability.',
        'Extraction supports three labelled UTF-8 text layouts; OCR, arbitrary PDFs and live model evaluation are unperformed.'])
