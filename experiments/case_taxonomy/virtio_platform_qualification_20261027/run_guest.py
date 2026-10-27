from pathlib import Path
import subprocess,json,hashlib,gzip,socket,time,sys,shutil
H=Path(__file__).resolve().parent;CACHE=Path('/root/.cache/linux-bug-analyze/virtio-platform-20261027');OUT=CACHE/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
variant=sys.argv[1] if len(sys.argv)>1 else 'parent'
suffix='_serial' if '--serial-observer' in sys.argv else ''
if '--ext4-observer' in sys.argv:suffix='_ext4'
if variant not in ('parent','fixed'):raise RuntimeError('variant')
image=CACHE/f'{variant}.Image'
if not image.exists():raise RuntimeError('save named image first')
if not (H/'guest_build.json').exists():
 q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra',str(H/'guest.c'),'-o',str(CACHE/'pid1')],capture_output=True,text=True);save(H/'guest_build.json',dict(code=q.returncode,stderr=q.stderr,pid1_sha256=sha(CACHE/'pid1') if q.returncode==0 else None))
 if q.returncode:raise RuntimeError('PID1 build')
 listing='dir /dev 755 0 0\ndir /proc 755 0 0\ndir /sys 755 0 0\nnod /dev/console 600 0 0 c 5 1\nfile /init '+str(CACHE/'pid1')+' 755 0 0\n';(H/'initramfs.list').write_text(listing)
 tool=OUT/'usr/gen_init_cpio'
 if not tool.exists():tool=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/parent-4k/usr/gen_init_cpio')
 b=subprocess.check_output([str(tool),str(H/'initramfs.list')]);(CACHE/'initrd.gz').write_bytes(gzip.compress(b,mtime=0));save(H/'initramfs_identity.json',dict(tool=str(tool),tool_sha256=sha(tool),pid1_sha256=sha(CACHE/'pid1'),initrd_sha256=sha(CACHE/'initrd.gz')))
for api in ([1] if '--only-api1' in sys.argv else [0,1]):
 name=f'{variant}_api{api}'+suffix;d=H/name
 if d.exists():raise RuntimeError('preserve boot attempt '+name)
 d.mkdir();qmp=CACHE/(name+'.sock');console=d/'console.log';live=CACHE/(name+'.console.log')
 args=['qemu-system-aarch64','-M','virt','-cpu','cortex-a57','-smp','1','-m','256M','-nographic','-nodefaults','-serial','stdio','-monitor','none','-no-reboot','-kernel',str(image),'-initrd',str(CACHE/'initrd.gz'),'-append','console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/init panic=-1','-global','virtio-mmio.force-legacy=false','-device',f'virtio-keyboard-device,iommu_platform={"on" if api else "off"},packed=off','-qmp',f'unix:{qmp},server=on,wait=off']
 start=time.monotonic();actions=[];sent=False;timed=False;conn=None
 with live.open('wb') as f:
  p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT)
  while p.poll() is None and time.monotonic()-start<60:
   try:txt=live.read_text(errors='replace')
   except OSError:time.sleep(.1);continue
   if 'LBA_USER_READY fd=' in txt and not sent:
    conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn.settimeout(5);conn.connect(str(qmp));stream=conn.makefile('rwb',buffering=0);hello=json.loads(stream.readline());actions.append(dict(greeting=hello.get('QMP',{})))
    def command(cmd,arguments=None):
     obj={'execute':cmd}
     if arguments is not None:obj['arguments']=arguments
     stream.write(json.dumps(obj).encode()+b'\n')
     while True:
      r=json.loads(stream.readline())
      if 'return' in r or 'error' in r:actions.append(dict(command=obj,response=r));return r
    command('qmp_capabilities')
    for down in [True,False]:
     command('input-send-event',{'events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':'a'}}}]});time.sleep(.2)
    sent=True
   time.sleep(.1)
  if p.poll() is None:p.terminate();timed=True
  try:code=p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();code=p.wait()
  if conn:conn.close()
 shutil.copyfile(live,console)
 record=dict(variant=variant,api_requested=api,args=args,code=code,timed_out=timed,input_sent=sent,seconds=round(time.monotonic()-start,3),image_sha256=sha(image),config_sha256=sha(OUT/'.config'),console_sha256=sha(console),actions=actions,live_console=str(live))
 save(d/'receipt.json',record);print(json.dumps(dict(name=name,code=code,timed_out=timed,input_sent=sent,seconds=record['seconds'])),flush=True)
