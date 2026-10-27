"""Assemble a reviewed, fixed-case source-route card; not a preprocessor."""
from pathlib import Path
import hashlib,json,posixpath

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q(source,start,end):
    p=Path(source['saved_path']);lines=p.read_text(encoding='utf-8').splitlines()
    raw=p.read_bytes();assert sha(p)==source['sha256']
    oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert oid==source['blob_sha1']
    return dict(saved_path=str(p),source_path=source['source_path'],revision=source['revision'],sha256=source['sha256'],blob_sha1=oid,
        start_line=start,end_line=end,text='\n'.join(lines[start-1:end]))

inputs=load(HERE/'inputs_pre.json')
manifest=load(HERE/'export_manifest.json')
assert manifest['saved_files']==2 and manifest['missing_files']==0
sources={o['role']:o for o in manifest['observations']}
old=inputs['old_source']
uapi=load(BASE/'encoded_length_contract_20261008/header_manifest.json')['source']
assert uapi['revision']==old['revision']==inputs['revision']
make=sources['top_makefile'];wrapper=sources['public_wrapper']
quotes=dict(old_include=q(old,10,10),final_make_invocation=q(make,224,225),source_tree_roots=q(make,232,253),
    user_include=q(make,503,510),kernel_include=q(make,512,519),kernel_cpp_define=q(make,527,527),
    exported_settings=q(make,543,546),additional_user_flags=q(make,1022,1025),
    wrapper_guard_and_includes=q(wrapper,11,20),uapi_guard=q(uapi,17,18),uapi_tag=q(uapi,122,127),
    old_count_consumers=q(old,72,81))
assert quotes['old_include']['text']=='#include "../include/linux/if_pppox.h"'
assert '#include <uapi/linux/if_pppox.h>' in quotes['wrapper_guard_and_includes']['text']
assert '-I$(objtree)/include' in quotes['kernel_include']['text']
assert '$(if $(building_out_of_srctree),-I$(srctree)/include)' in quotes['kernel_include']['text']
assert '__be16 tag_len;' in quotes['uapi_tag']['text']
token='../include/linux/if_pppox.h'
assert posixpath.normpath(posixpath.join('include',token))=='include/linux/if_pppox.h'
assert posixpath.normpath(posixpath.join('include','uapi/linux/if_pppox.h'))==uapi['source_path']
prior=load(BASE/'driver_binding_20261009/binding_card.json')
conditions=prior['conditions']
assert len(conditions)==12 and all(c['proven'] is False for c in conditions)
for c in conditions:
    if c['name']=='actual_declaration_binding':
        c['evidence_level']='conditional_static_source_route_supported_not_preprocessed'
        c['reason']='The visible source-root include setting normalizes the complete token to the public wrapper, which includes the same-revision UAPI. Effective command/search precedence/guard state are not observed.'

card=dict(revision=inputs['revision'],card_method='fixed-case reviewed source/text checks and POSIX path normalization; not automatic Make/C semantic resolution',
    include_token=token,primary_private_path='drivers/staging/r8188eu/include/linux/if_pppox.h',primary_private_path_status='missing_from_previous_fixed_batch',
    conditional_static_route_supported=True,
    route_contexts=[
        dict(context='in_source_tree_final_make_invocation',source_variables='srctree=.; objtree=.; building_out_of_srctree empty',
            visible_flag='-I$(objtree)/include',source_relative_search_root='include',
            normalized_complete_token='include/linux/if_pppox.h',assumption='objtree is the source tree and visible LINUXINCLUDE participates in effective C invocation'),
        dict(context='out_of_source_tree_final_make_invocation',source_variables='srctree=.. or abs_srctree; objtree=.; building_out_of_srctree=1',
            visible_flag='$(if $(building_out_of_srctree),-I$(srctree)/include)',source_relative_search_root='include',
            normalized_complete_token='include/linux/if_pppox.h',assumption='the conditional source-root include flag is effective in the actual C invocation')],
    wrapper_chain=dict(public_header='include/linux/if_pppox.h',include_text='#include <uapi/linux/if_pppox.h>',
        same_source_root_candidate='include/uapi/linux/if_pppox.h',same_revision_saved_uapi=True,
        target_declaration='struct pppoe_tag: __be16 tag_type; __be16 tag_len; char tag_data[0]; packed attribute',
        earlier_search_roots_or_guard_state_checked=False),
    route_prerequisites=[
        'Final normal Make invocation and expected source/object tree relation.',
        'Visible LINUXINCLUDE is carried into effective target C invocation with no overriding command-line value.',
        'No earlier quote, architecture, generated or additional search root supplies a competing complete-token header.',
        'Public and UAPI guards permit the required declarations; transitive headers/macros do not change their meaning.'],
    actual_preprocessing_certified=False,actual_build_certified=False,actual_layout_certified=False,complete_length_certified=False,
    conditions=conditions,source_quotes=quotes,
    implications_for_automated_checks=dict(
        supported='A same-revision source-route witness can accompany the BE16-to-host-count candidate and prevent silent standard-header substitution.',
        not_supported='No mandatory C assertion, complete length/capacity proof, actual compiler binding, hardware result or generalization claim follows from this card.',
        proposed_next='Implement a small source-route evidence gate on saved declarations: separate conditional candidate from insufficient, validate positive/ambiguous/missing synthetic fixtures, then choose whether real preprocessing is necessary.'),
    new_confirmed_cases=0,independent_positive_cases=0)
target=HERE/'route_card.json';assert not target.exists()
target.write_text(json.dumps(card,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(card_sha256=sha(target),source_quote_records=len(quotes),conditional_static_route_supported=True,
    actual_preprocessing_certified=False,new_confirmed_cases=0),ensure_ascii=False))
