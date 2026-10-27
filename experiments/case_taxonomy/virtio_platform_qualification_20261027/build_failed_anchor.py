from pathlib import Path
import subprocess,json,hashlib,difflib,os,time
H=Path(__file__).resolve().parent;CACHE=Path('/root/.cache/linux-bug-analyze/virtio-platform-20261027');SRC=CACHE/'source';OUT=CACHE/'build';REV='db191ba0c8564ff84877e5b1c9553e991feca239'
def save(n,v):(H/n).write_text(json.dumps(v,indent=2)+'\n')
def run(args,label,timeout=1200):
 start=time.monotonic();print(label,flush=True)
 with (H/(label+'.log')).open('w') as log:p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 r=dict(label=label,code=p.returncode,seconds=round(time.monotonic()-start,3),args=args);steps.append(r);save('build_steps.json',steps)
 if p.returncode:raise RuntimeError(label+' failed; preserve log')
steps=[]
if CACHE.exists():raise RuntimeError('preserve existing cache and attempt')
SRC.mkdir(parents=True);OUT.mkdir()
with (H/'archive.stderr').open('wb') as err:
 a=subprocess.Popen(['git','-C','/root/repos/linux','archive',REV],stdout=subprocess.PIPE,stderr=err)
 t=subprocess.run(['tar','-x','-C',str(SRC)],stdin=a.stdout,stderr=err);a.stdout.close();rc=a.wait()
 if t.returncode or rc:raise RuntimeError('source archive')
print('fixed source archive complete',flush=True)
files=['drivers/virtio/virtio_input.c','drivers/virtio/virtio_ring.c'];original={p:(SRC/p).read_text() for p in files}
s=original[files[0]];s=s.replace('#include <linux/input/mt.h>','#include <linux/input/mt.h>\n#include <linux/dma-map-ops.h>\n#include <asm/cache.h>\n#include <asm/cputype.h>\n#include <asm/cpufeature.h>')
needle='\tvi->vdev = vdev;'
probe=r'''
 pr_info("LBA_ABI struct=%zu event=%zu evts=%zu end=%zu lock=%zu ready=%zu align=%zu base=%px evtbase=%px lockptr=%px\n",
  sizeof(*vi), sizeof(vi->evts[0]), offsetof(struct virtio_input, evts),
  offsetof(struct virtio_input, evts) + sizeof(vi->evts),
  offsetof(struct virtio_input, lock), offsetof(struct virtio_input, ready),
  __alignof__(struct virtio_input), vi, vi->evts, &vi->lock);
 pr_info("LBA_PLATFORM parent=%s coherent=%d custom=%d access=%d packed=%d ctr_raw=%llx ctr_safe=%llx dma_min=%d kmalloc_min=%d dma_cache_align=%d\n",
  dev_name(vdev->dev.parent), dev_is_dma_coherent(vdev->dev.parent), !!vdev->map,
  virtio_has_feature(vdev, VIRTIO_F_ACCESS_PLATFORM),
  virtio_has_feature(vdev, VIRTIO_F_RING_PACKED),
  (unsigned long long)read_cpuid_cachetype(),
  (unsigned long long)read_sanitised_ftr_reg(SYS_CTR_EL0),
  ARCH_DMA_MINALIGN, ARCH_KMALLOC_MINALIGN, dma_get_cache_alignment());
'''
if s.count(needle)!=1:raise RuntimeError('probe anchor')
s=s.replace(needle,needle+probe)
needle='\t\t\tspin_unlock_irqrestore(&vi->lock, flags);\n\t\t\tinput_event'
s=s.replace(needle,'\t\t\tpr_info("LBA_RECV event=%px len=%u type=%u code=%u value=%u\\n", event, len, le16_to_cpu(event->type), le16_to_cpu(event->code), le32_to_cpu(event->value));\n'+needle)
(SRC/files[0]).write_text(s)
s=original[files[1]].replace('#include <linux/virtio.h>','#include <linux/virtio.h>\n#include <uapi/linux/virtio_ids.h>\n#include <linux/dma-map-ops.h>')
anchor='/* Map one sg entry. */';helper=r'''
static void lba_map_trace(const struct vring_virtqueue *vq,
 struct scatterlist *sg, dma_addr_t addr, u32 len, const char *route)
{
 static unsigned int count;
 phys_addr_t phys;
 if (vq->vq.vdev->id.device != VIRTIO_ID_INPUT || count++ >= 72)
  return;
 phys = sg_phys(sg);
 pr_info("LBA_MAP route=%s phys=%pa dma=%pad len=%u use_api=%d custom=%d\n",
  route, &phys, &addr, len, vq->use_map_api, !!vq->vq.vdev->map);
}
'''
if s.count(anchor)!=1:raise RuntimeError('map helper anchor')
s=s.replace(anchor,helper+'\n'+anchor)
s=s.replace('\t\t*addr = (dma_addr_t)sg_phys(sg);','\t\t*addr = (dma_addr_t)sg_phys(sg);\n\t\tlba_map_trace(vq, sg, *addr, *len, "bypass");')
anchor='\tif (vring_mapping_error(vq, *addr))\n\t\treturn -ENOMEM;\n\n\treturn 0;'
if s.count(anchor)!=1:raise RuntimeError('map finish anchor')
s=s.replace(anchor,'\tif (vring_mapping_error(vq, *addr))\n\t\treturn -ENOMEM;\n\tlba_map_trace(vq, sg, *addr, *len, "api");\n\n\treturn 0;')
anchor='\tvirtqueue_unmap_page_attrs(&vq->vq,\n\t\t\t\t   extra->addr,'
if s.count(anchor)!=1:raise RuntimeError('unmap anchor')
add=r'''
 if (vq->vq.vdev->id.device == VIRTIO_ID_INPUT)
  pr_info("LBA_UNMAP dma=%pad len=%u flags=%u\n", &extra->addr, extra->len, extra->flags);
'''
s=s.replace(anchor,add+anchor);(SRC/files[1]).write_text(s)
diff=[];manifest=[]
for p in files:
 new=(SRC/p).read_text();diff.extend(difflib.unified_diff(original[p].splitlines(True),new.splitlines(True),fromfile='a/'+p,tofile='b/'+p));b=original[p].encode();blob=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',REV+':'+p],text=True).strip()
 if hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=blob:raise RuntimeError('source identity')
 manifest.append(dict(path=p,original_blob=blob,instrumented_sha256=hashlib.sha256(new.encode()).hexdigest()))
(H/'instrumentation.patch').write_text(''.join(diff));save('source_identity.json',dict(revision=REV,source_root=str(SRC),build_root=str(OUT),files=manifest,observation_effect='extra printk and read-only feature/address reads; scheduling perturbed, no concurrency proof'))
base=['make','-C',str(SRC),'O='+str(OUT),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-']
run(base+['allnoconfig'],'allnoconfig',120)
opts=['EXPERT','PRINTK','BINFMT_ELF','BLK_DEV_INITRD','RD_GZIP','TTY','SERIAL_AMBA_PL011','SERIAL_AMBA_PL011_CONSOLE','ARCH_VIRT','INPUT','INPUT_EVDEV','VIRTIO_MENU','VIRTIO','VIRTIO_MMIO','VIRTIO_INPUT','DEVTMPFS','DEVTMPFS_MOUNT','PROC_FS','SYSFS','TMPFS','SHMEM','DEBUG_INFO_NONE','UNIX98_PTYS']
cmd=[str(SRC/'scripts/config'),'--file',str(OUT/'.config')]
for n in opts:cmd+=['--enable',n]
for n in ['RANDOMIZE_BASE','DEBUG_INFO','GCC_PLUGINS','NET','PCI']:cmd+=['--disable',n]
cmd+=['--set-str','LOCALVERSION','-lba-virtio-platform']
run(cmd,'config_options',30);run(base+['olddefconfig'],'olddefconfig',120)
config=(OUT/'.config').read_text()
for n in ['CONFIG_VIRTIO_INPUT=y','CONFIG_INPUT_EVDEV=y','CONFIG_VIRTIO_MMIO=y','CONFIG_ARCH_VIRT=y']:
 if n not in config:raise RuntimeError('config not enabled '+n)
(H/'kernel.config').write_text(config);run(base+['-j8','Image','usr/gen_init_cpio'],'image_build',1200)
save('build_complete.json',dict(revision=REV,image=str(OUT/'arch/arm64/boot/Image'),image_sha256=hashlib.sha256((OUT/'arch/arm64/boot/Image').read_bytes()).hexdigest(),vmlinux_sha256=hashlib.sha256((OUT/'vmlinux').read_bytes()).hexdigest(),config_sha256=hashlib.sha256((OUT/'.config').read_bytes()).hexdigest()))
print('instrumented fixed-parent ARM64 image built',flush=True)
