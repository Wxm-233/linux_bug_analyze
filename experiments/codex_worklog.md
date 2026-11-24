> 2026-11-06 起停用：工作记录改写在外层主文件夹的 `进度日志.md`（Claude 与 GPT 共用）。以下为停用前的记录。

## 2026-11-09 GPT semhint_dev_20261109 接手执行器编码（实现前）
- 本次用户明确指定只写 `semhint_dev_20261109/harness/` 和本工作日志，并要求在本日志追加；因此按本次较新的限定执行，不改外层交接文档、进度日志或本轮其他文件。
- 已全文读外层交接文档、进度日志末尾记录、仓库 AGENTS.md、本轮 criteria.md，已读上一轮 dt_init2.c 的完整探测和关机代码及两个 shell 脚本。首次 PowerShell 读取未显式指定 UTF-8，中文显示错误；已改用 UTF-8 重读。
- 实现前核对判据 SHA256：`d124fd00cee1c70f344eedad596e88cf75cd6f82fc6c00337b01d678c8bf632f`；不修改判据。
- 计划：实现同源静态 /init、打包/运行/解析脚本，手写三架构自测并在三个指定的已有内核各运行一次。仅用自测，不读或执行 gen/ 正式用例，不构建内核、不联网、不安装。
- 固定实现约定（运行前）：xorshift64 移位顺序 13/7/17；每次生成一个 64 位数，其低位决定指针/64，同一个数取模决定槽。先按参数下标填主缓冲区，再按槽号填池 0–31；所有 g 共享本用例随机状态和池。调试输出将地址归一为槽号后比较，并校验整个池。
- 自测扩展：新增 `f:pipeblockrd`，持有写端但不写数据，以确定阻塞；不改变已有记号。自测首行 `# SH_SELFTEST` 开启调试/计时输出，正式无该行则不输出调试。失败进程的未观测 b/pool 表达已异步询问用户，独立工作继续。
- 下一步：写 harness 源码与自测；先用 selftest/run_selftest.sh inspect 读取三个目标工具链的 unistd 宏和内核镜像元数据，随后只构建 /init 并运行 QEMU。


## 2026-11-06 构建矩阵与边界枚举（后台启动异常）
- 改了：boundary_enum_20261106/criteria.md、criteria_sha256.txt、build.sh、README.md、stats.json，以及本工作日志。
- 运行：重读项目说明；冻结判据并复核 SHA256 一致；通过 WSL 执行一次 nohup 后台启动，返回 0，但后续 ls 确认输出目录为空，无 driver.log、progress.txt，也无匹配的构建进程。git status --short 为空。完成构建 0，自测未运行。
- 结论：后台启动未取得可验证执行结果，按失败即停未重启；不能报告任一架构构建完成。
- 没做到或不确定：启动异常具体原因未核实；三个构建、数据库、枚举工具、自测、nm 补充及边界/样本统计均未完成，统计数量用 null，不是零。

## 2026-11-06 boundary_enum_20261106 继续枚举（前置命令错误停止）
- 改了：本轮 README.md、stats.json、criteria_amendment1.md；原判据摘要复核一致。
- 运行：读取 AGENTS.md 和 criteria.md；WSL 前置核对命令因我对 PATH 引号处理不当，在含括号的路径处产生 Bash 语法错误，退出码 1；未重试。自测未运行，枚举未运行。
- 结论：用户报告 Claude 已在修正 LLVM 工具 PATH 后完成三架构构建，已注明执行者及首次 llvm-ar 缺失失败；本次尚未独立复核构建产物。按失败停止规则收尾。
- 没做到或不确定：枚举工具、手工样例、nm 补充、边界点与符号、三架构交集、样本命中和解析失败数全部未取得，不能报零。前台替代后台执行另写 amendment，未修改原判据。

## 2026-11-10 heldout_prep pipeline 阶段：目标参数化及必做回归通过
- 改了：仅 experiments/case_taxonomy/heldout_prep_20261110/pipeline/ 中的七个复制脚本、settings.py、cli.py、构建/排序输入快照、回归与冒烟脚本及产物；父判据与旧轮次未改。
- 运行：WSL 前台 selftest.sh（riscv 12/12、loongarch 13/13）；regress.sh 的 hints/rank/layouts/extract/audit 四项必做回归全部逐字段相同：hints 3708 点、rank 160→40、布局三架构各52类型且错误0、抽取1个成功单元5685函数2558宏（只排除计时）。static2/casemodel 的 CUR sites 相同。api_check.sh：7个CLI帮助正常，vocab完整输出相同。
- 结论：架构切换与必做回归已完成；LoongArch smoke 当前构建4/4单元解析成功，7个系统调用入口，I1宏288/函数79，其中目标头文件宏114；未评估留出集。
- 没做到或不确定：补充 probe_check.sh 首项断言失败：TASK_SIZE_MAX=nonconst，NR_syscalls=473，未改期望未重跑，具体原因未核实，完整宏探针等价性未验证。初次回归汇总并发覆盖已修为逐项落盘并补齐记录。下一步写完整使用说明、最终核对并收尾。按本次用户限制，只写 pipeline 与本工作日志，不更新外层交接文件。

## 2026-11-10 heldout_prep_20261110/pipeline 收尾：可指定目标架构，必做回归4/4通过
- 改了：本轮 pipeline/ 下的 extract3.py、hints4.py、macro_values.py、macro_values2.py、layouts.py、vocab.py、rank.py（均从旧轮次复制后修改）；新增 settings.py、cli.py、run.sh、builds.json、boundary_names.json/nr_tables.json/version_tables.json/rank_policy.json 只读快照、criteria.md 与 SHA256、README.md、regress_riscv.md、source_manifest.json、changes.patch、delivery_manifest.json、stats.json，及自测/回归/冒烟/收尾脚本和 tests/、regression/、smoke/ 结果。只改本目录与本工作日志，未改外层交接及父判据。
- 运行：全部 WSL 命令经首行 source tools/wsl_env.sh 的 .sh 前台运行，无内核构建、执行器运行、软件安装或联网。selftest.sh：RISC-V 12/12、LoongArch 13/13；四项必做回归8个逐字段比较均相同：hints4 全返回值/词表/统计/sites（3708点，335入口，T=252；词表301调用751参数）、rank CUR 两文件（160→40）、布局（59根，每架构找到51根/总52类型/错误0）、futex 单元原/新输出（1个成功单元5685函数2558宏，只排除计时）。static2 与 casemodel CUR facts 的全部 sites 相同，rank 维持原 static2 输入。接口整理后再次运行 rank/layouts/extract，仍全部相同；api_check.sh 7个help正常、vocab完整输出相同；run.sh 的 LoongArch rank --selftest 通过。
- LoongArch 冒烟：读取已完成 vmlinux，生成数据库到本轮 smoke/（7874项，不改构建目录）；按文件名顺序抽3个 arch/loongarch/kernel 单元（acpi.c、alternative.c、cacheinfo.c）加 kernel/futex/syscalls.c，4/4成功、合并6811函数，7个 __do_sys_*，I1宏288/函数79，目标目录宏114。没有完整常量取值，空取值映射下 sites=0，不评价留出集。
- 结论：必做回归4/4通过，已具备目标架构与输入/输出切换接口；LoongArch 强制禁用RISC-V边界池，FIXITEMS/FIXC不用于LoongArch，排序不再import生成器。finish.sh 汇总复核：父/本轮判据SHA一致，10个旧脚本/数据源SHA未变，内核工作树干净。
- 没做到或不确定：额外 probe_check.sh 失败于 RISC-V 首项，断言要求全整数而 TASK_SIZE_MAX=nonconst、NR_syscalls=473；保留失败JSON，未改期望未重跑，具体原因未核实，LoongArch探针分支未到达；两个宏探针的全量等价性、历史组回归、LoongArch全量事实/词表/布局/排名均未验证。默认调用号/版本表快照仍只有旧RISC-V组，LoongArch完整排序须显式提供实际 loongarch 与 cur_loongarch 表，缺少则报错。旧轮次和动态侧中的riscv常量不在本次范围。
- 停在哪里及下一步：本次编码交付完成，使用方式见 pipeline/README.md；复核入口为 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline/finish.sh。需要继续LoongArch完整静态流水线时，由Claude准备实际调用号/版本输入并依README传参；不得读取candidates.json或LoongArch补丁调规则。附加宏探针失败单独留待决定，不声称该项通过。初次回归汇总并发覆盖已改为独立比较文件并补齐记录。

## 2026-11-15 16:31:12 Codex：第二标注人盲判

- 按本次任务限定，只读取允许的判据、60 项样本、codex_blind 下的文件及内核历史；未读取第一标注人的结论或交接、进度文档。
- 逐项读取全部 60 个提交的完整补丁，并按需要检查修复前后的源码；独立判断已写入 `experiments/case_taxonomy/depmine_20261115/codex_blind/codex_judgement.json`，难判说明与判据意见写入同目录 `notes.md`。
- 同目录保存完整补丁、读取脚本和校验脚本。运行 `validate_blind.py` 完成样本顺序、60 项完整性、字段类型、完整补丁记录及 SHA256 校验，结果保存至 `review_validation.json`；没有遗漏条目。
- 未构建、未联网、未调用其他模型，内核仓库只读。本条只记录操作与输出位置，不记录判断结论细节。

- 2026-11-15：独立盲判 P1 的 30 条 O1 静态报告，并只读核查 df2908090cda 的源码与调用路径；输出位于 experiments/case_taxonomy/p1check_20261115/codex_blind/codex_o1.json 和 experiments/case_taxonomy/p1check_20261115/codex_blind/notes.md。

## 2026-11-15 19:54:19 +08:00 Codex：contract_20261115 前 30 条第二标注人盲判

- 本轮任务：按用户特别授权，独立判断固定提交 df2908090cda 的 review_top30.txt；不读取第一标注人的结论、实验 README、外层交接文档及进度日志。本次仅按要求追加本工作日志，不更新外层文档；没有与第一份标注比较。
- 新建文件（均在 experiments/case_taxonomy/contract_20261115/codex_blind/）：codex_top30.json（30 项正式盲判）、notes.md（难点、源码依据、方法局限及输入哈希）、criteria.md（先固定的盲判协议）、read_kernel.sh（固定提交的只读查询脚本）。原有 prompt.md 未修改，未修改挖掘器、内核源码或其他轮次文件。
- 判据先于逐条完整源码核对写定，SHA256：efbc8293371d8eba9bde2c7c8c095e8d45e9b6c38dba2be7d94ae208a169f135。报告 SHA256：bfbd9089a29fb784490ff197ebd13f639eabf617a6d4e0b14f12d2614e841af8。实验允许读取的 criteria.md、criteria_amendment1.md、criteria_amendment2.md 的哈希另记于 notes.md。
- 主要命令：PowerShell Get-Content 仅读允许的报告和判据；WSL 使用 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/contract_20261115/codex_blind/read_kernel.sh <文件:行段>，脚本第一行 source tools/wsl_env.sh，内部仅 git -C /root/repos/linux show df2908090cda:<文件> 或 git grep -n -E <模式> df2908090cda -- <源码路径>。追踪了锁包装/回调配对、hugetlb 的辅助解锁、kstrtobool 的返回传播、malloc 链式赋值、软中断快照、页表分类与调用者持锁保证，以及 ptep_set_access_flags 的通用与部分架构实现。
- 结果：可能 0；不可能 30；说不清 0。K2 17 条、K3 13 条；12 条加锁后的 K3 报告中，9 条属于持锁返回包装/回调，3 条在辅助函数内解锁。第 30 条由访问权限更新接口完成所需写入，不能要求统一的清空重装序列。该结果仅否定本批报告所声称的缺失，不推算全部候选的准确率。
- 验证：ConvertFrom-Json 解析；逐项核对 k=1..30、loc 与原报告完全一致（30/30），字段恰为 k/loc/verdict/why、verdict 合法、why 非空、无乱码替换字符；报告及盲判判据哈希未变化。首次源码查询的竖线参数引用错误已拆开重跑；首次校验的 PowerShell 数组嵌套错误已修正重跑，均为自己的命令问题，未改变结果。
- 统计与未验证：其他模型调用 0；构建 0；联网/下载/安装 0；新确认缺陷 0；动态验证 null；跨架构配置逐一验证 null；标注一致性 null。未运行内核、未改分支、未 commit/push。
- 正式结果 SHA256：codex_top30.json = 2f6566010e588964657e2b5734c91d622f9350f49564ada6cdbeaa6679879ec9；notes.md = 475b176d2d161657a9b5bfc043640cd340e94335e00dfd07c7d545f6350f6dd8。
- 停止点：30 条均已独立标注且格式和位置校验完成。后续由取得两份独立结果的人进行一致性比较及裁定；本标注人不读取第一份结论。若要复查第 30 条，可运行：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/contract_20261115/codex_blind/read_kernel.sh 'mm/memory.c:3883-3918' 'mm/pgtable-generic.c:60-80'。

## 2026-11-15 20:36:17 +08:00 Codex：encrank 新增 26 条报告第二标注人盲判

任务与边界：按本次用户特别要求，跳过外层交接文档、进度日志及其通常交接流程；未打开其他标注人的判断、相关实验 README，也未打开被禁止的 p1check/contract/p1dyn 判断文件。只使用 encrank 父目录允许的 review_new.txt、criteria.md、criteria_amendment1.md、table.md，以及 df2908090cda 固定提交的内核源码。例外说明：本次明确要求向这个旧工作日志追加记录，因此仅在末尾追加，不更新外层文档，不修改其他实验内容。本目录原有 prompt.md 未修改。

新增文件均位于 experiments/case_taxonomy/encrank_20261115/codex_blind/：
- criteria.md、criteria_sha256.txt：在逐条完整源码复核前固定盲判协议；复核结束 SHA256 仍为 d3be8cc21a318f379c62682bbd96a99ab885a0751ae5aa216650c1a7cbb1d9cc，未作事后修改。
- read_kernel.sh：第一行 source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh；仅对 /root/repos/linux 执行 git show/git grep，固定 revision=df2908090cda；支持编号行范围和 --grep64。
- codex_new.json：26 项，字段 k/loc/verdict/why；每条理由两三句。
- notes.md：第 6 条的完整并发路径、构造与架构位定义、功能影响局限，以及其他条目的排除依据；第 26 条列明 vm_normal_page/vm_normal_folio 调用者检查范围。
- validation.json：正式输入与 JSON 的哈希、26 项交付格式与位置核对结果，未开展的验证为 null。

检查方法与命令：Windows 端使用 PowerShell 显式 UTF-8 读取；WSL 调用通过本轮 .sh 文件，不直接拼接运行内核操作。使用 git grep 搜索全部相关调用者，再以 git show 核对上游 present 分流、锁、返回旧值语义、构造方式及架构 Kconfig/头文件；重点追查 apply_to_page_range/apply_to_existing_page_range、设备迁移、vm_normal_page/vm_normal_folio 及其辅助函数。复核命令示例（已运行）：

```text
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/encrank_20261115/codex_blind/read_kernel.sh mm/migrate_device.c:976-1110 lib/test_hmm.c:1600-1660 mm/pgtable-generic.c:277-316
```

统计与结论：可能 1 条（k=6，mm/migrate_device.c:1023），不可能 25 条，说不清 0 条。第 6 条：test_hmm 对同一匿名 PMD 范围的并发设备迁移，可以使先收集单页空洞的线程后来读到另一线程安装的 device-private PMD；loongarch/powerpc 上 pmd_leaf=1 而 present=0、trans_huge=0，按题设“标志接口对非 present 返回 1”的编码表口径记为可能。直接后果是 goto abort 并清除 MIGRATE_PFN_MIGRATE；但此时地址已被占据，拒绝覆盖是合理的，未证明额外迁移损失、权限错误或数据损坏，不能把这 1 条折算为确认功能缺陷。其余条目按具体调用链中的 present 分流、内核映射构造、架构可达性、旧值返回语义等排除，详见 JSON/notes。

交付验证：严格 UTF-8 解码与 JSON 解析通过；26 个编号唯一且为 1～26，26/26 loc 与 review_new.txt 标题一致，26/26 字段正确、verdict 有效、why 为两三句；判据哈希不变。首次检索中未编码正则的 | 被 WSL 参数转义误作管道，出现 command not found；改为 --grep64 并重跑相关检索。首次 PowerShell 计数验证把 ConvertFrom-Json 返回的整个数组包成一项，误报 count mismatch；改为直接赋值后 26/26 通过。两者是命令问题，未据此改变判据或结论。

未做与未验证：构建 0，配置 0，内核启动 0，联网/安装 0，其他模型调用 0；逐架构构建验证=null，动态复现=null，功能影响验证=null，与第一标注人的一致性=null，最终功能缺陷确认数=null。不 commit/push/切分支，不修改内核源码，不结束进程，不对外报告。

正式结果 SHA256：61d7b7296de9f59c1e09cabbfb2f986daad95a4fb272be85e6b186d331870edc。
notes.md SHA256：dcfe850f158582589f3d6567deb83709124e2a0d938f7264c0188efb668395d8。
validation.json SHA256：4455f62a41ed8777204c2e3c0f37a30487c7e686f6c06b5a71e95d0a5562bb60。
输入四文件哈希保存在 validation.json。

停止点与下一步：26 条独立盲判及交付检查已完成，无待运行任务；由后续独立裁定环节合并标注。本次不读取另一份判断。若需复查第 6 条，先运行上述只读命令，并参照 notes.md 的 lib/test_hmm.c:1291-1349、mm/migrate_device.c:45-70/798-891、相关架构头文件路径；尚不能从本轮静态证据给出动态复现数字。

## 2026-11-16 Codex：restblind 27 条报告的第二标注人盲判

- 任务：独立判断当前提交 df2908090cda 上 27 处“没查 present 就用受限接口”的报告。本次按用户明确的白名单读取，未读其他标注人的结果、裁决、往轮判断/README、confirmed_bugs、交接文档和进度日志；也未读取本工作日志旧内容。
- 判据：experiments/case_taxonomy/restblind_20261116/criteria.md 第二节。开始判定前计算 SHA256 为 70283cc1d907c0e5981911de5a0ddd61ff039cb0a6d6f1ee3ee09e80609eed6c，完成时重新计算未变；未改判据。
- 写入文件：experiments/case_taxonomy/restblind_20261116/codex_blind/codex.json（27 项结果）和同目录 notes.md（关键调用链、软件标记覆盖、执行边界）；本条日志为用户明确要求的追加。未更新本次禁止读取的交接文档或进度日志。
- 源码命令：通过 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/restblind_20261116/codex_blind/read_source.sh show <文件> <起:止...>，以及同脚本 grep64 <UTF8正则的Base64> [路径...]，只读 git show/git grep 的 df2908090cda。已逐条追查 mprotect、rmap/page_vma_mapped、NUMA/RWP fault、GUP、huge PMD 拆分/插入/回收、DAX 与驱动调用者；全源码检索四个 userfaultfd helper，补查 uprobes/folio_walk_start 的 present 守卫。
- 结果：可能 0，不可能 27，说不清 0。各条排除依据已写入 JSON，另外区分了 Linux present 与硬件 Present 位、清除前返回的旧项与页表新值、PTE 软件标记与普通 THP PMD。第 9 条可先提取非 present 的错误 PFN，但其结果随后被 present 检查丢弃，无后续影响。
- 结构校验：PowerShell ConvertFrom-Json -InputObject 解析成功；27 项编号完整、顺序正确，k/loc 与 review.txt 的 27 条头逐项匹配，每项四个规定字段齐全，why 非空，verdict 合法；判据散列复核通过。
- 命令问题：一次 PowerShell/WSL 正则管道引号错误，改用现有 grep64 后成功重跑；一次 JSON 数组经管道被包成单元素数组而导致校验计数错误，改成直接 ConvertFrom-Json -InputObject 后全部通过。均为自己的命令错误，没有据错误输出作判断，无实质性实验失败。
- 未验证：未构建、未启动内核、未做动态验证；未与第一标注人比对，一致率和 Cohen kappa 为 null。其他模型调用 0，构建 0，新确认缺陷 0，本次判为“可能”的新疑点 0；Codex 独立标注 1 次。
- 停点：本次 27 项盲判已完成。下一步由汇总人将 codex_blind/codex.json 与其独立完成的另一份判定做一致率计算和分歧裁决；本次不读取或生成裁决文件。
- codex.json SHA256：4acbf680b562ef36a4ede11dc0a086c7c55a59832d90a1a43ba295a8bc5c5251

## 2026-11-16 15:16（Codex，xvdom 第二标注人独立盲判）

- 任务：独立复核 xvdom_20261116/review.txt 的 30 条页表接口定义域报告；按本次用户特例，不读取交接文档、进度日志、旧工作日志、第一标注结果、裁决文件、其他轮次判断或 confirmed_bugs.md。
- 读取范围：本轮 review.txt、criteria.md、criteria_amendment1.md、table2.md、codex_blind/ 和固定提交 df2908090cda 的内核源码。源码只读，没有构建、运行内核、联网、安装软件或调用其他模型。
- 新增文件：experiments/case_taxonomy/xvdom_20261116/codex_blind/codex.json（30 项，逐条中文两句理由）；同目录 notes.md（调用链、宏覆盖、软件 marker 与副本比较分析、四份输入 SHA256、未决点）。本文件仅追加这一记录；未修改其他实验材料和判据。
- 结果数字：可能 0，不可能 29，说不清 1（k=28，include/linux/pgtable.h:1034）。动态触发次数、具体触发架构、实际触发 PFN 和运行时错误后果均未取得，为 null；没有宣称确认缺陷。
- 核查方法/命令：使用 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/xvdom_20261116/codex_blind/read_source.sh show <内核文件> <行段> 与 grep64 <UTF8正则的Base64> [源码路径...]，核对架构 __HAVE_ARCH_*、PVMW 两种模式、softleaf 种类判断、PTL 复核、mremap 批量长度、vmwgfx/TTM 的 VM_SPECIAL 约束、DAX 既有项插入路径。
- 关键依据：第 1/2/8 条的错误架构均覆盖所报默认实现；第 6 条剩余 arm 用户入口限定 present。第 4/5/13/14 条的无守卫入口仅清理临时副本比较真实 swap，保留 present 判别且不回写。第 7/9 条的实际用户为 vmwgfx，TTM 特殊 VMA 排除 guard/uffd 注册，空项不能通过局部 write/dirty 条件。迁移和设备项路径依靠调用者与遍历器种类保证；第 29 条 mremap 的非 present 输入固定 nr=1，不执行所报循环体。
- 未决 k=28：DAX → vmf_insert_page_mkwrite → insert_page_into_pte_locked 的非空分支只检查 pte_pfn 相等，没有显式 present 检查。未证明实际 DAX 页能与软件 marker 的解码 PFN 相等并产生错误后果，也未完整排除此路径，因此判说不清。
- 交付检查：PowerShell ConvertFrom-Json 成功解析 30 项；编号严格为 1～30；loc 与 review.txt 的 30 个标题逐项相同；四字段、三种合法 verdict、非空且两至三句的理由均通过；四份输入 SHA256 未变。codex.json SHA256=8FCBE88C640F7AF87F0EE3C5807BA13651D8544CA77FFAD7FF700FD16EA26DAA。
- 命令问题及纠正：初次 PowerShell 文本读取未指定 UTF8 的显示问题已用 UTF8 重读；正则经 WSL 引号传递的问题改用已有 grep64 重查；首次 JSON 检查因 PowerShell 管道数组封装把数组计为一项，改为 ConvertFrom-Json -InputObject 后重跑，全部 PASS。没有把这些命令问题当作实质实验失败。
- 停止点：本次 30 条盲判及说明文件完成，未与其他标注人结果比较。若后续继续第 28 条静态核查，可先运行：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/xvdom_20261116/codex_blind/read_source.sh show mm/memory.c 2482:2519 2999:3017；再对照实际 DAX 配置的可用 PFN、架构 pte_pfn/swap 编码和 marker 安装时序，补齐 notes.md 列出的三个条件。此次没有动态验证。

## 2026-11-16：xvlift 23 条报告第二标注人盲判完成

- 本次按用户指定的盲判范围，只读取 xvlift_20261116 的 review.txt、criteria.md、criteria_amendment1.md、codex_blind/，xvdom_20261116/table2.md，以及固定提交 df2908090cda 的内核源码。未读取其他标注人的结论、轮次 README、交接文档、进度日志或 confirmed_bugs.md；本日志仅追加，未读取旧内容。
- 新建 experiments/case_taxonomy/xvlift_20261116/codex_blind/codex.json 和 notes.md。codex.json 共 23 项：可能 3 条（4、5、15），不可能 20 条，说不清 0 条；每项包含 k、loc、verdict、why，位置和顺序与 review.txt 对应。
- 4、5 的闭合路径：Nouveau make_device_exclusive 在普通匿名 folio 的 PTE 中留下 device-exclusive 项，rmap 遍历仍能找到它；arm64 实际 test/clear young 实现没有 present 守卫，清 PTE_AF 会把交换类型 30 改为 14，后续可能按普通交换项处理。分别核对了架构覆盖、批量包装以及 CONFIG_ARM64_CONTPTE 的实现差异。
- 15 的正式依据明确限于 CONFIG_DEBUG_VM=y、CONFIG_SPARSEMEM_VMEMMAP=y 且错误解码 PFN 落入未映射物理洞的 x86_64 路径：大 folio 的 device-exclusive 项进入 folio_pte_batch，首个 WARN 不返回，后续调试表达式对按 present 格式错误解码的 PFN 调用 page_folio，从而可能非法访问。没有声称非调试配置必然产生相同后果，也未测量当前机器的物理洞或动态复现。备注中的位运算推演仅为辅助分析，不作为已复现结果。
- 不可能项逐条核查了调用者的锁内项类型守卫、参数常量导致的不可达分支、按值副本的比较结果是否受影响，以及 PMD/PTE 层级和特殊映射的调用约定。完整定位与必要的配置条件保存在 notes.md。
- 源码检查命令使用用户提供的 read_source.sh：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/xvlift_20261116/codex_blind/read_source.sh show <文件> [起:止 ...]；跨符号检索使用同一脚本的 grep64 <base64 正则> [路径 ...]。核对范围包括 mm/rmap.c、mm/vmscan.c、mm/util.c、mm/internal.h、mm/page_vma_mapped.c、mm/memory.c、mm/mprotect.c、mm/huge_memory.c、mm/mremap.c、mm/swapfile.c、mm/gup.c、mm/madvise.c，以及相关通用和 arm64/x86/RISC-V/s390 架构页表实现。
- 判据未修改。criteria.md SHA256：504e6708e96ae5c0f8bdb8d803c2770c745a816639966ba4e059d6f97f2fa066；criteria_amendment1.md SHA256：d6574f7f5fe172a38d0dbe5dc2d084e2ba40dfd1be71ffb774ea09550e3d72bf。
- 已验证 JSON 可解析、23 个编号唯一、字段集合正确、判断值合法、理由非空，并逐一匹配 review.txt 的编号和位置。首次 PowerShell 校验把反序列化数组额外包装导致计数错误，修正校验命令后全部通过，输出数据未因此修改。codex.json SHA256：E36B89486B0952E7C267E8A643C7B29067CBE0AC2CC5A78C333BACD6276D30D1。
- 未修改内核源码，未构建、未联网、未安装软件、未调用其他模型，未运行动态验证；运行验证所得数字为 null。本次盲判和输出已完成，停在交付第二标注结果处。下一步由后续裁定环节使用 codex.json 和 notes.md 对照第一标注结果；本轮不读取其结论，也不启动实验。

## 2026-11-16 20:02:10 +08:00 Codex：orddom_20261116 第二标注人盲判（30 条）

- 任务范围：独立审查固定源码 df2908090cda 上的 30 条“大阶数用于页缓存却没和上限比较”报告。仅读取本轮允许的 review.txt、criteria.md、samples.md、consts.md、codex_blind/read_source.sh 及内核源码；没有读取其他标注结果、裁定、README、交接文档、进度日志、confirmed_bugs 或本日志既有内容。
- 新增文件：experiments/case_taxonomy/orddom_20261116/codex_blind/codex.json（30 项，字段 k/loc/verdict/why，每项 2—3 句）；同目录 notes.md（关键调用链、反例条件、排除依据及未验证事项）。按本次用户要求在本日志末尾追加记录，没有修改内核或其他项目文件。
- 判据沿用原文件，未修改；criteria.md SHA256：643ab513236c81cd51dd66aa6ff1668544019fe381aab8f4d42194c7b9612378。
- 结论数字：可能 3 条（20、23、24），不可能 27 条，说不清 0 条。三个“可能”分别是 force 策略入口、分配消费点、默认继承掩码来源，均属于同一条 shmem 路径，不是三个独立缺陷。
- 关键路径：arm64-64k，HPAGE_PMD_ORDER=13 > MAX_PAGECACHE_ORDER=11，shmem_init 默认 inherit=BIT(13)。合法的 shmem_enabled=force 可使匿名共享 VMA 经 shmem_allowable_huge_orders():1865-1866 直接返回继承掩码，绕过 1877 行过滤；shmem_fault → shmem_get_folio_gfp → shmem_alloc_and_add_folio → shmem_add_to_page_cache 可在满足对齐、空区间、内存与记账等条件时插入阶数 13 项。
- 后果依据：该组合只在 ARM64_4K_PAGES 时选择 ARCH_WANTS_THP_SWAP，因此 64K 页时 THP_SWAP=n。启用 swap 后回收上述脏页，pageout → shmem_writeout → split_folio_to_list → 均匀拆到阶数 0 → xas_split_alloc，满足 xa_shift(0)+2*XA_CHUNK_SHIFT(6)<=13，lib/xarray.c:1051 WARN，随后设置 -ENOMEM 并拆分失败。均为静态推导；实际运行复现次数、实测 WARN 次数均为 null。
- 主要排除依据：DAX 明确不适用普通页缓存拆分上限；khugepaged 和 MADV_COLLAPSE 的两个入口都有 THP_ORDERS_ALL_FILE_DEFAULT 过滤；匿名页、页表及反向映射计数不创建同阶数页缓存项；当前 swap cache 是每簇平面数组，按槽保存条目并检查 SWAPFILE_CLUSTER 边界。
- 命令：所有源码查询均用提供的 read_source.sh show/grep64，只读固定版本。复查重点可运行：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/orddom_20261116/codex_blind/read_source.sh show mm/shmem.c 627:703 1818:2041 2509:2528 5376:5419 5457:5479；以及同一脚本 show lib/xarray.c 1032:1075。更多具体范围在 notes.md。
- 文件校验：PowerShell ConvertFrom-Json 成功；30 个编号连续且唯一；loc 逐条匹配 review.txt；四个字段和三值枚举有效；每条 why 为 2—3 句。最终检查结果 PASS。codex.json SHA256：6716ab285a8e42876acb0cb00e8712cda557ec0904cbc530c724c1187579c297；notes.md SHA256：aea6d0f3707efde5c70190365ac1d5af203bfad881f2d34aa30e9d645d6e350d。
- 自身命令错误已纠正：最初 JS 环境没有 btoa，改为本地 Base64 编码后重跑；最初 PowerShell 校验把 ConvertFrom-Json 数组额外包在 @() 内导致统计成 1，移除外层包装后确认两个文件均为 30 项并完成全部检查。这两项均未造成研究步骤的实质性失败。
- 停止位置：30 项盲判与证据说明完成。后续裁定可先逐行核对 notes.md 中 force 分支是否绕过 global_orders=0，重点区分匿名共享 VMA、普通匿名 VMA、普通 tmpfs 及强制合并入口。本轮没有运行内核、设置 sysfs、构建、联网、安装、调用其他模型、提交或推送；未重测常量和历史样本，也没有声称动态复现或数据结构损坏。


## 2026-11-17 00:28:37 +08:00 Codex：widthtrunc_20261116 第二标注人盲判（完成）

- 任务与边界：独立判断 review.txt 中 30 条“32 位架构上的位宽截断”报告。只读取用户允许的 review.txt、criteria.md、samples.md、widths.md、codex_blind/ 与必要的内核源码；未读取 claude.json、adjudication.json、README.md、review.json、head.json、旧轮次判断、confirmed_bugs、交接文档或进度日志。本文件按用户明确要求仅追加，未读取已有内容；本次不更新交接文档和进度日志。
- 新增文件：experiments/case_taxonomy/widthtrunc_20261116/codex_blind/codex.json（30 项 k/loc/verdict/why）；同目录 notes.md（源码证据、值域推导、可达性限制和验证记录）。未修改已有判据、报告、内核源码或其他实验文件。
- 判据 SHA256：5E7CB578DE5330E60A8A9FA770472143485EA8B9A2A7A807D26959BAED1F10FD；完成时复核未变。
- 源码固定版本：df2908090cda，沿用已有 codex_blind/read_source.sh 内的版本。所有源码读取均使用 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc_20261116/codex_blind/read_source.sh show <文件> [起:止 ...] 或 grep64 <UTF-8 正则的 base64> [路径...]。
- 代表性命令：上述 show mm/Kconfig 500:550 1210:1255；show include/linux/pagemap.h 1583:1607；show fs/ext4/inode.c 2690:3025；show fs/f2fs/file.c 2990:3225；show fs/nilfs2/recovery.c 1:58 330:391 500:520；show fs/nilfs2/page.c 506:625。还读取各有关 Kconfig、Makefile、类型定义及调用处，证据位置见 notes.md。未构建、运行内核、联网、安装软件或调用其他模型。
- 逐条结果：可能 7 条（1、18、19、20、21、29、30）；不可能 22 条；说不清 1 条（28）。该统计是报告条目数，未去重，也不等于动态确认的缺陷数。
- 关键排除：hugetlb 多处表达式用于页内偏移或对齐；MEMORY_HOTPLUG 依赖 64BIT，使 powerpc 热插拔与 FUSE DAX 的相关路径不在 32 位上编译，memory-failure 该辅助函数的设备内存调用路径也不可达；ext2 的 dir_pages() 先转 unsigned long 再右移，n<npages 使第 292 行的 n 左移不会溢出；GFS2 配额 ID 与 88 字节记录把该文件块号限制到 2^31 以下。
- 整数推导复核：5 GiB 在 32 位页号左移后成为 1 GiB；4 KiB 块的 1048576 个块左移后成为 0；配额文件最大记录末端 755914244096 字节（704 GiB）、最大逻辑块号 1476395007；4 KiB 页下 ext2 该循环内 n 最大 1048574；simple_getattr 首个溢出条件为 2199023255552 字节（2 TiB）实际驻留缓存。
- 文件验证：PowerShell ConvertFrom-Json 解析通过；恰好 30 项，编号 1～30 唯一，全部 loc 与 review.txt 对应，字段集合和判定值符合要求，每条 why 为两至三句。第一次检查命令因 Windows PowerShell 管道外层 @() 将 JSON 数组包成一项而误报条数；已改为 ConvertFrom-Json -InputObject 接收原文后重跑并全部通过，判定数据未因此改动。
- codex.json SHA256：6483598F8924C5B439B899CADE74B57D869A128AF288672BC0D627FFF11C6C45。
- notes.md SHA256：06C1F9F020125A118EE89C9D72488DCD0DF8329CFF2E60F9A318A3293B0DB803。
- 未验证：运行时复现结果为 null。第 29 条需要至少 4 GiB 连续延迟分配缓存及相应 HIGHMEM/脏页配置；第 28 条需要至少 2 TiB 驻留缓存，但尚未证实可承载该缓存和元数据的合法 32 位配置，也未证明所有 32 位配置都排除该容量，故保留“说不清”。F2FS 条目只确认预写回区间错误，未声称已证实最终文件内容损坏。
- 停止点与下一步：本次盲判输出完成，可交给用户进行双人裁定；本轮不读取其他标注文件。若继续调查第 28 条，应先在相同源码版本中核对 32 位大页/扩展物理地址配置、低端内存与页缓存元数据的容量上界，不能仅用大稀疏文件逻辑大小证明触发。

## 2026-11-17 — Codex：widthtrunc2 第二标注人独立盲判

- 本轮按用户的专门盲判要求执行，不读取外层交接文档、进度日志或其他标注/裁定；原 codex_worklog 内容也未读取，仅按本次明确要求在末尾追加本条。
- 依据：widthtrunc2_20261117/review.txt 的 30 项、criteria.md、widthtrunc_20261116/samples.md 与 widths.md；内核源码通过 codex_blind/read_source.sh 读取固定版本 df2908090cda。判据写入判断前取得的 SHA256 为 96ed2fef5b620aa3955b8c27833c778f69bf9e0fc0bfee5cd254e065ea96e4d9，结束时复核未变。
- 新增文件：experiments/case_taxonomy/widthtrunc2_20261117/codex_blind/codex.json（30 项，k/loc/verdict/why）；同目录 notes.md（源码证据、配置依赖、条件和未验证项）。未修改内核源码、旧轮次或其他研究文件。
- 命令：前台运行 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc2_20261117/codex_blind/read_source.sh show <源码文件> <起:止>，以及该脚本的 grep64 <正则base64> <内核路径>。重点核查 NTFS CLST 的类型/Kconfig，交换项掩码，BPF arena 创建门槛，uprobe 推测与回退路径，ARC HIGHMEM/PAE40 与 FDT 范围处理，ARM crashkernel/ABI/DMA/缓存颜色，以及 LoongArch32/EFI/计时/hugetlb 和 MIPS compat 的构建条件。
- 结果：可能 12 项（1、5、6、8、10、11、13、14、19、20、21、24）；不可能 15 项；说不清 3 项（25、26、27，LA32 的实际 EFI 高地址描述可达性未确认）。19～21 明确标注为旧 time32 ABI 范围限制，不作为新内部计算回归宣传；11 明确要求同一 inode 的高、低对应偏移同时有探针；13～14 明确限定 HIGHMEM=y、PAE40=n 且 DT 保留高地址块的配置。
- 校验：PowerShell ConvertFrom-Json 验证 30 项连续且唯一编号、所有 loc 与 review.txt 完全对应、字段集合、三种合法 verdict、非空且每项两三句理由；复核 criteria SHA256，全部通过。首轮校验命令因 Windows PowerShell 外层 @() 包裹 JSON 根数组而误报计数，修正直接赋值后重跑通过；这是命令问题，未改判据或判断以适应结果。最后全树检查频率赋值点发现 SMBIOS 来源，补查 CPUCFG 初始化后修正第 28 条的值域理由，判定未改变，最终完整校验再次通过。
- 停止点：盲判文件交付完成，等待主流程统一裁定；未读取或生成 adjudication。可直接复查命令：Get-Content -LiteralPath 'experiments/case_taxonomy/widthtrunc2_20261117/codex_blind/codex.json' -Encoding UTF8 -Raw | ConvertFrom-Json。
- 未验证：不构建、不运行候选代码、不制作触发镜像；未联网、下载、安装、调用其他模型、commit/push/切分支。真实触发与运行结果数字为 null；25～27 的实际 LA32/EFI 可达性证据仍缺失。

## 2026-11-17 09:40（Asia/Shanghai）Codex：widthtrunc3 第二标注人独立盲判完成

- 任务：独立判断打乱顺序的 40 条 32 位位宽截断报告。严格按本次用户的阅读白名单执行，未读取其他标注结果、历史判断、criteria.md、交接文档、进度日志或 confirmed_bugs.md；本日志只追加，未读取旧内容。本次按用户特例写 experiments/codex_worklog.md，不更新外层交接/进度文件。
- 输入：experiments/case_taxonomy/widthtrunc3_20261117/review.txt、widthtrunc_20261116/samples.md、widthtrunc_20261116/widths.md、本轮 codex_blind/read_source.sh 和内核源码。review.txt SHA256=A27F9399C3C40CAE771E9F82DD63413763D017B9536FD768401BB84B6734F029；其余输入哈希见 notes.md。没有为盲判读取或修改已有判据。
- 新增文件：experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/codex.json（40 项，每项 k、loc、verdict、why）；同目录 notes.md（主要证据、触发边界、输入哈希和验证说明）。除此之外仅追加本日志。未修改内核、分析器或其他实验文件，未构建、联网、安装软件、调用其他模型、commit/push 或操作其他进程。
- 源码命令：始终运行 wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/read_source.sh show <文件> <起:止> 或 grep64 <base64正则> <源码路径>。现有脚本固定读取 df2908090cda；没有改查 HEAD。检查了报告涉及的文件、编号分配/磁盘格式、I/O 长度入口、XArray/MRU 缓存接口及相关架构 Kconfig/Makefile。
- 结果：可能 6 条（k=12、14、16、17、20、22），不可能 34 条，说不清 0 条；40 条均为 A 形态。“可能”的主要依据为 Btrfs XArray 并发预留别名、约 136 年单调秒数回绕、XFS filestream MRU 的编号别名两处、SMB 大交换文件块数窄化、ext4 WRITE_ZEROES 向 ssize_t 传入 2 GiB 字节长度。k=14 的覆盖年限是源码明确接受的设计边界，k=16/17 只确认关联/局部性问题，均在说明中标明，未宣称动态复现或数据损坏。
- 重要复核：k=22 不能直接套用单个 unwritten extent 的长度上限。ES 已写映射可跨 extent 合并，32 位 ssize_t 接收 2147483648 后变为 -2147483648，EXT4_MAX_BLOCKS 在 4 KiB 块、offset=0 时得到 0xFFF80000，存在越出已清零区间进行转换的静态路径。k=12 的 xa_release 只清 XA_ZERO_ENTRY，不会删除普通 inode 指针；判“可能”基于相差 2^32 的编号共享预留槽及失败释放窗口，细节见 notes.md。
- 校验命令与结果：使用 PowerShell Get-Content -Encoding UTF8、ConvertFrom-Json、正则读取 review.txt 头部，以及逐项字段/句数断言；最终 PASS：40 项、k 唯一覆盖 1..40、40 个 loc 全匹配、字段恰为 k/loc/verdict/why、结论合法、每条 why 两至三句，notes.md 计数一致。首次校验在 Windows PowerShell 管道外额外包数组导致条目数检查失败，修正命令后重跑通过；这属于校验命令错误，没有据此改变判断。
- 输出 SHA256：codex.json=6DA76D217B11310447FA704D771AFBDC73E045E2AE96ACFC546FE4121194E410；notes.md=F7EA44A094906AD0096181D920E1EC19413CBCA941E231A46CBDFBB123594F88。
- 停止位置：本次 40 条盲判及格式核对已完成，未启动与其他标注人的比较。未验证：所有触发均未做内核构建或运行复现，动态复现数量为 null，特别是 k=12 并发时序、k=14 极长运行年限、k=20 大容量交换文件和 k=22 WRITE_ZEROES 路径均只有静态证据。
- 下一步如需只读复核，可直接执行：
  - wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/read_source.sh show fs/ext4/extents.c 4598:4709 5132:5196
  - wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/read_source.sh show fs/btrfs/inode.c 4021:4048 6666:6688 6877:6889

## 2026-11-17｜Codex｜60 个留出修复提交第二标注人盲判

独立阅读本轮判据、60 个修复提交的完整补丁，并按需核对修复时内核源码，完成第二标注人的盲判及输出完整性校验。

输出：`experiments/case_taxonomy/heldout_commit_20261117/codex_blind/codex_label.json`（60 项判断）、`notes.md`（难判说明）；完整补丁、源码节选和校验记录也保存在同一 `codex_blind/` 目录。


## 2026-11-17 19:26:55 +08:00 Codex：23 条 TLB / 缓存钩子候选独立盲判

任务：作为第二标注人，独立盲判 review.txt 的 23 条 TLB / 缓存钩子候选。

读取边界：按本次用户指令，只读 review.txt、codex_blind/ 和固定提交 df2908090cda 的内核源码；没有读取本轮其他文件、既有判断、旧轮次 README、confirmed_bugs.md、交接文档或进度日志。本条按用户明确要求追加到 experiments/codex_worklog.md，未读取该日志旧内容。

新增文件：
- experiments/case_taxonomy/tlbhook_20261117/codex_blind/codex.json
- experiments/case_taxonomy/tlbhook_20261117/codex_blind/notes.md
另仅追加本工作日志，没有改动内核源码或其他实验文件。

运行与核对：
- 使用用户提供的 wsl -u root -- bash .../codex_blind/read_source.sh show <文件> <起:止...> 和 grep64 <base64正则> <路径...> 读取源码；脚本以 git show / git grep 固定在 df2908090cda。
- 核对了 RISC-V/ Xtensa 用户缺页及 TLB 实现，BPF arena 安装回调及包装刷新，直接映射恢复实现和配置限制，highmem 槽位复用及架构钩子，HugeTLB vmemmap 批量刷新，KASAN 初始化/动态影子/内存热插拔，percpu 和 vmalloc 的外层及 lazy 刷新。关键文件行号和可复查命令保存在 notes.md。
- Get-FileHash -Algorithm SHA256 review.txt：28f1c27ac8dd52880783741a4a934d9553f193808d1249286d1e68af6717d447。
- PowerShell ConvertFrom-Json 校验：23 项，编号严格 1 至 23；每项字段恰为 k/verdict/why，枚举合法，依据各为两三句。首次校验脚本因额外 @() 造成顶层数组嵌套而误报数量，改正脚本后通过，判断文件未因该误报改动。
- codex.json SHA256：41da11f390a6accdb8a0b281eda7293bfe5648b430a038d0fc71f3baad4855bf。
- notes.md SHA256：7c612ae427edec596969bc53fdd13dcb726ff94147f08648bc75afce5dac63d0。

结果：
- 可能：1 项，编号 14。RV64 + KASAN_VMALLOC 时，flush_cache_vmap 接收到影子地址，但 RISC-V 钩子的 vmalloc/module/vmemmap 范围过滤不覆盖 KASAN 影子；非 VM_ALLOC 的 get_vm_area 在普通映射刷新前就会 unpoison 影子。若 CPU 新映射位已经清零且存在旧无效翻译，影子内核缺页可能无法经 sfence.vma 重试并 Oops。此为源码推理，未复现。
- 说不清：1 项，编号 13。启动期有架构收尾刷新，设备 memremap 运行时路径也有 arch_add_memory 全局刷新；memmap-on-memory online 的零影子安装后，尚未闭合其首次实际访问与有效刷新的先后关系。
- 不可能：21 项，编号 1 至 12、15 至 23。主要依据为假性缺页可自愈、实际有 SMP 刷新、误把块设备 flush 当成 TLB 维护、回调外层刷新、架构配置限制及有意的延迟刷新。

停点：23 项独立标注及格式校验已完成，未开展与第一标注人的比对或裁决。

后续若继续静态复查，优先核对编号 13 的运行时路径，可运行：
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show drivers/base/memory.c 233:283
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show mm/memory_hotplug.c 1086:1135
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show mm/kasan/init.c 480:496

未验证：实际硬件或模拟器上的无效项缓存行为、编号 14 的动态复现、编号 13 的完整运行时访问时序；动态实验数与复现次数为 null。全程未构建、未联网、未安装软件、未调用其他模型、未 commit/push/切分支。


## 2026-11-17：TLB / 缓存钩子第二标注人盲判
按本次任务特例，仅读取 review.txt、codex_blind/read_source.sh 及其指定提交 df2908090cda 的内核源码；未读取交接文档、进度日志、其他轮次或第一标注人的判据与结果。通过 read_source.sh show/grep64 核查 KSM replace_page、KASAN 影子页安装、per-CPU 虚拟区域分配、RISC-V cacheflush/pgtable/kasan 布局、初始化与异常处理路径。
输出 experiments/case_taxonomy/tlbhook2_20261117/codex_blind/codex.json：候选 1 不可能（注释命中且实际排除 PMD 大页），候选 2 可能（影子地址未设置延迟刷新标志，per-CPU 路径可能先访问影子）；JSON 解析验证通过，共 2 项。仅静态判断，未构建、未运行复现，动态结果为 null；未联网、未调用其他模型、未修改内核。盲判已完成，后续由任务发起方对照两位标注结果。

## 2026-11-18 Codex：调用上下文 21 条候选第二标注人盲判

- 按本次用户指令限定读取范围，仅读取 ctxeff_20261118/review.txt、codex_blind/read_source.sh，以及该脚本通过 git show/grep 读取的 df2908090cda 内核源码；未读取第一标注人结果、其他轮次、交接文档或进度日志。本条仅追加，不读取既有工作日志。
- 新建 experiments/case_taxonomy/ctxeff_20261118/codex_blind/codex.json（21 项，逐项两三句理由）和 notes.md（范围及限制）。判断为可能 3 项：4、12、13；不可能 18 项；说不清 0 项。
- 命令：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/ctxeff_20261118/codex_blind/read_source.sh show <文件> <范围>，以及 grep64 <正则Base64> <源码路径>。核对了页分配、futex、ptrace、AIO、SWIOTLB、休眠、KGDB、大页恢复及 arm64/riscv/sh/arc 架构条件分支和 Kconfig。
- 关键依据：解锁后调用不能继承关中断；arm64 DEBUG_PAGEALLOC/KFENCE 拆分早退；零 PTE 不触发指令缓存刷新；SH 无 HIGHMEM；SH SMP KGDB 禁用通用缓存刷新；休眠失败清理时仅剩单个在线 CPU。可能项目为 SHX3 SMP AIO 同步刷新，以及 ARC/RISC-V SMP KGDB 普通 IPI 等待。
- 验证：PowerShell ConvertFrom-Json 成功，确认 21 项编号连续、判断枚举有效且理由非空；未构建、未运行复现、未联网、未调用其他模型。未展开的其他示例调用点未穷举，特别是第 2 项只排除所给连续页分配链，不宣称钩子的所有其他调用安全。
- 工具问题：首次读取中文编码异常后改 UTF-8；搜索参数生成的 btoa 不可用后改用 PowerShell Base64，均已更正重跑。
- 停止位置：盲判结果已写完；下一步由用户解除盲判后再进行双人结果比对，本轮不读取或比对其他标注。按本次明确要求追加此日志，未修改交接文档和进度日志。
## 2026-11-19 weakov2 历史修复提交盲判（Codex，第二标注人）

- 按本次任务定义，逐个阅读 `experiments/case_taxonomy/weakov2_20261118/packets/001.md` 至 `008.md`，判断修复前的架构覆盖实现是否遗漏公共调用方依赖的通用效果，并由此次修复补齐或报告失败。
- 共标注 8 个样本：yes 1 个（001），no 7 个（002～008），unsure 0 个。每项写明通用效果及一两句判定理由。
- 结果写入 `experiments/case_taxonomy/weakov2_20261118/codex_labels.json`。已解析 JSON，检查编号与 packets 完整且唯一对应、字段及标签合法、effect/reason 非空，全部通过。
- 首次校验脚本用 @() 包裹 ConvertFrom-Json，在本机 PowerShell 中把整个 JSON 数组作为一个元素，错误地报告样本数量不符；已修正校验脚本并重跑通过，未改动标注内容。
- 判定依据为 packets 材料；未读取本轮分析器结果文件及另一位标注人的标签，未运行 weakov2.py，未查询完整 git 提交、未联网、未运行内核实验。未计算双人一致率或分析器召回率。
- 仅新建 codex_labels.json 并追加本记录；依本次明确要求，不修改 packets、外层交接文档、外层进度日志或其他文件。

### 2026-11-19 Codex：110个内核修复提交第二标注人盲判

独立阅读分析集44个、封存集66个修复提交的完整补丁，并按需只读同版本内核源码，完成中文标签；核对两份JSON的结构、全部编号与12位提交号，覆盖数分别为44和66。输出位于 `experiments/case_taxonomy/heldout2_20261119/codex_blind/codex_label_analysis.json`、`codex_label_sealed.json`；同目录 `notes.md` 记录判据SHA256及分析集疑难判断，`validation.json` 保存校验结果。


## 2026-11-19 Codex：线性映射接口历史提交分类盲判（第二标注人）

- 按用户给定定义，逐份阅读 experiments/case_taxonomy/linmap_20261119/packets/001.txt 至 080.txt，完成全部 80 个历史提交的独立分类，逐项填写 n、label、addr 和一两句中文理由。
- 分类数量：yes 25、no 53、unsure 2（027、041）。027 无法确认原有驱动是否确实把 vmalloc/SG 缓冲区送入默认页回调；041 主要修复调试条目泄漏，材料未明确其余待检查地址的非线性来源。新增 vmalloc/kmap 支持、原本已正确分流的重构、改名和格式调整均按本次定义区分。
- 补充材料仅用本地只读 git show：007、027、031、032（地址转换相关上下文）、041、061，以及 031 提交说明所引用的 515ce6061312。未读取 linmap_20261119 下的 claude_labels.json、mined.json、head*、dev* 或 *.log，未运行 linmap.py，未查看或比较分析器结果和另一位标注人的结论。
- 写入文件：D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\linmap_20261119\codex_labels.json；本记录仅追加于 D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\codex_worklog.md。遵循本次用户要求，不修改外层交接文档、进度日志、判据或其他文件。
- 核对：JSON 可解析，内容与独立标注逐项一致；编号为整数且 1～80 各出现一次，标签及地址类别合法，80 项理由齐全。已比对全部 80 个 packet 的 SHA256，材料未改变；工作记录按追加方式写入。未构建或运行内核，未运行仓库测试，也未做标注一致性统计。
- 操作说明：最初读取中文文档时默认解码不正确，已显式按 UTF-8 重读；少数只读 WSL 命令被启动警告影响 PowerShell 返回状态，后续显式传回原生 LASTEXITCODE，确认正常读取。
- 停点：80 项标注全部完成。后续由主标注人或用户进行双人一致性计算和争议裁定；本轮保持盲判，不开展结果比对。

## 2026-11-19 20:46 Codex：capguard 两部分独立标注（第二标注人）

- 本次按用户直接给出的判定口径工作：历史提交只有修复既有的“架构能力缺失仍执行依赖操作／误认静默成功”，并补上相应判断才标 yes。新增功能、自测新增、搬迁重命名、compat ABI 转换、按架构需求补资源或维护操作等不据此标 yes。当前候选同时检查可达性、上游门控、查询／清理语义。
- 写入且仅写入以下三个文件：
  - experiments/case_taxonomy/capguard_20261119/codex_labels.json（新建）
  - experiments/case_taxonomy/capguard_20261119/codex_review.json（新建）
  - experiments/codex_worklog.md（本条追加）
  本次用户明确指定以上输出并禁止修改其他文件，因此没有更新外层进度日志、交接文档，也没有新建 criteria、脚本或内核文件。
- 读取边界的偏差如实说明：开头按通用 AGENTS.md 的启动要求读取了根 AGENTS.md、外层 ../交接文档.md 和 ../进度日志.md 最后 180 行，输出编码异常且被截断；这超出了本次“只看 packets/ 和 review/ 材料”的范围。后续判断以这 117 个 packet、11 个 review 和授权的 Git 源码为依据。没有读取 capguard_20261119 下的 claude_*.json、mined.json、head*、dev*、*.log、adjudication.json，没有运行 capguard.py，没有对照或裁决其他标注人的结果。
- 过程：通过 PowerShell Get-Content -Encoding UTF8 分批查看 packets/001.txt 至 117.txt 和 review/R01.txt 至 R11.txt；材料中若节选未显示判断函数，使用 wsl.exe -u root -- git -C /root/repos/linux show 补查相应提交。没有联网、下载、安装、调用模型接口、构建或运行内核，没有 commit/push/切分支。
- 历史补查：0105b0562a5e:io_uring/wait.c；474fe91f213a:mm/hugetlb_cma.c；c43203154d8a:io_uring/register.c；f2542a3be327:drivers/scsi/scsi_ioctl.c；f05916281fd7:drivers/staging/vc04_services/interface/vchiq_arm/vchiq_dev.c；05289402d717:mm/debug_vm_pgtable.c；4049866f0913:drivers/gpu/drm/i915/selftests/huge_pages.c；02b15e343aee:drivers/mtd/chips/cfi_cmdset_0002.c；另查看 d5aad4c2ca05、348ad1606f4c 的完整补丁，以及 1da177e4c3f4:drivers/mtd/chips/cfi_cmdset_0001.c 中的中断查询。补查主要用于区分准备性抽象和实际修复、补齐 pred 名称。
- 当前源码核对均固定在 df2908090cda，使用 git show <版本>:<路径>：arch/x86/events/core.c；kernel/power/snapshot.c；mm/execmem.c；arch/arm64/mm/pageattr.c；arch/arm64/Kconfig；arch/arm64/kernel/module.c；mm/hugetlb.c；mm/secretmem.c；mm/hugetlb_sysfs.c；mm/Kconfig；arch/Kconfig；include/linux/hugetlb.h；arch/powerpc/mm/hugetlbpage.c；arch/s390/mm/hugetlbpage.c；arch/x86/mm/hugetlbpage.c；mm/hugetlb_cma.c。
- 历史结果：117/117，yes=10、no=107、unsure=0。yes 编号：023、049、072、073、086、098、109、110、112、114。每条均包含 n、label、pred、reason，没有留空 pred。
- 当前结果：11/11，likely=0、unlikely=11、unsure=0。关键依据：
  - R01：x86 perf_callchain_user 内部已有 nmi_uaccess_okay 门控，返回的是实际取得的部分调用链。
  - R02/R03：safe_copy_page 只在 kernel_page_present 为假时临时映射并配对撤销；arm64 的能力缺失并不产生相应的解除映射。
  - R04/R05：代码受 CONFIG_ARCH_HAS_EXECMEM_ROX 保护，当前 arm64 未选择该隐藏配置；R05 还只是错误回滚分支。
  - R06：MDWE 状态查询，不启用保护。
  - R07：hugetlb_parse_params 调用的三类参数处理器已有 hugepages_supported 检查；分配器对零 max_huge_pages 返回。
  - R08/R09：已有大页资源的释放／降级路径，入口和状态由成功初始化建立。
  - R10：size_to_hstate 是元数据查重；参数调用者检查能力和具体大小，架构路径检查大小支持。
  - R11：释放已有 secretmem 私有状态，创建和初始化入口已经门控。
- 文件校验：从落盘 JSON 重新解析，检查连续完整编号（1..117、R01..R11）、允许标签、精确字段集合、非空理由和 pred，128/128 条通过。第一次校验命令对 ConvertFrom-Json 外套 @() 在本机形成嵌套数组，误报 Wrong count；改成直接赋值后重跑通过，输出文件没有因此改判。一次源码切片管道因 Select-Object -First 提前关闭管道返回非零，后改为先完整捕获再筛选，读取成功。
- codex_labels.json SHA256：50df712bb51c5f90706cbd432279cbe9a5e6fd157a07f060788cc3b7d2038769
- codex_review.json SHA256：b53c347529fe41203be8171b4e35ff9a1c47773aa9f62e95ff64eafa0ac83860
- 停点：两份标注完成，等待用户后续比对。下一步可由用户安排与其他标注对照；本轮没有读取其他答案，也没有编译、启动、动态复现或证明这些候选在所有配置下绝对无问题。


- 2026-11-20 完成晚期样本独立盲判与根因归并。逐条记录、根因清单和数字汇总存于 experiments/case_taxonomy/effsupply_20261120/sealed_late/。

## 2026-11-20　E-ZERO 第二审查人盲判

读取本轮判据、两份修订和 packets.md，用 WSL git show、git grep 核对 df2908090cda 的函数及辅助实现，读取 6829e274a623、e89f5b370153 等历史提交说明。已写入 effzero_20261120/review/codex_labels.json 和 codex_notes.md，复读 JSON 得 13 项，确认 0、可能 1、排除 9、证据不足 3。第 1、3、4、5 项未完成端到端可达性及影响验证。未构建、未联网、未读另一审查人的判断或封存集，未计算一致率。

- 2026-11-20 完成晚期回放盲判及汇总校验，输出位于 experiments/case_taxonomy/effreplay_20261120/sealed_replay/ 下的 scorer_replay.json 和 summary.json。

## 2026-11-20｜outparam 第二审查人盲判

依据冻结判据、修订和去来源审查材料，核对 9 个代表调用点。通过 WSL 的 git show 检查 df2908090cda 的调用方、辅助函数与宏，并读取三个 defconfig 的相关配置。结果为排除 9 条，其中调用方不依赖 5 条、合法的实现差异 2 条、性质表示不了 2 条。已写入 outparam_20261120/review/codex_labels.json 和 codex_notes.md，回读 JSON 核对了编号和判定数。未构建、未做动态验证、未比对第一审查人的标签。后续由汇总人按 id 对齐两份判定并计算一致率。

## 2026-11-20　firstbreak_20261121 第二标注人盲判

按本次任务覆盖交接流程。读取 criteria.md、collected.json，以 WSL git show 核对 20 个修复及父树行号，并查 arm64 defconfig 编译数据库的 mmu.c 条目。输出本轮 codex_registry.json、codex_notes.md。PowerShell 回读 JSON 校验 21 个样本键、证据字段、首断点及自动化类别。S2/S3/S4/S5/S6 分别 8/2/3/6/2；具备 8、只能人工核验 7、其他 6。历史构建未验证，Poly1305 覆盖未知。未读第一标注结果，未计算一致率。未构建、未联网、未调用其他模型。

## evcard_20261121 第二审查（盲判）
读取 criteria.md、review/packets.md，以 git show、git grep 核对 df2908090cda 的类型、配置依赖和调用点。新增 review/codex_review.json 与 review/codex_notes.md；用 ConvertFrom-Json 校验序号 1–24。完整线索 1，未决 2，排除 21，未知 0。JSON SHA256 为 4F3B1AB4698C6C0082D6E755761B70C9238951844D9BE35210910A35AAA21B90。构建 0，其他模型调用 0。未做运行验证或双审裁决。

## 2026-11-20 incscan 第二审查人盲审

判据 criteria.md 的 SHA256 为 8B542480FF1D2050ED39E04F132B6EC89189469E759D208E124C79C51481D670。读取本轮 packets.md，用 git show、git grep 核对 aebb7274476403040d582c61478df8f4a7bf9cd3 的源码，写入 review/codex_review.json 和 review/codex_notes.md。JSON 回读核对 1–16 号，完整线索 1 条（第 1 条），排除 15 条，未决与未知均为 0。未构建、未运行测试、未查看第一审查人结论；两人一致率待盲审结束后另算。

2026-11-21　完成晚期候选盲判、根因归并和汇总核对。输出位于 experiments/case_taxonomy/abisupply_20261121/sealed_late/ 下的 scorer_judgement.json、rootcauses.json 和 summary.json。

2026-11-21　完成晚期候选盲判、父版本核对及根因去重。逐条记录、根因表和汇总均存于 experiments/case_taxonomy/capsupply_20261121/sealed_late/。

2026-11-22　swaprev_20261122 第二审查人完成 df2908090cda 的 R1～R8 静态盲判，结果与依据见 review/codex_review.json、review/codex_notes.md；内核构建及运行均为 0。
2026-11-22　完成 R1 QEMU 动态证据复核，四组实测前后页号吻合，一组拆分前页号为推算；总评基本确认，见 swaprev_20261122/review/codex_qemu_review.md，本次未运行 QEMU。

2026-11-22　完成 ecscan 第二审查人独立盲审，34 组中完整线索 0、可能 2、排除 32；逐项依据及审查边界见 ecscan_20261122/review/codex_review.json 和 codex_notes.md。
2026-11-22 独立盲审 ecnoise 四条候选（df2908090cda）：N1、N2 排除为规则误报，N3、N4 为完整线索；判定与静态依据见 ecnoise_20261122/review/codex_review.json、codex_notes.md，未运行内核。
2026-11-22：依据 pool.tsv 与本地 Linux Git 历史独立盲标 EC 历史召回候选，25 条中 9 是、16 否；已写入 ecrecall_20261122/label/codex_labels.json 并核对哈希及顺序。

2026-11-22　独立盲审 df2908090cda 的 14 条编码一致性候选，13 条排除、N11 可能、完整线索 0 条；结果和依据见 ecprot_20261122/review/codex_review.json 与 codex_notes.md。

2026-11-23 独立盲审 ecsrc 的 M1～M4，对照 df2908090cda 源码手算，4 条均排除；结论和行号见 ecsrc_20261123/review/codex_review.json、codex_notes.md。未运行内核。

2026-11-23 第二审查人完成 ecunreach 本轮 17 条独立盲审，完整线索 0、可能 7（同源）、排除 10。结果见 ecunreach_20261123/review/codex_review.json 和 codex_notes.md。
