"""Reproduce narrow corrections against archived build evidence, not full analysis."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=read(raw/'manifest.json');entry=next(x for x in manifest if x['mode']=='parent');folder=raw/'parent'
for n in ('kernel.config','super.i'):assert sha(folder/n)==entry['artifacts'][n]
assert sha(folder/'super.observed.c')==entry['source_after_sha256']
prep=read(HERE/'prepared.json');delivery=read(HERE/'delivery.json')
assert delivery['semantic_review_allowed']
answer=ROOT/prep['current_attempt']/'final.md';assert sha(answer)==delivery['final_sha256']
text=answer.read_text(encoding='utf-8');assert 'CONFIG_BLK_DEV_ZONED=y' in text
config=(folder/'kernel.config').read_text(encoding='utf-8').splitlines()
config_rows=[(i+1,s) for i,s in enumerate(config) if 'CONFIG_BLK_DEV_ZONED' in s]
assert config_rows==[(541,'# CONFIG_BLK_DEV_ZONED is not set')]
pre=(folder/'super.i').read_text(encoding='utf-8').splitlines()
assert 'btrfs_is_zoned' in pre[63297] and 'fs_info->zoned != 0' in pre[63299]
source=(folder/'super.observed.c').read_text(encoding='utf-8').splitlines()
assert 'lba_cache = info->sectorsize' in source[787]
assert 'lba_result = min_t' in source[788]
assert 'lba_disk = btrfs_super_sectorsize' in source[794]
records=[]
for name,lo,hi in [('kernel.config',541,541),('super.i',57063,57066),('super.i',63298,63301),('super.i',68124,68133),('super.observed.c',786,799)]:
 p=folder/name;lines=p.read_text(encoding='utf-8').splitlines()
 records.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),start_line=lo,end_line=hi,
  text='\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1))))
result=dict(status='narrow_facts_verified',revision=entry['revision'],image_sha256=entry['image_sha256'],
 model_claim_config_zoned=True,actual_build_config_zoned=False,config_claim='contradicted',
 helper_body_present=True,helper_presence_does_not_establish_config=True,
 source_event_order=dict(cache_capture=788,arithmetic_consumption=789,reference_sample=795),
 event_order_kind='source ordering only; not machine scheduling or stability proof',
 records=records,model_final_sha256=sha(answer),semantic_decisions_external=True,
 deadline='insufficient',whole_path='insufficient',new_kernel_runs=0)
(HERE/'review_facts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Verified actual config contradicts model claim; source consume/sample events remain distinct')
