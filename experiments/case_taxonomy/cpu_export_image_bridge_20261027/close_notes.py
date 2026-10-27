"""Record the completed source/image/publication bridge and next mechanism."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
OUTER=HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(value,reason):
    if not value:
        raise ValueError(reason)

SECTION='''## 10月27日 最新进展：CPU导出object—镜像—发布证据桥及限定方法评审

完成上一轮待办的具体证据连接。四份历史运行配置的冻结完整CPP，按原代码生成选项重新编译到本轮隔离目录；去除预处理选项，显式cpp-output输入，x86执行原objtool后处理。4次编译均首次成功，4份完整object与原文件逐字节相同，未重建整内核。原配置、autoconf、编译命令、object、vmlinux及启动镜像采集前后SHA一致。

核实际thin archive两级成员，各有准确topology.o路径；成员名只作输入链记录，不单独作为链接证明。对ELF64小端x86/大端s390建立有界重定位检查：属性组→完整数组→属性名/读取回调、读取函数、sysfs注册回调、CPUHP设置与initcall逐项核对命名目标或实际字符串，非重定位字节全部比较。四构建共73个函数实体、77个数据实体通过；实体按构建重复计，不当接口/独立样本数。x86的PREL32 initcall为4字节、s390为8字节，由原object单项section导出，不假设同布局。

从4份原boot_image内提取实际gzip载荷，按固定版本构建规则变换vmlinux：x86移除comment/符号后的ELF、s390移除comment/vmlinux.info后的raw binary。每份解压载荷与对应转换结果整块字节一致，大小分别17557616与3867904；镜像SHA与旧build/boot收据相同。代码和属性关系由此连接到原启动镜像，链接地址域仍不是实际guest地址。

复核原始日志、N2.16旧SHA索引、版本/config/image/profile/PID1和CPU选择。旧x86两版、旧s390的CPU0/1均有3项die读回；修复s390对应两CPU均3项ENOENT而普通拓扑项可读，与镜像die表项3/3/3/0相符。新增显式必要关系published_die_any => compiled_die_any AND linked_die_any，在8个历史CPU观察上下文均成立；它组合本轮编译/镜像工件与旧发布样本，记录各自层级。公共核心不改，8项关系及1项不足控制共9次调用，消费期限和whole_path仍不足。两格s390还复核16项已有ID/单CPU列表读回；没有补出未观察的package_cpus，也未重算成新运行。

13项构造错误输入全部拒判：9项内存副本中实际ELF字节变化（架构、端序、指令、回调、表项、组字段、属性名、initcall和emitter重定位），2项身份错配、1项缺观察、1项无发布但桥接证据未知。最初桥接适配器在读取Windows反斜杠索引时KeyError，于生成契约前停止；代码和失败保存bridge_attempt1，归一化路径后通过，不算编译失败或Linux缺陷。初版链接图也完整保留，最终图在linked_graphs_final。

形成method_card及5机制横向比较：有效来源资格取决于具体版本/用途；宏存在、默认值、原生值、对象准备、数量/身份及消费期限不能互相代替。die原生双来源政策与package/core文档默认许可分别登记，旧版修复政策反事实及ABI不足继续保留。冻结CPP能生成同一object，不足以唯一恢复历史源码写法，旧runtime/binding的文本来源unknown不回填；实际物理拓扑、首次内容消费、初始化保证及热插拔/并发稳定性仍未证。静态initcall链不是执行轨迹。

本接口状态更新为“die成组导出来源/用途政策的限定开发方法阶段评审完成”，不是整个CPU家族、运行真值或独立自动检测完成。新增自动组件核编译等价、ELF对象/回调、镜像载荷和发布准入；权威/版本化政策、有限语义、角色和支持域仍人工审核。N1自动推导、统一检查器及公平独立评价尚未完成。

下一项转CPU身份与启动范围的已有机制材料，先核cpu_identity_contract、cpu_mapping_transfer、cpu_domain_qualification、cpu_stage_propagation、cpu_write_effects及cpu_independent_admission的最新结果，冻结命名空间/映射、身份选择、数量/上界和阶段关系，评估合法输入、同用途正常资格与完整启动的可行成本。已失败参考和已读接触史保留，不恢复为独立样本；旧N2.19/21计划不误写为未执行，也不恢复旧Claude/累计预算口径。导出缺口挂账，virtio非一致缓存/并发、表示/R3暂缓及VT-d后置不变；Kimi大请求输出停点保留。

统计：4次新object编译、4次镜像载荷提取/匹配；0新完整内核构建、启动、模型调用、Linux缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/cpu_export_image_bridge_20261027/：objects、images含原工件副本/规则/收据，archive_membership、linked_graphs_final、bridge_evidence_final、publication_inputs/results、controls、method_card、mechanism_comparison、delivery_manifest及next_cpu_identity_scope。原WSL缓存仍/root/.cache/linux-bug-analyze/die-contract-20261013，源码Git/root/repos/linux，新工件在Windows挂载工作区；没有独立/root/repos/linux_bug_analyze副本。日志、待办、进展、交接和家族规划同轮更新，三份WSL镜像以notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

'''

def main():
    out=HERE/'notes_update.json'; need(not out.exists(),'preserve_notes_update')
    before=json.loads((HERE/'notes_before.json').read_bytes())['before_sha256']
    for name,digest in before.items():
        need(sha(OUTER/name)==digest,'working_note_changed_during_round:'+name)
    plan=OUTER/'接口验证后续规划.md'
    need(sha(plan)==sha(HERE/'plan_before.md'),'family_plan_changed_during_round')
    text=plan.read_text(encoding='utf-8')
    old='| 拓扑阶段方法已整理；导出补齐本轮有效来源/用途政策，仍在核对象、镜像和发布联系；非全家族完成 |'
    new='| 拓扑与die导出两用途限定方法已整理；导出已补工件到发布样本，身份/范围继续复核；非全家族完成 |'
    need(text.count(old)==1,'CPU_family_status_not_unique')
    text=text.replace(old,new)
    marker='\n## 当前执行顺序\n'
    need(text.count(marker)==1,'execution_order_heading_not_unique')
    addition='| 2026-10-27 | CPU／die导出object—镜像—发布与来源政策方法 | 限定方法阶段评审完成：4份CPP重编object完全等同，4镜像载荷匹配，73函数/77数据实体及8历史CPU观察绑定；linux_bug_analyze/experiments/case_taxonomy/cpu_export_image_bridge_20261027/ | 13构造错误拒判；历史文本来源/物理值/首次消费/生命周期仍不足，政策/角色人工；转核身份与启动范围的既有材料及合法正常资格，非全家族或独立评价完成 |\n'
    text=text.replace(marker,addition+marker)
    start=text.index(marker)+len(marker)
    while text[start]=='\n':
        start+=1
    end=text.index('\n\n',start)
    text=text[:start]+('CPU信息导出的限定来源政策方法评审已完成，新增object—链接实体—原启动镜像—历史发布样本的有界连接；历史文本原生来源、物理拓扑、首次消费和并发稳定性缺口保留。下一项先核CPU身份与启动范围的既有SPARC/映射/平台限额材料及最新结果，区分命名空间、选择数量、编号上界和阶段，落实合法正常资格并评估真实启动成本后再登记最小新实验；next_cpu_identity_scope仅准备，尚未执行新身份实验。DMA/virtio非一致缓存效果仍需合格平台，表示/R3暂缓、VT-d后置不变。')+text[end:]
    # All checks precede any mutation of the shared notes.
    for name in before:
        path=OUTER/name; old_text=path.read_text(encoding='utf-8'); title,rest=old_text.split('\n',1)
        path.write_text(title+'\n\n'+SECTION+rest.lstrip('\n'),encoding='utf-8')
    plan.write_text(text,encoding='utf-8')
    log=OUTER/'日志/2026-10-27.md'
    with log.open('a',encoding='utf-8') as f:
        f.write('\n\n'+SECTION.replace('以下为历史记录，以本节及用户最新指示为准。\n\n',''))
    result={'before_sha256':before,'after_sha256':{name:sha(OUTER/name) for name in before},
            'family_plan_sha256':sha(plan),'daily_log_sha256':sha(log)}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'updated_notes':len(before),'daily_log':'2026-10-27.md','family_plan':True}))

if __name__=='__main__':
    main()
