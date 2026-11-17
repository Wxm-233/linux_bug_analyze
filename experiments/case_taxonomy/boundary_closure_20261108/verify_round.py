"""Independent cross-artifact, input immutability and handoff-scope checks."""
import ast
import re
from collections import Counter
from common import *

def main():
    checks={};details={}
    checks['criteria_frozen']=bool(check_criteria())
    inputs=[]
    for p in read(HERE/'evidence/sample_input_manifest.json'):inputs.append((Path(p),read(HERE/'evidence/sample_input_manifest.json')[p]))
    for entries in read(HERE/'evidence/runtime_input_manifest.json').values():
        inputs.extend((Path(p),row) for p,row in entries.items())
    changed=[str(p) for p,r in inputs if sha(p)!=r['sha256']]
    assert not changed,changed
    checks['consumed_inputs_unchanged']=True;details['consumed_input_files']=len(inputs)
    original=read(AUDIT/'evidence/old_manifest.json')
    differences=[name for name,h in original.items() if sha(OLD/name.replace('\\','/'))!=h]
    assert not differences,differences
    checks['old_enumeration_manifest_unchanged']=True;details['old_enumeration_files']=len(original)
    current=read(HERE/'evidence/current_ranges.json')
    assert all(sha(KSRC/f)==r['sha256'] for f,r in current.items())
    checks['current_source_evidence_unchanged']=True;details['current_source_files']=len(current)
    match=read(HERE/'sample_match_v2.json');rows=match['samples'];summary=match['summary']
    assert len(rows)==120 and len({r['id'] for r in rows})==120
    assert Counter(r['check'] for r in rows)=={1:37,2:57,3:26}
    assert sum(r['hit'] for r in rows)==summary['union']['hits']
    for arch,d in revised().items():
        syms={s['id']:s for s in read(d/f'symbols_runtime_{arch}.json')}
        assert sum(r['architectures'][arch]['hit'] for r in rows)==summary['by_arch'][arch]['hits']
        for c in (1,2,3):assert sum(r['check']==c and r['architectures'][arch]['hit'] for r in rows)==summary['by_arch'][arch]['by_check'][str(c)]['hits']
        for s in rows:
            a=s['architectures'][arch]
            assert a['hit']==bool(a['evidence'])
            for evidence in a['evidence']:
                r=evidence['range'];assert r['start']<=r['end']
                for p in evidence['body_use_examples']:
                    assert p['use']['file']==evidence['current_file']
                    assert r['body_start']<=p['use']['line']<=r['end']
                    assert p['symbol_id'] in syms
                for sym in evidence['boundary_symbols']:assert sym==syms[sym['id']]
        for s in rows:
            for ent in s['entities']:
                assert ent['historical_ranges']
                for r in ent['historical_ranges']:
                    assert r['changed_lines'] and all(r['start']<=n<=r['end'] for n in r['changed_lines'])
    assert summary['by_arch']['riscv']['lost_vs_legacy_riscv_ids']==[]
    assert all(r['hit']==any(a['hit'] for a in r['architectures'].values()) for r in rows)
    checks['sample_entities_and_hit_evidence_reconcile']=True
    unresolved={}
    for s in read(HERE/'evidence/sample_entities.json'):
        missing=[{'path':v['path'],'version':v['version'],'status':v['status'],
                  'unassigned_changed_lines':v.get('unassigned_changed_lines',[])}
                 for f in s['files'] for v in f['versions']
                 if v['status']!='ok' or v.get('unassigned_changed_lines')]
        if missing:unresolved[s['id']]=missing
    write('evidence/sample_unparsed_regions.json',unresolved)
    details['samples_with_unsupported_or_unassigned_lines']=len(unresolved)
    clos=read(HERE/'closure_stats.json'); combined={s['id']:False for s in rows}
    for arch,st in clos['architectures'].items():
        ns=list(lines(HERE/f'closure_nodes_{arch}.jsonl.gz'))
        by_key={key(n['symbol']):n for n in ns}
        assert len(ns)==len(by_key)==st['candidate_functions']
        assert Counter(n['depth'] for n in ns)=={int(k):v for k,v in st['new_nodes_by_depth'].items()}
        for n in ns:
            p=n['parent']
            if p is None:assert n['depth']==0
            else:
                assert by_key[key(p)]['depth']+1==n['depth']
                assert side(n['symbol']['definition']['file'])==side(p['definition']['file'])
        rs=read(HERE/f'closure_{arch}.json')['samples']
        assert sum(s['combined_hit'] for s in rs)==st['samples_combined_hits']
        assert [s['id'] for s in rs if s['closure_only']]==st['samples_closure_only_ids']
        for s in rs:
            combined[s['id']]|=s['combined_hit']
            for r in s['matches']:
                assert len(r['path'])==r['depth']+1
                assert all(n['edge_to_next'] is not None for n in r['path'][:-1])
    assert sum(combined.values())==clos['union_combined_hits']
    checks['closure_nodes_depths_sides_and_sample_paths_reconcile']=True
    matrix=read(HERE/'config_matrix.json');val=read(HERE/'config_validation/rv64_bpf.json')
    assert matrix['audit_a_count']==len(matrix['audit_a_mapping'])==32
    assert val['completed'] and not val['kernel_build_executed']
    assert val['config_sha256']==sha(Path(val['output'])/'.config')
    assert val['matrix_sha256']==sha(HERE/'config_matrix.json')
    assert all(c['passed'] for c in val['checks'].values())
    assert not val['source_status_before'] and not val['source_status_after']
    for arch in ARCHES:
        assert read(OLD/f'result_{arch}.json')['inputs']['config_sha256']==sha(Path('/root/work/boundary_build')/(arch+'_defconfig')/'.config')
    checks['configuration_validation_and_original_configs_reconcile']=True
    for name in ('selftest_match_result.json','selftest_closure_result.json','selftest_prototype_result.json','prototype_batch_selftest_result.json'):
        assert read(HERE/name)['passed']
    p=read(HERE/'selftest_prototype_result.json')
    assert p['expected_sha256']==sha(HERE/'prototype_src/expected.json')
    real=read(HERE/'real_prototype_result.json')
    assert len(real['cases'])==2 and not real['full_rescan']
    assert all(c['libclang_direct_target_instantiations']==0 and c['outer_with_dependency']>0 for c in real['cases'])
    checks['prototype_fixtures_and_targeted_evidence_reconcile']=True
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(encoding='utf-8'),filename=str(p));syntax.append(p.name)
    for p in sorted(HERE.glob('*.sh')):
        assert p.read_text().splitlines()[0]=='source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh'
        subprocess.run(['bash','-n',str(p)],check=True,capture_output=True)
        syntax.append(p.name)
    checks['python_and_shell_syntax']=True;details['syntax_files']=syntax
    links=0
    for p in HERE.glob('*.md'):
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if target.startswith(('https:','http:','#')):continue
            target=target.strip('<>').split('#')[0]
            assert (p.parent/target).exists(),(p,target)
            links+=1
    checks['documentation_local_links_exist']=True;details['local_links_checked']=links
    if (HERE/'evidence/handoff_update_verification.json').exists():
        proof=read(HERE/'evidence/handoff_update_verification.json')
        raw=(HERE.parents[3]/'交接文档.md').read_bytes()
        start=raw.index('## 四、当前进度'.encode());end=raw.index('## 五、每轮实验怎么做'.encode())
        assert hashlib.sha256(raw[:start]).hexdigest()==proof['outside_before_sha256']
        assert hashlib.sha256(raw[end:]).hexdigest()==proof['outside_after_sha256']
        checks['handoff_only_section4_changed']=True
    assert not git('status','--porcelain=v1')
    checks['kernel_source_clean']=True
    details['limitations']='Input immutability covers all consumed manifests and the old 97-file enumeration manifest; no whole-kernel no-miss proof.'
    write('verification.json',{'passed':True,'checks':checks,'details':details})
    print('verification passed',len(checks),'groups; old files',len(original))

if __name__=='__main__':main()
