from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'notes_update.json').exists()
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
before={n:sha(ROOT/n) for n in names}
block='''## 10月25日 用户确认的最终方向与当前阶段优先级

长期目标单独记录于根目录[最终研究目标与阶段推进原则.md](最终研究目标与阶段推进原则.md)：统一入口、统一契约表示、统一证据与判定流程，允许不同事实提取和观测适配器，结合程序筛选与模型辅助语义分析。仅使用Markdown记录；不创建或恢复会话级目标，先前提前登记的目标保持暂停。

**当前先做：**逐类提取接口的判定方法、规范依据、条件关系、提供者保证、事实证据、合法对照、自动/模型/人工边界及可复用部分。保持记录提纲一致，不急于统一实现。机制多样性与方法成熟度比接口数量更重要；积累若干不同机制后横向复核共性、适配成本和支持边界，再决定启动统一框架实现，不预设固定数量门槛。

**排程调整：**撤回“优先把CPU和Btrfs接入同一入口”的建议。当前先收束Btrfs判定方法及证据边界，已有正常页几何配置池核查须直接服务该关系；不把扩展选择器或搭建入口本身当研究目标。各阶段仍按“要求有依据→有效对照→可解释检查”收尾，缺证如实记录，不无限深挖整个子系统。随后逐类积累、开发迁移、横向复核，再实施统一框架并冻结独立评价。提前保留未用于开发的评价材料。

本轮为用户授权方向记录，无新增实验、项目模型调用或内核运行；Word未改，既有证据等级不变，独立正例/正常样本仍0/0。Btrfs期限契约仍不足，表示接口/R3暂缓、VT-d后置保留。日志、待办、进展和交接同轮维护，三份WSL镜像以本轮notes_sync.json为准。最终方向文件的权威入口为Windows工作区根目录。
'''
for n in names:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。先逐类积累判定机制，再实施统一检查器；长期方向见最终研究目标与阶段推进原则.md。\n\n'+block+'\n以下为历史记录，以最新用户确认安排为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block)
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('notes_before.json',dict(before_sha256=before))
save('notes_update.json',dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(HERE.parent/'btrfs_selection_bridge_20261025/sync_work_notes.py',HERE/'sync_work_notes.py')
save('direction_receipt.json',dict(path='最终研究目标与阶段推进原则.md',sha256=sha(ROOT/'最终研究目标与阶段推进原则.md'),session_goal_resumed=False))
print('Direction document and staged priorities recorded; sync pending')
