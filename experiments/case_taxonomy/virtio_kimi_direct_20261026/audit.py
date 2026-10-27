from pathlib import Path
import json
H=Path(__file__).resolve().parent;rows=json.loads((H/'results.json').read_text());out=[]
for r in rows:
 lines=r['stdout'].splitlines();mode=r['mode'];result=list(map(int,lines[-1].split()[1:]));addr,bounce,dev,cpu,allcpu,bouncecpu,clean,unmap=result
 if cpu:assert lines.index(next(x for x in lines if x.startswith('ARCH_CPU ')))<lines.index('CPU_ALL')<lines.index('SWIOTLB_CPU_HELPER')<lines.index('MARK_CLEAN')<lines.index('SWIOTLB_UNMAP_HELPER')
 if bouncecpu and not cpu:assert lines.index('SWIOTLB_CPU_HELPER')<lines.index('MARK_CLEAN')<lines.index('SWIOTLB_UNMAP_HELPER')
 if addr==(1<<64)-1:assert not unmap
 out.append(dict(mode=mode,coherent=r['coherent'],skip=r['skip'],route='mapping_error' if addr==(1<<64)-1 else 'bounce_helper' if bounce else 'MMIO_control' if mode>=7 else 'direct_address',sequence='pass_local_callbacks',virtinput_attrs_scope='attrs0_shape' if mode<7 and not r['skip'] else 'synthetic_attribute_control',actual_dma_target='insufficient',cache_effect='insufficient',whole_path='insufficient'))
(H/'audit.json').write_text(json.dumps(out,indent=2));print('40 traces audited; helper calls not equated with actual bounce or cache effects')
