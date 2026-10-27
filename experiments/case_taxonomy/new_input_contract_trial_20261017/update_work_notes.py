"""Record this completed research batch; do not rewrite historical records."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def main():
    before = json.loads((HERE / 'notes_before.json').read_text(encoding='utf-8'))
    for name, digest in before.items():
        assert hashlib.sha256((OUTER / name).read_bytes()).hexdigest() == digest, name
    todo_path = OUTER / '当前代办.md'
    todo = todo_path.read_text(encoding='utf-8')
    top_start = todo.index('更新：')
    top_end = todo.index('\n\n## 当前停点与统计口径', top_start)
    top = '更新：2026-10-17。本轮连续完成N2.6两项父版试用/修复独立裁定及N2.7离线输出协议修正。两次Opus完整返回，但E是公共helper定义域/架构符号依赖整理，F是参考频率基准/单位接口，均非首次准备修复；14文件来源绑定，25候选/12局部项因输入协议缺口全部不足，不构成有效端到端检测评价。后继格式生成器8项合成测试通过，不追认E/F成绩。没有新确认缺陷、合法配置运行或正式独立正/正常；下一项N2.8回到已确认架构配对，事前登记同材料/同预算研究对照，分清程序和人工复核贡献。研究主线仍为架构差异如何破坏公共接口要求、跨层传播及造成不对称暴露。大规模筛选由天宇重点推进，R3继续暂缓。每轮连续完成实质小闭环后集中汇报，10/1取消的余额停止条件不恢复。'
    todo = todo[:top_start] + top + todo[top_end:]
    start = todo.index('**下一操作：N2.6')
    end = todo.index('\n\n## 两个核心方向', start)
    next_step = '''**下一操作：N2.8，回到已确认架构配对做研究对照，不继续按路径凑新阳性。** 先用R4既有s390/x86首次消费及N2.5已对齐材料，登记有限语义问题和独立审阅判准，再用N2.7明确输出协议开展同材料、同预算的直接模型与候选/程序路线比较。两路线获得相同源码、配置与观测线索，明确是已读开发材料；不借本轮新hash声称留出。分开要求有无依据、是否实际适用、对象/期限是否正确、程序到底验证了什么、哪些结论仍由人工改判；若增益仅来自人工复核，不能归功自动程序。先核定可执行、可评分的最小设计再付费，不以改提示词或反复格式重试代替研究贡献。不为E/F追加调用、扩源或运行；合法独立同机制阳性/正常另建，N1/N2及R5/R6不整体勾选，R3暂缓。'''
    todo = todo[:start] + next_step + todo[end:]
    old = '  - [ ] **N2.6 新输入身份适配、资格与有限试用（下一项）。**'
    assert old in todo
    pos = todo.index(old)
    finish = todo.index('\n', pos)
    replacement = '''  - [x] **N2.6 新输入身份适配、资格与有限试用（10/17有界完成，未形成有效检测评价）。** [结果](linux_bug_analyze/experiments/case_taxonomy/new_input_contract_trial_20261017/README.md)：固定两队列E/F各一例，每例7份父版文件，两次Opus完整返回后才解封补丁并独立裁定。E为定义域/配置依赖，F为参考频率基准与单位；均非首次准备修复，不计正式正/正常。14来源绑定，25候选和12局部项因引用格式/CASE占位全部不足；输入脚本漏发规范，不能统一归为模型推理失败。预算分类v2于父版已读后修订，13方法测试通过，核心不改；客户端可见702239 token、内部实际账单未知，不与预占相加，无新编译/运行/确认。原回答、失败和v1保留。
  - [x] **N2.7 输出协议的独立后继离线修正（10/17）。** [方法及限制](linux_bug_analyze/experiments/case_taxonomy/candidate_packet_protocol_20261017/method_notes.md)：从真实材料组生成profile，明确document/start_line/end_line及24行上限；8项合成正反测试通过，并经独立限域审查。仅证明格式交接，不是Linux语义、效果或泛化验证；没有改旧回答/上游核心、重跑E/F或新增API。
  - [ ] **N2.8 同材料、同预算的研究对照（下一项，先登记设计）。** 采用已确认配对限定问题，比较直接模型与候选/程序路线，分清自动事实、语义审核和人工贡献，不把拒判或合成正例当准确率。方法有效性、架构差异见证和独立输入仍需证实。'''
    todo = todo[:pos] + replacement + todo[finish:]
    todo = todo.replace('文稿修订及N1.4g–h有界资格已完成；N2.1–5已推进到有限池选配、旧回放、受限接线、配置源码视图与模型候选/程序/语义核对。下一项N2.6按固定边界转向未参与开发输入，不继续辅助helper扩展。',
                        '文稿修订及N1.4g–h有界资格已完成；N2.1–7已推进到有限选配、旧证据接线、条件候选、新输入范围裁定及格式交接修正。下一项N2.8先登记已确认配对的同材料研究对照，不继续辅助helper扩展或按路径凑阳性。')
    marker = '**当前继续入口：**顶部N2.6。'
    assert marker in todo
    start = todo.index(marker); end = todo.index('\n', start)
    todo = todo[:start] + '**当前继续入口：**顶部N2.8。N2.6原始失败不改，N2.7只有离线格式连通；下一轮先登记可评分研究设计，再按预算执行完整小闭环。正式独立0/0、N1/N2整体未完，R3暂缓。' + todo[end:]
    todo += '\n\n**本次操作核对（2026-10-17，N2.6–7连续闭环）：**两例父版预测先于修复释放，独立oracle与后续模型比较分开保存；实际修复均不属于首次准备机制。输入规范欠完整导致25候选/12局部项全不足，24callee人工可定位但不追认程序成绩；85段引用中22段超明确上限。E未建立非x86故障，F缺完整转换读端且已读目标文件，不增加确认数或独立分母。新阶段8项合成格式测试通过且独立审查，原结果及冻结核心不改。两API顶层任务共客户端可见702239、内部费用未知；无新构建/内核运行/Word/GitHub动作。下一项N2.8受控研究对照，记录与待办同步Windows/WSL，R3暂缓。\n'
    todo_path.write_text(todo, encoding='utf-8')

    progress_path = OUTER / '当前研究方向与进展.md'
    progress = progress_path.read_text(encoding='utf-8')
    start = progress.index('更新：'); end = progress.index('\n\n', start)
    progress = progress[:start] + top + progress[end:]
    first_section = progress.index('\n## ')
    section = '''
## 10月17日：新输入试用、修复范围裁定与格式交接修正

按固定500两队列无补选取E/F，各采7份精确父版原始文件；两次Windows Claude Code2.1.301＋AWS-Claude-Opus-5.5任务完整返回（217.375/213.828秒，客户端可见合计702239，预占不另加、实际账单未知）。保存预测后才读取两个修复，独立oracle先于审查者读取模型答案保存。

E实际调整公共helper定义域与x86符号依赖，明确无功能变化；F统一容量/频率参考基准、来源和单位接口，均非首次准备修复。它们说明配置可用域和数据基准值得分别记录，但未建立实际CPU架构A/B暴露；F仍为开发型，E也不是合格同机制正/正常。没有新增确认缺陷，两段发现时间仍未知。

14份原始来源绑定，但25候选/12局部项全部止于profile/引用协议门槛：脚本未传完整引用对象且未实例化CASE占位。不能用此轮评价端到端语义检测，也不把人工能找到24callee追认程序成功。模型还漏掉E的实际目标，F只部分涉及同基准要求，并提出过强online期限；E不消费分支应判不适用，不能称满足。人工复核结论不自动回填正式特征。

独立后继N2.7已实现明确格式说明和真实材料组实例化，8项合成正反测试及限域独立审查通过；未改旧回答/冻结核心、重跑E/F或再调用模型。这是工程修复，不是创新或Linux泛化成绩。下一项N2.8先在已确认配对上登记同材料/同预算直接模型对照，明确增益来自程序还是人工；不再按路径逐项付费凑阳性。新构建/内核运行/正式特征回填0，正式独立正/正常0/0，R3暂缓。

详见[N2.6完整结果](linux_bug_analyze/experiments/case_taxonomy/new_input_contract_trial_20261017/README.md)与[N2.7方法](linux_bug_analyze/experiments/case_taxonomy/candidate_packet_protocol_20261017/method_notes.md)。下文保留各轮当时状态，当前入口以上节和当前代办为准。
'''
    progress = progress[:first_section] + '\n' + section + progress[first_section:]
    progress_path.write_text(progress, encoding='utf-8')
    receipt = {'before_sha256': before, 'after_sha256': {name: hashlib.sha256((OUTER/name).read_bytes()).hexdigest() for name in before},
               'next': 'N2.8 registered same-material research comparison; R3 deferred'}
    (HERE/'notes_update.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'updated','files':list(before)},ensure_ascii=False))


if __name__ == '__main__':
    main()
