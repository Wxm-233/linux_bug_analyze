"""Independent bounded generator probes; only synthetic development inputs."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
MODULES=HERE.parent.parent
sys.path.insert(0,str(MODULES))
import contract_assertion_generator as generator
import structured_hci_single_revision as structured
from outbound_scalar_single_revision_test import REQUEST, SKBUFF

HEADER='struct command { __le16 small; __be32 medium; __le64 large; } __packed;\n'
CORE='struct device { __u16 small; __u32 medium; __u64 large; };\n'


def files_for(converted=False):
    expressions={name:(f'cpu_to_{endian}{bits}(dev->{name})' if converted else f'dev->{name}')
                 for name,endian,bits in [('small','le',16),('medium','be',32),('large','le',64)]}
    return {'driver.c':'#include <net/bluetooth/hci.h>\n#include <net/bluetooth/hci_core.h>\n'
            +'void send(struct device *dev) { struct command cp; '
            +' '.join(f'cp.{name}={expr};' for name,expr in expressions.items())
            +' hci_req_add(req,OP,sizeof(cp),&cp); }',
            structured.HCI:HEADER,structured.HCI_CORE:CORE,
            structured.scalar.REQUEST:REQUEST,structured.scalar.SKBUFF:SKBUFF}


def plan(files,change=None):
    report=structured.analyze_files('driver.c',files,revision='independent_synthetic_audit')
    if change:
        change(report)
    return generator.build_plan(report,files)


def main():
    phase=sys.argv[1] if len(sys.argv)>1 else 'draft'
    if not phase.replace('_','').isalnum():
        raise ValueError('simple phase name required')
    outputs=[]
    baseline=files_for()
    cases=[]
    def add(name,files,expected='refused',change=None):
        cases.append((name,files,expected,change))
    add('mixed_16_32_64_LE_BE_raw',baseline,'generated')
    add('mixed_16_32_64_LE_BE_converted',files_for(True),'generated')
    changed=copy.deepcopy(baseline);changed['driver.c']=changed['driver.c'].replace('cp.large=dev->large;','')
    add('partial_payload',changed)
    changed=copy.deepcopy(baseline);changed['driver.c']=changed['driver.c'].replace('cp.small=dev->small;','cp.small=cpu_to_le16(cpu_to_le16(dev->small));')
    add('double_encoding',changed)
    changed=copy.deepcopy(baseline);changed[structured.HCI_CORE]=CORE.replace('__u16 small','__le16 small')
    add('encoded_source_not_host',changed)
    changed=copy.deepcopy(baseline);changed[structured.HCI]=HEADER.replace('__packed','__packed __aligned(16)')
    add('unknown_layout_suffix',changed)
    changed=copy.deepcopy(baseline);changed[structured.HCI]='#define __packed __attribute__((aligned(16)))\n'+HEADER
    add('known_packed_macro_redefinition',changed)
    changed=copy.deepcopy(baseline);changed[structured.HCI]='#pragma pack(push,1)\n'+HEADER.replace('__packed','')+'#pragma pack(pop)\n'
    add('plain_layout_pack_context',changed)
    changed=copy.deepcopy(baseline);changed['driver.c']=changed['driver.c'].replace('#include <net/bluetooth/hci.h>','#ifdef CONFIG_X\n#include <net/bluetooth/hci.h>\n#endif')
    add('conditional_payload_include',changed)
    changed=copy.deepcopy(baseline);changed['driver.c']=changed['driver.c'].replace('struct command cp;','struct command cp; { alternate_command cp;')+'}'
    add('unknown_typedef_target_shadow',changed)
    changed=copy.deepcopy(baseline);changed['driver.c']=changed['driver.c'].replace('dev->small;','dev->medium;')
    add('mismatched_source_width',changed)
    add('forged_producer_status',baseline,change=lambda report:report['findings'][0].update(status='matched_conversion'))
    add('forged_source_hash',baseline,change=lambda report:report['findings'][0]['assignment'].update(source_sha256='0'*64))
    add('forged_target_type',baseline,change=lambda report:report['findings'][0]['target_declaration'].update(type='__be16'))
    add('forged_assignment',baseline,change=lambda report:report['findings'][0]['assignment'].update(text='cp.small=cpu_to_le16(dev->small);'))
    for name,files,expected,change in cases:
        result=plan(files,change)
        output={'name':name,'expected':expected,'status':result['status'],'rejections':result['rejections']}
        if result['programs']:
            program=result['programs'][0]
            text=generator.emit_c(program)
            source_name=phase+'_'+name+'.c'
            (HERE/source_name).write_text(text,encoding='utf-8')
            (HERE/(phase+'_'+name+'_program.json')).write_text(json.dumps(program,indent=2)+'\n',encoding='utf-8')
            output.update(source=source_name,source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                          fields=[{key:item[key] for key in ('name','endian','bits','original_assignment')} for item in program['fields']])
        output['expected_status_met']=result['status']==expected
        outputs.append(output)
    baseline_program=plan(baseline)['programs'][0]
    for name,mutation in [
        ('emit_field_injection',lambda p:p['fields'][0].update(original_assignment='cp.small=0; injected();')),
        ('emit_payload_injection',lambda p:p['payload_declaration'].update(text='struct command { int x; }; injected();')),
        ('emit_identifier_prefix_injection',lambda p:p.update(generated_identifier_prefix='x; injected();')),
        ('emit_test_values_tamper',lambda p:p['test_values']['64'].__setitem__(0,1<<64)),
    ]:
        program=copy.deepcopy(baseline_program);mutation(program)
        try:
            generator.emit_c(program);refused=False
        except ValueError:
            refused=True
        outputs.append({'name':name,'expected':'emit ValueError','expected_status_met':refused})
    result={'scope':'independent synthetic audit; no held-out or historical target source read',
            'phase':phase,'module_sha256':hashlib.sha256(Path(generator.__file__).read_bytes()).hexdigest(),
            'test_sha256':hashlib.sha256((MODULES/'contract_assertion_generator_test.py').read_bytes()).hexdigest(),
            'outputs':outputs,'all_expected':all(item['expected_status_met'] for item in outputs)}
    (HERE/(phase+'_probe_results.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase':phase,'module_sha256':result['module_sha256'],'all_expected':result['all_expected'],
                      'cases':[{'name':item['name'],'status':item.get('status'),'met':item['expected_status_met']} for item in outputs]},indent=2))


if __name__=='__main__':
    main()
