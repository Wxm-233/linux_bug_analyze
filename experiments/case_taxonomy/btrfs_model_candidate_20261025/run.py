"""One raw model output -> strict ingestion -> intent guard -> original core."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.model_candidate import parse_model_candidate,CandidateInputError
from linux_bug_analyze.interface_intent import evaluate_with_intent
from linux_bug_analyze.contract_archive import load_verified_archive

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 if args.output.exists():raise ValueError('preserve prior output')
 read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 pins=read(HERE/'frozen_inputs.json')
 for p,h in pins.items():
  if sha(ROOT/p)!=h:raise ValueError('frozen input changed: '+p)
 protocol=read(HERE/'protocol.json');folder=Path(protocol['output']);receipt=read(folder/'receipt.json')
 if receipt['status']=='started':raise ValueError('call still running')
 assert sha(folder/'prompt.md')==protocol['prompt_sha256']==receipt['prompt_sha256']
 result=dict(status='delivery_not_admitted',model_calls=1,new_boots=0,independent_positive=0,independent_normal=0,
  receipt_sha256=sha(folder/'receipt.json'),delivery={k:receipt.get(k) for k in ('status','started_at','elapsed_seconds','actual_models','finish_reasons','done_marker','network_eof','usage','visible_reported_tokens','usage_known','final_characters')},
  candidate_count=0,human_candidate_rewrite=False,model_output_used_as_review_ledger=False,
  input_scope=protocol['input_scope'],platform_billing_independently_verified=False)
 if receipt['status']=='complete_final_received' and receipt['semantic_review_allowed']:
  assert receipt['finish_reasons']==['stop'] and receipt['actual_models']==['Kimi-K3']
  assert receipt['done_marker'] and receipt['network_eof']
  try:
   ingested=parse_model_candidate((folder/'final.md').read_text(encoding='utf-8'),read(HERE/'documents.json'))
   result.update(status='candidate_ingested',candidate_count=1,ingestion=ingested)
  except CandidateInputError as exc:
   result.update(status='candidate_ingestion_rejected',ingestion_error=str(exc))
  if result['candidate_count']:
   # Trusted intents and evidence are separately frozen; neither goes to the model.
   oldpins=read(HERE.parent/'btrfs_mainline_20261025/frozen_inputs.json')
   for p,h in oldpins.items():assert sha(ROOT/p)==h,p
   relative='linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/registered_inputs.json'
   bundles,_=load_verified_archive(ROOT/relative,oldpins[relative]);by={b['record']['id']:b for b in bundles}
   intents=read(HERE.parent/'btrfs_mainline_20261025/registered_intents.json');rows=[]
   for item in intents:
    if 'observer.parent:' not in item['record_id']:continue
    b=by[item['record_id']];candidate=copy.deepcopy(ingested['candidate'])
    label=candidate['deadline_event']
    event_map={'cache_capture':b['record']['context_id']+':cache',
      'min_consumption':b['record']['deadline_event'],'disk_sample':b['record']['sample_event']}
    if label not in event_map:
     rows.append(dict(record_id=item['record_id'],status='unknown_abstract_event',value=label));continue
    candidate['deadline_event']=event_map[label]
    # Do not rewrite model origins or rename old review facts to manufacture approval.
    out=evaluate_with_intent(item['intent'],candidate,b['ledger'],b['record'])
    rows.append(dict(record_id=item['record_id'],event_mapping=dict(abstract=label,concrete=event_map[label]),result=out))
   assert len(rows)==2
   result.update(status='structured_candidate_pipeline_executed',rows=rows,
    evidence_policy='Original reviewed evidence retained unchanged; no automatic promotion of model provenance.',
    separate_technical_stages=['delivery','JSON and citation identity','registered intent match','reviewed evidence and original core'])
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('ingestion','rows')},ensure_ascii=True))

if __name__=='__main__':main()
