"""Write one completed round to the three notes, daily log and family plan."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(value, reason):
    if not value:
        raise ValueError(reason)

SECTION = '''## 10月27日 最新进展：CPU导出有效来源重建及用途政策对照

按下一项待办继续既有die案例，补N2.16只核直接源码候选、未展开实际运行配置完整编译单元的缺口。对父版555a0ce4558d87d5b97c4321f34b19e051c7b0c1、修复版2c4dcd7fd57b20a21b65da04d89c38a7217d79cf各自的x86_64/s390 SMP历史运行构建，使用原.topology.o.cmd的include/forced include及选项，新执行4次完整topology.c预处理。只去除依赖输出并将编译动作改为-E -dD -H，输出到本轮；未运行make/objtool，原配置、autoconf、命令、object和镜像前后SHA一致，autoconf与旧归档一致。

每个x86上下文含470个固定源码文件/13个生成输入，每个s390为442/22；全部源码核对对应Git blob，无外部文件输入。新适配器追踪目标宏和配置宏的define/undef，在读取函数展开及完整属性表处取有效状态，核已审核宏体与实际SMP/SYSFS/NR_CPUS=4及架构配置。这里的“有效”限当前新重建编译上下文；当前编译器/环境不是被恢复的历史进程，不证明物理拓扑或初始化。

四格最终都有同名die宏，但x86 ID/mask均为架构定义，s390均为公共默认；表项数x86旧/修复3/3、s390旧/修复3/0。复用不变contract_protocol.py，修复双来源成组政策下3项满足、旧s390反事实1项不满足。旧文档允许默认值，父版历史ABI责任仍不足；不得追认旧版已有双原生禁令。旧四格runtime/binding文件及其来源unknown原样保留，未把新CPP注入历史运行事实。编译表项、实际发布、首次内容消费及全路径继续分开。

进一步核同一old/fixed s390上下文的package/core两个用途，形成4个“配置×用途”默认政策正常控制：physical_package_id/core_id分别展开为-1/0，core_cpumask/sibling_cpumask使用给定CPU，读取函数及公共表项保留，同版文档允许该默认。四项用途政策关系均满足。这说明die原生门控不能扩大为“任何fallback导出都错”；不是4个新正常案例，也不证明实际拓扑值正确。

最终die错误输入13项、正常用途错误许可/缺来源3项均拒判；含架构头转发fallback、缺来源而无表项、错误版本政策、配置错配、定义顺序与用途越界。最终8项源码上下文+16个构造控制共24次核心调用；旧六格静态/四格runtime另回验10次，runtime均不足。初轮15次新判定+10次回验保留，补配置守卫后第二轮17+10及正常用途7，全轮核心调用59；调用数不是案例数或准确率。仅4次新CPP，0编译/内核构建/启动/付费模型调用，0新Linux缺陷，独立正例/正常0/0。

自动部分增加了实际上下文来源事实提取和用途政策接入；权威依据、版本/用途许可、有限宏体语义、组及对象角色、支持域仍由研究者登记。N1自动推导尚未完成，统一检查器未建立。阶段是“新重建层级的来源/政策补证已完成，CPU导出接口仍进行中”，不能写整个CPU家族或独立检测已完成。

下一步仍留在CPU信息导出：先核读取函数/属性表与可归档目标文件、链接镜像及实际发布观察的联系，判断现存工件可否形成有界证据桥；关键身份缺失时再登记最小新构建/运行，不以不同配置补来源。随后整理来源政策方法卡及横向比较。virtio非一致硬件/并发缺口、表示/R3暂缓、VT-d后置不变；Kimi大请求输出限制及失败停点单列保留，本轮未重试模型。

证据：linux_bug_analyze/experiments/case_taxonomy/cpu_source_policy_20261027/。主结果analysis_attempt2/results.json、normal_policy.json；preprocessing保留四格CPP/命令/include来源/receipt，policy_sources有2版本×3份完整文件，README和delivery_manifest说明统计与边界，analysis_attempt1及根目录首轮结果保留。WSL源/构建缓存仍/root/.cache/linux-bug-analyze/die-contract-20261013/{old,fixed}/linux和runtime/{profile}，无新独立WSL项目副本。日志、待办、进展、交接和规划同轮维护；三份WSL镜像以本轮notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

def main():
    update = HERE / 'notes_update.json'
    need(not update.exists(),'preserve_notes_update')
    before = json.loads((HERE/'notes_before.json').read_bytes())['before_sha256']
    for name,digest in before.items():
        need(sha(OUTER/name)==digest,'Windows_note_changed_during_round:'+name)
    need(sha(OUTER/'接口验证后续规划.md')==sha(HERE/'plan_before.md'),'family_plan_changed_during_round')
    for name in before:
        path = OUTER/name
        raw = path.read_text(encoding='utf-8')
        title, rest = raw.split('\n',1)
        path.write_text(title+'\n\n'+SECTION+rest.lstrip('\n'),encoding='utf-8')
    plan = OUTER/'接口验证后续规划.md'
    text = plan.read_text(encoding='utf-8')
    old = '| 拓扑阶段方法已整理；其他用途有不同深度材料，非全家族完成 |'
    new = '| 拓扑阶段方法已整理；导出补齐本轮有效来源/用途政策，仍在核对象、镜像和发布联系；非全家族完成 |'
    need(text.count(old)==1,'CPU_status_row_not_unique')
    text = text.replace(old,new)
    marker = '\n## 当前执行顺序\n'
    need(text.count(marker)==1,'execution_order_heading_not_unique')
    addition = '| 2026-10-27 | CPU／die有效来源与版本化用途政策 | 本子阶段完成：4次实际运行配置完整CPP，复用公共核心；同s390配置package/core默认政策4用途控制；linux_bug_analyze/experiments/case_taxonomy/cpu_source_policy_20261027/ | 最终16项构造错误拒判；来源语义/许可仍人工，旧政策反事实与历史ABI分开。新重建不升级历史runtime；继续对象/镜像/实际发布桥，接口进行中 |\n'
    text = text.replace(marker,addition+marker)
    start = text.index(marker)+len(marker)
    end = text.index('\n\n',text.index('\n',start)+1) if False else text.index('\n\n',start+2)
    # Replace only the first current-order paragraph; the pre-round copy is
    # preserved in plan_before.md, and all old stage rows remain.
    paragraph_start = start
    while paragraph_start < len(text) and text[paragraph_start]=='\n':
        paragraph_start += 1
    paragraph_end = text.index('\n\n',paragraph_start)
    text = text[:paragraph_start]+('CPU信息导出正在分析：已完成四个历史运行配置的新完整CPP来源重建，并核同配置package/core的默认政策正常资格。下一项先核读取函数/表项到目标文件、链接镜像和实际发布观察的证据桥，必要时再登记最小新构建/运行；随后整理来源政策方法与横向比较，尚不转下一个接口。旧运行来源未知及消费/物理值/稳定窗口不足保留。DMA/virtio已有四格真实guest正常路径；非一致缓存效果需不同合格平台，继续挂账。表示/R3暂缓、VT-d后置不变。')+text[paragraph_end:]
    plan.write_text(text,encoding='utf-8')
    log = OUTER/'日志/2026-10-27.md'
    with log.open('a',encoding='utf-8') as f:
        f.write('\n\n'+SECTION.replace('以下为历史记录，以本节及用户最新指示为准。\n\n',''))
    changes = {'before_sha256':before,'after_sha256':{name:sha(OUTER/name) for name in before},
               'plan_after_sha256':sha(plan),'daily_log_sha256':sha(log)}
    update.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'updated_notes':len(before),'daily_log':'2026-10-27.md','family_plan':True}))

if __name__=='__main__':
    main()
