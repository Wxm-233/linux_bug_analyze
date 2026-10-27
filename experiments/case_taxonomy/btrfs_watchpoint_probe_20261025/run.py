"""Bounded local RSP watchpoint capability test, never a Btrfs verdict."""
from pathlib import Path
import hashlib,json,socket,subprocess,time,os
HERE=Path(__file__).resolve().parent
OUT=HERE/'runtime'
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
class RSP:
 def __init__(self,path,trace):
  self.s=socket.socket(socket.AF_UNIX);self.s.settimeout(8);self.s.connect(str(path));self.trace=trace
 def readn(self,n):
  result=b''
  while len(result)<n:
   chunk=self.s.recv(n-len(result))
   if not chunk:raise RuntimeError('RSP disconnected')
   result+=chunk
  return result
 def command(self,text):
  data=text.encode();self.s.sendall(b'$'+data+b'#'+f'{sum(data)%256:02x}'.encode())
  while True:
   c=self.readn(1)
   if c==b'$':break
   if c==b'-':raise RuntimeError('negative acknowledgement')
  packet=b''
  while True:
   c=self.readn(1)
   if c==b'#':break
   packet+=c
  assert int(self.readn(2),16)==sum(packet)%256
  self.s.sendall(b'+')
  decoded=bytearray();i=0
  while i<len(packet):
   if packet[i]==125:i+=1;decoded.append(packet[i]^32)
   elif packet[i]==42:i+=1;decoded.extend([decoded[-1]]*(packet[i]-29))
   else:decoded.append(packet[i])
   i+=1
  response=decoded.decode()
  self.trace.write(json.dumps(dict(command=text,response=response))+'\n');self.trace.flush()
  return response
 def ok(self,s):assert self.command(s)=='OK',s
 def memory(self,address):return int.from_bytes(bytes.fromhex(self.command(f'm{address:x},4')),'little')
 def pc(self):return int.from_bytes(bytes.fromhex(self.command('p20')),'little')
def main():
 OUT.mkdir(exist_ok=False)
 subprocess.run(['aarch64-linux-gnu-as','-o',str(OUT/'probe.o'),str(HERE/'probe.S')],check=True)
 subprocess.run(['aarch64-linux-gnu-ld','-Ttext=0x40080000','-e','_start','-o',str(OUT/'probe.elf'),str(OUT/'probe.o')],check=True)
 nm=subprocess.check_output(['aarch64-linux-gnu-nm','-n',str(OUT/'probe.elf')]).decode()
 (OUT/'symbols.txt').write_text(nm)
 symbols={line.split()[2]:int(line.split()[0],16) for line in nm.splitlines() if len(line.split())==3}
 (OUT/'disassembly.txt').write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d',str(OUT/'probe.elf')]))
 version=subprocess.check_output(['qemu-system-aarch64','--version']).decode()
 rows=[]
 for name,address,length,expected in [('exact',0x40100000,4,3),('overlap',0x40100002,2,3),('wrong_address',0x40100008,4,0),('disabled',None,None,0)]:
  folder=OUT/name;folder.mkdir();sock=Path('/tmp')/f'lba-watch-{os.getpid()}-{name}.sock'
  assert not sock.exists()
  cmd=['qemu-system-aarch64','-machine','virt','-accel','tcg','-cpu','max','-m','128','-smp','1','-display','none','-serial','none','-monitor','none','-nic','none','-kernel',str(OUT/'probe.elf'),'-S','-gdb',f'unix:{sock},server=on,wait=off']
  with (folder/'qemu.stderr').open('wb') as err,(folder/'rsp.jsonl').open('w') as trace:
   q=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=err)
   r=None
   try:
    for _ in range(100):
     if sock.exists():break
     if q.poll() is not None:raise RuntimeError('QEMU exited')
     time.sleep(.05)
    r=RSP(sock,trace)
    r.command('qSupported:xmlRegisters=aarch64');r.command('?')
    r.command('qXfer:features:read:target.xml:0,fff')
    r.ok(f'Z0,{symbols["armed"]:x},4');r.ok(f'Z0,{symbols["finished"]:x},4')
    first=r.command('c');assert r.pc()==symbols['armed']
    assert r.memory(0x40100000)==0x1234
    r.ok(f'z0,{symbols["armed"]:x},4')
    if address is not None:r.ok(f'Z2,{address:x},{length:x}')
    stops=[]
    for _ in range(8):
     reply=r.command('c');pc=r.pc();value=r.memory(0x40100000)
     stops.append(dict(reply=reply,pc=pc,target_value=value))
     if pc==symbols['finished']:break
    else:raise RuntimeError('stop bound exceeded')
    hits=[s for s in stops if 'watch:' in s['reply']]
    assert len(hits)==expected,(name,stops)
    if expected:
     assert [s['pc'] for s in hits]==[symbols[n] for n in ('same_write','changed_write','restored_write')],hits
    assert r.memory(0x40100000)==r.memory(0x40100004)==0x1234
    rows.append(dict(name=name,command=cmd,watch_address=address,watch_length=length,stops=stops,hits=len(hits),passed=True))
    save(folder/'result.json',rows[-1])
   finally:
    if r:r.s.close()
    q.terminate()
    try:q.wait(timeout=3)
    except subprocess.TimeoutExpired:q.kill();q.wait()
    if sock.exists():sock.unlink()
 save(HERE/'results.json',dict(status='passed',qemu_version=version,probe_sha256=hashlib.sha256((OUT/'probe.elf').read_bytes()).hexdigest(),symbols=symbols,runs=rows,
      model_calls=0,linux_boots=0,btrfs_mounts=0,scope='synthetic flat-memory single-CPU TCG guest stores only'))
 print(json.dumps(dict(status='passed',synthetic_boots=len(rows),hits=[r['hits'] for r in rows])))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  save(HERE/'failure.json',dict(error=repr(exc)));raise
