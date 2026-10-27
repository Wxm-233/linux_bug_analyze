from pathlib import Path
import json,collections
H=Path(__file__).resolve().parent
def assess(row):
 if any(k not in row for k in ['finalise','stage','sva_enabled']):return 'insufficient'
 if row['finalise']!=0 or row['stage']!=0 or not row['sva_enabled']:return 'outside_supported_test_scope'
 return 'conditional_s1_function_scope'
rows=json.loads((H/'results.json').read_text());output=[]
for row in rows:
 decision=assess(row)
 output.append(dict(args=row['args'],decision=decision,whole_path='insufficient',source='compiled original local functions with doubles'))
 # An unobserved stage cannot be filled from feature-enable success.
 missing=dict(row);del missing['stage'];assert assess(missing)=='insufficient'
with (H/'admission_results.json').open('x') as f:json.dump(dict(policy='researcher registered supported function-test scope, not Linux correctness rule',rows=output,counts=dict(collections.Counter(r['decision'] for r in output)),missing_stage_controls=len(rows),new_hardware_profiles=0),f,indent=2)
print(dict(collections.Counter(r['decision'] for r in output)))
