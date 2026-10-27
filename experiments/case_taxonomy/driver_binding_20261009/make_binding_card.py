"""One reviewed source card with explicit text checks, not a general Kbuild parser."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,re

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quote(source,start,end):
    raw=Path(source['saved_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==source['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']
    lines=raw.decode('utf-8').splitlines()
    assert 0<start<=end<=len(lines)
    return {**{k:source[k] for k in ['saved_path','source_path','revision','sha256','blob_sha1']},
        'start_line':start,'end_line':end,'text':'\n'.join(lines[start-1:end])}
inputs=load(HERE/'inputs_pre.json');manifest=load(HERE/'export_manifest.json')
assert manifest['status']=='fixed_requests_complete'
records={o['role']:o for o in manifest['observations']}
# These are recorded expectations after reading the fixed batch; mismatch stops.
assert records['private_header']['status']=='missing'
assert records['makefile']['status']==records['kconfig']['status']=='saved'
mf=records['makefile'];kc=records['kconfig'];old=inputs['old_source']
mlines=Path(mf['saved_path']).read_text(encoding='utf-8').splitlines()
klines=Path(kc['saved_path']).read_text(encoding='utf-8').splitlines()
assert len(mlines)==55 and len(klines)==16
assert mlines[1].strip()=='r8188eu-y = \\'
assert mlines[35].strip()=='core/rtw_br_ext.o \\'
assert mlines[54].strip()=='obj-$(CONFIG_R8188EU) := r8188eu.o'
assert klines[1]=='config R8188EU' and klines[2].strip().startswith('tristate ')
assert klines[3].strip()=='depends on WLAN && USB && CFG80211' and klines[4].strip()=='depends on m'
assert not any(re.search(r'(?:^|\s)-I|(?:subdir-)?ccflags-y|CFLAGS_|LINUXINCLUDE',line) for line in mlines)
conditions=deepcopy(load(BASE/'encoded_length_composition_20261009/runs/initial/results.json')['evidence']['condition_evidence_card'])
for condition in conditions:
    condition['proven']=False
    if condition['name']=='actual_declaration_binding':
        condition['evidence_level']='unresolved_primary_relative_path_missing'
        condition['reason']='The direct private path is absent; final quote/-I resolution and wrapper declarations were not retrieved.'
citations=dict(include_token=quote(old,inputs['include']['start_line'],inputs['include']['end_line']),
    local_aggregate=quote(mf,2,3),target_member=quote(mf,35,37),config_object_entry=quote(mf,55,55),
    local_makefile_context=quote(mf,1,55),local_config=quote(kc,2,10))
card=dict(revision=inputs['revision'],scope='one already-read driver, three predefined local Git paths',
    card_construction='reviewed fixed-source text checks; not a general Kbuild analyzer',
    include_evidence=dict(token=inputs['include']['token'],primary_relative_path=inputs['include']['primary_relative_path'],
        primary_relative_path_status='missing',raw_missing_response=records['private_header']['response_header'],
        actual_include_binding_certified=False,final_header_resolution='unresolved',
        private_path_missing_implies_unbuildable=False,standard_uapi_binding_assumed=False,
        possible_other_quote_or_I_search='not inspected; do not conclude a particular wrapper is used'),
    local_build_evidence=dict(member_object='core/rtw_br_ext.o',aggregate_variable='r8188eu-y',aggregate_object='r8188eu.o',
        object_selector='obj-$(CONFIG_R8188EU)',local_object_chain_text_observed=True,
        local_explicit_include_flags=[],global_include_flags='not retrieved',
        parent_kbuild_or_kconfig_entry='not retrieved',actual_CONFIG_R8188EU='unknown',actual_build_certified=False),
    local_config_evidence=dict(symbol='R8188EU',type='tristate',depends_on=['WLAN && USB && CFG80211','m'],
        selected_symbols=['WIRELESS_EXT','WEXT_PRIV','LIB80211','LIB80211_CRYPT_WEP','LIB80211_CRYPT_CCMP'],
        module_constraint_text_observed=True,current_configuration_certified=False,all_architecture_support_certified=False),
    conditions=conditions,source_quotes=citations,
    unresolved=['Final quote/-I search and declaration/wrapper chain.',
        'Parent build/config inclusion, complete flags, generated headers and actual CONFIG values.',
        'Actual typedef/storage widths, CHAR_BIT, packed/zero-array layout and conversion implementations.',
        'Runtime reachability, count range/overflow, complete length and external contract applicability.'],
    new_confirmed_cases=0,independent_positive_cases=0,actual_runtime_path_certified=False,
    complete_length_contract_certified=False)
target=HERE/'binding_card.json';assert not target.exists()
target.write_text(json.dumps(card,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(card_sha256=sha(target),fixed_file_requests=3,git_commands=2,
    local_object_chain_text_observed=True,actual_include_binding_certified=False,actual_build_certified=False),ensure_ascii=False))
