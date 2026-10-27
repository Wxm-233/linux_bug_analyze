"""Compile emitted synthetic C and independently verify actual stdout bytes."""
import hashlib
import json
import subprocess
import sys
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent


def run(args):
    p=subprocess.run(args,capture_output=True,text=True)
    return {'command':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}


def main():
    phase=sys.argv[1] if len(sys.argv)>1 else 'draft'
    if not phase.replace('_','').isalnum():raise ValueError('simple phase required')
    output={'phase':phase,'scope':'synthetic reduced C only; no kernel/controller execution',
            'layout_context':[],'programs':[]}
    for stem in ('layout_context_proof','mixed_layout_proof'):
        layout_source=HERE/(stem+'.c')
        layout_exe=HERE/(phase+'_'+stem)
        compile_layout=run(['gcc','-std=c11','-Wall','-Wextra','-Werror',str(layout_source),'-o',str(layout_exe)])
        compile_layout['source_sha256']=hashlib.sha256(layout_source.read_bytes()).hexdigest()
        output['layout_context'].append(compile_layout)
        if not compile_layout['exit_code']:output['layout_context'].append(run([str(layout_exe)]))
    probes=json.loads((HERE/(phase+'_probe_results.json')).read_text())
    for item in probes['outputs']:
        if item.get('status')!='generated':continue
        source=HERE/item['source']
        plan=json.loads((HERE/(phase+'_'+item['name']+'_program.json')).read_text())
        schemas={field['name']:field for field in plan['fields']}
        for target,compiler,flags,runner,endian in [
            ('native_ubsan','gcc',['-fsanitize=undefined','-fno-sanitize-recover=all'],[], 'little'),
            ('s390x','s390x-linux-gnu-gcc',['-static'],['qemu-s390x'], 'big')]:
            binary=HERE/(phase+'_'+item['name']+'_'+target)
            compiled=run([compiler,'-std=c11','-O1','-Wall','-Wextra','-Werror',*flags,str(source),'-o',str(binary)])
            record={'case':item['name'],'target':target,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'compile':compiled}
            if compiled['exit_code']:
                record['verification']='compile_failed';output['programs'].append(record);continue
            executed=run([*runner,str(binary)])
            record['run']=executed
            errors=[];summary=defaultdict(Counter);rows=[]
            if executed['exit_code']:errors.append('nonzero process exit')
            if executed['stderr']:errors.append('runtime stderr (including UBSan) must be inspected')
            for line in executed['stdout'].splitlines():
                row=json.loads(line);rows.append(row)
                if row['host_endian']!=endian:errors.append('unexpected actual target endian')
                if row['kind']=='layout':
                    if row['size']!=14:errors.append('mixed packed payload size differs from 14')
                    continue
                schema=schemas[row['field']]
                expected_value=row['value'] if row['case_field']==row['field'] else 0
                width=schema['bits']//8
                expected_bytes=expected_value.to_bytes(width,'little' if schema['endian']=='le' else 'big')
                actual_bytes=bytes.fromhex(row['actual_bytes'])
                decoded=int.from_bytes(actual_bytes,'little' if schema['endian']=='le' else 'big')
                ok=actual_bytes==expected_bytes and decoded==expected_value
                if row['width']!=width or row['expected_value']!=expected_value:errors.append('C source input/width inconsistent')
                if bytes.fromhex(row['expected_bytes'])!=expected_bytes or row['decoded']!=decoded or row['pass']!=ok:
                    errors.append('C result disagrees with independent Python byte/value oracle')
                expected_offset={'small':0,'medium':2,'large':6}[row['field']]
                if row['offset']!=expected_offset:errors.append('field offsetof differs from mixed packed schema')
                summary[row['variant']]['pass' if ok else 'fail']+=1
                if row['variant']=='reference' and not ok:errors.append('reference conversion failed')
                if row['value']==0 and not ok:errors.append('zero control did not mask direct-copy difference')
            record.update(verification='passed' if not errors else 'failed',errors=errors,
                          summary={key:dict(value) for key,value in summary.items()},rows=rows)
            output['programs'].append(record)
    output['module_sha256']=probes['module_sha256'];output['test_sha256']=probes['test_sha256']
    output['all_verified']=all(item['verification']=='passed' for item in output['programs']) and all(not item['exit_code'] for item in output['layout_context'])
    (HERE/(phase+'_c_results.json')).write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase':phase,'all_verified':output['all_verified'],
        'programs':[{key:item[key] for key in ('case','target','verification','summary')} for item in output['programs']]},indent=2))


if __name__=='__main__':main()
