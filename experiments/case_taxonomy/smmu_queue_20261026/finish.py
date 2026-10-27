from pathlib import Path
import json,hashlib,subprocess
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
results=json.loads((H/'results.json').read_text(encoding='utf-8'));audit=[]
for r in results['cases']:
 raw=json.loads((H/(r['name']+'.json')).read_text(encoding='utf-8'));bad=0
 for w0,w1 in raw['words']:
  if w0&255==0x12:
   tg=(w1>>10)&3;ttl=(w1>>8)&3;num=(w0>>12)&31;scale=(w0>>20)&31
   bad+=bool(tg and ttl==num==scale==0)
 accepted=r['cons_index']==r['prod'] and r['error']==0 and r['gerror']==r['gerrorn']
 if r['name']=='unknown_opcode':assert r['error']==1 and r['gerror']^r['gerrorn']==1 and r['cons_index']==0
 else:assert accepted and bad==r['reserved']
 audit.append(dict(case=r['name'],reserved_commands_from_words=bad,queue_consumed=accepted,encoding_rule='violation' if bad else 'not_applicable_control' if r['name'] in ['sync_only','unknown_opcode'] else 'pass_this_rule_only',emulator_as_reserved_encoding_oracle='not_qualified',translation_effect='insufficient'))
assert sum(a['reserved_commands_from_words'] for a in audit)==3
save('audit.json',audit)
identity=[]
for cmd in [['sha256sum','/usr/bin/qemu-system-aarch64'],['dpkg-query','-W','qemu-system-arm']]:
 p=subprocess.run(['wsl.exe','-d','Ubuntu','--']+cmd,capture_output=True);assert p.returncode==0;identity.append(dict(command=cmd,stdout=p.stdout.decode('utf-8'),stderr_hex=p.stderr.hex()))
save('source_and_binary.json',dict(binary=identity,upstream_url='https://raw.githubusercontent.com/qemu/qemu/v8.2.2/hw/arm/smmuv3.c',upstream_sha256=sha(H/'qemu-v8.2.2-smmuv3.c'),source_limit='upstream reference, not asserted byte-identical to Ubuntu patched package',source_observation='range_inval computes range without rejecting TG!=0 NUM=SCALE=TTL=0; consume dispatch rejects unknown opcode',authority_path='../smmu_chain_20261026/authority.json',authority_sha256=sha(H.parent/'smmu_chain_20261026/authority.json')))
body='''## 10月26日 最新进展：SMMU命令队列实测与观测器资格

对当前安装QEMU 8.2.2 Ubuntu包进行了10组隔离qtest命令队列实验，每组新模型，CPU暂停且无guest内核。8组复用已有父/修复1/31/33/65页命令字，另加SYNC单独控制及未知opcode=0xff控制。写RAM后逐字读回，配置CMDQ_BASE、确认CR0ACK，再推进PROD并读取CONS/GERROR/GERRORN。总计提交22项队列条目：11条TLBI、10条SYNC、1条未知opcode；消费20项，未知opcode及其后的SYNC停留队列。

**核心结果：**8组历史字编码及SYNC控制均消费完成且无错误；其中旧1/33/65页3组确含规范保留组合，QEMU仍放行。未知opcode控制则CERROR_ILL=1、GERROR置位、CONS索引停0，说明观测通道可发现部分非法命令，但不能据此认为覆盖保留字段组合。当前模型不具备作为这条契约正确性判定器的资格；不能用QEMU没报错覆盖源码/规范判出的违规。

新增audit.json从原始命令字重新解TG/NUM/SCALE/TTL，分开登记encoding_rule、queue_consumed、观测器资格、translation_effect。即使队列通过，已知保留组合仍判violation，真实翻译效果仍insufficient。这是已有人工规则的观测适配与资格核验，不是自动N1推导或独立发现。已查阅并保存QEMU官方v8.2.2源码：范围分支未检查该组合，与实测相符；官方源码不冒称等同Ubuntu补丁后二进制，二进制SHA/包版本另存。

边界：未安装STE/CD或建立DMA翻译缓存，未发真实DMA，SYNC被消费不证明物理设备完成。此前SSID=0导致SVA完整绑定复现受阻仍成立；本轮是仿真命令队列层实测。qtest EOF后GLib timer断言及有界终止保留，关键请求均完整返回、寄存器/内存逐项核验，不称干净退出。没有修改模拟器或强造SVA能力。

下一项：继续接口主线，将上游触发、输入资格、编码义务、观测器资格整理为可复核的SMMU专用判定方法，明确每项事实来源及缺证处理；优先复核单页真实入口条件和已有主分析义务覆盖，不再重复扩大QEMU输入矩阵。完整SVA运行保留为外部平台缺口，接口未结项；virtio深分析随后，表示接口/R3暂缓、VT-d后置不变。

统计：新增10次临时QEMU模型启动，22项队列提交、20项消费；无新局部编译、guest内核构建/启动、真实SVA绑定、物理设备操作、项目模型调用或新缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_queue_20261026/（run、各组原始JSON、results、audit、source_and_binary）。日志、待办、进展、交接同轮维护；WSL三镜像以notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''
(H/'README.md').write_text('# SMMU仿真命令队列与判定器资格\n\n'+body+'\n源码参考：[QEMU v8.2.2 smmuv3.c](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/hw/arm/smmuv3.c)，smmuv3_range_inval和smmuv3_cmdq_consume。\n',encoding='utf-8')
before=json.loads((H/'notes_before.json').read_text(encoding='utf-8'))['before_sha256'];after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+body+rest.lstrip(),encoding='utf-8');after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
with (R/'日志/2026-10-26.md').open('a',encoding='utf-8') as f:f.write('\n'+body)
save('delivery_manifest.json',{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ['delivery_manifest.json','notes_sync.json']})
print('10 cases audited; observer disqualified for reserved encoding oracle; notes updated.')
