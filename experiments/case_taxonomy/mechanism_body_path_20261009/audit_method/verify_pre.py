"""Independent saved-input and static-method review; no Git or detector import."""
from pathlib import Path
import ast
import hashlib
import json
import re

HERE = Path(__file__).resolve().parents[1]
BASE = HERE.parent
PROJECT = HERE.parents[2]
INPUT = PROJECT / 'analysis_out/stratified-20260921/manifest.json'
LOCK_SHA = 'ac769b7f92e8f5e6f33a2d74323728cf371c87d4a46291376b9af585ddd17d2e'
SCRIPT_SHA = '271616aa80b714b0ddd176db19277c1424132034105880f8e86b7568493179b9'
REP = r'(?<![A-Za-z0-9])(?:endian(?:ness)?|byte[ -]?order|(?:le|be)(?:16|32|64)|convert(?:ed|ing|s)?|conversion)(?![A-Za-z0-9])'
COUNT = r'(?<![A-Za-z0-9])(?:len|length|size|count|bytes)(?![A-Za-z0-9])'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

assert sha(HERE / 'freeze_pre.json') == LOCK_SHA
assert sha(HERE / 'prepare.py') == SCRIPT_SHA
lock = load(HERE / 'freeze_pre.json')
assert lock['git_before_freeze'] == lock['source_before_freeze'] == lock['rule_before_freeze'] == 0
assert not (HERE / 'raw').exists() and not (HERE / 'retrieval_manifest.json').exists()
locked_paths = {Path(row['path']).resolve() for row in lock['files']}
assert len(locked_paths) == len(lock['files'])
for row in lock['files']:
    assert sha(Path(row['path'])) == row['sha256'], row['path']
exposure_files = {p.resolve() for p in (HERE / 'audit_exposure').rglob('*') if p.is_file()}
assert exposure_files <= locked_paths

pool = load(HERE / 'metadata_pool.json')
manifest = load(INPUT)
assert len(manifest['samples']) == 500
assert sha(INPUT) == pool['source_sha256'] == '8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a'
expected = []
representation_order = 0
for index, item in enumerate(manifest['samples'], 1):
    if item['stratum'] != 'representation':
        continue
    representation_order += 1
    if 33 <= representation_order <= 64:
        match = re.search(REP, item['subject'], re.I)
        expected.append(dict(pool_order=len(expected) + 1, representation_order=representation_order,
                             original_manifest_index=index, commit=item['hash'], subject=item['subject'],
                             stratum=item['stratum'], band=item['band'],
                             representation_title_match=match.group() if match else None))
    if representation_order == 64:
        break
assert pool['records'] == expected and len(expected) == pool['pool_count'] == 32
assert pool['representation_regex'] == REP and pool['count_regex'] == COUNT
assert pool['model_results_used'] is False

audit = load(HERE / 'audit_exposure/exposure_audit.json')
scope = load(HERE / 'audit_exposure/scope_search.json')
assert audit['metadata_pool_sha256'] == scope['metadata_pool_sha256'] == sha(HERE / 'metadata_pool.json')
assert audit['scope_search_sha256'] == sha(HERE / 'audit_exposure/scope_search.json')
assert audit['matches_sha256'] == sha(HERE / 'audit_exposure/matches.json')
assert audit['search_receipts_sha256'] == sha(HERE / 'audit_exposure/search_receipts.json')
assert audit['searched_files'] == scope['searched_files']
assert len(scope['searched_files']) == scope['searched_file_count'] == audit['searched_file_count'] == 752
assert scope['excluded_entire_stage'] == HERE.name
assert set(scope['search_extensions']) == {'.md', '.json', '.tsv'}
assert scope['inventory_exit_code'] == 0
assert scope['inventory_stdout_sha256'] == sha(HERE / 'audit_exposure/inventory.stdout')
assert scope['inventory_stderr_sha256'] == sha(HERE / 'audit_exposure/inventory.stderr')
inventory_paths = set()
for value in (HERE / 'audit_exposure/inventory.stdout').read_text(encoding='utf-8').splitlines():
    path = Path(value).resolve()
    if path.suffix.lower() in {'.md', '.json', '.tsv'} and HERE not in path.parents:
        inventory_paths.add(path.relative_to(BASE).as_posix())
assert inventory_paths == {row['path'].replace('\\', '/') for row in scope['searched_files']}
for row in scope['searched_files']:
    assert sha(BASE / row['path']) == row['sha256'], row['path']
records = {row['commit']: row for row in audit['records']}
assert len(records) == 32 and set(records) == {row['commit'] for row in expected}
assert sum(row['reference_count'] for row in records.values()) == 222
for row in records.values():
    assert row['reference_count'] == len(row['all_references'])
    if row['status'] == 'source_exposure_confirmed':
        assert row['source_exposure_confirmed'] is True and row['actual_source_evidence']
    else:
        assert row['status'] == 'no_evidence_in_defined_scope'
        assert row['source_exposure_confirmed'] is False and not row['actual_source_evidence']
    for evidence in row['actual_source_evidence']:
        source = BASE / evidence['path']
        assert sha(source) == evidence['sha256']
        assert source.read_text(encoding='utf-8').splitlines()[evidence['line'] - 1] == evidence['text']

selection = load(HERE / 'selection_pre.json')
eligible = [row for row in expected if row['representation_title_match'] is not None
            and records[row['commit']]['status'] == 'no_evidence_in_defined_scope'
            and records[row['commit']]['source_exposure_confirmed'] is False]
assert selection['queue'] == eligible[:8] and selection['eligible_count'] == len(eligible) == 1
assert selection['queue_cap'] == 8 and selection['no_replacement_after_retrieval'] is True
assert selection['selected_by_metadata_only'] is True
assert selection['queue'][0]['commit'] == '7a2bccd1a27f0c8fc87e4ed56abd6ea9fa7314a6'
assert selection['source_exposed_commits'] == [row['commit'] for row in expected if records[row['commit']]['source_exposure_confirmed']]

# Parse only: neither prepare.py nor any detector/source gate is imported/executed.
tree = ast.parse((HERE / 'prepare.py').read_text(encoding='utf-8'))
imports = set()
for node in tree.body:
    if isinstance(node, ast.Import):
        imports.update(alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        imports.add(node.module)
assert imports == {'pathlib', 'hashlib', 'json', 'posixpath', 're', 'subprocess', 'sys'}
assert not (HERE / 'raw').exists() and not (HERE / 'retrieval_manifest.json').exists()

review = dict(
    date='2026-10-09', auditor='/root/body_path_method', ready_for_retrieval=True,
    script_sha256=SCRIPT_SHA, freeze_sha256=LOCK_SHA,
    metadata_pool_sha256=sha(HERE / 'metadata_pool.json'),
    exposure_audit_sha256=sha(HERE / 'audit_exposure/exposure_audit.json'),
    selection_sha256=sha(HERE / 'selection_pre.json'),
    verifier_sha256=sha(Path(__file__).resolve()),
    frozen_file_checks=len(lock['files']), exposure_saved_file_checks=len(exposure_files),
    historical_scope_file_checks=752, actual_source_quote_checks=sum(len(r['actual_source_evidence']) for r in records.values()),
    pool_count=32, representation_title_matches=sum(r['representation_title_match'] is not None for r in expected),
    queue_size=1, blocked_findings=[],
    static_checks=['subject first message line excluded from body',
                   'only tail continuous pure known-trailer paragraphs removed; original message_line retained',
                   'commit raw payload Git object SHA-1 checked before message parsing',
                   'non-single parent, unavailable, bad encoding and unsupported paths remain insufficient without replacements',
                   'at most eight commit queries and eight path queries; no source/patch queries',
                   'all queue observations precede global C-first then header selection',
                   'purposeful count hints and implementation-path labels do not certify mechanism, defect or inline code'],
    limitations=['Only the fixed historical research-record scope was audited; not global blindness.',
                 'Message body may reveal the author explanation; this is disclosed purposeful selection.',
                 'Body and path selection cannot establish encoded length shape or actual declaration binding.',
                 'Message line is Python splitlines numbering, not a byte offset.'],
    git_commands=0, new_source_reads=0, patch_reads=0, detector_runs=0, source_gate_runs=0)
output = HERE / 'audit_method/review.json'
assert not output.exists()
output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: review[k] for k in ['ready_for_retrieval', 'script_sha256', 'freeze_sha256', 'frozen_file_checks', 'historical_scope_file_checks', 'queue_size']}, ensure_ascii=False))
