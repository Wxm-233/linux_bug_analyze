"""Evidence bridge and common-core publication relation, with explicit tiers."""
from pathlib import Path
import copy
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
INNER=HERE.parents[2]
PREVIOUS=HERE.parent/'cpu_source_policy_20261027'
BASE=HERE.parent/'die_arch_contract_20261013/runtime/profiles'
sys.path.insert(0,str(PREVIOUS))
import source_adapter as source
from binding import _identity
from elf64 import ELF64,need
from link_graph import analyze

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def verify_identity(profile,build,object_receipt,image_receipt):
    revision,arch=source.PROFILES[profile]
    for row in [build,object_receipt,image_receipt]:
        need(row['profile']==profile and row['revision']==revision and row['arch']==arch,'profile_revision_architecture_mismatch')
    need(object_receipt['compile_returncode']==0 and object_receipt['whole_object_byte_equal'] is True,'frozen_CPP_object_not_reproduced')
    need(object_receipt['before_sha256']==object_receipt['after_sha256'],'old_object_inputs_changed')
    need(image_receipt['before_sha256']==image_receipt['after_sha256'],'old_image_inputs_changed')
    need(build['image_sha256']==object_receipt['before_sha256']['image']==image_receipt['before_sha256']['image'],'boot_image_identity_mismatch')
    need(build['config_sha256']==object_receipt['before_sha256']['config'],'configuration_identity_mismatch')
    need(object_receipt['before_sha256']['vmlinux']==image_receipt['before_sha256']['vmlinux'],'linked_ELF_identity_mismatch')
    need(image_receipt['payload_matches_linked_kernel'] is True,'image_payload_match_missing')

def collect(profile):
    build,boot=load(BASE/profile/'build.json'),load(BASE/profile/'boot.json')
    obj_receipt=load(HERE/'objects'/profile/'receipt.json')
    image_receipt=load(HERE/'images'/profile/'receipt.json')
    verify_identity(profile,build,obj_receipt,image_receipt)
    paths={'rebuilt_object':HERE/'objects'/profile/'topology.o','archived_object':HERE/'objects'/profile/'archived_topology.o',
           'ELF':HERE/'images'/profile/'vmlinux','image':HERE/'images'/profile/'boot_image',
           'payload':HERE/'images'/profile/'actual_payload','expected_payload':HERE/'images'/profile/'expected_payload'}
    digests={name:sha(path) for name,path in paths.items()}
    need(digests['rebuilt_object']==digests['archived_object']==obj_receipt['before_sha256']['object'],'object_copy_identity_mismatch')
    need(digests['ELF']==obj_receipt['before_sha256']['vmlinux'],'ELF_copy_identity_mismatch')
    need(digests['image']==build['image_sha256'],'image_copy_identity_mismatch')
    need(digests['payload']==digests['expected_payload']==image_receipt['payload']['decompressed_sha256'],'payload_copy_identity_mismatch')
    previous_index={key.replace('\\','/'):value for key,value in load(PREVIOUS/'analysis_attempt2/input_index.json').items()}
    proof_path=PREVIOUS/'analysis_attempt2'/(profile+'_effective_source.json')
    need(sha(proof_path)==previous_index['analysis_attempt2/'+profile+'_effective_source.json'],'reviewed_source_proof_changed')
    proof=load(proof_path)
    need(proof['config_sha256']==build['config_sha256'] and proof['preprocessed_sha256']==obj_receipt['frozen_CPP_sha256'],'CPP_context_mismatch')
    expected={name:row['members'] for name,row in proof['projection']['evidence']['arrays'].items()}
    graph=analyze(ELF64(paths['rebuilt_object']),ELF64(paths['ELF']),expected)
    die_names={'dev_attr_die_id','bin_attr_die_cpus','bin_attr_die_cpus_list'}
    listed=[row['member'] for value in graph['arrays'].values() for row in value['members'] if row['member'] in die_names]
    need(len(listed) in [0,3],'linked_die_group_partial')
    _identity(profile,build,boot)
    old_index=load(HERE.parent/'runtime_source_binding_20261020/binding_inputs.json')['input_sha256']
    old_index={key.replace('\\','/'):value for key,value in old_index.items()}
    for name in ['build.json','boot.json','kernel.config','autoconf.h','qemu_boot.stdout.log']:
        path=BASE/profile/name
        need(sha(path)==old_index[str(path.relative_to(INNER)).replace('\\','/')],'historical_runtime_input_changed:'+name)
    raw=(BASE/profile/'qemu_boot.stdout.log').read_text(encoding='utf-8')
    events=[]
    for line in raw.splitlines():
        start=line.find('{"event":')
        if start>=0:
            events.append(json.loads(line[start:]))
    need(events==boot['observations']['events'],'raw_runtime_JSON_mismatch')
    runtime=source.legacy.project_runtime(events)
    need(runtime['status']=='supported' and [row['cpu'] for row in runtime['cpus']]==[0,1],'runtime_publication_scope_incomplete')
    compiled=proof['projection']['listed_any']; linked=bool(listed)
    need(type(compiled) is bool and compiled==linked,'source_linked_selection_disagrees')
    normal=[]
    if profile.endswith('s390'):
        for cpu in [0,1]:
            expected_reads={'physical_package_id':'-1\n','core_id':'0\n','core_cpus_list':str(cpu)+'\n','thread_siblings_list':str(cpu)+'\n'}
            for name,value in expected_reads.items():
                path='/sys/devices/system/cpu/cpu'+str(cpu)+'/topology/'+name
                matches=[e for e in events if e.get('event')=='file_read' and e.get('path')==path]
                need(len(matches)==1 and matches[0]['status']=='ok' and matches[0]['raw']==value,'documented_default_observation_mismatch')
                normal.append({'cpu':cpu,'attribute':name,'raw':value,'matches_reviewed_default_behavior':True})
    evidence={'profile':profile,'revision':build['revision'],'arch':build['arch'],'config_sha256':build['config_sha256'],
              'image_sha256':build['image_sha256'],'artifact_digests':digests,'source_proof_sha256':sha(proof_path),
              'graph':graph,'compiled_die_any':compiled,'linked_die_any':linked,'runtime_projection':runtime,
              'archived_raw_log_sha256':sha(BASE/profile/'qemu_boot.stdout.log'),'normal_default_readbacks':normal,
              'normal_readbacks_are_reused_archived_observations':True,
              'historical_textual_macro_origin':'unknown','physical_topology_truth':'unknown','first_content_consumption':'unknown',
              'new_object_compilation':True,'new_kernel_build':False,'new_boot':False,'new_model_call':False}
    return evidence,events,expected

def envelope(evidence,cpu,path):
    profile=evidence['profile']; context='cpu.imagebridge.'+profile+'.cpu'+str(cpu['cpu'])
    ident=context+'.publication'; obj=context+'.topology_group'; sample=context+'.probe_window'; deadline=context+'.first_content_consumption'
    origins={key:'researcher_authored' for key in ['scope','relation','symbols','required_claims','authority_kind']}
    symbols={name:{'type':'bool','role':'observation' if name=='published_any' else 'configuration'}
             for name in ['sysfs_enabled','compiled_any','linked_any','published_any']}
    sym=lambda name:{'symbol':name}
    relation={'op':'or','args':[{'op':'not','args':[sym('published_any')]},
                                {'op':'and','args':[sym('compiled_any'),sym('linked_any')]}]}
    contract={'schema':'architecture_contract_v1','id':ident,'revision':evidence['revision'],'authority_kind':'consumer_inferred',
              'sufficient_for_correctness':False,'field_origins':origins,'symbols':symbols,
              'required_claims':{role:'review.'+role for role in source.legacy.CLAIM_ROLES},
              'scope':sym('sysfs_enabled'),'relation':relation}
    docs={}
    for name,document in [('evidence',path),('policy',HERE/'publication_review.md')]:
        docs[name]={'context_revision':evidence['revision'],'source_revision':evidence['revision'],
                    'path':str(document.relative_to(INNER)),'start_line':1,
                    'end_line':len(document.read_text(encoding='utf-8').splitlines()),'sha256':sha(document)}
    refs=lambda name:[{'document':name,'start_line':1,'end_line':docs[name]['end_line']}]
    record={'id':ident+'.record','revision':evidence['revision'],'basis':'archived_runtime','context_id':context,
            'object_id':obj,'sample_event':sample,'deadline_event':deadline,'sample_kind':'sample','facts':{},
            'observation_binding':{'object_id':obj,'event_id':sample,'deadline_id':deadline,'claim':'review.observation'}}
    ledger={'contract_id':ident,'revision':evidence['revision'],'basis':'archived_runtime','context_id':context,
            'field_origins':copy.deepcopy(origins),'documents':docs,'claims':{},
            'compiled_facts_evidence_tier':'new frozen-CPP/byte-equivalent-object/image reconstruction',
            'published_facts_evidence_tier':'old archived per-CPU probe window',
            'historical_textual_origin_upgraded':False}
    for role in source.legacy.CLAIM_ROLES:
        ledger['claims']['review.'+role]={'role':role,'status':'supported','origin':'researcher_review','context_id':context,
            'statement':'Reviewed source/object/image agreement and this exact archived CPU publication sample; no historical textual-source, physical truth or lifecycle claim.',
            'references':refs('policy' if role in ['authority','consumer_requirement'] else 'evidence')}
    ledger['claims']['review.authority'].update(authority_kind='consumer_inferred',supports_requirement='review.consumer_requirement')
    for role,expr in [('applicability','scope'),('consumer_requirement','relation')]:
        ledger['claims']['review.'+role].update(expression=copy.deepcopy(contract[expr]),symbols=copy.deepcopy(symbols))
    for role in ['consumer_requirement','provider_binding','object_binding','deadline_binding']:
        ledger['claims']['review.'+role]['object_id']=obj
    ledger['claims']['review.deadline_binding'].update(event_id=deadline,event_kind='content_consumption',actual_occurrence_proved=False)
    ledger['claims']['review.observation']={'role':'observation_binding','status':'supported','origin':'researcher_review',
        'context_id':context,'statement':'Original per-CPU read window, not the first read or concurrent stability.',
        'references':refs('evidence'),'binding':{'object_id':obj,'event_id':sample,'deadline_id':deadline,'context_id':context,'event_kind':'sample'}}
    values={'sysfs_enabled':True,'compiled_any':evidence['compiled_die_any'],'linked_any':evidence['linked_die_any'],'published_any':cpu['listed_any']}
    for name,value in values.items():
        fact={'symbol':name,'value':value,'role':symbols[name]['role'],'context_id':context}
        record['facts'][name]={'value':value,'claim':'fact.'+name}
        if name=='published_any':
            fact.update(object_id=obj,event_id=sample); record['facts'][name].update(object_id=obj,event_id=sample)
        ledger['claims']['fact.'+name]={'role':'fact','status':'supported','origin':'program_projection','context_id':context,
            'statement':'Fact from the explicitly recorded evidence tier, not newly observed historical macro origin.',
            'references':refs('evidence'),'fact':fact}
    return {'profile':profile,'cpu':cpu['cpu'],'contract':contract,'ledger':ledger,'record':record}

def main():
    out=HERE/'bridge_evidence_final'; out.mkdir(exist_ok=False)
    need(sha(source.CORE)==source.CORE_SHA,'common_core_changed')
    evidence_rows,inputs,results=[],[],[]
    for profile in source.PROFILES:
        evidence,_,_=collect(profile)
        path=out/(profile+'.json'); save(path,evidence); evidence_rows.append(evidence)
        for cpu in evidence['runtime_projection']['cpus']:
            item=envelope(evidence,cpu,path)
            result=source.legacy.evaluate_contract(item['contract'],item['ledger'],item['record'])
            need(result['relation_at_observation']=='satisfied' and result['whole_path']=='insufficient','unexpected_publication_relation')
            inputs.append(item); results.append({'profile':profile,'cpu':cpu['cpu'],'published_die_any':cpu['listed_any'],'result':result})
    save(HERE/'publication_inputs.json',inputs)
    save(HERE/'publication_results.json',{'rows':results,'common_core_sha256':sha(source.CORE),
        'new_core_evaluations':len(results),'new_independent_samples':0,'old_source_policy_runtime_results_unchanged':True})
    print(json.dumps({'profiles':len(evidence_rows),'publication_CPU_contexts':len(results),'satisfied':len(results),
                      'functions_verified':sum(len(r['graph']['functions']) for r in evidence_rows),
                      'data_objects_verified':sum(len(r['graph']['data_objects']) for r in evidence_rows),
                      'reused_normal_file_reads':sum(len(r['normal_default_readbacks']) for r in evidence_rows),
                      'new_boots':0,'historical_textual_origin_upgrades':0}))

if __name__=='__main__':
    main()
