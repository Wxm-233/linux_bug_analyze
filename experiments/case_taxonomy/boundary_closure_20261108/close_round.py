"""Append final handoff record after all outputs and validations exist."""
from datetime import datetime,timezone,timedelta
from common import *

def main():
    v=read(HERE/'verification.json');assert v['passed'] and v['checks']['handoff_only_section4_changed']
    m=read(HERE/'sample_match_v2.json')['summary'];c=read(HERE/'closure_stats.json')
    now=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    prefix='D:\\homework\\software\\linux_bug_analyze\\linux_bug_analyze\\experiments\\case_taxonomy\\boundary_closure_20261108\\'
    record=f'''
## {now} GPT boundary_closure_20261108 最终对账与交接
- 做了什么：四个阶段已逐项记录；补齐中文README、stats.json、执行命令、保留区域、输入/代码摘要，更新外层交接文档第四节。最终独立对账{len(v['checks'])}组全部通过，检查包括冻结判据、12个消耗输入、旧枚举97文件SHA、155个当前源码证据、120样本范围与点、三架构闭包节点/深度/同侧/路径、原三配置和唯一新配置、原型期望集合、Python/shell语法、文档链接及交接第四节外字节。
- 改了哪些文件：本轮新增 {prefix}README.md、stats.json、write_docs.py、verify_round.py、verification.json、update_handoff.py、handoff_section4.md、close_round.py、evidence/tool_manifest.json、sample_unparsed_regions.json、handoff_section4_before.md、handoff_update_verification.json；完整脚本/夹具清单和SHA见tool_manifest。修改 D:\\homework\\software\\linux_bug_analyze\\交接文档.md 仅第四节；追加 D:\\homework\\software\\linux_bug_analyze\\进度日志.md。未改experiments根索引、其他旧轮或汇报/论文。
- 运行的命令与结果：本地 python -B .../write_docs.py、update_handoff.py；WSL run.sh verify_round.py最终退出0（{len(v['checks'])}组）；README全部本地链接有效。阶段1最终RISC-V{m['by_arch']['riscv']['hits']}/120（19/34/15），arm6415，x86_6412，三架构并集{m['union']['hits']}（21/35/19）；闭包后RISC-V70、并集{c['union_combined_hits']}（22/36/19），新增A078/B577。配置17计划/32条a类/1项olddefconfig四值通过。原型17项自测通过，A058/A081真实依赖15/7处，libclang直接内层记录均0。统计未变，查全率仍null。
- 最终代码修正与复核：实质修改行判断原先和范围扫描共用去字符串的词法清理，可能把独立字符串行误排除；我改为只在“判断语义修改行”时保留字面量，添加小自测，重跑collect_samples.py与match_samples.py，仍为300个恢复实体、68/75命中。闭包输入和匹配布尔值未变，跨产物校验通过，无需重跑已有调用闭包。34条样本含不支持域/未归属行，逐行保留，未强算覆盖。没有改判据或预期集合来追数字。
- 停在哪里：本次四项按授权范围完成；没有全量内核构建/扫描/重合并。模型接口0；内核构建0；配置olddefconfig实际验证1项；新确认内核缺陷0；新内核疑点0。小夹具和2个真实TU解析不冒充全量扫描。
- Claude下一步具体命令：
  1. wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv64_bpf build --jobs 20
  2. config.sh list核对其余15个未阻塞未验证配置，逐项 <名称> prepare→核对→<名称> build --jobs 20；阻塞rv64_user_cfi不执行，不安装/改参数绕过。完整名单和依赖在config_matrix.md、claude_commands.md。
  3. wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh riscv --limit 8，前台重复到complete；arm64/x86_64替换arch。然后 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py riscv（其余架构同理）。新配置构建成功后两条命令均带 --profile <名称>。失败记录不能静默跳过，长阶段立即记日志；不使用nohup/&。
- 没有做完或没验证：其余16配置生效/全部构建、真实全量宏回调采集及资源规模均null；新配置完整边界枚举与宏/回调/闭包/匹配统一接线未实现。精确宏参数/展开时刻/来源、回调字段/索引/跨TU值流、段/函数属性、隐含ABI与硬件内存模型仍欠缺。三类检查器、修复前评估、误报/查全率与定向差分模糊测试未做。现有75/77只是当前版本候选位置描述，不能承诺“不漏报”。
'''
    with (HERE.parents[3]/'进度日志.md').open('a',encoding='utf-8',newline='') as f:f.write(record)
    print('final record appended')

if __name__=='__main__':main()
