"""Replay the two exact old configured regions, without a source projection."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main():
    from linux_bug_analyze.consumer_obligations import analyze_consumer
    out = HERE/'linux_replay.json'
    if out.exists():
        raise RuntimeError('preserve first Linux replay')
    old = HERE.parent/'aligned_contract_candidates_20261017'
    spec = importlib.util.spec_from_file_location('n29_old_bind',old/'run_candidate_checks.py')
    binding = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(binding)
    raw = (old/'documents.json').read_bytes()
    packet = json.loads(raw)
    bound = binding.bind_documents(packet,{row['path']:(ROOT/row['path']).read_bytes() for row in packet['input_manifest']})
    results = []
    for doc in packet['documents']:
        if doc['id'] not in {'D05','D10'}:
            continue
        assert bound[doc['id']]['status']=='source_bound'
        assert hashlib.sha256(doc['text'].encode('utf-8')).hexdigest()==doc['text_sha256']
        analysis = analyze_consumer(dict(doc))
        results.append({'id':doc['id'],'profile':doc['profile'],'revision':doc['revision'],
                        'function':doc['function'],'configuration_sha256':doc['configuration_sha256'],
                        'source_sha256':doc['text_sha256'],'source_layer':'exact_existing_configured_instrumented_region',
                        'source_rewritten':False,'analysis':analysis})
    assert len(results)==2
    result = {'source_packet_sha256':hashlib.sha256(raw).hexdigest(),'documents':results,
              'manual_source_correspondence_is_not_automatic':True,'new_kernel_runs':0,
              'limits':'No deleting GNU statements, stubs, hand-rewritten C, changed source bytes or supported-prefix promotion.'}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'documents':[{ 'id':row['id'],'status':row['analysis'].get('status'),'reasons':row['analysis'].get('reasons')} for row in results]},ensure_ascii=False))


if __name__=='__main__':
    main()
