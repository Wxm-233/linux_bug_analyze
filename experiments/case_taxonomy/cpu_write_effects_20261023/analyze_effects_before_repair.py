"""Use the bounded component on collected compiler records, with honest scope."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.gimple_write_effects import analyze_write_effects, check_write_candidate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / 'program_results.json'
    assert not out.exists(), 'preserve first analysis'
    frozen = json.loads((HERE / 'method_manifest.json').read_text(encoding='utf-8'))
    for name, digest in frozen['files_sha256'].items():
        assert sha(ROOT / name) == digest, name
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    collection = json.loads((HERE / 'compiler_execution.json').read_text(encoding='utf-8'))
    assert collection['status'] == 'completed'
    rows = []
    for profile, archive in zip(protocol['profiles'], collection['profiles'], strict=True):
        assert profile['id'] == archive['id']
        directory = HERE / profile['id']
        for name, digest in archive['files_sha256'].items():
            assert sha(directory / name) == digest, name
        selected = directory / 'selected.cfg'
        document = {'id': 'N222_' + profile['id'], 'path': str(selected.relative_to(ROOT)).replace('\\', '/'),
                    'revision': protocol['fragment']['revision'], 'text': selected.read_text(encoding='utf-8')}
        target, function = protocol['query_scalar'], protocol['query_function']
        facts = analyze_write_effects(document, function=function, target=target, expected_sha256=sha(selected))
        source = (directory / 'setter.i').read_text(encoding='utf-8')
        # Fixed-spelling evidence locators, not a general C declaration resolver.
        object_hits = [{'line': i, 'text': line} for i, line in enumerate(source.splitlines(), 1)
                       if re.fullmatch(r'\s*extern unsigned int nr_cpu_ids;\s*', line)]
        macro_hits = [{'line': i, 'text': line} for i, line in enumerate(source.splitlines(), 1)
                      if re.fullmatch(r'#define nr_cpu_ids \(\(unsigned int\)NR_CPUS\)', line)]
        nr_hits = [{'line': i, 'text': line} for i, line in enumerate(source.splitlines(), 1)
                   if re.fullmatch(r'#define NR_CPUS [14]', line)]
        if len(object_hits) == 1 and not macro_hits:
            binding = 'extern_object'
        elif len(macro_hits) == 1 and len(nr_hits) == 1 and not object_hits:
            binding = 'macro_constant'
        else:
            binding = 'insufficient'
        base = {'function': function, 'target': target, 'source_sha256': sha(selected),
                'scope': 'selected_function_scalar_spelling'}
        candidates = {claim: check_write_candidate(document, dict(base, claim=claim))
                      for claim in ('direct_write_exists', 'unconditional_write')}
        source_locus = all(any(loc['path'] == protocol['fragment']['path'] and
                              protocol['fragment']['first_line'] <= loc['line'] <= protocol['fragment']['last_line']
                              for loc in event['source_locations']) for event in facts['writes'])
        rows.append({'id': profile['id'], 'configuration_defines': profile['defines'],
                     'binding_observation': {'status': binding, 'preprocessed_sha256': sha(directory/'setter.i'),
                                             'object_declarations': object_hits, 'macro_definitions': macro_hits,
                                             'NR_CPUS_definitions': nr_hits,
                                             'resolver_scope': 'researcher-selected exact spelling in one finite projection'},
                     'effects': facts, 'candidates': candidates,
                     'source_fidelity': {'original_fragment_sha256': protocol['fragment']['fragment_sha256'],
                                         'write_locus_in_original_fragment': source_locus,
                                         'binding_expected_match': binding == profile['binding_expected'],
                                         'direct_write_expected_match': (facts['status'] == 'direct_write_observed') == profile['direct_write_expected']},
                     'actual_runtime_effect': 'not_evaluated', 'complete_contract': 'insufficient'})
    checks = [value for row in rows for key, value in row['source_fidelity'].items() if key.endswith('_match')]
    assert all(row['effects']['status'] != 'insufficient' for row in rows), 'unsupported compiler fact input'
    assert all(row['source_fidelity']['write_locus_in_original_fragment'] for row in rows), 'source locus missing'
    assert all(checks), 'do not rewrite expected results to fit output'
    result = {'task': 'N2.22', 'status': 'bounded_source_facts_checked', 'profiles': rows,
              'summary': {'profiles': len(rows), 'direct_write_observed': sum(bool(row['effects']['writes']) for row in rows),
                          'no_direct_write_observed': sum(row['effects']['status'] == 'no_direct_write_observed' for row in rows),
                          'binding_and_write_reference_checks': len(checks), 'reference_matches': sum(checks),
                          'unconditional_candidates_insufficient': sum(row['candidates']['unconditional_write']['status'] == 'insufficient' for row in rows)},
              'method_manifest_sha256': sha(HERE/'method_manifest.json'),
              'compiler_execution_sha256': sha(HERE/'compiler_execution.json'),
              'human_dependencies': protocol['human_inputs'], 'automatic_contract_derivation': False,
              'legacy_candidate_protocol_changed': False, 'production_cli_integrated': False,
              'scope': 'new companion candidate adapter on known compiler projections; not end-to-end source or model pipeline',
              'new_cases': 0, 'independent_positive': 0, 'independent_normal': 0,
              'kernel_boots': 0, 'paid_model_requests': 0}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
