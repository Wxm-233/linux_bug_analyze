from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
body='''## 10月26日 最新研究进展：SMMU调用链补证，接口分析仍进行中

**完成口径纠正生效：**SMMU/virtio此前仅完成局部实验复核与方法整理，撤回整项阶段收束及立即转CPU身份/固件的安排。下面的新工作仍不表示完整接口分析完成。研究要求是依据明确、实际对象/路径/条件可核、程序事实获取落实、对照排除错误解释，而非重放旧测试后列缺口即结项。

**新证据一：原调用链。** 编译6个父/修复×PAGE_SHIFT的函数链程序、执行120组输入，执行原SVA回调、ASID/域包装器、walk包装器和范围函数，保留队列/ATC/ASID全失效及MM对象替身。核BTM绕过、零/全范围哨兵、RIL/E2H路由，分别追踪ASID/PASID/VMID。walk使用表大小形状，未执行真正unmap；bitmap为同粒度族多位，不再仅一个bit。父版18组命中范围保留组合、修复0组，均为开发输入组合，不是新增缺陷。

**新证据二：编码与规范。** 另编译1个明确标注的历史TLBI三case分支投影，单次执行编码672条链式命令，18条旧保留组合在命令字中仍存在，未执行完整构造器/队列/设备。源码另核batch_add当次编码进批次存储、submit请求同步；不推断设备完成。已查询Arm官方IHI0070C.a §4.4/4.4.1.1（印刷129–131页）文本，核TG非零全零NUM/SCALE/TTL为保留编码、TTL缩窄层级范围、长度公式及CMD_SYNC完成区别。此前仅修复说明的规范依据现有外部补强，但其他架构版本/errata、软件扩大范围许可和设备实测仍未闭合。PDF截图失败，未声称视觉核验。

**新证据三：主分析及纠错。** 按AGENTS调用Windows原生Claude Code2.1.301/AWS-Claude-Opus-5.5新SMMU任务，正常end_turn完整返回，376.859秒、可见62282 token、保守预占20万，每调用独立1M不累计扣减；不把客户端任务数等同底层推理次数或可见用量当完整账单。最终10项义务逐项复核，纠正首轮scale总>=1、非整页必ffs(0)、整除必须页位移相等三处过强表述；有界算术反例不作合法平台或Linux缺陷。首次审核脚本误预计草稿11项，在写结果前断言失败，随后按最终10项重新审核；原文不改，不采纳草稿为最终分析。

**仍缺什么：**完整源揭示restrict_pgsizes优先CPU页并缩减页/块族，finalise把配置回填domain；但真实成功路径、同domain生命周期、CD粒度和SVA S1绑定尚未形成完整事实链。现有输入合法性不能由替身赋值证明。另缺非大块对齐地址、可达最大范围/字段截断、真实notifier注册、队列及设备执行。程序新增的是有界调用链捕获与字编码核验，未获得自动跨函数对象恢复或完整N1/N2。

**立即下一项仍为SMMU：**优先绑定restrict_pgsizes→domain bitmap→SVA CD粒度/stage及注册/分配成功条件，建立有依据的合法输入池；随后用规范条件约束实际命令字，补地址/宽度边界控制，非法前提与真实可达输入分开。再按明确问题决定设备补证。virtio深入实际目标/后端/所有权链随后推进；CPU身份/固件扩展暂缓，表示接口/R3暂缓、VT-d后置不变。

统计：新编译7个有界程序（6链式+1编码投影），120次链式及1次编码程序执行，672条命令；1个项目主分析调用，0内核构建/启动、0设备操作、0新缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_chain_20261026/的README、source_manifest、function_manifest、chain_results、encoding_results、chain_audit、authority、model_review、model_counterexamples。模型原件在忽略目录模型调用测试/2026-10-26/smmu_caller_chain。Word及历史实验不改；本日日志与三份持续文档同步，镜像一致性以本轮notes_sync.json为准。

以下为完成口径纠正及历史记录，以本节和用户最新指示为准。

'''
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n in before:
 p=R/n;title,rest=p.read_text(encoding='utf-8').split('\n',1)
 assert '用户纠正：撤回SMMU与virtio的过早收束' in rest
 p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('Status corrected, research recorded, SMMU remains active.')
