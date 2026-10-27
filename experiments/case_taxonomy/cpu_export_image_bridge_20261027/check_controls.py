"""Constructed binary/evidence mutations. Original files are never edited."""
from pathlib import Path
import copy
import json
import struct

import check_bridge as bridge
from elf64 import ELF64,need
from link_graph import analyze

HERE=Path(__file__).resolve().parent

def main():
    target=HERE/'controls.json'; need(not target.exists(),'preserve_original_controls')
    profile='old_s390'
    obj_path=HERE/'objects'/profile/'topology.o'; image_path=HERE/'images'/profile/'vmlinux'
    obj=ELF64(obj_path); image=ELF64(image_path)
    evidence=bridge.load(HERE/'bridge_evidence_final'/(profile+'.json'))
    graph=evidence['graph']
    proof=bridge.load(bridge.PREVIOUS/'analysis_attempt2'/(profile+'_effective_source.json'))
    arrays={name:row['members'] for name,row in proof['projection']['evidence']['arrays'].items()}
    controls=[]
    def file_offset(address,size):
        rows=[s for s in image.sections if s['type']!=8 and s['flags']&2 and s['address']<=address and address+size<=s['address']+s['size']]
        need(len(rows)==1,'control_address_not_unique')
        return rows[0]['offset']+address-rows[0]['address']
    def binary(name,offset,replacement):
        raw=bytearray(image.raw); before=bytes(raw[offset:offset+len(replacement)])
        need(before!=replacement,'control_did_not_change_input')
        raw[offset:offset+len(replacement)]=replacement
        try:
            analyze(obj,ELF64(image_path,raw=bytes(raw)),arrays)
        except (ValueError,KeyError,IndexError,struct.error,UnicodeDecodeError) as exc:
            controls.append({'name':name,'layer':'constructed ELF bytes below artifact hash gate','expected':'insufficient',
                'actual':'insufficient','file_offset':offset,'before_hex':before.hex(),'after_hex':replacement.hex(),
                'reason':str(exc),'historical_file_edited':False})
            return
        raise ValueError('binary mutation incorrectly accepted:'+name)
    binary('opposite_machine_header',18,(62).to_bytes(2,image.order))
    binary('wrong_byte_order_header',5,b'\x01')
    function=next(row for row in graph['functions'] if row['name']=='die_id_show')
    offset=file_offset(function['linked_address'],1)
    binary('changed_nonrelocated_getter_instruction',offset,bytes([image.raw[offset]^1]))
    attribute=next(row for row in graph['data_objects'] if row['name']=='dev_attr_die_id')
    callback=next(row for row in attribute['relocations_verified'] if row['kind']=='function')
    offset=file_offset(attribute['linked_address']+callback['offset_in_symbol'],8)
    binary('die_attribute_points_to_core_getter',offset,image.unique('core_id_show',2)['value'].to_bytes(8,image.order))
    id_array=graph['arrays']['default_attrs']; index=next(i for i,row in enumerate(id_array['members']) if row['member']=='dev_attr_die_id')
    binary('die_pointer_prematurely_NULL',file_offset(id_array['address']+index*8,8),b'\0'*8)
    field=graph['group_fields']['default_attrs']
    binary('ID_group_points_to_binary_array',file_offset(graph['group_address']+field['offset'],8),graph['arrays']['bin_attrs']['address'].to_bytes(8,image.order))
    literal=next(row for row in attribute['relocations_verified'] if row['kind']=='string')
    binary('wrong_exported_attribute_name',file_offset(literal['linked_target'],1),b'x')
    initcall=next(row for row in graph['data_objects'] if row['name'].startswith('__initcall__'))
    offset=file_offset(initcall['linked_address'],1)
    binary('initcall_target_changed',offset,bytes([image.raw[offset]^1]))
    emitter=next(row for row in function['relocations_verified'] if row.get('symbol')=='sysfs_emit')
    offset=file_offset(function['linked_address']+emitter['offset_in_symbol'],4)
    replacement=bytearray(image.raw[offset:offset+4]); replacement[-1]^=1
    binary('getter_emitter_relocation_changed',offset,bytes(replacement))
    # Upper-layer identity must reject different versions even where a
    # selected getter's generated code could happen to be identical.
    def reject_identity(name,mutate):
        selected='old_x86_64'
        build=bridge.load(bridge.BASE/selected/'build.json')
        o=bridge.load(HERE/'objects'/selected/'receipt.json'); im=bridge.load(HERE/'images'/selected/'receipt.json')
        mutate(build,o,im)
        try:
            bridge.verify_identity(selected,build,o,im)
        except (ValueError,KeyError) as exc:
            controls.append({'name':name,'layer':'constructed artifact identity','expected':'insufficient','actual':'insufficient','reason':str(exc)})
            return
        raise ValueError('identity control incorrectly accepted:'+name)
    reject_identity('other_version_image_receipt',lambda b,o,i:i.update(bridge.load(HERE/'images/fixed_x86_64/receipt.json')))
    reject_identity('different_build_configuration',lambda b,o,i:b.update(config_sha256='0'*64))
    boot=bridge.load(bridge.BASE/profile/'boot.json'); events=copy.deepcopy(boot['observations']['events'])
    one=next(e for e in events if e.get('path')=='/sys/devices/system/cpu/cpu0/topology/die_cpus_list')
    events.remove(one)
    projected=bridge.source.legacy.project_runtime(events)
    need(projected['status']=='insufficient','partial_runtime_group_accepted')
    controls.append({'name':'missing_one_runtime_trio_observation','layer':'constructed archived event list','expected':'insufficient','actual':'insufficient','reason':projected['unknowns']})
    items=bridge.load(HERE/'publication_inputs.json')
    item=copy.deepcopy(next(i for i in items if i['profile']=='fixed_s390' and i['cpu']==0))
    item['ledger']['claims']['review.provider_binding']['status']='unknown'
    verdict=bridge.source.legacy.evaluate_contract(item['contract'],item['ledger'],item['record'])
    need(verdict['relation_at_observation']=='insufficient','unknown_bridge_short_circuited_by_no_publication')
    controls.append({'name':'no_publication_cannot_bypass_unknown_bridge','layer':'constructed review ledger','expected':'insufficient','actual':'insufficient','result':verdict})
    bridge.save(target,{'controls':controls,'all_expected_rejections':True,'count':len(controls),
                        'new_core_evaluations':1,'binary_mutations':9,'identity_mutations':2,
                        'event_mutations':1,'ledger_mutations':1,'new_boots':0,'new_independent_samples':0})
    print(json.dumps({'controls':len(controls),'rejected':len(controls),'historical_files_modified':0,'core_calls':1}))

if __name__=='__main__':
    main()
