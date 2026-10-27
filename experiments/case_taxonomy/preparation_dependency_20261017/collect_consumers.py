"""Collect the two located complete functions, keeping the old locator failure."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

stage=Path(__file__).resolve().parent
plan=json.loads((stage/'protocol_pre.json').read_text(encoding='utf-8'))
locations=json.loads((stage/'definition_locations.json').read_text(encoding='utf-8'))
if (stage/'consumer_functions.json').exists():
    raise SystemExit('Consumer material already saved.')
spec=importlib.util.spec_from_file_location('old_collector',stage.parent/'preparation_eligibility_20261016/collect_sources.py')
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
definitions=[]
for line in locations['lines']:
    revision,path,number,source=line.split(':',3)
    if source.lstrip().startswith('void ') and not source.rstrip().endswith(';'):
        name=next((n for n in plan['definition_names'] if n+'(' in source),None)
        if name:
            definitions.append({'name':name,'path':path,'start_line':int(number)})
if sorted(d['name'] for d in definitions)!=sorted(plan['definition_names']):
    raise RuntimeError('Missing or ambiguous registered definitions')
cache={}
documents=[]
failures=[]
for definition in definitions:
    relative=definition['path']
    if relative not in cache:
        raw=subprocess.run(['git','-C','/root/repos/linux','show',plan['parent']+':'+relative],capture_output=True,check=True).stdout
        target=stage/'source_files'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        cache[relative]=raw
    raw=cache[relative]
    try:
        lo,hi,source=helper.complete_function(raw,definition['name'])
        location_method='unchanged_existing_complete_function'
    except ValueError as exc:
        failures.append({'function':definition['name'],'old_locator_error':str(exc),'raw_not_modified':True})
        # Collection-only fallback: exact prelocated definition line and balanced
        # braces in comment/literal-masked original text. Not a C semantic parser.
        text=raw.decode('utf-8')
        masked=helper.lexical_mask(text)
        lines=text.splitlines(keepends=True)
        begin=sum(len(l) for l in lines[:definition['start_line']-1])
        opening=masked.find('{',begin)
        if opening<0 or text.count('\n',begin,opening)>3 or ';' in masked[begin:opening]:
            raise RuntimeError('Located header does not form a supported complete definition')
        depth=0
        closing=None
        for i in range(opening,len(masked)):
            depth += (masked[i]=='{')-(masked[i]=='}')
            if depth==0:
                closing=i
                break
        if closing is None:
            raise RuntimeError('Truncated definition')
        lo=definition['start_line'];hi=text.count('\n',0,closing)+1
        source=''.join(lines[lo-1:hi])
        location_method='researcher_exact_location_balanced_original_collection_only'
    documents.append({'id':definition['name'],'revision':plan['parent'],'path':relative,'function':definition['name'],'start_line':lo,'end_line':hi,'text':source,'function_sha256':hashlib.sha256(source.encode()).hexdigest(),'full_file_sha256':hashlib.sha256(raw).hexdigest(),'location_method':location_method,'semantic_analysis_automated':False,'actual_configuration_proved':False})
record={'parent':plan['parent'],'documents':documents,'prior_locator_failures':failures,'source_files':[{'path':p,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for p,raw in cache.items()],'helper_body_inspection_in_scope':False,'project_model_requests':0,'builds':0,'kernel_runs':0}
(stage/'consumer_functions.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'definitions':[{k:d[k] for k in ['function','path','start_line','end_line','location_method']} for d in documents],'prior_locator_failures':failures},ensure_ascii=False))
