from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;INNER=HERE.parents[2];OUTER=INNER.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
module=HERE.parent/'new_input_contract_trial_20261017/run_raw_candidate_checks.py'
spec=importlib.util.spec_from_file_location('n217_unchanged_raw_adapter',module);raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)

def main():
 p=argparse.ArgumentParser();p.add_argument('case',choices=['P01','P02']);a=p.parse_args();out=HERE/('candidate_checks_'+a.case+'.json');assert not out.exists()
 manifests=json.loads((HERE/'packet_manifest.json').read_bytes());m=next(x for x in manifests['packets'] if x['case']==a.case)
 assert sha((HERE/'protocol_pre.json').read_bytes())==m['protocol_sha256']
 versions=json.loads((HERE/'method_versions.json').read_bytes());assert sha((HERE/'method_versions.json').read_bytes())==m['method_versions_sha256']
 for path,digest in versions['raw_interface_versions'].items():assert sha((HERE.parent/path).read_bytes())==digest,path
 for path,digest in versions['component_version_record']['reusable_components'].items():assert sha((INNER/path).read_bytes())==digest,path
 raw.verify_baseline()
 packet_bytes=(HERE/('documents_'+a.case+'.json')).read_bytes();assert sha(packet_bytes)==m['documents_sha256'];packet=json.loads(packet_bytes)
 artifacts={}
 for p in packet['input_manifest']:
  file=(INNER/p['path']).resolve();assert file.is_relative_to(INNER)
  value=file.read_bytes();assert sha(value)==p['sha256']==manifests['artifacts'][p['path']];artifacts[p['path']]=value
 bound=raw.bind_documents(packet,artifacts)
 folder=OUTER/m['model_directory'];receipt=json.loads((folder/'receipt.json').read_bytes());plan=json.loads((folder/'call_plan.json').read_bytes())
 assert plan['prompt_sha256']==m['prompt_sha256']==sha((folder/'prompt.md').read_text(encoding='utf-8').encode('utf-8'))
 # The existing runner sends read_text-normalized UTF-8, not Windows CRLF bytes.
 physical_prompt_sha256=sha((folder/'prompt.md').read_bytes())
 result={'case':a.case,'documents_sha256':m['documents_sha256'],'source_layer':'raw_source_only','document_bindings':[{k:v for k,v in x.items() if k!='document'} for x in bound.values()],'formal_features_updated':False,'semantic_or_effect_proof':False,'receipt_status':receipt['status']}
 complete=(receipt['status']=='complete_final_received' and receipt.get('exit_code')==0 and receipt.get('result_subtype')=='success' and receipt.get('result_is_error') is not True and receipt.get('actual_models')==receipt.get('response_models')==['AWS-Claude-Opus-5.5'] and receipt.get('refusal_observed') is False and receipt.get('stop_reasons') and set(receipt['stop_reasons'])<= {'end_turn','stop_sequence'})
 if not complete:
  result.update(status='not_evaluated_incomplete_delivery',model_answer_consumed=False)
 else:
  data=(folder/'final.md').read_bytes();result.update(raw_final_sha256=sha(data),model_answer_consumed=True)
  try:
   output,mode=raw.old.parse_final(data);result['parse_mode']=mode;result.update(raw.check_output(output,bound));result['status']='bounded_raw_source_checks_complete'
  except (raw.old.EvidenceError,ValueError,TypeError,KeyError) as e:result.update(status='insufficient',error=str(e))
 with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'case':a.case,'status':result['status'],'bound':sum(x['status']=='source_bound' for x in bound.values()),'candidate_statuses':[x['status'] for x in result.get('candidate_bindings',[])],'local_statuses':[x['status'] for x in result.get('local_checks',[])]}))
if __name__=='__main__':main()
