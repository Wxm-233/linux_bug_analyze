"""Audit final bridge artifacts and references; no experiments are repeated."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
INNER=HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def need(value,reason):
    if not value:
        raise ValueError(reason)

def main():
    out=HERE/'delivery_manifest.json'; need(not out.exists(),'preserve_delivery_manifest')
    objects=load(HERE/'object_collection.json')['rows']; images=load(HERE/'image_collection.json')['rows']
    need(len(objects)==len(images)==4,'profile_collection_incomplete')
    for row in objects:
        folder=HERE/'objects'/row['profile']
        need(row['compile_returncode']==0 and row['whole_object_byte_equal'] is True,'object_not_reproduced')
        need(sha(folder/'topology.o')==sha(folder/'archived_topology.o')==row['rebuilt_object_sha256'],'object_digest_mismatch')
        need(row['before_sha256']==row['after_sha256'],'old_build_changed')
    for row in images:
        folder=HERE/'images'/row['profile']
        need(sha(folder/'vmlinux')==row['before_sha256']['vmlinux'],'ELF_digest_mismatch')
        need(sha(folder/'boot_image')==row['before_sha256']['image'],'boot_image_digest_mismatch')
        need(sha(folder/'actual_payload')==sha(folder/'expected_payload')==row['payload']['decompressed_sha256'],'payload_digest_mismatch')
    membership=load(HERE/'archive_membership/summary.json')
    need(all(a['topology_entry_exactly_one'] for r in membership['rows'] for a in r['archives']),'archive_membership_incomplete')
    graph_summaries=load(HERE/'graph_results_final.json')
    need(all(r['status']=='supported' for r in graph_summaries),'final_graph_unsupported')
    evidences=[load(HERE/'bridge_evidence_final'/(row['profile']+'.json')) for row in objects]
    need(all(row['graph']['static_initcall_and_CPUHP_callbacks_bound'] for row in evidences),'initialization_link_missing')
    results=load(HERE/'publication_results.json'); inputs=load(HERE/'publication_inputs.json')
    need(len(results['rows'])==len(inputs)==8,'publication_count_mismatch')
    need(all(r['result']['relation_at_observation']=='satisfied' and r['result']['relation_at_deadline']=='insufficient' and r['result']['whole_path']=='insufficient' for r in results['rows']),'scope_promoted')
    need(all(e['historical_textual_macro_origin']=='unknown' for e in evidences),'historical_origin_promoted')
    for item in inputs:
        for doc in item['ledger']['documents'].values():
            path=INNER/doc['path']
            need(sha(path)==doc['sha256'],'review_document_changed')
    controls=load(HERE/'controls.json')
    need(controls['count']==13 and all(c['actual']==c['expected']=='insufficient' for c in controls['controls']),'control_rejection_missing')
    core=INNER/'linux_bug_analyze/contract_protocol.py'
    need(sha(core)==results['common_core_sha256']=='42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e','core_changed')
    artifact_rows={}
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name.startswith('before_') or path.name=='plan_before.md':
            continue
        artifact_rows[str(path.relative_to(HERE))]={'sha256':sha(path),'bytes':path.stat().st_size}
    result={'date':'2026-10-27','status':'bounded_export_source_policy_method_review_complete_not_family_or_independent_validation',
        'new_frozen_CPP_object_compilations':4,'successful_object_compilations':4,'failed_compilations':0,'new_kernel_builds':0,'new_boots':0,'new_model_calls':0,
        'image_payload_extractions_and_full_matches':4,'function_entities_across_builds':sum(len(e['graph']['functions']) for e in evidences),
        'data_entities_across_builds':sum(len(e['graph']['data_objects']) for e in evidences),
        'reused_historical_CPU_publication_contexts':8,'reused_normal_file_reads':sum(len(e['normal_default_readbacks']) for e in evidences),
        'constructed_controls':13,'new_core_evaluations':9,'historical_textual_source_origin_upgrades':0,
        'adapter_failures_preserved':[{'path':'bridge_attempt1/failure.json','kind':'Windows archive-index path separator normalization','before_core_evaluation':True}],
        'graph_versions_preserved':['graph_initial/','linked_graphs/','linked_graphs_final/'],
        'new_defects':0,'formal_independent_positive_normal':[0,0],
        'core_sha256':sha(core),'method_card':'method_card.md','next':'next_cpu_identity_scope.json',
        'open':['historical textual macro provenance','physical topology and initialization truth','first content-consumption identity','CPUHP/concurrent lifecycle stability','automatic requirement inference and independent evaluation'],
        'manual_inputs':['authority and versioned use policy','finite macro/ELF semantic support domain','object and stage roles','legal normal qualification'],
        'artifact_index_scope':'research artifacts at audit time, before working-note sync',
        'artifacts':artifact_rows}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='artifacts'},ensure_ascii=False))

if __name__=='__main__':
    main()
