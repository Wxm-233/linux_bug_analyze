from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
old=HERE.parent/'btrfs_fix_watch_20261025'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[old/'run_repeat.py',old/'prepared.json',ROOT/'linux_bug_analyze/linux_bug_analyze/btrfs_watch_facts.py',HERE.parent/'btrfs_watchpoint_probe_20261025/run_step.py']
(HERE/'frozen_inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in paths},indent=2)+'\n',encoding='utf-8')
(HERE/'prepared.json').write_bytes((old/'prepared.json').read_bytes())
s=(old/'run_repeat.py').read_text(encoding='utf-8')
s=s.replace('import importlib.util,json,hashlib,subprocess,socket,time,os,shutil','import importlib.util,json,hashlib,subprocess,socket,time,os,shutil,sys')
s=s.replace("HERE=Path(__file__).resolve().parent","HERE=Path(__file__).resolve().parent\nMODE=sys.argv[1]\nassert MODE in ('default','explicit')\nDIAG=[]")
s=s.replace("out=HERE/'runtime_repeat'","out=HERE/('runtime_'+MODE)").replace("Path('/root/.cache/linux-bug-analyze/btrfs-fix-watch-repeat-20261025.img')","Path('/root/.cache/linux-bug-analyze/btrfs-step-diagnostic-'+MODE+'-20261025.img')")
anchor="   r.command('qSupported:xmlRegisters=aarch64');r.command('?');r.command('qXfer:features:read:target.xml:0,fff')"
extra="""
   bits=r.command('qqemu.sstepbits');mask=r.command('qqemu.sstep');physical=r.command('qqemu.PhyMemMode')
   assert bits=='ENABLE=1,NOIRQ=2,NOTIMER=4' and mask=='0x7' and physical=='0'
   if MODE=='explicit':r.ok('Qqemu.sstep=0x7');assert r.command('qqemu.sstep')=='0x7'
   save(out/'debug_mode.json',dict(mode=MODE,bits=bits,initial_mask=mask,physical_memory_mode=physical))
   def snapshot(pc,positive):
    result={name:r.command(command) for name,command in [('x0','p0'),('x19','p13'),('sp','p1f'),('pc','p20'),('pstate','p21'),('instruction',f'm{pc:x},4'),('positive',f'm{positive:x},8')]}
    return result
"""
assert anchor in s;s=s.replace(anchor,anchor+extra)
anchor="     step=r.command('s');after_pc=r.pc()"
extra="""     pre=snapshot(pc,positive)
     step=r.command('s');after_pc=r.pc()
     post=snapshot(after_pc,positive)
     DIAG.append(dict(original_pc=pc,step_reply=step,after_pc=after_pc,pre=pre,post=post))
     save(out/'step_diagnostics.json',DIAG)
     if after_pc!=pc+4 or 'watch:' in step:
      save(out/'anomaly.json',dict(stop_query=r.command('?'),fresh_pc=r.pc(),latest=DIAG[-1]))"""
assert anchor in s;s=s.replace(anchor,extra)
s=s.replace("HERE/'results_repeat.json'","HERE/('results_'+MODE+'.json')").replace("HERE/'failure_repeat.json'","HERE/('failure_'+MODE+'.json')")
(HERE/'run.py').write_text(s,encoding='utf-8')
notes=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(HERE/'notes_before.json').write_text(json.dumps(dict(before_sha256={n:sha(ROOT/n) for n in notes}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Frozen source; two predefined diagnostic modes, no retry-until-pass')
