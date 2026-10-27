from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];P=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in names}))
heading='''## 10月26日 用户纠正：撤回SMMU与virtio的过早收束

此前两轮只完成局部实验复核和方法整理，未达到CPU/Btrfs机制分析的深度。撤回将SMMU/virtio接口分析标为阶段收束并立即转向CPU身份/固件的安排；旧原始实验及其局部结论保留，完成口径以本节为准。

当前优先深入SMMU：连通调用者用途、输入条件、命令构造和硬件消费要求；针对影响判定的缺口补证，再决定自动程序的提取与检查能力。virtio随后深入实际ABI/分配、后端/真实DMA目标、维护及所有权链。不以重复局部测试、列出缺口或文档形式替代机制分析完成。

验收要求是：要求依据明确、实际对象/路径/条件可核、程序事实获取有落实、对照能够排除错误解释；无法闭合的层次保持不足，不将整项称已完成。新接口扩展暂缓；表示接口/R3暂缓、VT-d后置不变。独立评价仍0/0。

本轮研究进行中，具体结果随后补入本节之前。以下为历史记录。

'''
for n in names:
 p=R/n;title,rest=p.read_text(encoding='utf-8').split('\n',1);p.write_text(title+'\n\n'+heading+rest.lstrip(),encoding='utf-8')
shutil.copyfile(P/'virtio_method_20261026/sync_work_notes.py',H/'sync_work_notes.py')
d=json.loads((P/'cross_arch_smmu_source_20261013.json').read_text(encoding='utf-8'));out=H/'source';out.mkdir()
manifest=[]
for i,s in enumerate(d['sources']):
 if 'text' not in s:continue
 text=s['text'];raw=text.encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert blob==s['blob']
 name=f'{i:02d}_'+s['path'].replace('/','__');p=out/name;p.write_text(text,encoding='utf-8')
 manifest.append(dict(file=name,path=s['path'],revisions=s['revisions'],blob=blob,sha256=sha(p)))
save('source_manifest.json',manifest)
save('protocol.json',dict(task='caller-to-command mechanism review, not replay-only closure',new_model_request='SMMU caller/domain/encoding review; not retry of earlier Btrfs or CPU refusal',model_route='Windows native Claude Code AWS-Claude-Opus-5.5',independent_evaluation=False,open_layers=['caller reachability','object and configuration binding','encoding and hardware authority','automatable fact acquisition']))
print('Completion wording corrected; fixed archive sources extracted and verified.')
