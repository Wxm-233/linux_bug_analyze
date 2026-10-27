from pathlib import Path
import importlib.util,json,hashlib,subprocess,socket,time,os,shutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('probe',HERE.parent/'btrfs_watchpoint_probe_20261025/run_step.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 cfg=json.loads((HERE/'prepared.json').read_text());o=cfg['offsets'];entry=cfg['entry']
 out=HERE/'runtime';out.mkdir(exist_ok=False)
 disk=Path('/root/.cache/linux-bug-analyze/btrfs-kernel-watch-20261025.img');assert not disk.exists()
 shutil.copyfile(cfg['blank'],disk);assert hashlib.sha256(disk.read_bytes()).hexdigest()==cfg['blank_sha256']
 sock=Path('/tmp')/f'lba-kernel-{os.getpid()}.sock';assert not sock.exists()
 cmd=['qemu-system-aarch64','-machine','virt','-accel','tcg','-cpu','max','-m','1024','-smp','1','-display','none','-serial',f'file:{out}/boot.log','-monitor','none','-no-reboot','-kernel',cfg['image'],'-initrd',cfg['initrd'],'-append','console=ttyAMA0 rdinit=/init panic=-1 nokaslr','-drive',f'file={disk},format=raw,if=none,id=fs','-device','virtio-blk-device,drive=fs','-nic','none','-S','-gdb',f'unix:{sock},server=on,wait=off']
 save(out/'command.json',cmd);rows=[];r=None
 with (out/'qemu.stderr').open('wb') as err,(out/'rsp.jsonl').open('w') as trace:
  q=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=err)
  try:
   for _ in range(100):
    if sock.exists():break
    time.sleep(.05)
   r=m.RSP(sock,trace);r.s.settimeout(60)
   r.command('qSupported:xmlRegisters=aarch64');r.command('?');r.command('qXfer:features:read:target.xml:0,fff')
   reg=lambda n:int.from_bytes(bytes.fromhex(r.command(f'p{n:x}')),'little')
   read=lambda a,n:int.from_bytes(bytes.fromhex(r.command(f'm{a:x},{n:x}')),'little')
   r.ok(f'Z0,{entry:x},4')
   for encounter in range(8):
    reply=r.command('c');assert r.pc()==entry,reply
    info=reg(0);options=reg(1);ret=reg(30);sp=reg(31)
    r.ok(f'z0,{entry:x},4')
    if options==0:
     r.command('s');r.ok(f'Z0,{entry:x},4');continue
    option=bytes.fromhex(r.command(f'm{options:x},40')).split(b'\0')[0].decode()
    assert option in ('max_inline=2048','max_inline=8192'),option
    superptr=read(info+o['super_pointer'],8);target=superptr+o['disk_sector'];positive=info+o['max_inline'];pointer=info+o['super_pointer']
    row=dict(encounter=encounter,option=option,info=info,super=superptr,entry_sp=sp,return_pc=ret,
       cache=read(info+o['cache'],4),disk_before=read(target,4),positive_events=[])
    for address,length in [(target,4),(pointer,8),(positive,8)]:r.ok(f'Z2,{address:x},{length:x}')
    r.ok(f'Z0,{ret:x},4')
    for _ in range(20):
     reply=r.command('c');pc=r.pc()
     if pc==ret:
      assert reg(31)==sp
      break
     assert 'watch:' in reply,reply
     address=int(reply.split('watch:')[1].split(';')[0],16)
     assert positive<=address<positive+8,('target write or unexpected address',reply,pc)
     before=read(positive,8);r.ok(f'z2,{positive:x},8')
     step=r.command('s');after_pc=r.pc()
     assert 'watch:' not in step and after_pc==pc+4,(step,pc,after_pc)
     row['positive_events'].append(dict(pc=pc,before=before,after=read(positive,8),step_pc=after_pc,targets_remained_armed=True))
     r.ok(f'Z2,{positive:x},8')
    else:raise RuntimeError('stop bound exceeded')
    row.update(disk_after=read(target,4),super_after=read(pointer,8),return_value=reg(0),target_watch_hits=0)
    assert row['positive_events'] and row['disk_before']==row['disk_after'] and row['super_after']==superptr and row['return_value']==0
    rows.append(row);save(out/'progress.json',rows)
    for address,length in [(target,4),(pointer,8),(positive,8)]:r.ok(f'z2,{address:x},{length:x}')
    r.ok(f'z0,{ret:x},4')
    if len(rows)==2:break
    r.ok(f'Z0,{entry:x},4')
   assert [row['option'] for row in rows]==['max_inline=2048','max_inline=8192']
   r.command('D');r.s.close();r=None
   assert q.wait(timeout=120)==0
   boot=(out/'boot.log').read_text();assert 'EXPERIMENT_DONE failures=0' in boot
   save(HERE/'results.json',dict(status='bounded_observation_complete',runs=1,intervals=rows,new_model_calls=0,
        scope='selected parse entry-return virtual addresses under TCG single CPU; not alias/DMA/global coverage',
        image_sha256=cfg['image_sha256'],disk=str(disk),boot_sha256=hashlib.sha256((out/'boot.log').read_bytes()).hexdigest(),
        deadline_admission='insufficient',whole_path='insufficient'))
   print(json.dumps(dict(status='bounded_observation_complete',intervals=len(rows),positive_events=[len(x['positive_events']) for x in rows])))
  finally:
   if r:r.s.close()
   if q.poll() is None:q.terminate()
   try:q.wait(timeout=3)
   except subprocess.TimeoutExpired:q.kill();q.wait()
   if sock.exists():sock.unlink()
if __name__=='__main__':
 try:main()
 except Exception as exc:save(HERE/'failure.json',dict(error=repr(exc)));raise
