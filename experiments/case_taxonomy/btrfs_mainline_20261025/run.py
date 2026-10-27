"""Interface question -> structured candidate guard -> unchanged core."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contract_archive import load_verified_archive
from linux_bug_analyze.interface_intent import evaluate_with_intent
from linux_bug_analyze.contract_protocol import evaluate_contract

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 if args.output.exists():raise ValueError('preserve existing output')
 read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
 pins=read(HERE/'frozen_inputs.json')
 for p,h in pins.items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('frozen input changed: '+p)
 archive='linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/registered_inputs.json'
 bundles,snapshots=load_verified_archive(ROOT/archive,pins[archive]);by={b['record']['id']:b for b in bundles}
 rows=[]
 for item in read(HERE/'registered_intents.json'):
  b=by[item['record_id']]
  for mode in ('original_C','equivalent_rename','cache_self_reference','move_deadline_to_sample','adjacent_sample_as_reference'):
   candidate=copy.deepcopy(item['candidate']);c=candidate['contract'];bindings=candidate['symbol_bindings']
   if mode=='equivalent_rename':
    c['symbols']['reference_value']=c['symbols'].pop('disk_at_deadline')
    bindings['reference_value']=bindings.pop('disk_at_deadline')
    c['relation']['args']=[{'symbol':'reference_value'},{'symbol':'cache'}]
   elif mode=='cache_self_reference':
    c['symbols'].pop('disk_at_deadline');bindings.pop('disk_at_deadline')
    c['relation']['args']=[{'symbol':'cache'},{'symbol':'cache'}]
   elif mode=='move_deadline_to_sample':candidate['deadline_event']=b['record']['sample_event']
   elif mode=='adjacent_sample_as_reference':bindings['disk_at_deadline']='adjacent_disk'
   out=evaluate_with_intent(item['intent'],candidate,b['ledger'],b['record'])
   expected=mode in ('original_C','equivalent_rename')
   assert out['core_executed']==expected,(mode,out)
   assert out['evaluation']['relation_at_deadline']==out['evaluation']['whole_path']=='insufficient'
   rows.append(dict(record_id=item['record_id'],candidate_kind=mode,
    provenance='original researcher registration' if mode=='original_C' else 'researcher-authored development control',result=out))
 diagnostic=[]
 for b in bundles:
  if b['contract']['id']=='btrfs.layered.B':diagnostic.append(evaluate_contract(b['contract'],b['ledger'],b['record']))
 assert [r['relation_at_observation'] for r in diagnostic]==['violated','violated','satisfied','satisfied']
 result=dict(status='interface_intent_guard_integrated',archive_events=4,structured_candidates=len(rows),
  intent_matches=sum(r['result']['core_executed'] for r in rows),intent_mismatches=sum(not r['result']['core_executed'] for r in rows),
  rows=rows,cross_time_diagnostics=diagnostic,
  new_boots=0,model_calls=0,new_independent_cases=0,independent_positive=0,independent_normal=0,
  candidate_extraction='manual structured transcription; not automated NLP',
  normative_authority='still externally reviewed / C unresolved',
  original_core_modified=False,scope='registered interface intent consistency, not source-level requirement inference')
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows','cross_time_diagnostics')}))

if __name__=='__main__':main()
