from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
body='''## 10月26日 最新进展：SMMU stage资格、有限准入和非块对齐地址

继续SMMU，未切新接口。补核固定版本domain_alloc/finalise、nesting及SVA功能使能路径：非identity、初始S1、设备支持S1、未启nesting且finalise成功时可得到条件性S1保证。功能使能检查不读取翻译域stage，通用使能入口也不能补出此保证；SVA标志不能替代成功绑定。设备probe中的S1/S2组合是NESTING能力条件，不能误读成SVA的stage条件。

**原函数实验：**编译原finalise与SVA功能使能相关函数，72组阶段/能力/SSID/失败组合全部符合已登记分支预期。分配器、最终stage初始化和IOPF为替身；21组非S1仍功能使能成功，仅反驳“flag推出S1”，不证明真实绑定成功或新缺陷。能力元组是人工输入，不认证真实硬件可达。admission.py只检查有界函数支持域：finalise成功、已知S1、使能成功，3条条件准入、69条范围外；72项移除stage控制均不足。全路径始终不足，范围外不是Linux错误真值。

**地址/编码补证：**另编译父/修复两份链式程序，8组1/31/33/65页请求采用0x7f1234567000（页对齐、非2M块对齐）。复用的编码投影二进制SHA核验后执行8次，按实际命令字解地址/长度核覆盖。旧版1/33/65页仍保留组合违规，31页scale=0但组合合法；修复避免该组合，受影响请求扩大一页。结果不依赖旧1G对齐常量，但仍是合成回调输入，不是实际VMA/设备。旧链式stage标签与本轮真实枚举实验不跨记录拼成同一对象。

**程序与机制边界：**当前可以给出条件性stage路径保证、拒绝以功能flag补stage缺证，并核新地址的编码范围。仍未证明真实attach/bind生命周期、CD安装、group锁全链、mm范围来源和最大可达宽度；对象语义/支持域由研究者登记。本轮是上一轮主分析义务补证，没有新项目模型调用或自动N1推导。

**下一步仍为SMMU：**将已分清的两个domain角色、粒度收敛和stage资格组成同一有限证据包，明确合法SVA输入所需最小外部证明，继续核group附着/注册/CD安装及失败/释放联系；再核真实可达范围宽度和编码截断，不能用巨大合成数直接报真实问题。SMMU不结项；virtio实际目标/所有权待深入，其他新接口扩展暂缓，表示接口/R3暂缓、VT-d后置不变。

统计：新增3次局部编译、72次stage程序执行、8次地址链执行、8次复用编码程序执行，以及72项内存缺证控制；不是新增案例数。新内核构建/启动、设备操作、项目模型、新缺陷均0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_stage_20261026/（README、build、results、summary、address_results、admission_results及源码）。Word和历史结果未改；日志、待办、进展、交接已维护，三份WSL镜像以本轮notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

'''
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Stage/entry/address evidence recorded; SMMU remains active.')
