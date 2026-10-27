from pathlib import Path
import subprocess,json
H=Path(__file__).resolve().parent;s=(H/'unmap.c').read_text()
s=s.replace('(void)i;walks++;','(void)i;assert(root[a/n]==0);puts("PARENT_CLEAR_OBSERVED");walks++;')
s=s.replace('.queued=mode==5','.queued=mode==5||mode==11').replace('mode<=3||mode==6','mode<=3||mode==6||mode==11').replace('if(mode<=3){','if(mode<=3||mode==11){').replace('if(mode>=7)assert','if(mode>=7&&mode!=11)assert')
s=s.replace('if(!frees)for(int k=0;k<childcount;k++)free(children[k]);free(root);return 0;}','if(!frees){for(int k=0;k<childcount;k++)free(children[k]);}free(root);return 0;}')
(H/'unmap_observed.c').write_text(s);rows=[];builds=[]
for shift in [12,14,16]:
 exe=H/f'observed_{shift}.bin';p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',f'-DPAGE_SHIFT={shift}',str(H/'unmap_observed.c'),'-o',str(exe)],capture_output=True,text=True);builds.append(dict(shift=shift,code=p.returncode,stderr=p.stderr));assert p.returncode==0,p.stderr
 for mode in [1,11]:
  for coherent in [0,1]:
   p=subprocess.run([str(exe),str(mode),str(coherent)],capture_output=True,text=True,timeout=10);assert p.returncode==0,p.stderr
   rows.append(dict(shift=shift,mode=mode,coherent=coherent,stdout=p.stdout))
(H/'observed_results.json').write_text(json.dumps(dict(builds=builds,cases=rows),indent=2));print('3 enhanced builds / 12 runs: parent clear observed at callback; queued nonleaf still flushes')
