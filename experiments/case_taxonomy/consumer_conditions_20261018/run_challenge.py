"""Evaluate the frozen method against a separately frozen finite reference."""
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from linux_bug_analyze.consumer_obligations import analyze_consumer,evaluate_consumer
    out = HERE/'challenge_results.json'
    if out.exists():
        raise RuntimeError('preserve first actual challenge result')
    baseline=json.loads((HERE/'method_baseline.json').read_text(encoding='utf-8'))
    for name,digest in baseline['files'].items():
        assert sha(ROOT/name)==digest,name
    oracle=HERE/'oracle'
    assert sha(oracle/'freeze_manifest.json')==baseline['independent_oracle_manifest_sha256']
    reference=json.loads((oracle/'freeze_manifest.json').read_text(encoding='utf-8'))
    for name,digest in reference['files'].items():
        assert sha(oracle/name)==digest,name
    index=json.loads((oracle/'challenge_index.json').read_text(encoding='utf-8'))
    sources={}; results={}
    for row in index['sources']:
        path=oracle/row['path']
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['sha256']
        analysis=analyze_consumer({'id':row['id'],'path':path.relative_to(ROOT).as_posix(),
                                   'revision':'independent_synthetic_n29_v1','text':raw.decode('utf-8')})
        sources[row['id']]=(row,analysis)
        results[row['id']]={'id':row['id'],'registered_scope_expectation':row['eligibility'],
                            'source_sha256':row['sha256'],'analysis':analysis,
                            'reference_records':0,'evaluated':0,'insufficient':0,'skipped_source_insufficient':0,
                            'return_matches':0,'return_mismatches':0,'first_mismatches':[]}
    diagnoses=Counter(); record_count=0
    with gzip.open(oracle/'expected_records.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            record=json.loads(line); record_count+=1
            metadata,analysis=sources[record['source_id']]
            row=results[record['source_id']]; row['reference_records']+=1
            if analysis.get('status')!='extracted_bounded_conditions':
                row['skipped_source_insufficient']+=1
                continue
            assert analysis['parameters']==metadata['parameters']
            evaluated=evaluate_consumer(analysis,dict(zip(analysis['parameters'],record['args'])))
            if evaluated['status']!='evaluated_under_explicit_inputs':
                row['insufficient']+=1
                for reason in evaluated.get('unknown',[]): diagnoses[reason]+=1
                if len(row['first_mismatches'])<4:
                    row['first_mismatches'].append({'record':record['record'],'kind':'evaluation_insufficient',
                                                     'args':record['args'],'unknown':evaluated.get('unknown')})
                continue
            row['evaluated']+=1
            same=evaluated['return_value']==record['expected']['return']
            row['return_matches' if same else 'return_mismatches']+=1
            if not same and len(row['first_mismatches'])<4:
                row['first_mismatches'].append({'record':record['record'],'kind':'return_mismatch',
                    'args':record['args'],'expected':record['expected'],'actual':evaluated})
    for name,digest in baseline['files'].items(): assert sha(ROOT/name)==digest,name
    for name,digest in reference['files'].items(): assert sha(oracle/name)==digest,name
    rows=list(results.values())
    summary={'source_functions':len(rows),'registered_supported_scope':sum(x['registered_scope_expectation']=='supported_scope' for x in rows),
             'source_extracted':sum(x['analysis'].get('status')=='extracted_bounded_conditions' for x in rows),
             'source_insufficient':sum(x['analysis'].get('status')!='extracted_bounded_conditions' for x in rows),
             'reference_records':record_count,**{key:sum(row[key] for row in rows) for key in
                    ['evaluated','insufficient','skipped_source_insufficient','return_matches','return_mismatches']}}
    result={'status':'frozen_challenge_execution_recorded','summary':summary,'sources':rows,
            'evaluation_insufficient_reasons':dict(diagnoses),'method_baseline_sha256':sha(HERE/'method_baseline.json'),
            'oracle_manifest_sha256':sha(oracle/'freeze_manifest.json'),'method_and_oracle_unchanged':True,
            'scope_control_note':'A generic parse rejection is not evidence that the intended mutable-bound/while semantic gate was exercised.',
            'no_semantic_gain_claim':'Zero evaluated states cannot be reported as zero mismatches/fully correct extraction.',
            'new_Linux_cases':0,'paid_model_calls':0,'r3_resumed':False}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
