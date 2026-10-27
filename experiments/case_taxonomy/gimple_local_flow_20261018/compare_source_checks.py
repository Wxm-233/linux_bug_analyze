"""Compare frozen source-truth checks to previously computed local facts.

No expected field is an input to the analyzer. Counts are development/source
fidelity checks, not accuracy, new Linux cases or interface-obligation proof.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(value):
    return str(value).strip().removesuffix(':').strip().removeprefix('<').removesuffix('>')


def selected(analysis, selector):
    rows = []
    selector = selector or {}
    for event in analysis.get('events', []):
        kinds = selector.get('kind')
        if kinds is not None and event.get('kind') not in ([kinds] if isinstance(kinds, str) else kinds):
            continue
        if ('source_line' in selector or 'source_path' in selector) and not any(
                ('source_line' not in selector or loc.get('line') == selector['source_line']) and
                ('source_path' not in selector or loc.get('path') == selector['source_path'])
                for loc in event.get('source_locations', [])):
            continue
        if 'local_line' in selector and not (event.get('dump_line_start', -1) <= selector['local_line'] <= event.get('dump_line_end', -1)):
            continue
        contains = selector.get('code_contains', [])
        if isinstance(contains, str):
            contains = [contains]
        if not all(text in event.get('code', '') for text in contains):
            continue
        field = event.get('field') or {}
        if 'field' in selector and field.get('field') != selector['field']:
            continue
        if 'field_not_in' in selector and (not field or field.get('field') in selector['field_not_in']):
            continue
        if 'callee' in selector and (event.get('call') or {}).get('callee') != selector['callee']:
            continue
        rows.append(event)
    return rows


def relevant_opaque(analysis, selector):
    scope = {key: value for key, value in (selector or {}).items() if key in {'source_line', 'source_path', 'local_line'}}
    return [event['id'] for event in selected(analysis, scope) if event.get('kind') == 'opaque']


def dependency_state(analysis, definition, use, variable=None):
    """Walk only recorded region-bounded definition edges; never infer CFG."""
    edges = analysis.get('dependencies', [])
    region = use.get('region')
    pending = [use['id']]
    seen = set()
    while pending:
        event_id = pending.pop()
        if event_id in seen:
            continue
        seen.add(event_id)
        incoming = [e for e in edges if e.get('use_event') == event_id and e.get('region') == region]
        if event_id == use['id'] and variable is not None:
            incoming = [e for e in incoming if e.get('variable') == variable]
        for edge in incoming:
            if edge.get('definition_event') == definition['id']:
                return 'supported', {'path_events_visited': sorted(seen), 'terminal_edge': edge}
            pending.append(edge.get('definition_event'))
    relevant_variables = {variable} if variable is not None else set(definition.get('defines', []))
    unresolved = [row for row in analysis.get('unresolved_uses', [])
                  if row.get('use_event') == use['id'] and
                  row.get('variable') in relevant_variables]
    if unresolved:
        return 'unresolved', {'unresolved_uses': unresolved}
    return 'not_established', {'reason': 'No recorded chain and no explicit relevant unresolved use.'}


def evaluate(check, analysis):
    answer = {'id': check['id'], 'profile': check['profile'], 'op': check['op'],
              'status': 'insufficient', 'expected': check['expected']}
    if analysis.get('status') != 'partial_local_facts':
        return {**answer, 'reason': 'Source did not yield a bounded local fact packet.'}
    for selector_name in ('selector', 'def_selector', 'use_selector', 'from_selector'):
        selector = check.get(selector_name, {})
        if 'source_line' in selector and 'source_path' not in selector:
            paths = {loc.get('path') for event in selected(analysis, selector)
                     for loc in event.get('source_locations', []) if loc.get('line') == selector['source_line']}
            if len(paths) > 1:
                return {**answer, 'reason': 'A source line selector spans multiple source paths.'}
    expected = check['expected']
    if check['op'] == 'event_count':
        events = selected(analysis, check.get('selector'))
        actual = len(events)
        answer.update(actual={'count': actual}, event_ids=[e['id'] for e in events])
        opaque = relevant_opaque(analysis, check.get('selector'))
        if opaque and actual <= expected['count']:
            return {**answer, 'reason': 'Relevant opaque spans prevent complete count certification.', 'opaque': opaque}
        answer['status'] = 'match' if actual == expected['count'] else 'mismatch'
    elif check['op'] == 'dependency':
        definitions = selected(analysis, check['def_selector'])
        uses = selected(analysis, check['use_selector'])
        if len(definitions) != 1 or len(uses) != 1:
            return {**answer, 'reason': 'Definition/use anchors must each resolve uniquely.',
                    'definition_anchors': len(definitions), 'use_anchors': len(uses)}
        state, evidence = dependency_state(analysis, definitions[0], uses[0], check.get('variable'))
        answer.update(actual={'relation': state}, evidence=evidence)
        if state == 'not_established':
            return {**answer, 'reason': 'No support or explicit unresolved evidence for this relation.'}
        if state == 'unresolved' and expected['relation'] == 'supported':
            return {**answer, 'reason': 'Expected local connection is not established by the method.'}
        answer['status'] = 'match' if state == expected['relation'] else 'mismatch'
    elif check['op'] == 'explicit_edge':
        anchors = selected(analysis, check['from_selector'])
        if len(anchors) != 1:
            return {**answer, 'reason': 'Explicit edge source must resolve uniquely.', 'source_anchors': len(anchors)}
        events = {e['id']: e for e in analysis.get('events', [])}
        edges = [e for e in analysis.get('control_edges', []) if e.get('source_event') == anchors[0]['id']]
        if not edges or any(e.get('target_event') not in events or
                            events[e['target_event']].get('kind') != 'label' for e in edges):
            return {**answer, 'reason': 'Every displayed target must bind to an actual label event.'}
        actual = sorted(label(e['target_label']) for e in edges)
        wanted = expected.get('target_labels')
        if wanted is None:
            one_target = expected.get('target_label', check.get('target_label'))
            if one_target is None:
                return {**answer, 'reason': 'Reference has no public explicit-target selector.'}
            wanted = [one_target]
        wanted = sorted(label(value) for value in wanted)
        answer.update(actual={'target_labels': actual}, edges=edges)
        answer['status'] = 'match' if actual == wanted else 'mismatch'
    else:
        answer['reason'] = 'Check operation not in the preregistered adapter.'
    return answer


def main():
    out = HERE / 'source_check_results.json'
    if out.exists():
        raise RuntimeError('preserve first source comparison result')
    baseline = json.loads((HERE / 'method_baseline.json').read_text(encoding='utf-8'))
    for name, digest in baseline['files'].items():
        assert sha(ROOT / name) == digest, name
    reference = HERE / 'reference'
    assert sha(reference / 'freeze_manifest.json') == baseline['reference_manifest_sha256']
    manifest = json.loads((reference / 'freeze_manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        assert sha(reference / name) == digest, name
    packet = json.loads((HERE / 'program_results.json').read_text(encoding='utf-8'))
    assert packet['method_baseline_sha256'] == sha(HERE / 'method_baseline.json'), 'stale method packet'
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    inputs = {row['id']: row for row in protocol['inputs']}
    assert len(inputs) == len(protocol['inputs'])
    assert len(packet['documents']) == len(inputs)
    assert {row['id'] for row in packet['documents']} == set(inputs)
    for row in packet['documents']:
        item = inputs[row['id']]
        assert row['input_sha256'] == item['sha256'] == sha(ROOT / item['path'])
        assert row['binding_sha256'] == item['binding_sha256'] == sha(ROOT / item['binding_path'])
        assert row['analysis']['source_sha256'] == item['sha256']
    analyses = {row['id']: row['analysis'] for row in packet['documents']}
    checks = json.loads((reference / 'source_truth_checks.json').read_text(encoding='utf-8'))['checks']
    results = [evaluate(check, analyses[check['profile']]) for check in checks]
    counts = dict(Counter(row['status'] for row in results))
    result = {'status': 'frozen_known_source_comparison_recorded', 'summary': {'checks': len(results), **counts},
              'checks': results, 'program_results_sha256': sha(HERE / 'program_results.json'),
              'method_baseline_sha256': sha(HERE / 'method_baseline.json'),
              'reference_manifest_sha256': sha(reference / 'freeze_manifest.json'),
              'scope': 'Independent-role source-fidelity checks on known development fragments, not held-out Linux accuracy or new defects.'}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
