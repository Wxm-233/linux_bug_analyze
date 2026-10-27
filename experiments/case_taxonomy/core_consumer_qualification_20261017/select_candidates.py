"""Apply registered path priorities without looking at source, patches or model labels."""
from pathlib import Path
import hashlib
import json

stage = Path(__file__).resolve().parent
load = lambda name: json.loads((stage / name).read_text(encoding='utf-8'))
protocol = load('protocol_pre.json')
metadata = load('git_metadata.json')
exposure = load('exposure_index.json')
assert metadata['protocol_sha256'] == hashlib.sha256((stage / 'protocol_pre.json').read_bytes()).hexdigest()
assert exposure['fixed_pool']['manifest_sha256'] == metadata['pool_sha256'] == protocol['pool_sha256']
assert len(metadata['records']) == 500
out = stage / 'selection.json'
if out.exists():
    raise SystemExit('Selection already exists; preserve the first registered result.')

exposure_by_hash = {record['hash']: record for record in exposure['items']}
exclusions = {key: [reason] for key, reason in protocol['explicit_prior_exclusions'].items()}
for key in ['known_source_read_or_method_development_exclude', 'documented_prior_13_case_family_exclude', 'confirmed_same_fix_family_only_exclude', 'possible_related_theme_defer_no_family_proof']:
    for commit in exposure['exposure_sets'][key]:
        exclusions.setdefault(commit, []).append(key)

queues = []
selected = []
already = set()
for queue in protocol['queues_in_order']:
    eligible = []
    excluded_hits = []
    for record in metadata['records']:
        if record['status'] != 'single_parent_metadata':
            continue
        paths = {change['path'] for change in record['changes']}
        implementations = sorted(paths.intersection(queue['implementation_paths']))
        headers = sorted(paths.intersection(queue['header_paths']))
        if not implementations and not headers:
            continue
        if record['hash'] in exclusions:
            excluded_hits.append({'hash': record['hash'], 'reasons': exclusions[record['hash']], 'matched_paths': implementations + headers})
            continue
        exposure_record = exposure_by_hash[record['hash']]
        candidate = {
            **{key: record[key] for key in ['hash', 'subject', 'band', 'stratum', 'parents', 'author', 'author_date', 'committer_date']},
            'queue': queue['name'],
            'priority': 0 if implementations else 1,
            'matched_paths': implementations + headers,
            'all_changes': record['changes'],
            'rank_sha256': hashlib.sha256((protocol['seed'] + ':' + record['hash']).encode('utf-8')).hexdigest(),
            'contact_status': exposure_record['contact_status'],
            'source_review_evidence_paths': exposure_record['source_review_evidence_paths'],
            'scanned_reference_hits': exposure_record['scanned_reference_hits'],
            'existing_holdout_review_paths': exposure_record['existing_holdout_review_paths'],
            'family_status': exposure_record['family_status'],
            'core_cross_arch_eligibility': 'pending_source_and_authority',
            'same_mechanism_truth': 'unknown',
            'same_use_normal_truth': 'unknown',
            'independent_eligibility_proved': False,
        }
        eligible.append(candidate)
    eligible.sort(key=lambda record: (record['priority'], record['rank_sha256'], record['hash']))
    choices = [record for record in eligible if record['hash'] not in already][:queue['quota']]
    selected.extend(choices)
    already.update(record['hash'] for record in choices)
    queues.append({'name': queue['name'], 'eligible_count': len(eligible), 'implementation_count': sum(record['priority'] == 0 for record in eligible), 'excluded_hits': excluded_hits, 'ordered_hashes': [record['hash'] for record in eligible], 'selected_hashes': [record['hash'] for record in choices]})

assert len(selected) <= protocol['maximum_candidates']
result = {
    'task': 'N1.4g',
    'protocol_sha256': metadata['protocol_sha256'],
    'metadata_sha256': hashlib.sha256((stage / 'git_metadata.json').read_bytes()).hexdigest(),
    'exposure_index_sha256': hashlib.sha256((stage / 'exposure_index.json').read_bytes()).hexdigest(),
    'seed': protocol['seed'],
    'pool_count': len(metadata['records']),
    'exclusion_count': len(exclusions),
    'queues': queues,
    'candidates': selected,
    'postselection_family_review': 'pending',
    'new_source_body_reads': 0,
    'new_project_model_requests': 0,
    'new_independent_positive_normal': [0, 0],
}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'queues': [{key: queue[key] for key in ['name', 'eligible_count', 'implementation_count', 'selected_hashes']} for queue in queues], 'selected': [{key: record[key] for key in ['hash', 'subject', 'parents', 'matched_paths', 'author', 'contact_status', 'scanned_reference_hits']} for record in selected]}, ensure_ascii=False, indent=2))
