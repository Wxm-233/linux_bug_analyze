"""Bind an attributed known-source review to a frozen generation plan.

The claims below are explicit assistant review, not extracted semantic truth.
The gate checks only the binding/reference completeness and declared states.
"""
import copy
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from authority_gate import evaluate

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent/'contract_assertions_20261001/final_run_01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def source_reference(files, path, needle, before=0, after=0):
    source=files[path]['text']
    assert source.count(needle)==1, (path,needle)
    start=source.index(needle)
    line=source.count('\n',0,start)+1
    lines=source.splitlines()
    count=len(needle.splitlines())
    first=max(1,line-before)
    last=min(len(lines),line+count-1+after)
    return dict(file=path,line=first,quote='\n'.join(lines[first-1:last]),sha256=sha_text(source))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory',type=Path,default=HERE/'development')
    args=parser.parse_args()
    output=args.output_directory
    gate_start=hashlib.sha256((HERE/'authority_gate.py').read_bytes()).hexdigest()
    output.mkdir(exist_ok=True)
    if (output/'results.json').exists():
        raise RuntimeError('preserve existing gate-development evidence')
    plan=read(PRIOR/'parent_plan.json')
    assert len(plan['programs'])==1
    program=plan['programs'][0]
    revision=program['source_revision']
    report=program['validated_inputs']['report']
    files={path:dict(revision=revision,text=text,sha256=sha_text(text))
           for path,text in program['validated_inputs']['files'].items()}
    for item in report['files_read']:
        files[item['path']]['git_blob']=item['git_blob']
    evidence=read(HERE/'source_authority/evidence.json')
    assert evidence['parent_commit']==revision
    for source in evidence['sources']:
        meta=dict(revision=revision,text=source['full_text'],
                  sha256=source['full_file_sha256'],git_blob=source['git_blob_sha1'])
        assert sha_text(meta['text'])==meta['sha256']
        if source['path'] in files:
            assert files[source['path']]['text']==meta['text']
        files[source['path']]=meta
    provider=read(HERE/'provider_projection/source.json')
    consumer=read(HERE/'provider_projection/consumer.json')
    assert provider['revision']==consumer['revision']==revision
    provider_ref=source_reference(files,provider['function']['file'],provider['function']['quote'])
    consumer_ref=source_reference(files,consumer['function']['file'],consumer['function']['quote'])
    payload_ref=source_reference(files,'include/net/bluetooth/hci.h',consumer['structure']['quote'])
    condition_ref=source_reference(files,program['source_file'],
        'cp.tx_len = hdev->le_max_tx_len;',before=5,after=3)
    default_ref=source_reference(files,program['source_file'],
        'hdev->le_max_tx_len = 0x001b;',before=1,after=2)
    card=dict(binding={key:program[value] for key,value in (
        ('revision','source_revision'),('source_file','source_file'),('function','function'),
        ('variable','variable'),('payload_struct','payload_struct'))},
        review=dict(status='reviewed',reviewed_by='Codex source authority review, 2026-10-01',
                    reviewer_kind='assistant',scope='source_contract'),fields=[],
        limitations=['Review claims are attributed assistant source review, not human expert truth.',
                     'Local source schema and Linux saved-command reader; external historical format not proven.',
                     'No runtime device/configuration reachability or full kernel proof.'])
    for field in program['fields']:
        card['fields'].append(dict(name=field['name'],
            producer=dict(struct=field['source_struct'],field=field['source_field'],type=field['source_type']),
            consumer=dict(endian=field['endian'],bits=field['bits']),facts=[
                dict(kind='source_numeric_domain',status='supported',origin='source_review',value='host_numeric',
                     claim='Same-version defaults are numeric constants, successful response uses le16_to_cpu, failure preserves prior values; reviewed direct references do not show pre-encoding.',
                     evidence=[provider_ref,default_ref]),
                dict(kind='consumer_format',status='supported',origin='source_review',value=dict(endian=field['endian'],bits=field['bits']),
                     claim='Local parameter is __le16; actual Linux completion reader uses le16_to_cpu on saved command fields. This supports only the local source contract, not external controller authority.',
                     evidence=[payload_ref,consumer_ref]),
                dict(kind='applicability',status='supported',origin='source_review',
                     value=dict(revision=revision,scope='source_contract'),
                     claim='Applies to this init4 source block under the LE data-length feature condition. Init sequencing and response branches reviewed separately; real runtime reachability remains unknown.',
                     evidence=[condition_ref]),
            ]))
    external=copy.deepcopy(card)
    for field in external['fields']:
        fact=next(fact for fact in field['facts'] if fact['kind']=='consumer_format')
        fact.update(status='conditional',origin='normative_review',
            document_version='Bluetooth Core 5.4: newer corroboration only; applicable historical text unread',
            historical_applicability=dict(status='unknown',claim='Core 5.1 original document body was not obtained as verified text.'),
            claim='Newer SIG text agrees with the source format, but it is not certified as the authority applicable to this historical revision.')
    missing=copy.deepcopy(card)
    missing['fields'][0]['facts'][0]['evidence']=[]
    conflict=copy.deepcopy(card)
    conflict['fields'][0]['facts'][0]['status']='conflict'
    # These controls describe gate behavior, never independent defects.
    cases={'local_source_review':card,'historical_external_pending':external,
           'missing_source_reference':missing,'reported_conflict':conflict,'no_review_card':None}
    expected={'local_source_review':'source_contract_ready','historical_external_pending':'conditional',
              'missing_source_reference':'insufficient','reported_conflict':'conflict','no_review_card':'insufficient'}
    outputs={}
    for name,item in cases.items():
        result=evaluate(plan,item,files)
        assert result['status']==expected[name], (name,result)
        assert not any(result[key] for key in ('machine_contract_proven','runtime_reachability_proven','full_kernel_proven','external_protocol_proven'))
        outputs[name]=result
    assert hashlib.sha256((HERE/'authority_gate.py').read_bytes()).hexdigest()==gate_start
    save(output/'source_files.json',files)
    save(output/'local_source_card.json',card)
    save(output/'external_history_card.json',external)
    save(output/'results.json',dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Known-source attributed review and synthetic gate controls; no independent new label.',
        gate_sha256=hashlib.sha256((HERE/'authority_gate.py').read_bytes()).hexdigest(),
        gate_unchanged_during_run=True,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),outputs=outputs,
        input_plan_sha256=hashlib.sha256((PRIOR/'parent_plan.json').read_bytes()).hexdigest()))
    print('gate development verified:',{name:result['status'] for name,result in outputs.items()})


if __name__=='__main__':
    main()
