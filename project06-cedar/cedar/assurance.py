"""Offline CycloneDX 1.6 validation and exact synthetic advisory matching."""
import json
from pathlib import Path
from functools import lru_cache
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from .ingest import current_assertions, undated_assertions

VENDOR=Path(__file__).resolve().parent.parent/'vendor'


@lru_cache(maxsize=1)
def validator():
    resources=[]
    for p in VENDOR.glob('*.schema.json'):
        schema=json.loads(p.read_text())
        resource=Resource.from_contents(schema)
        resources.extend([(f'http://cyclonedx.org/schema/{p.name}',resource),
                          (f'https://cyclonedx.org/schema/{p.name}',resource)])
    registry=Registry().with_resources(resources)
    schema=json.loads((VENDOR/'bom-1.6.schema.json').read_text())
    return Draft7Validator(schema,registry=registry)


def inventory_errors(inventory):
    return [e.message for e in validator().iter_errors(inventory)]


def software_assurance(inputs,package_id,assertions,as_of):
    sources=inputs.get('structured',{})
    name=f'inventory/{package_id}.cdx.json'
    if name not in sources:
        return [{'id':'INVENTORY-MISSING','disposition':'unresolved','reason':'No inventory provided.','consequence':'Request a versioned software inventory before technical review.'}]
    inv=json.loads(sources[name]['content'])
    errors=inventory_errors(inv)
    if errors:
        return [{'id':'INVENTORY-INVALID','disposition':'unresolved','reason':'; '.join(errors),
            'inventory_hash':sources[name]['hash'],'consequence':'Request a schema-valid CycloneDX 1.6 inventory.'}]
    advisories=json.loads(sources.get('advisories.json',{}).get('content','[]'))
    exposures=json.loads(sources.get('assurance.json',{}).get('content','{}')).get(package_id,[])
    current=current_assertions(assertions,as_of)
    undated=undated_assertions(assertions)
    results=[]
    for comp in inv.get('components',[]):
        if not comp.get('version') or not comp.get('purl'):
            evidence=[a for a in current if a['key'].startswith('A_')]
            results.append(dict(id='INVENTORY-IDENTITY-'+comp.get('bom-ref',comp['name']),
                title='Unresolved component identity',component=comp['name'],version=comp.get('version'),
                purl=comp.get('purl'),disposition='unresolved',reason='Component identity or version is missing; absence of an advisory match cannot establish unaffected status.',
                inventory_source=name,inventory_hash=sources[name]['hash'],assertions=[a['id'] for a in evidence],
                consequence='Request component identity, version and a complete inventory before relying on advisory matching.',
                limitation='Synthetic inventory; completeness and deployed binaries are not verified.'))
        for advisory in advisories:
            base=advisory.get('purl','').rsplit('@',1)[0]
            matches_identity=bool(comp.get('purl')) and comp['purl'].rsplit('@',1)[0]==base
            if comp['name']!=advisory['component'] and not matches_identity:
                continue
            identity=bool(comp.get('version')) and comp.get('purl')==base+'@'+comp['version'] and base.startswith('pkg:generic/')
            exposure=next((x for x in exposures if x['advisory_id']==advisory['id']),None)
            evidence=[a for a in current if exposure and a['document_id']==exposure['document_id'] and a['key']==exposure['key']]
            uncertain=[a for a in undated if exposure and a['package_id']==package_id and a['key']==exposure['key']]
            if advisory['published']>as_of:
                status='unresolved'; reason='Advisory was not published by the declared evaluation date.'
            elif not identity:
                status='unresolved'; reason='Component identity or version is incomplete. Name similarity is insufficient.'
            elif comp['version'] in advisory['fixed_versions']:
                status='fixed'; reason='Declared exact component version is listed as fixed in the synthetic advisory; not a deployed-build verification.'
            elif comp['version'] not in advisory['affected_versions']:
                status='unresolved'; reason='Version is outside the exact affected/fixed lists; no range inference is made.'
            elif uncertain:
                status='unresolved'; reason='Application exposure evidence has missing or invalid validity dates; its applicability cannot be established.'
            elif exposure and any(a['key']==exposure['key'] and (a['unresolved_interpretation'] or str(a['value'])!=exposure['status']) for a in current):
                status='unresolved'; reason='Current application exposure declarations conflict or remain uninterpretable.'
            elif not evidence or not exposure:
                status='unresolved'; reason='Affected component is declared, but application exposure evidence is missing or no longer current.'
            elif exposure['status'] in {'affected','unaffected'} and all(str(a['value'])==exposure['status'] for a in evidence):
                status=exposure['status']; reason=exposure['rationale']
            else:
                status='unresolved'; reason='Component is listed as affected; exposure disposition is unresolved or contradicts source.'
            results.append(dict(id=advisory['id'],title=advisory['title'],component=comp['name'],version=comp.get('version'),
                purl=comp.get('purl'),disposition=status,reason=reason,published=advisory['published'],source=advisory['source'],
                inventory_source=name,inventory_hash=sources[name]['hash'],advisory_hash=sources['advisories.json']['hash'],
                assertions=[a['id'] for a in evidence+uncertain],
                consequence='Require a documented remediation or support commitment before procurement proceeds.' if status in {'affected','unresolved'} else 'Preserve evidence and confirm shipped inventory during a pilot.',
                limitation='Synthetic advisory and supplier-declared inventory. Completeness, deployed binaries and field exposure have not been independently verified.'))
    return results
