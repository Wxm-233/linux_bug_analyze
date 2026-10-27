"""Decode only the registered observation transformation; no pointer lifetime inference."""
import re
class ObservationError(ValueError):pass
def project_operands(boot,fsid,context):
 pattern=r'LBA_CLAMP info=([0-9a-f]+) super=([0-9a-f]+) fsid=([0-9a-f-]+) request=(\d+) cache=(\d+) disk=(\d+) result=(\d+)'
 events=list(re.finditer(pattern,boot))
 native=list(re.finditer(r'BTRFS info \(device vda\): max_inline at (\d+)',boot))
 mounts=list(re.finditer(r'^MOUNT request=(\d+) rc=0 errno=0$',boot,re.M))
 if len(events)!=2 or boot.count('LBA_CLAMP')!=2 or len(native)!=2 or len(mounts)!=2:raise ObservationError('missing/duplicate observation')
 records=[]
 for i,(event,plain,mount) in enumerate(zip(events,native,mounts)):
  info,superptr,uuid,requested,cache,disk,result=event.groups()
  request,cache,disk,result=map(int,(requested,cache,disk,result))
  if uuid!=fsid:raise ObservationError('filesystem mismatch')
  if not int(info,16) or not int(superptr,16) or info==superptr:raise ObservationError('invalid object pointer')
  if not event.end()<plain.start()<mount.start() or (i and events[i].start()<mounts[i-1].end()):raise ObservationError('event interval/order mismatch')
  if request!=[2048,8192][i] or request!=int(mount[1]):raise ObservationError('request mismatch')
  if result!=min(request,cache) or result!=int(plain[1]):raise ObservationError('operand/result mismatch')
  if not 0<cache<2**32 or not 0<disk<2**32:raise ObservationError('invalid geometry value')
  records.append({'event_id':f'{context}:clamp{i+1}','object_id':f'{context}:mount{i+1}:info{info}',
   'info_pointer':info,'super_pointer':superptr,'fsid':uuid,'request':request,
   'consumed_cache':cache,'adjacent_disk_sample':disk,'result':result,
   'cache_equals_adjacent_disk':cache==disk,
   'boot_line':boot.count('\n',0,event.start())+1,
   'basis':'instrumented_runtime_operand_capture','reference_sampling':'after_clamp_not_atomic',
   'whole_path':'insufficient','cross_mount_pointer_lifetime':'not_inferred'})
 return records
