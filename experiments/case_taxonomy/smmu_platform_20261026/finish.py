from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
q=json.loads((H/'qtest.json').read_text(encoding='utf-8'));words=[int(x,16) for x in re.findall(r'^OK (0x[0-9a-f]+)$',q['stdout'],re.M)];assert len(words)==6
header=H.parent/'smmu_chain_20261026/source/02_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.h';hs=header.read_text(encoding='utf-8')
def field(name,index):
 line=re.search(r'^#define '+name+r'\s+([^\n]+)',hs,re.M)[1].strip()
 if line.startswith('GENMASK'):
  hi,lo=map(int,re.findall(r'\d+',line));mask=((1<<(hi-lo+1))-1)<<lo
 else:
  lo=int(re.fullmatch(r'\(1 << (\d+)\)',line)[1]);mask=1<<lo
 return (words[index]&mask)>>lo
decoded={n:field(n,i) for n,i in [('IDR0_S1P',0),('IDR0_S2P',0),('IDR0_COHACC',0),('IDR0_ATS',0),('IDR1_SSIDSIZE',1),('IDR3_RIL',3),('IDR5_GRAN4K',5),('IDR5_GRAN16K',5),('IDR5_GRAN64K',5)]}
assert decoded['IDR1_SSIDSIZE']==0 and decoded['IDR3_RIL']==1
save('platform_admission.json',dict(raw_registers=[hex(v) for v in words],decoded=decoded,header_sha256=sha(header),observation='qtest MMIO; guest CPU paused; reset model not full Linux',sva_case='outside_supported_platform',reason='fixed driver master_sva_supported requires nonzero ssid_bits; device model global SSID width is zero',command_queue='RIL advertised, implementation validation fidelity still unverified',xp_status='all-zero debug view conflicts with qtest; excluded from capability truth',whole_path='insufficient',manual_dependencies=['map selection','register semantics','driver prerequisite selection'],independent_positive_normal=[0,0]))
anchors=[]
for fn,needles in [('03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c',['return master->ssid_bits;','if (!size)','arm_smmu_atc_inv_domain']),('00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c',['if (!size) {','cmd->atc.size = ATC_INV_SIZE_ALL;','if (!(smmu_domain->smmu->features & ARM_SMMU_FEAT_ATS))','if (!atomic_read(&smmu_domain->nr_ats_masters))'])]:
 p=header.parent/fn;ls=p.read_text(encoding='utf-8').splitlines()
 for n in needles:
  hits=[dict(line=i+1,text=l) for i,l in enumerate(ls) if n in l];assert hits
  anchors.append(dict(source=str(p.relative_to(R)),sha256=sha(p),needle=n,hits=hits))
save('source_anchors.json',anchors)
body='''## 10月26日 最新进展：SMMU平台资格实测与块stride补证

现有WSL为x86_64 Microsoft内核，/sys/class/iommu无条目，不能将宿主直接当ARM SVA环境。已安装QEMU 8.2.2的virt支持smmuv3；本轮启动3次临时模型（CPU暂停，无guest内核），分别读内存布局、监视器xp和qtest MMIO。观测基址0x9050000。xp返回全零，改用qtest得到IDR0=0x0d44101a、IDR1=0x02730010、IDR3=0x1404、IDR5=0x74。xp记录保留但明确排除能力真值；不据全零宣称SMMU不存在。

按固定源码头文件自动提取位掩码解码：RIL=1但SSID位宽=0。驱动master_sva_supported要求非零ssid_bits，因此当前已测模型配置不能直接承担SVA绑定/单页历史复现。不是所有QEMU版本均不支持的泛化判断，也不表示范围命令队列不能测试。qtest六次寄存器读已成功返回；EOF后stderr出现GLib timer断言，进程由脚本有界终止，保留原始输出，不称干净退出。此为仿真模型MMIO观察，不是物理设备或真实SVA操作。

原ARM64宏/函数另编译3个页配置，12组块stride形状执行通过：普通分支仍end/end，达到页数上限仍全范围哨兵；没有真实hugepage映射。全失效相关源码补核：SVA零size在BTM0时全ASID失效；ATC转换零size明确为SIZE_ALL，但ATC实际下发还受ATS能力、活跃ATS master及设备使能门禁。不能把ATC函数被调用当成已下发或已完成。

自动化新增platform_admission.json：从实际MMIO读数及固定头文件掩码生成平台字段，明确排除当前SVA配置，命令队列可测性/whole_path仍不足。平台先决条件和字段含义由研究者登记，并非自动N1推导；未实现统一检查器。此前局部机制证据保持，真实绑定、同对象生命周期和设备完成仍缺。

下一项：保持SVA真实复现的平台阻碍，优先核当前QEMU范围命令的实现/校验能力，决定是否能作为命令队列层对照，而非强造SSID后冒称合法SVA实验；同时将单页入口的触发条件与待补外部平台要求固化。接口不结项，virtio随后，表示接口/R3暂缓、VT-d后置不变。

统计：3次局部编译、12次函数执行、3次临时QEMU模型启动、6次qtest ID寄存器读取；另有xp六字调试读取但不采纳能力结论。无guest内核构建/启动、真实SVA绑定、物理设备操作、项目模型或新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_platform_20261026/（environment、registers、qtest、platform_admission、stride_results、source_anchors）。Word未改；日志与三份持续文档已维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU平台资格与全失效/stride补证\n\n'+body,encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print(json.dumps(decoded));print('Platform scope and next step recorded.')
