"""Run frozen bounded syntax components on the two unchanged consumer functions."""
from pathlib import Path
import hashlib
import json
import sys

stage=Path(__file__).resolve().parent
root=stage.parents[2]
sys.path.insert(0,str(root))
from linux_bug_analyze.source_conditions import analyze_function
from linux_bug_analyze.forward_guards import extract_forward_paths

target=stage/'structural_diagnostic.json'
if target.exists():
    raise SystemExit('Keep the first diagnostic result; do not overwrite.')
material=json.loads((stage/'consumer_functions.json').read_text(encoding='utf-8'))
items=[]
for document in material['documents']:
    assert hashlib.sha256(document['text'].encode()).hexdigest()==document['function_sha256']
    local=analyze_function(document,annotations=('__init',))
    forward=extract_forward_paths(document)
    items.append({'function':document['function'],'source':local,'forward':forward,'original_source_unchanged':True,'new_model_claim':False,'actual_dependency_effect_proved':False})
record={'stage':'already_read_auxiliary_development','items':items,'frozen_components_modified':False,'macros_deleted':False,'new_type_stubs_added':False,'whole_contract':'insufficient','new_independent_positive':0,'new_independent_normal':0}
target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'function':i['function'],'source_status':i['source']['status'],'source_reasons':i['source']['reasons'],'source_call_inventory':[{'callee':c['callee'],'line':c['line'],'arguments':c['arguments']} for c in i['source']['calls']],'forward_status':i['forward']['status'],'forward_reasons':i['forward']['reasons']} for i in items],ensure_ascii=False))
