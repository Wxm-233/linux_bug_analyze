from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent; R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):
 p=H/n;assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
S=H.parent/'btrfs_runtime_20261023';m=read(S/'source_review_manifest.json')
for f in m['files']:assert sha(S/f['saved'])==f['sha256']
assert sha(S/'source_review/fix_commit.patch')==m['patch_sha256']
p=S/'source_review/parent_fs__btrfs__inode.c'; lines=p.read_text(encoding='utf-8').splitlines()
assert 'start == 0 && fs_info->sectorsize == PAGE_SIZE' in lines[1099]
assert 'data_len > fs_info->max_inline' in lines[366]
rows=read(H/'reconstructed_observations.json')
assert len(rows)==6 and sum(len(x['files']) for x in rows)==36
assert all(f['persisted_equal'] for x in rows for f in x['files'])
save('source_audit.json',dict(manifest_sha256=sha(S/'source_review_manifest.json'),files=m['files'],patch_sha256=m['patch_sha256'],anchors=[dict(line=1100,text=lines[1099]),dict(line=367,text=lines[366])],method_sha256=sha(H/'README.md'),failure='Initial comparison failed solely because Windows artifact dictionary paths used backslashes; observations identical. Normalize key separators only; byte hashes unchanged. Source audit initially used line 368 for the max_inline gate; assertion stopped before writes, corrected to observed line 367.'))
body='''## 10月26日 最新闭环：Btrfs判定方法与正常几何边界收束

按先积累接口判定机制的安排，完成Btrfs方法说明及三种既有几何配置回验，未搭建统一入口。重新核验原始材料SHA并重构6次历史运行、36条文件记录，与旧结果完全一致；四份归档构建配置及测试程序来源核验通过。同版4K/4K、64K/64K、64K/4K是ARM64页/扇区配置差异，不是不同CPU架构，父/修复对照也单独保留。

**判定方法的新明确项：**准备契约c=d、请求行为min(r,c)=min(r,d)、最终inline文件布局分别判断。对非负整数，裁剪结果相等当且仅当c=d或r<=min(c,d)；小请求相等不能证明准备正确。手工代数分析经35937个有限边界组合核验，不计作案例或自动定理推导。12条归档请求诊断中，仅父版64K/64K的8192请求与按离线磁盘几何计算的值不一致；其余11条不因此成为准备契约正常样本。离线磁盘几何仍不替代消费期限参考。

**用途和对照边界：**按固定SHA复核历史inode.c，普通写回inline入口还要求start=0且sectorsize=PAGE_SIZE；64K/4K未进入这一inline尝试路径，全部regular不能当缺陷。页=扇区也不是inline充分条件。4K/4K与64K/64K同时改变页和扇区，64K/64K与64K/4K还改变入口资格。已有文件布局及持久化证据支持局部行为分析，不升级为全路径因果证明。

**自动化与人工边界：**程序执行哈希、配置来源、日志/extent重构和有限算术核查；规范权威、对象/阶段语义、合法池及适用关系仍经人工登记。旧模型候选、完整条件和选择器均未改，正式核心本轮执行0。C/whole_path仍不足；现有局部组件可复用，未形成经过独立验证的完整自动检测器。

**收束及下一项：**Btrfs本阶段方法已整理为可复核档案，完整契约的最小缺口仍为同对象同消费期限的权威几何参考和完整用途条件，不再为收束无限增加挂载格子。下一项整理既有CPU拓扑的集合、资格和阶段判定方法，按一致提纲比较复用部分、专用适配和人工成本；这是已读开发材料比较，不急建统一入口，不自动调用付费模型。Btrfs缺口挂账，表示接口/R3继续暂缓、VT-d后置。

统计：新模型请求/内核构建/启动/挂载/缺陷均0；6次旧运行、36个旧文件、12条请求诊断是不同统计单位，独立正例/正常样本仍0/0。本轮未重跑旧111项测试，也不重计。首次比较因Windows/WSL路径分隔符不同失败，观测完全一致，仅归一化哈希字典键后通过，原始文件及旧结果未改。证据入口：linux_bug_analyze/experiments/case_taxonomy/btrfs_method_20261026/（README.md、results.json、inputs.json、reconstructed_observations.json、source_audit.json）。本轮Word未改；三份镜像同步结果以本目录notes_sync.json为准，未成功前不声称一致。

以下为历史记录，以本节及用户最新指示为准。

'''
before=read(H/'notes_before.json')['before_sha256']
after={}
for n,d in before.items():
 p=R/n;assert sha(p)==d
 text=p.read_text(encoding='utf-8');title,rest=text.split('\n',1)
 p.write_text(title+'\n\n文档维护：2026-10-26。先逐类积累判定机制，长期方向见最终研究目标与阶段推进原则.md。\n\n'+body+rest.lstrip(),encoding='utf-8')
 after[n]=sha(p)
save('notes_update.json',dict(before_sha256=before,after_sha256=after))
log=R/'日志/2026-10-26.md';log.parent.mkdir(exist_ok=True)
with log.open('a',encoding='utf-8') as f:f.write(('' if log.stat().st_size else '# 2026-10-26 工作日志\n\n')+body)
print('Source anchors, all archived persistence checks and three note updates complete.')
