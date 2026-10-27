from pathlib import Path
import json,re,hashlib,collections
H=Path(__file__).resolve().parent;R=H.parents[3];M=R/'模型调用测试/2026-10-26/smmu_caller_chain'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
receipt=read(M/'receipt.json');assert receipt['status']=='complete_final_received' and not receipt['refusal_observed']
text=(M/'final.md').read_text(encoding='utf-8');blocks=re.findall(r'```json\s*(.*?)```',text,re.S);assert len(blocks)==1
candidate=json.loads(blocks[0]);assert len(candidate)==10
with (M/'obligations.json').open('x',encoding='utf-8') as f:json.dump(candidate,f,ensure_ascii=False,indent=2)
dispositions={
'O1':'Reserved triple authority now supplied by Arm C.a; chain and encoded words confirm it persists. Correct prose: fixed first scale >=1 only for affected residue-one inputs, not all nonleaf inputs.',
'O2':'Normative range formula now located. Current encoded widths checked; overflow, maximum reachable size and full address constraints unresolved.',
'O3':'Reject necessity claim: positive integral page count is a sufficient supported-domain condition, not every nonmultiple forces ffs(0); fixed residue-one guard can cover a partial page. PAGE_SHIFT equality is not mathematically necessary for divisibility. Domain finalisation/restrict_pgsizes adds conditional source evidence.',
'O4':'Original SVA wrapper produces leaf=false and zero-initialized TTL; Arm C.a explains that nonzero TTL narrows required levels. CPU table shape is still unobserved.',
'O5':'Original callback gating exercised: BTM suppresses SMMU TLBI but not ATC; zero/full sentinel uses ASID. Registration and live device capability remain unproved.',
'O6':'Actual ASID/domain routing exercised with doubles; full SVA S1 binding and same-domain lifetime remain open.',
'O7':'Table-shaped wrapper controls have no reserved triple; actual unmap walker not executed. Validity depends on granule and level relation.',
'O8':'Full source batch_add encodes at each call into batch storage; submit requests sync. Not device completion evidence.',
'O9':'Multi-bit same-granule-family bitmap and original callers/wrappers now used. Non-block-aligned start, genuine notifier reachability and leaf gather remain to test.',
'O10':'Normative authority partially supplemented; no hardware execution claim. Full queue and device effects remain insufficient.',
}
assert set(dispositions)=={x['id'] for x in candidate}
save('model_review.json',dict(model='AWS-Claude-Opus-5.5',client='native Claude Code 2.1.301',receipt_sha256=sha(M/'receipt.json'),final_sha256=sha(M/'final.md'),complete_delivery=True,visible_reported_tokens=receipt['visible_reported_tokens'],independent_per_call_ceiling=1000000,not_billing_total=True,not_automatically_adopted=True,dispositions=dispositions,main_text_corrections=['size=end-start equal zero routes to ASID invalidation; avoid ambiguous otherwise-range shorthand','block-aligned iova is not proved by the supplied branch alone','SVA arbitrary positive page count is not proven real reachability for all chosen integers']))
rows=read(H/'chain_results.json');encoded=read(H/'encoding_results.json')['records'];counts=collections.Counter()
for i,r in enumerate(rows):
 mode,pages,ril,btm,e2h,stage=r['args'];cmd=r['commands']
 if r['kind']=='sva_range':
  expected=bool(not btm);assert bool(cmd)==expected
  if btm:counts['btm_no_tlbi_but_atc']+=1
  if not btm and ril:
   assert bool(r['invalid_triples'])==(r['version']=='old')
   counts[r['version']+'_sva_range_exposed']+=1
 if r['kind']=='sva_zero_or_full':
  assert not cmd and r['meta'][6]==0;counts['asid_or_btm_scope_control']+=1
 if r['kind']=='walk_table_shape':assert r['invalid_triples']==0;counts['table_shape_control']+=1
 for j,c in enumerate(cmd):
  e=next(e for e in encoded if e['case']==i and e['command']==j)
  assert e['invalid_range_triple']==(bool(ril) and c[4]==c[5]==c[6]==0)
save('chain_audit.json',dict(counts=dict(counts),encoded_commands=len(encoded),independent_cases=0,all_preconditions_runtime_proved=False))
save('authority.json',dict(url='https://documentation-service.arm.com/static/5f900f54f86e16515cdc090d',document='Arm IHI 0070C.a, SMMUv3.0/3.1/3.2',section='4.4 and 4.4.1.1',printed_pages=[129,130,131],verified='web parsed official PDF text; screenshot requests failed with cache miss',rules=['TG nonzero with NUM/SCALE/TTL all zero is reserved and specified to cause CERROR_ILL','Nonzero TTL narrows the required translation-level match','TG selects translation granule; range is (NUM+1)*2^SCALE*granule','Command consumption is not invalidation completion; CMD_SYNC semantics separate'],limits=['not a live device measurement','no full errata analysis','implementation over-invalidation permission does not alone approve arbitrary software-expanded request']))
print('10 final model obligations reviewed; 120 chain records and 672 encoded commands checked.')
