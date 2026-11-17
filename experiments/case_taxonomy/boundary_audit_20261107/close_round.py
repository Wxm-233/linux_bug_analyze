"""Append UTF-8 progress records from a file, avoiding PowerShell stdin encoding."""
from pathlib import Path
from record import record

HERE=Path(__file__).resolve().parent
PREFIX=r'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\boundary_audit_20261107'
WSL='/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107'

def main():
    record('问题1阶段记录中文编码更正',f'''
- 更正说明：10:55的本轮阶段记录经PowerShell标准输入传递时，中文被替换成问号；这是我自己的记录命令编码错误。按只追加规则保留原记录，以下补记完整内容；分析结果JSON/Markdown由UTF-8文件生成，没有这一损坏。11:05的问题2记录同样在下一条更正。
- 做了什么：逐条读100份本地完整补丁，核对当前源码、riscv .config与compile_commands、既有缓存和39个相关C单元的函数范围；判据先冻结，SHA256=a2a23f31e0c7e7509c2e940751fda9f361f3cf18c2348be12376b1bdc6a87ba2。
- 改了哪些文件：新增 {PREFIX}\\analyze_samples.py、{PREFIX}\\sample_miss_analysis.json、{PREFIX}\\sample_review.md；完整补丁在 {PREFIX}\\evidence\\patches\\，带行号当前源码在 {PREFIX}\\evidence\\current\\；证据JSON为sample_inputs、sample_extra、scopes、compiled_sources、relevant_boundaries、name_queries、more_queries、aio_debug、sample_final_queries（均在本轮evidence目录）。
- 运行的命令与结果：WSL经run.sh运行collect.py、scopes.py、queries.py、more_evidence.py、aio_debug.py、sample_final_queries.py；本地 python -B experiments/case_taxonomy/boundary_audit_20261107/analyze_samples.py，最终退出0。120=20原命中+64非空未命中+36空字段。64条主因a22/b9/c3/d0/e30；36条a10/b2/c8/d2/e14；100条a32/b11/c11/d2/e44，u0。check1/2/3未命中32/45/23，a/b/c/d/e分布分别(10,2,5,2,13)/(14,6,4,0,21)/(8,3,2,0,10)。空字段27条有文件交集，15条有恢复符号交集，A105虽THREAD_SIZE已枚举但KASAN分支未开，主因仍a。
- 关键结论：非空30条e中29条是现有使用点未按使用方函数匹配，B435是提取/历史位置问题。空字段14条主因e；不能把36条都算无法分析。A058的vmemmap是嵌套宏漏依赖；B446的公共强实现与公共弱桩同USR造成歧义，真实生成表引用被漏。配置外与旧名字失效也不能冒充工具漏项。
- 停在哪里：逐条证据与分类完成。下一步工具修订与最终汇总见本日志最后一条，不需重新读对话。
- 没有验证：未把历史补丁行机械映射到当前行；文件/函数有点不证明修复行或触发配置覆盖。历史修复前缺陷查全率=null；a含另一架构/RV32输入不匹配，不能据此说整个三架构矩阵都不含相应实现。
''')
    record('问题2阶段记录中文编码更正',f'''
- 做了什么：按冻结判据4层各选4个单元（SHA排序），固定种子20261107每层抽100处细查；riscv没有merge pickle，预先写criteria_amendment1.md，改用nm、目标缓存和已解析调用恢复所需定义索引，未全量扫描。
- 改了哪些文件：新增 {PREFIX}\\unresolved.py、inspect_unresolved.py、unresolved_queries.py、unresolved_details.py、unresolved_sources.py、analyze_unresolved.py（同一完整目录前缀），结果 {PREFIX}\\unresolved_analysis.json；本轮evidence下保存unit_selection、definition_lookup、unresolved_population、unresolved_unit_counts、unresolved_reference_sample、unresolved_ast、unresolved_queries、unresolved_compilation、unresolved_details、unresolved_asm_definitions、unresolved_source_lines、unresolved_classified_population等JSON。
- 运行的命令与结果：WSL均用 wsl -u root -- bash {WSL}/run.sh <脚本.py>；本地python -B .../analyze_unresolved.py。16/16单元的definition_not_found与旧报告逐一完全对上，共30141处；400处细查。四层总体单元110/2203/1647/225，抽中原始引用7151/10254/8231/4505（顺序arch/drivers/公共/生成）。
- 分类数字：编译器内建11723、不完整类型前向声明10489、编译期/优化守卫6742、活动架构汇编632、链接脚本272、关闭配置dummy声明130、未活动公共C127、公共模块等非core定义14、模块alias6、未完整恢复static-call4、未活动架构C1、未构建架构汇编1。局部变量/参数/普通字段0，因为采集器已过滤/转为所属类型。未发现同TU同USR完整类型漏认；不是断言全内核为0。
- 核心结论：632次活动汇编引用中562次跨层、70次层内；跨层去除重复头文件/单元后150个源位置。562/30141=1.86457%是所选引用的确认漏项下界，不是总体估计或查全率。例bitmap.h:269 memcpy→arch/riscv/lib/memcpy.S，最终nm W绑定。旧对象证据只处理汇编发出的未定义引用，漏C→汇编反方向；另有254次链接脚本符号可能跨层，未混入下界。
- 停在哪里：问题2完成；工具和全部交接状态见最后一条。
- 没有验证：全riscv8971092处的漏项比例/数量=null，16个整群单元不能按400个独立样本估全内核区间。4处static-call绑定未完全恢复；400处中的162个builtin隐式声明不在普通TU声明遍历中，显式保留null及原因，不编造项目定义。
- 自己的命令错误：shell换行拼接、WSL无rg改用grep、modules.order误当.ko导致二进制文本解码错误均已改正；过慢文本查询仅中止自己启动的任务，改为nm+目标缓存。最终对账全部通过。没有为结果改判据/自测预期。
''')
    record('分析完成与修订工具交接',f'''
- 做了什么：本轮三个问题已完成分析、逐条证据与中文README；判断当前边界全集不足以支撑三类检查“不漏报”。先冻结criteria与修订说明，再保存新工具，仅做小规模验证。旧轮97个文件SHA256逐个一致，没有修改旧enumerate.py或旧产物。
- 改了哪些文件（本轮完整目录前缀为 {PREFIX}）：新增README.md、stats.json、criteria_amendment2.md及criteria_amendment2_sha256.txt、repair_policy.py、remerge.py、claude_remerge_batch.sh、report_revised.py、selftest_original/源夹具与verify.py/result.json、selftest_revision.py及selftest_revision_src/、selftest_revision_result.json、verify_real_repairs.py、real_repairs_verification.json、verify_audit.py、verification.json、summarize_audit.py、validate_scripts.sh、handoff_section4.md、update_handoff.py、close_round.py；证据与代码摘要在evidence/。同时只更新 D:\\homework\\software\\linux_bug_analyze\\交接文档.md 的第四节，前后其他节字节一致，校验见evidence/handoff_update_verification.json；追加 D:\\homework\\software\\linux_bug_analyze\\进度日志.md。未改experiments/README等其他已有文件，当前轮入口已写交接第四节。
- 判据摘要：criteria SHA256=a2a23f31e0c7e7509c2e940751fda9f361f3cf18c2348be12376b1bdc6a87ba2；amendment2 SHA256=5dd78f17b7f532e4dc06affe4661ff500419f1de1304e4fd3925b40778ee9c54。修订只处理任意层别强弱绑定、C→asm独立对象证据和生成/host候选分池；宏闭包等没有实现。
- 小规模验证命令（均实际运行，最终退出0）：
  - wsl -u root -- bash {WSL}/run.sh selftest_original/verify.py：原预期19点/12符号全部通过，预期块与旧脚本逐字一致。
  - wsl -u root -- bash {WSL}/run.sh selftest_revision.py：5个C单元+1个汇编的小夹具；1个AST跨层点，2个C→asm点（1跨层、1层内），公共强弱、旧歧义复现、非唯一拒绝消歧、模块范围、检查点保存恢复、生成/host分池和汇总辅助逻辑全部通过。
  - wsl -u root -- bash {WSL}/run.sh verify_real_repairs.py：只读既有pgetevents相关缓存及nm，真实B446的compat/native两个引用由旧ambiguous改为fs/aio.c；另一个真实bitmap→memcpy汇编提供者验证通过。
  - wsl -u root -- bash {WSL}/validate_scripts.sh：shell语法/Python AST语法与remerge --help通过，不启动扫描/合并。
  - python -B experiments/case_taxonomy/boundary_audit_20261107/summarize_audit.py：8组跨产物校验通过，100样本/16单元/400细查/3架构生成分组对账、SHA及旧目录不可变性通过，写stats.json与代码清单。
- 其他写入说明：为真实验证链接规则，两套小夹具的目标/ELF/缓存写在独立的 /root/work/boundary_build/enumeration/boundary_audit_20261107_original_selftest/ 与 boundary_audit_20261107_revision_selftest/，不动三个内核构建及旧缓存。这是小夹具编译链接，不是内核构建。模型接口调用0，内核构建0，全量扫描0，全量重合并0，新确认内核缺陷0，新内核疑点0。
- 停在哪里：分析与局部修订已交付，三架构修订重合并尚未开始，结果数字均null。旧集合差只删模块元数据可得3605/198827、6395/443407、7428/243747，是集合推导，不能冒充新工具输出。生成接口表375/383/604点保留；模块元数据14/16/0点单列但原始证据保留。
- 下一步由Claude执行（前台分批，不用nohup/&，不得覆盖旧目录）：
  1. 对riscv重复：wsl -u root -- bash {WSL}/claude_remerge_batch.sh riscv 128
  2. 对arm64重复：wsl -u root -- bash {WSL}/claude_remerge_batch.sh arm64 128
  3. 对x86_64重复：wsl -u root -- bash {WSL}/claude_remerge_batch.sh x86_64 128
  各架构首次初始化，之后每次128个C单元，名义调用次数34/86/25。直到complete.txt出现；输出在本轮revised/<arch>/<摘要>/，控制台打印路径。输入/工具不一致会拒绝继续或采用新摘要目录。初始化读全缓存与对象表但不解析源码，耗时未测。
  4. 三个架构完成后：wsl -u root -- bash {WSL}/run.sh report_revised.py
  该脚本写本轮revised_stats.json，核对4185/10822/3022单元、失败0、摘要一致及B446 compat表引用。分别报告AST/运行时池/C→asm证据与剩余未解析数，不能直接相加异质点数；不要运行旧summarize/report覆盖原结果。每架构完成立即追加日志。
- 没有验证或未完成：未跑修订全量重合并及全三架构新汇总；新历史样本匹配统计未实现；全riscv漏项比例/数量、历史修复前查全率均null。嵌套宏（A058）、回调/描述表/内部实现闭包、链接脚本域、配置约束/矩阵、函数与段属性、隐含ABI/硬件内存模型尚未实现；4处static-call绑定仍未恢复。三类检查器、误报/查全率评估、定向差分模糊测试均未做。本次工具修订不能自动恢复“不漏报”。
- 自己的校验命令问题已纠正：Windows/WSL相对路径分隔符不同曾造成旧SHA比较假阳性，改为as_posix后97文件全部一致；400处声明检查最初误要求builtin出现在普通声明遍历，改为对其显式null与原因进行验证，非builtin声明均有实证。中文日志管道错误已在本次追加更正，未回改历史记录。
''')
    record('最终证据一致性补记', '''
- 做了什么：最终检查发现unresolved_analysis的汇总数字和400处细查正确，但“前20组”和“确认漏项例子”在重复应用分类函数时，已分类类别名未被识别，导致例子的类别标签错误。我修正了分类函数对规范类别的重复处理，并增加组/例子标签及漏项布尔值一致性核对。没有改判据、样本选择或任何统计数字。
- 改了哪些文件：本轮analyze_unresolved.py、verify_audit.py、close_round.py；重新生成unresolved_analysis.json、evidence/unresolved_classified_population.json、stats.json、verification.json、evidence/audit_code_manifest.json。原轮97文件仍逐字节一致。
- 运行的命令与结果：python -B experiments/case_taxonomy/boundary_audit_20261107/analyze_unresolved.py；python -B .../summarize_audit.py，最终均退出0，原8组校验及新增例子一致性全部通过。README链接全部可访问，交接第四节之外的前后字节SHA一致，修正后的中文日志可读，全部shell第一行source规则符合。
- 停在哪里/下一步：分析结论与Claude四条批次/汇总命令不变，见上一条完整交接。本轮没有启动全量重合并，未完成与局限仍同上一条。
''')
    print('UTF-8 correction and final handoff records appended')

if __name__=='__main__':main()
