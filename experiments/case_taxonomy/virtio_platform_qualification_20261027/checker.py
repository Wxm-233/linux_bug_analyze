"""Bounded parser for this instrumented ARM64 guest input experiment only."""
from pathlib import Path
import json,re,hashlib,copy
H=Path(__file__).resolve().parent
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def require(v,why):
 if not v:raise ValueError(why)
def fields(line):return dict(re.findall(r'(\w+)=([^\s]+)',line))
def assess(text,receipt,expected_image,expected_config):
 try:
  require(receipt.get('code')==0 and not receipt.get('timed_out') and receipt.get('input_sent') is True,'observer_terminal')
  require(receipt['image_sha256']==expected_image and receipt['config_sha256']==expected_config,'build_identity')
  require(receipt['console_sha256']==sha_bytes(text.encode()),'transcript_identity')
  lines=text.splitlines();abi=[fields(x) for x in lines if x.startswith('LBA_ABI ')];platform=[fields(x) for x in lines if x.startswith('LBA_PLATFORM ')]
  require(len(abi)==len(platform)==1,'unique_probe');a=abi[0];p=platform[0]
  dec={k:int(a[k]) for k in ['struct','event','evts','end','lock','ready','align']};base=int(a['base'],16);evt=int(a['evtbase'],16);lock=int(a['lockptr'],16)
  require(evt==base+dec['evts'] and lock==base+dec['lock'] and base%dec['align']==0,'object_layout_binding')
  require(dec['event']==8 and dec['end']-dec['evts']==64*dec['event'] and dec['end']<=dec['lock']<dec['struct'],'event_group_range')
  api=receipt['api_requested'];require(int(p['access'])==api and int(p['packed'])==0 and int(p['custom'])==0 and int(p['ops'],16)==0,'runtime_mapping_qualification')
  ctr=int(p['ctr_safe'],16);line=4<<((ctr>>16)&15);cwg=(ctr>>24)&15
  maps=[(i,fields(x)) for i,x in enumerate(lines) if x.startswith('LBA_MAP ')];recv=[(i,fields(x)) for i,x in enumerate(lines) if x.startswith('LBA_RECV ')];unmaps=[(i,fields(x)) for i,x in enumerate(lines) if x.startswith('LBA_UNMAP ')]
  require(len(maps)==68 and len(recv)==4 and len(unmaps)==(4 if api else 0),'registered_event_count')
  initial=[int(m['phys'],16) for _,m in maps[:64]];require(len(set(initial))==64 and initial==list(range(initial[0],initial[0]+512,8)),'initial_event_addresses')
  for _,m in maps:
   require(m['route']==('api' if api else 'bypass') and int(m['use_api'])==api and int(m['custom'])==0 and int(m['len'])==8,'map_route')
   require(int(m['phys'],16)==int(m['dma'],16),'mapped_target_identity')
  expected=[(1,30,1),(0,0,0),(1,30,0),(0,0,0)];actual=[];lifecycle=[]
  for k,(pos,r) in enumerate(recv):
   v=int(r['event'],16);off=v-evt;require(0<=off<512 and off%8==0 and int(r['len'])==8,'event_token_range');idx=off//8;phys=initial[idx]
   actual.append(tuple(int(r[x]) for x in ['type','code','value']))
   post=[i for i,m in maps[64:] if int(m['phys'],16)==phys];require(len(post)==1 and pos<post[0],'read_then_remap')
   if api:
    matched=[i for i,u in unmaps if int(u['dma'],16)==phys and int(u['len'])==8 and int(u['flags'])==2];require(len(matched)==1 and matched[0]<pos,'unmap_then_read')
   lifecycle.append(dict(event_index=idx,guest_virtual=v,guest_physical=phys,unmap_before_read=bool(api),read_then_remap=True))
  require(actual==expected,'kernel_event_values')
  user=[fields(x) for x in lines if x.startswith('LBA_USER_EVENT ')];require([tuple(int(r[k]) for k in ['type','code','value']) for r in user]==expected,'userspace_roundtrip')
  require('LBA_USER_DONE down=1 up=1 total=4' in text and 'Power down' in text,'guest_done')
  for action in receipt['actions']:
   if 'response' in action:require('return' in action['response'] and 'error' not in action['response'],'qmp_acceptance')
  head_shared=(evt-1)//line==evt//line;tail_shared=(base+dec['end']-1)//line==lock//line
  return dict(status='observed_guest_roundtrip',address_domain='guest virtual/physical, not host hardware DMA',layout=dec,base=base,maintenance_stride=line,cwg_bytes=4<<cwg if cwg else None,dma_cache_align=int(p['dma_cache_align']),coherent=bool(int(p['coherent'])),access_platform=bool(api),custom=False,route='standard_dma_api_direct_by_config_and_null_ops' if api else 'physical_bypass',head_geometry_shared=head_shared,tail_geometry_shared=tail_shared,group_geometry='shared' if head_shared or tail_shared else 'isolated',cache_hazard_applicability='not_applicable_to_observed_coherent_device' if int(p['coherent']) else 'needs_hardware_cache_effect_evidence',lifecycle=lifecycle,hardware_cache_effect='insufficient',whole_path='insufficient_for_noncoherent_cache_contract')
 except (ValueError,KeyError,TypeError,ZeroDivisionError) as e:return dict(status='rejected',reason=str(e))
if __name__=='__main__':
 parent=json.loads((H/'build_complete.json').read_text());fixed=json.loads((H/'fix_build.json').read_text());require(parent['config_sha256']==fixed['config_sha256'],'paired_config')
 names=['parent_api0_serial','parent_api1_ext4','fixed_api0_ext4','fixed_api1_ext4'];rows=[]
 for name in names:
  d=H/name;r=json.loads((d/'receipt.json').read_text());text=(d/'console.log').read_bytes().decode();image=parent['image_sha256'] if name.startswith('parent') else fixed['image_sha256'];out=assess(text,r,image,parent['config_sha256'])
  require(out['status']=='observed_guest_roundtrip',str((name,out)));require(out['group_geometry']==('shared' if name.startswith('parent') else 'isolated'),'layout_pair')
  rows.append(dict(name=name,receipt_sha256=sha_bytes((d/'receipt.json').read_bytes()),console_sha256=r['console_sha256'],**out))
 base=H/'parent_api1_ext4';text=(base/'console.log').read_bytes().decode();r=json.loads((base/'receipt.json').read_text());controls=[]
 for name in ['wrong_image','missing_unmap','unmap_after_read','wrong_event_base','wrong_access_flag','missing_user_release']:
  rr=copy.deepcopy(r);ls=text.splitlines()
  if name=='wrong_image':rr['image_sha256']='0'*64
  elif name=='missing_unmap':ls.pop(next(i for i,l in enumerate(ls) if l.startswith('LBA_UNMAP ')))
  elif name=='unmap_after_read':
   a=next(i for i,l in enumerate(ls) if l.startswith('LBA_UNMAP '));b=next(i for i,l in enumerate(ls) if l.startswith('LBA_RECV '));ls[a],ls[b]=ls[b],ls[a]
  elif name=='wrong_event_base':
   i=next(i for i,l in enumerate(ls) if l.startswith('LBA_ABI '));f=fields(ls[i]);ls[i]=ls[i].replace('evtbase='+f['evtbase'],'evtbase='+format(int(f['evtbase'],16)+8,'x'))
  elif name=='wrong_access_flag':ls=[l.replace('access=1','access=0') if l.startswith('LBA_PLATFORM ') else l for l in ls]
  else:ls=[l for l in ls if l!='LBA_USER_EVENT type=1 code=30 value=0']
  changed='\n'.join(ls)+'\n';rr['console_sha256']=sha_bytes(changed.encode());out=assess(changed,rr,parent['image_sha256'],parent['config_sha256']);require(out['status']=='rejected',name);controls.append(dict(name=name,result=out,receipt=rr,text=changed))
 (H/'runtime_results.json').write_text(json.dumps(rows,indent=2)+'\n');(H/'controls.json').write_text(json.dumps(controls,indent=2)+'\n');print('4 actual guest configurations qualify;6 altered transcript/build controls rejected')
