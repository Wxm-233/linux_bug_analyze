"""Run a small exact historical-mask storage probe on LE and BE userspace."""
from pathlib import Path
import subprocess,json,re,hashlib,shutil

here=Path(__file__).parent
revision='1dc39ed655750d6c679d3ada4adf4a937f2a63fc'
source_path='drivers/scsi/hisi_sas/hisi_sas_v3_hw.c'
header_path='drivers/scsi/hisi_sas/hisi_sas.h'
def git(path):return subprocess.run(['git','-C','/root/repos/linux','show',revision+':'+path],capture_output=True,text=True,check=True).stdout
source=git(source_path);header=git(header_path)
assert re.search(r'__le32\s+dw0\s*;',header)
names=['CMD_HDR_FORCE_PHY_OFF','CMD_HDR_FORCE_PHY_MSK']
defs=[]
for name in names:
    m=re.search(r'^\s*#define\s+'+name+r'\s+(.+)$',source,re.M)
    if not m:raise RuntimeError('historical mask definition missing')
    defs.append('#define '+name+' '+m.group(1))
outdir=here/'repr_v4_20260930';outdir.mkdir(exist_ok=True)
c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
MASK_DEFINITIONS
static uint32_t to_le32(uint32_t x) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
return __builtin_bswap32(x);
#else
return x;
#endif
}
int main(void) {
 uint32_t init[]={0,0x100U};
 for(unsigned i=0;i<2;i++) {
   uint32_t old=to_le32(init[i]),fix=old;
   old |= CMD_HDR_FORCE_PHY_MSK;
   fix |= to_le32(CMD_HDR_FORCE_PHY_MSK);
   uint32_t expected=init[i]|CMD_HDR_FORCE_PHY_MSK;
   unsigned char bytes[4];
   for(unsigned b=0;b<4;b++) bytes[b]=(expected>>(8*b))&255;
   printf("{\\"initial\\":%u,\\"mask\\":%u,\\"old_matches_le_contract\\":%s,\\"fixed_matches_le_contract\\":%s}\\n",init[i],CMD_HDR_FORCE_PHY_MSK,
    memcmp(&old,bytes,4)?"false":"true",memcmp(&fix,bytes,4)?"false":"true");
 }
 return 0;
}
'''.replace('MASK_DEFINITIONS','\n'.join(defs))
cpath=outdir/'historical_mask_probe.c';cpath.write_text(c,encoding='utf-8')
results=[]
for model,compiler,runner in [('x86_64','gcc',[]),('s390x','s390x-linux-gnu-gcc',['qemu-s390x'])]:
    if not shutil.which(compiler) or (runner and not shutil.which(runner[0])):
        results.append({'architecture':model,'status':'unavailable'});continue
    binary=Path('/tmp')/('repr_v4_mask_'+model)
    r=subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-O2','-static',str(cpath),'-o',str(binary)],capture_output=True,text=True)
    if r.returncode:raise RuntimeError(r.stderr)
    raw=subprocess.run(runner+[str(binary)],capture_output=True,text=True,check=True).stdout
    results.append({'architecture':model,'status':'ok','observations':[json.loads(l) for l in raw.splitlines()]})
    binary.unlink()
record={'development_revision':revision,'source_path':source_path,'header_path':header_path,
        'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'header_sha256':hashlib.sha256(header.encode()).hexdigest(),
        'macro_definitions':defs,'generated_source_sha256':hashlib.sha256(cpath.read_bytes()).hexdigest(),
        'results':results,'limit':'Exact historical macro but synthetic 32-bit storage; no real controller, descriptor submission or kernel execution. Development data only.'}
(outdir/'historical_mask_probe_results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results))
