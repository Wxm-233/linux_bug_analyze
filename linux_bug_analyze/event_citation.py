"""Check cited event locations against an external registry, not source semantics."""
from pathlib import Path
import hashlib


def check_event_citations(candidate, citations, registry, documents):
    result = dict(status='insufficient', semantic_authority_established=False,
                  deadline_evidence_established=False, matches=[], issues=[])
    if (registry.get('origin') != 'researcher_registered' or
            registry.get('interface_id') != candidate.get('interface_id') or
            registry.get('revision') != candidate['contract']['revision']):
        result['issues'].append('registry identity or origin mismatch')
        return result
    events=registry['events'];target=candidate['deadline_event']
    if target not in events:
        result['issues'].append('unknown declared event');return result
    # Validate all anchors against the separately pinned document bytes.
    normalize=lambda s:' '.join(s.split())
    for label,anchor in events.items():
        doc=documents[anchor['document']]
        raw=Path(doc['path']).read_bytes();lines=raw.decode('utf-8-sig').splitlines()
        lo,hi=anchor['start_line'],anchor['end_line']
        if (doc['revision']!=registry['revision'] or
                hashlib.sha256(raw).hexdigest()!=doc['sha256'] or
                not 1<=lo<=hi<=len(lines) or
                normalize(anchor['quote']) not in normalize('\n'.join(lines[lo-1:hi]))):
            result['issues'].append('unverified registry anchor: '+label);return result
    refs=[r for r in citations if r['supports']=='deadline_event']
    if not refs:result['issues'].append('no deadline citation')
    for ref in refs:
        labels=[label for label,a in events.items()
                if ref['document']==a['document'] and
                ref['start_line']<=a['start_line']<=a['end_line']<=ref['end_line'] and
                normalize(a['quote']) in normalize(ref['quote'])]
        result['matches'].append(dict(citation=ref,registered_events=labels))
        if labels!=[target]:result['issues'].append('citation does not uniquely support declared event')
    if refs and not result['issues']:result['status']='registered_event_location_matches'
    return result
