"""Append-only shared log records, UTF-8 end to end."""
from datetime import datetime, timezone, timedelta
import sys
from common import *

PREFIX='D:\\homework\\software\\linux_bug_analyze\\linux_bug_analyze\\experiments\\case_taxonomy\\boundary_closure_20261108\\'
def main():
    stage=sys.argv[1]
    when=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    if stage=='1':
        d=read(HERE/'sample_match_v2.json')['summary']
        nums='；'.join(f"{a} {v['hits']}/120（check1/2/3={','.join(str(v['by_check'][str(c)]['hits']) for c in (1,2,3))}）" for a,v in d['by_arch'].items())
        content=f'''## {when} GPT boundary_closure_20261108 阶段1：样本匹配第二版
- 做了什么：先写criteria.md并冻结SHA256={check_criteria()}。读取120条修复提交及父提交的完整本地源码，用真实增加/删除行与词法函数/宏/对象/类型范围相交；当前范围复用39单元AST并用词法范围补充。运行时池来自已完成的审计revised目录。历史映射12条（9条搬家/改名、A029的3个宏改成同名内联函数），均保存审计与当前源码证据。
- 改了哪些文件：新增完整前缀 {PREFIX} 下的 criteria.md、criteria_sha256.txt、common.py、run.sh、c_ranges.py、collect_samples.py、history_probe.py、match_samples.py、selftest_match.py、history_mappings.json、sample_match_v2.json、sample_match_v2.md、selftest_match_result.json、evidence/sample_entities.json、current_ranges.json、history_probe.json、sample_input_manifest.json、runtime_input_manifest.json及patches/120份补丁。只写本轮；本记录追加外层进度日志。
- 运行的命令与结果：本地 python -B experiments/case_taxonomy/boundary_closure_20261108/selftest_match.py；WSL通过run.sh依次运行collect_samples.py、history_probe.py、match_samples.py，均退出0。{nums}；三架构并集{d['union']['hits']}/120。RISC-V空functions命中{d['by_arch']['riscv']['empty_legacy_functions_hits']}/36；旧20命中全部保留。每条有具体范围/点和文件相交/5行邻近/无法对齐标记。RISC-V文件相交但无实体命中={len(d['by_arch']['riscv']['file_intersection_without_entity_ids'])}，可对齐但距点>5行={len(d['by_arch']['riscv']['file_intersection_far_ids'])}，相交但行对齐未知={len(d['by_arch']['riscv']['file_intersection_alignment_unknown_ids'])}。
- 关键判断：A261真正改动只有VMEMMAP_ADDR_ALIGN宏，不能把hunk上下文里的vmemmap_start_pfn算修改对象。A081还修改外层arch_xchg*，所以样本直接命中，不代表内层__arch_xchg_masked覆盖。B446宏生成系统调用表关系不由本次普通C声明提取自动恢复；仍明确未恢复。A062等即使其他修改宏命中，RV32触发分支仍不在RV64输入。修订池中B524、B580当前函数体确有使用点，与审计文字的“无点”有差异，保留原审计判断供对照，不改旧产物。
- 自己的代码错误：词法类型声明最初把结构成员误作全局对象，已修正并保持自测预期；全局对象尾部属性识别也已修正。没有为数字修改判据。
- 停在哪里：阶段1完成，新统计是跨版本描述性存在数字，不是缺陷检测查全率。
- 下一步：python -B experiments/case_taxonomy/boundary_closure_20261108/selftest_closure.py；wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh closure.py。只查询已有调用表，深度3，不扫描/重合并。
- 没有验证或不确定的：没有修复前版本构建/检测；历史缺陷检测查全率=null。词法扫描不能恢复所有宏生成声明、汇编和Kconfig实体；未解析行保留，不冒充覆盖。相同函数内有点也不说明修复行、配置分支或ABI语义已覆盖。三架构并集与旧RISC-V20不能作同口径比较。
'''
    elif stage=='2':
        d=read(HERE/'closure_stats.json')
        nums='；'.join(f"{a}：种子{v['seed_functions']}，深度1/2/3新增{','.join(str(v['new_nodes_by_depth'][str(i)]) for i in (1,2,3))}，累计{v['candidate_functions']}函数/{v['candidate_files']}文件，截断边{v['truncated_same_side_edges']}，闭包新增样本{v['samples_closure_only_ids']}" for a,v in d['architectures'].items())
        content=f'''## {when} GPT boundary_closure_20261108 阶段2：同侧内部实现闭包
- 做了什么：用三个修订direct_calls表和运行时池建立函数节点，节点以USR及定义位置区分同名静态函数。以边界提供函数及运行时跨层调用的调用方为深度0种子，只向同一侧的直接被调者传播3层，循环去重，并保留种子、父节点和样本最短路径。
- 改了哪些文件：新增 {PREFIX}closure.py、selftest_closure.py、selftest_closure_result.json、closure_stats.json、closure_riscv.json、closure_arm64.json、closure_x86_64.json、closure_nodes_riscv.jsonl.gz、closure_nodes_arm64.jsonl.gz、closure_nodes_x86_64.jsonl.gz。追加本日志；未改旧产物。
- 运行的命令与结果：本地python -B .../selftest_closure.py通过两侧、循环、3/4层、静态键、跨侧阻断、无出边未知节点；WSL run.sh closure.py退出0。{nums}。并集结合阶段1命中{d['union_combined_hits']}/120，只能靠闭包新增={d['union_closure_only_ids']}。
- 停在哪里：阶段2完成。A081的__arch_xchg_masked是宏而非C函数，不在函数调用闭包内；其外层宏已令阶段1样本命中，内层实现仍须阶段4。
- 下一步：准备config_matrix.json、配置依赖证据、config_matrix.md与新O=构建脚本；先只验证一个配置的olddefconfig，绝不执行全量内核构建。
- 没有验证或不确定的：候选正文总行数=null；区域内未解析/间接调用目标数=null；无出边不能当作叶函数。深度3之外、宏、回调、配置外实现没有完备性保证；闭包新增命中仍非缺陷检测查全率。
'''
    elif stage=='3':
        d=read(HERE/'config_matrix.json'); v=read(HERE/'config_validation/rv64_bpf.json')
        content=f'''## {when} GPT boundary_closure_20261108 阶段3：配置矩阵与单项olddefconfig验证
- 做了什么：逐条安排审计a类32条样本，形成17个新配置计划及2个已有输入条目；保存本地Kconfig原文、架构select和编译器能力探测。配置明确区分RV32/RV64、JIT、kexec、探测/跟踪、THP/热插拔、页分配调试、KASAN/KFENCE、用户态CFI与内核kCFI，以及驱动/监控器。只在新O=目录真实生成rv64_bpf配置。
- 改了哪些文件：新增 {PREFIX}config_probe.py、config_matrix.py、config_matrix.json、config_matrix.md、configure.py、config.sh、config_validation/rv64_bpf.json、evidence/kconfig_stanzas.json、kconfig_support_queries.json、compiler_capabilities.json、architecture_capabilities.json。WSL仅新增 /root/work/boundary_build/closure_20261108_rv64_bpf/（.config、配置日志与校验记录）；不动原三个构建目录。
- 运行的命令与结果：WSL run.sh config_probe.py、config_matrix.py退出0；wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv64_bpf prepare 退出0，执行defconfig、scripts/config、olddefconfig，BPF/BPF_SYSCALL/BPF_JIT/HAVE_EBPF_JIT全部y（4/4），.config SHA256={v['config_sha256']}；源码工作树前后均空。随后因计划文字证据补充，复核相同.config与请求值并更新矩阵摘要，没有再次构建或修改配置。
- 已知限制：当前Clang18按Kconfig原始-march=rv64ima_zicfiss_zicfilp -fcf-protection=full探测返回1，末行 requires '-menable-experimental-extensions' for experimental extension 'zicfiss'；rv64_user_cfi明确blocked_existing_compiler，未加参数绕过、未安装软件。-fsanitize=kcfi探测返回0，但不是用户态CFI。SCS受HAVE_SHADOW_CALL_STACK条件选择，不能强开隐藏能力。RV32需要NONPORTABLE，RV_MON_SLEEP需要RTAPP及每任务监控数>=3，当前CFI_CLANG只是过渡名，均已纳入计划。
- 停在哪里：阶段3完成配置设计和1项实际验证；没有执行全量内核构建（0）、全量扫描（0）、全量重合并（0）。其余16配置生效/全部17构建结果=null。
- 下一步由Claude执行：先 config.sh list；对计划中的未阻塞名称执行 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh <名称> prepare，核对成功后执行同脚本 <名称> build --jobs 20。rv64_bpf可直接build。每项前台运行，失败立即记录停下；不执行blocked用户态CFI、不使用nohup或&。完整名单/样本/依赖在config_matrix.md。
- 没有验证或不确定的：除rv64_bpf外其他配置尚未olddefconfig，三架构同功能配置不是完整笛卡尔积。B444/B445/B506已有arm64或x86输入，不能说riscv缺同一实现；RISCV_IOMMU与IOMMU_DMA不等价。配置开启不能证明修复分支、汇编/JIT、属性、ABI或内存模型已覆盖。初次Windows日志命令缺tzdata，已改用标准库固定UTC+8后成功追加，不安装依赖。
'''
    elif stage=='4':
        st=read(HERE/'selftest_prototype_result.json'); real=read(HERE/'real_prototype_result.json')
        content=f'''## {when} GPT boundary_closure_20261108 阶段4：宏依赖/回调设计与原型
- 做了什么：实现每TU的宏定义token候选图，外层展开连接内层宏/函数/对象/类型，并保留参数代入、重定义/undef、字符串化/拼接、递归与无法解释名字的整个外层/定义区域。实测libclang详细预处理记录不暴露全部内层宏；补存同参数clang -E -dD定义/undef轨迹，精确展开来源仍需PPCallbacks或等价前端接口。回调按规范函数类型保守收全部可见同型函数，记录ops/描述表的实际初始化引用；运行时赋值、转换、外部/未扫描TU均保留整个所属函数待分析。
- 改了哪些文件：新增 {PREFIX}prototype.py、selftest_prototype.py、real_prototype.py、prototype_src/arch/provider.h、provider.c、prototype_src/public.c、expected.json、expected_extra.json、prototype_fixture_macros.json、prototype_fixture_callbacks.json、selftest_prototype_result.json、real_prototype_result.json、evidence/prototype/夹具和A058/A081压缩预处理轨迹及宏依赖JSON、prototype_batch.sh、prototype_batch.py、prototype_summary.py、prototype_batch_selftest_result.json、prototype_scan/fixture/摘要目录、macro_callback_design.md、claude_commands.md。
- 运行的命令与结果：WSL run.sh selftest_prototype.py最终{len(st['checks'])}项通过；4个间接调用各有5个同型定义候选（不同文件同名static分开）、4个初始化对象的目标集合相同、1处运行时赋值和1处函数指针转换均保留待分析。prototype_batch.sh riscv --fixture --limit 1 连续两次，按0/2→1/2→2/2续跑并complete；run.sh prototype_summary.py riscv --fixture退出0，得到2TU、24条原始宏定义、9个外层区域（9个均保留待分析）、9个函数实体、4个间接点、1个类型组、4个初始化对象、1赋值/1转换，预期候选集合通过。
- 真实定点验证：run.sh real_prototype.py在2个不同既有编译单元上验证，宏参数未知保留策略补强后各重跑一次，共4次真实TU解析（不是全量扫描）。A058在mm/sparse.c的15处选定外层使用追到vmemmap，而libclang直接vmemmap展开0；A081在arch/riscv/errata/andes/errata.c的7处外层使用追到__arch_xchg_masked，而libclang直接展开0。所有仍不明确的外层区域保留；这些是依赖候选，不冒充精确展开或新样本命中。结果未并入75/77条完整统计。
- 停在哪里：四项任务的既有数据分析、配置设计/单项验证及原型均完成。全量扫描器/汇总器只在小夹具验证，未运行真实内核全量扫描或全量重合并；内核构建0，模型接口0，新内核缺陷/疑点0。
- 下一步由Claude执行：具体PowerShell命令在 {PREFIX}claude_commands.md。先 config.sh rv64_bpf build --jobs 20；其余配置逐项prepare→核对→build。原三个配置可各自 prototype_batch.sh <arch> --limit 8 前台重复到complete，再 run.sh prototype_summary.py <arch>。新配置构建成功后带 --profile <名称>。不得执行blocked的rv64_user_cfi。失败立即记录停下。
- 没有验证或不确定的：全量原型数量、时间/磁盘规模均null。宏参数精确代入/展开时刻绑定、token来源未实现；回调字段/表索引/跨TU指针值流、汇编和ABI转换目标未封闭。全量采集器压缩模式保守保留全部外层区域，不声称闭合。新配置的全部边界引用重扫、宏/回调/调用闭包/样本匹配统一流水线尚未接通；不能用旧枚举器defconfig硬编码去扫新配置。段/函数属性、隐含ABI与硬件内存模型、三类缺陷检测器及差分模糊测试仍未实现。
'''
    else:
        raise ValueError(stage)
    log=HERE.parents[3]/'进度日志.md'
    assert log.is_file(),log
    with log.open('a',encoding='utf-8',newline='') as f: f.write('\n'+content)
    print('appended stage',stage,'to',log)

if __name__=='__main__': main()
