"""Replace only section four; preserve every byte before/after the section."""
from datetime import datetime,timezone,timedelta
from common import *

def main():
    document=HERE.parents[3]/'交接文档.md'
    raw=document.read_bytes()
    start=raw.index('## 四、当前进度'.encode('utf-8'))
    end=raw.index('## 五、每轮实验怎么做'.encode('utf-8'))
    now=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    match=read(HERE/'sample_match_v2.json')['summary'];closure=read(HERE/'closure_stats.json')
    config=read(HERE/'config_validation/rv64_bpf.json')
    md=f'''## 四、当前进度

**{now}（GPT）停点：新轮 `boundary_closure_20261108` 的四项已完成到用户授权范围：已有数据样本匹配、3层内部实现闭包、配置矩阵/1项olddefconfig验证、宏与回调设计及小原型。边界输入仍不能支持三类检查“不漏报”。下一步由Claude执行新配置构建和宏/回调原型的分批全量证据采集，具体命令见本节末和本轮claude_commands.md。**

### 固定背景与已经完成的输入

- 当前方向只做跨架构缺陷发现，不用模型、不做修复迁移；三类保持数据一致性37条、实现完备性57条、调用上下文26条（另15条构建/工具链排除）。分类入口 `experiments/case_taxonomy/boundary_taxonomy_20261106/`。
- 内核固定 `df2908090cda368b01ff43709f51890076c56157`（v7.3-rc2），源码只读。原riscv RV64、arm64、x86_64 defconfig构建均成功；编译数据库4231/10898/3093条，成功C单元4185/10822/3022，失败0；构建在 `/root/work/boundary_build/<arch>_defconfig/`，配置摘要本轮复核未变。
- 原边界枚举在 `boundary_enum_20261106/`，不改旧工具/旧产物。审计在 `boundary_audit_20261107/`，Claude已于11-07 12:45完成三架构修订重合并；`revised_stats.json`指向完成目录。运行时池符号/点：riscv3764/199088、arm646630/443757、x86_647755/244222；C→asm独立跨层点6914/6853/5282，不与AST点直接相加。B446公共强/弱绑定已修复，但宏/回调/配置/ABI等剩余缺口仍存在。
- 审计100条旧未命中主因a32/b11/c11/d2/e44，全部有逐条证据。16个riscv单元30141引用里确认跨层C→asm漏项562次（150位置），1.86457%仅是这些单元的确认下界，全riscv漏项比例/数量仍null；4处static-call绑定仍未恢复。旧19点/12符号自测和局部修订自测通过不等于全内核完整性。

### 本轮入口与判据

本轮目录为 `linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/`。先读README.md、stats.json、criteria.md；样本证据sample_match_v2.json/md，闭包closure_stats.json及closure_<arch>.json，配置config_matrix.md/json，原型macro_callback_design.md，执行命令claude_commands.md。判据SHA256=`{check_criteria()}`，未修改判据或旧产物。

### 1. 样本匹配第二版

从120条修复提交和父提交的完整文件恢复真正增加/删除行所属函数/宏/对象/类型，不只相信旧functions或hunk提示。当前函数本身是边界提供者、函数体有点，或修改宏/对象/类型本身是边界，才计命中；文件相交另列。历史映射12条保存可核对证据，其中A029的3个宏已改成同名内联函数。

| 输入 | 检查一/37 | 检查二/57 | 检查三/26 | 合计/120 |
|---|---:|---:|---:|---:|
| riscv | {match['by_arch']['riscv']['by_check']['1']['hits']} | {match['by_arch']['riscv']['by_check']['2']['hits']} | {match['by_arch']['riscv']['by_check']['3']['hits']} | {match['by_arch']['riscv']['hits']} |
| arm64 | {match['by_arch']['arm64']['by_check']['1']['hits']} | {match['by_arch']['arm64']['by_check']['2']['hits']} | {match['by_arch']['arm64']['by_check']['3']['hits']} | {match['by_arch']['arm64']['hits']} |
| x86_64 | {match['by_arch']['x86_64']['by_check']['1']['hits']} | {match['by_arch']['x86_64']['by_check']['2']['hits']} | {match['by_arch']['x86_64']['by_check']['3']['hits']} | {match['by_arch']['x86_64']['hits']} |
| 三架构并集 | {match['union']['by_check']['1']['hits']} | {match['union']['by_check']['2']['hits']} | {match['union']['by_check']['3']['hits']} | {match['union']['hits']} |

RISC-V旧20命中全部保留，空functions的36条命中17条。文件相交但无实体命中18条；可对齐的修复行距点都>5行9条，完全不能对齐7条，集合有交集不能相加。相同行块是机械对齐，不保证历史语义/分支不变。全部数字仍是跨版本描述性存在，不是缺陷检测查全率，后者null。

例：A261真正只改VMEMMAP_ADDR_ALIGN，不能用hunk上下文的vmemmap_start_pfn算命中；A081还改外层arch_xchg*，所以样本直接命中但内层宏仍缺；A062虽其他宏命中，RV32触发分支仍未覆盖；B446宏生成表项仍未被普通C声明恢复。修订池的B524/B580当前函数体确有点，与审计文字有差异，逐条保存旧判断对照；点存在不等于ABI/属性检查完成。

### 2. 同侧3层直接被调者闭包

使用修订direct_calls表，节点按USR与定义位置区分；深度0为边界提供函数及已确认跨层调用的调用方，只沿同侧传播3条边。

| 架构 | 种子 | 深度1/2/3新增 | 累计函数/文件 | 深度3外截断边 |
|---|---:|---|---|---:|
'''
    for a,d in closure['architectures'].items():
        md+=f"| {a} | {d['seed_functions']} | {'/'.join(str(d['new_nodes_by_depth'][str(i)]) for i in (1,2,3))} | {d['candidate_functions']}/{d['candidate_files']} | {d['truncated_same_side_edges']} |\n"
    md+=f'''
闭包后riscv70/120，三架构并集77/120（检查一/二/三22/36/19）。只能靠新增闭包命中A078、B577；A078仅其头文件local_flush_icache_range被覆盖，FUNCTION_TRACER分支仍需补。A081的__arch_xchg_masked是宏，不冒充C调用闭包节点。候选正文行数、区域内未解析/间接调用量null；无记录出边不等于叶函数。

### 3. 配置矩阵与唯一实际验证

17个新配置计划、2个已有输入条目逐条安排32条a类样本；包括RV32/JIT/kexec/跟踪探测/THP/DEBUG_PAGEALLOC/KASAN/KFENCE/热插拔/CFI/监控器/MLX5。每项列架构、样本、依赖和限制。

只实际执行 `config.sh rv64_bpf prepare`：新O=`/root/work/boundary_build/closure_20261108_rv64_bpf`，defconfig→scripts/config→olddefconfig成功，BPF/BPF_SYSCALL/BPF_JIT/HAVE_EBPF_JIT四项y，配置SHA256=`{config['config_sha256']}`。原三个配置和内核源码未变；未执行全量内核构建。

其余16配置实际生效、全部配置构建结果null。用户态rv64_user_cfi受当前Clang18原始Kconfig能力测试阻塞（zicfiss需要experimental扩展），不安装、不改参数绕过；内核CFI是不同开关，当前CFI_CLANG为过渡名。SCS仍要核对HAVE_SHADOW_CALL_STACK；RV32需NONPORTABLE；RV_MON_SLEEP需RTAPP和>=3监控槽。

### 4. 宏/回调设计与原型

- 17项小夹具自测通过：4个间接调用各保留5个同型定义候选；4个ops/描述表初始化对象引用集合相同；同名static区分，1赋值/1转换明确待分析。分批原型只在2个夹具TU验证1+1续跑和汇总，9个外层宏区域全部保留待分析。
- 两个真实TU定点验证（修改策略后各重跑一次，总4次解析）：A058在mm/sparse.c的15处外层使用能追候选依赖到vmemmap；A081在所选errata单元7处追到__arch_xchg_masked；libclang对这两个内层宏直接展开均0。没有将定点候选并入75/77条全量匹配统计。
- libclang详细记录不足；原型以定义token图加clang -E -dD定义/undef轨迹保存候选。参数代入、重定义时刻、字符串化/拼接、递归、未知标识符保留整个外层/定义区域；精确来源需PPCallbacks或等价前端接口，尚未实现。回调按规范类型全收可见同型函数并记录真实初始化引用；字段/索引/跨TU指针值流未封闭，外部/运行时/转换目标保留整个函数区域。
- 全量原型扫描与新配置完整边界池集成尚未运行/接通。全量数量、耗时、磁盘规模均null；段/函数属性、隐含ABI/硬件内存模型、三类检查器、修复前评估、定向差分模糊测试仍未做。

### Claude下一步命令（完整名单见本轮claude_commands.md）

1. 已验证BPF配置可先构建：

   ```powershell
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv64_bpf build --jobs 20
   ```

2. 其他未阻塞配置先 `config.sh <名称> prepare`，全部请求值核对后再 `<名称> build --jobs 20`；`config.sh list`列出状态。不得执行阻塞用户态CFI；生效/构建失败按规则记录停下。
3. 原三个配置各自前台分批采集宏/回调证据，重复同一命令直到complete，再汇总。首次先评估小批次资源，不自行改旧枚举器/旧产物：

   ```powershell
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh riscv --limit 8
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py riscv
   ```

   arm64/x86_64替换arch；新配置成功构建后两条命令均加 `--profile <名称>`。这些是原型证据采集，不会自动产生统一的新边界全集；新配置的完整引用枚举/闭包/匹配接线还需开发。失败记录不能静默跳过。
4. 长任务每完成一项立即追加进度日志并更新这里。模型接口0、内核构建0、全量扫描0、全量重合并0、新内核缺陷/疑点0；本轮验证见verification.json。旧枚举97文件SHA、全部消耗输入摘要和原配置已核对未变，交接第四节外字节保持不变。

---

'''
    (HERE/'handoff_section4.md').write_text(md,encoding='utf-8')
    before=HERE/'evidence/handoff_section4_before.md'
    if not before.exists():before.write_bytes(raw[start:end])
    replacement=md.replace('\n','\r\n').encode('utf-8') if b'\r\n' in raw else md.encode('utf-8')
    document.write_bytes(raw[:start]+replacement+raw[end:])
    updated=document.read_bytes()
    assert updated[:start]==raw[:start] and updated[start+len(replacement):]==raw[end:]
    write('evidence/handoff_update_verification.json',{
        'outside_before_sha256':hashlib.sha256(raw[:start]).hexdigest(),
        'outside_after_sha256':hashlib.sha256(raw[end:]).hexdigest(),
        'old_section_sha256':sha(before),
        'new_section_sha256':hashlib.sha256(replacement).hexdigest(),'only_section4_changed':True})
    print('updated handoff section 4 only')

if __name__=='__main__':main()
