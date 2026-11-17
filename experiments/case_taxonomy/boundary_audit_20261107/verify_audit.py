"""Cross-artifact reconciliation and immutability checks; no kernel scan."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'boundary_enum_20261106'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks=[]
    for name in ['criteria','criteria_amendment2']:
        assert sha(HERE/f'{name}.md')==(HERE/f'{name}_sha256.txt').read_text().split()[0]
        checks.append(name+'_sha256')
    before=read(HERE/'evidence/old_manifest.json')
    after={p.relative_to(OLD).as_posix():sha(p) for p in OLD.rglob('*') if p.is_file()}
    assert before==after,{'changed':[k for k in before if before[k]!=after.get(k)],'added':sorted(set(after)-set(before))}
    checks.append('old_97_files_byte_identical')
    sample=read(HERE/'sample_miss_analysis.json');rows=sample['samples'];original=read(OLD/'sample_hits.json')['samples']
    missed={r['id']:r for r in original if not r['hit']}
    assert len(rows)==len(missed)==100 and {r['id'] for r in rows}==set(missed)
    assert Counter(r['check'] for r in rows)==Counter({1:32,2:45,3:23})
    assert sum(not bool(r['functions']) for r in rows)==36
    for r in rows:
        assert r['functions']==missed[r['id']]['functions'] and r['files']==missed[r['id']]['files']
        assert r['fix_is_ancestor_of_current']
        assert r['primary_category'] in 'abcdeu'
        assert (HERE/r['patch']).is_file() and r['patch_changed_lines']
        assert r['symbol_evidence'] and r['file_evidence'] and r['judgment']
        for f in r['file_evidence']:
            if f['exists']:assert (HERE/f['full_source_evidence']).is_file()
    checks.append('all_100_misses_have_evidence_and_unchanged_sample_fields')
    unresolved=read(HERE/'unresolved_analysis.json');u=unresolved['summary']
    assert len(unresolved['unit_reconciliation'])==16 and all(r['matched'] for r in unresolved['unit_reconciliation'])
    assert sum(u['categories'].values())==30141==sum(r['expected'] for r in unresolved['unit_reconciliation'])
    assert len(unresolved['reference_sample'])==400
    assert all(r['libclang_declaration'] is not None or
               (r['category']=='compiler_builtin' and r['declaration_missing_reason']=='implicit_compiler_builtin_not_in_TU_declaration_walk')
               for r in unresolved['reference_sample'])
    assert u['confirmed_missing_boundary_occurrences']==sum(s['confirmed_missing_boundary_occurrences'] for s in u['by_stratum'].values())
    assert all(g['category']==g['example']['category'] for g in unresolved['top20_declaration_groups'])
    assert all(r['confirmed_missing_boundary'] for r in unresolved['confirmed_missing_boundary_examples'])
    checks.append('16_units_and_400_reference_details_reconcile')
    generated=read(HERE/'generated_analysis.json')['architectures']
    for arch,g in generated.items():
        assert g['generated_use_points']==sum(v['points'] for v in g['groups'].values())
        assert g['original_points']==read(OLD/f'result_{arch}.json')['points']
    checks.append('generated_groups_reconcile_for_all_3_arches')
    orig_text=(OLD/'selftest/verify.py').read_text(encoding='utf-8')
    new_text=(HERE/'selftest_original/verify.py').read_text(encoding='utf-8')
    def expected_block(s):return s[s.index('    expected = set()'):s.index('    shared =')]
    assert expected_block(orig_text)==expected_block(new_text)
    assert read(HERE/'selftest_original/result.json')['points']==19
    assert read(HERE/'selftest_revision_result.json')['status']=='passed'
    assert read(HERE/'real_repairs_verification.json')['status']=='passed'
    checks.append('original_expected_19_points_unchanged_and_new_regression_passed')
    checks.append('real_B446_and_C_to_asm_targeted_replay_passed')
    result={'status':'passed','checks':checks,'old_files_verified':len(before),'full_kernel_scan_executed':False,
            'full_kernel_remerge_executed':False}
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
