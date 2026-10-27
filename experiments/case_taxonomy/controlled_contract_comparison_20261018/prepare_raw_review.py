"""Copy only terminal complete raw finals to ignored anonymous review inputs."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest_path = HERE / 'review_input_manifest.json'
    if manifest_path.exists():
        raise RuntimeError('preserve first review release')
    manifest = json.loads((HERE/'packet_manifest.json').read_text(encoding='utf-8'))
    seed = 'N28-raw-review-20261018'
    ordered = sorted(manifest['repeats'], key=lambda row:sha((seed+row['repeat']).encode('utf-8')))
    rows, mapping, usage = [], [], []
    folder = OUTER/'模型调用测试/2026-10-18/n28_review_inputs'
    if folder.exists():
        raise RuntimeError('preserve first review folder')
    for task in ordered:
        task_folder = OUTER/task['directory']
        receipt = json.loads((task_folder/'receipt.json').read_text(encoding='utf-8'))
        assert receipt['status'] in {'complete_final_received','response_refused','no_complete_final'}
    folder.mkdir(parents=True)
    for index, task in enumerate(ordered,1):
        task_folder = OUTER/task['directory']
        receipt_raw = (task_folder/'receipt.json').read_bytes()
        receipt = json.loads(receipt_raw)
        name = 'M'+str(index)
        row = {'id':name,'available_complete_final':receipt['status']=='complete_final_received'}
        mapped = {'id':name,'repeat':task['repeat'],'task_directory':task['directory'],
                  'receipt_sha256':sha(receipt_raw),'status':receipt['status']}
        if row['available_complete_final']:
            raw = (task_folder/'final.md').read_bytes()
            path = folder/(name+'_raw.md')
            with path.open('xb') as stream:
                stream.write(raw)
            row.update(path=path.relative_to(OUTER).as_posix(),raw_sha256=sha(raw))
            mapped['raw_sha256'] = sha(raw)
        rows.append(row); mapping.append(mapped)
        message_ids = set()
        events = task_folder/'events.jsonl'
        for line in events.read_text(encoding='utf-8').splitlines() if events.exists() else []:
            event = json.loads(line)
            if event.get('id'): message_ids.add(event['id'])
            if (event.get('message') or {}).get('id'): message_ids.add(event['message']['id'])
        usage.append({'repeat':task['repeat'],**{k:receipt.get(k) for k in ['status','started_at','local_pid','temporary_workdir','elapsed_seconds','visible_reported_tokens','conservative_accounted_tokens','stop_reasons','refusal_observed','final_characters']},'observed_message_ids':sorted(message_ids)})
    manifest_path.write_text(json.dumps({'review_inputs':rows,'source_rubric_sha256':sha((HERE/'source_rubric.json').read_bytes()),
                                        'limits':'Reviewer must assess only raw answers and rubric first, without mapping, usage or actual checker reports; historical exposure disclosed.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'repeat_mapping.json').write_text(json.dumps({'seed':seed,'mapping':mapping,'delivery':usage,
        'visible_reported_tokens':sum(x['visible_reported_tokens'] or 0 for x in usage),
        'conservative_accounted_tokens':sum(x['conservative_accounted_tokens'] or 200000 for x in usage),
        'upstream_inferences_or_actual_billing':'unknown; local processes and observed message identifiers do not count internal upstream recoveries'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'raw_review_released','inputs':rows},ensure_ascii=False))


if __name__ == '__main__':
    main()
