"""汇总既有结果、摘要和源文件差异，不运行新的内核分析。"""
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
TAX=HERE.parents[1]


def load(p): return json.loads(Path(p).read_text())


criteria_checks={}
for p in (HERE, HERE.parent):
    expected=(p/'criteria_sha256.txt').read_text().split()[0].lower()
    actual=hashlib.sha256((p/'criteria.md').read_bytes()).hexdigest()
    assert expected==actual, str(p)
    criteria_checks[str(p.relative_to(TAX))]=actual
comparisons=load(HERE/'regression/results.json')
required=['hints_vocab_saved','hints_stats','hints_sites','hints_all','rank_hints_saved',
          'rank_ranking_saved','layouts_saved','extract_futex']
assert all(comparisons[k]['equal'] for k in required)
smoke=load(HERE/'smoke/result.json')
selftests={t:len(load(HERE/'tests'/f'selftest_{t}.json')['passed']) for t in ('riscv','loongarch')}
kernel_status=subprocess.run(['git','-C','/root/repos/linux','status','--porcelain=v1'],
                             capture_output=True,text=True,check=True).stdout
stats={'required_regression_groups_passed':4,'required_regression_groups_total':4,
       'required_field_comparisons_passed':len(required),'selftest_passes':selftests,
       'api':load(HERE/'tests/api_result.json'),'riscv_hint_stats':comparisons['hints_stats']['stats'],
       'extract_futex':comparisons['extract_futex'],'layouts':comparisons['layouts_saved'],
       'old_files_unchanged':comparisons['old_files_unchanged']['equal'],
       'criteria_sha256':criteria_checks,'kernel_worktree_clean':not kernel_status.strip(),
       'loongarch_smoke':{k:smoke[k] for k in ('status','compile_commands','unit_status','functions',
                                            'syscall_entries_count','tree_boundary','target_macro_count','values_probed')},
       'supplemental_probe':load(HERE/'tests/supplemental_probe_failure.json'),
       'full_macro_values_regression':None,'loongarch_full_ranking':None,
       'model_calls':0,'kernel_builds':0,'new_confirmed_bugs':0,'new_suspicions':0}
(HERE/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
manifest=load(HERE/'source_manifest.json')
diff=[]
for source,h in manifest.items():
    path=TAX/source
    assert hashlib.sha256(path.read_bytes()).hexdigest()==h
    new=HERE/path.name
    if path.suffix=='.py' and new.exists():
        diff.extend(difflib.unified_diff(path.read_text().splitlines(True),new.read_text().splitlines(True),
                                        fromfile=source,tofile='pipeline/'+path.name))
(HERE/'changes.patch').write_text(''.join(diff))
files=[p for p in HERE.iterdir() if p.is_file() and p.name!='delivery_manifest.json']
(HERE/'delivery_manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},indent=2))
print('必做回归4/4；逐字段比较8/8；小样例',selftests,'；原/父判据未变；旧文件未变；内核工作树干净',not kernel_status.strip())
