"""Offline review record and one source-based contract transfer experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function
from linux_bug_analyze.git_repository import GitRepository
from linux_bug_analyze.semantic_signals import source_signals

REVIEW={
'93976a20345b':('control','Predicate representation refactor; no intended behavior change. Focused hunk replaces migration predicate; broad equivalence not proven by execution.'),
'03bfbc3ad6e4':('control','Helper inlining preserves the huge_pte_none special case. No concrete repaired contract violation established.'),
'14a84c708efd':('control','Adds config4 support and matching parsing/validation cases. Feature extension, not demonstrated repair.'),
'd8d8a0b3603a':('uncertain','Tool event CPU-map applicability changes; useful capability granularity example, but user-space scope and no architecture-specific failure established.'),
'c3d17464f026':('control','Logging prefix macro substitution preserves the literal cpu prefix; no topology state change in focused hunk.'),
'661f951e371c':('contract_related','Topology callback relies on stale implicit global NUMA level. Pass explicit level context; relevant to state-at-consumption contract. Not a proven repair-A-breaks-B chain.'),
'1c3e03b34042':('control','Removes redundant zero assignments after kzalloc; retains opaque atomic initialization.'),
'8870dbeedcf9':('control','Enables blocksize greater than pagesize after support work; feature scope, not itself evidence of prior supported-configuration defect.'),
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--linux-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True);a=ap.parse_args();out=a.outdir
    out.mkdir(parents=True,exist_ok=True)
    manifest_path=out/'manifest.json'
    if not manifest_path.exists():
        manifest_path.write_text(Path(__file__).with_name('samples.json').read_text())
    manifest=json.loads(manifest_path.read_text());repo=GitRepository(a.linux_dir)
    rows=[]
    for row in manifest['rows']:
        c=repo.get_commit(row['hash'],20000); label,reason=REVIEW[row['hash'][:12]]
        rows.append({**row,'reference':label,'review_reason':reason,'reviewer':'assistant source review; not expert gold',
            'scope':'commit description and focused hunk; broader source chain inspected for the contract-related case',
            'signals':source_signals(c),'diff_truncated':c.diff_truncated})
    (out/'local-review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    rev='661f951e371cc134ea31c84238dbdc9a898b8403';results={};sources=[]
    for mode in ('before','after'):
        raw=subprocess.check_output(['git','-C',str(a.linux_dir),'show',rev+('^' if mode=='before' else '')+':kernel/sched/topology.c'])
        (out/(mode+'-sched-topology.c')).write_bytes(raw)
        fn=function(raw.decode(),'static const struct cpumask *sd_numa_mask(')
        sources.append({'mode':mode,'source_sha256':hashlib.sha256(raw).hexdigest()})
        src='''#include <stdio.h>
#include <stdlib.h>
struct cpumask {unsigned bits;};
struct sched_domain_topology_level {int numa_level;};
static struct cpumask values[2][2]={{{1},{2}},{{3},{3}}};
static struct cpumask *sched_domains_numa_masks[2][2];
static int sched_domains_curr_level;
static int cpu_to_node(int cpu) {return cpu;}
'''+fn+'''
int main(int argc,char **argv) {
 if(argc!=4)return 2;
 struct sched_domain_topology_level tl={atoi(argv[1])};
 sched_domains_curr_level=atoi(argv[2]);int cpu=atoi(argv[3]);
 for(int l=0;l<2;l++)for(int c=0;c<2;c++)sched_domains_numa_masks[l][c]=&values[l][c];
 (void)tl;(void)sched_domains_curr_level;
'''+('const struct cpumask *p=sd_numa_mask(cpu);' if mode=='before' else 'const struct cpumask *p=sd_numa_mask(&tl,cpu);')+'''
 printf("%u\\n",p->bits);return 0;
}
'''
        c=out/(mode+'-transfer.c');c.write_text(src);exe=out/(mode+'-transfer')
        subprocess.run(['gcc','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
        test=[]
        for requested in (0,1):
            for cached in (0,1):
                for cpu in (0,1):
                    actual=int(subprocess.check_output([str(exe),str(requested),str(cached),str(cpu)],text=True))
                    expected=(1<<cpu) if requested==0 else 3
                    test.append(dict(requested=requested,cached=cached,cpu=cpu,actual=actual,expected=expected,passed=actual==expected))
        assert sum(not r['passed'] for r in test)==(4 if mode=='before' else 0)
        results[mode]=test
    (out/'transfer-results.json').write_text(json.dumps({'sources':sources,'rows':results},indent=2)+'\n')
    print(json.dumps({'references':{label:sum(r['reference']==label for r in rows) for label in ('control','uncertain','contract_related')},
        'local_signals':[(r['hash'][:12],[s['family'] for s in r['signals']]) for r in rows],
        'transfer_before_failed':4,'transfer_after_failed':0,'model_requests':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
