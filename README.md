# Linux Bug Analyze

## 项目简介（2026-11-17 更新）

**做什么**：用静态分析加动态验证，检测 Linux 内核里的**跨架构缺陷**。

**什么是跨架构缺陷**：
- 公共代码（`mm/`、`fs/`、`kernel/` 等）依赖架构层（`arch/<架构>/`）提供的接口；
- 有些性质没写进函数原型，比如“这个接口只对 present 页表项有意义”“这个阶数不超过页缓存上限”“这个类型是 64 位”；
- 这些性质在某些架构上成立，在另一些架构上不成立；
- 于是同一段公共代码，在 x86 上没事，在 arm64、riscv 或 32 位架构上就出错。

**评测目标**：
- 给定一批跨架构相关的提交，尽可能多地找出引入缺陷的提交；
- 同时尽量不误判正常提交。

**基本做法**：
- 主线是“效果依赖”：公共代码依赖架构接口的某种效果，就检查这个效果在每个架构上是否真的成立；
- 不用大模型做检测，Codex 只在两人标注时担任第二位标注人；
- 不做修复迁移。

检查分三类，文档里固定用这三个名字：

| 检查 | 查什么 | 例子 |
|---|---|---|
| 类型一致性检查 | 同一个类型、编码在不同架构上的宽度或含义不同 | 32 位架构上 `unsigned long` 只有 32 位；非 present 页表项的位在各架构编码不同 |
| 实现一致性检查 | 公共代码依赖的接口效果，某些架构没提供或提供得不同 | 没查 present 就调 `pmd_young()`；arm64 64K 页的 `HPAGE_PMD_ORDER`=13 超过页缓存上限 11 |
| 调用上下文检查 | 接口要求的调用环境（锁、中断、上下文）在某些路径上不满足 | （还没有推进） |

## 工作流程

```
历史修复挖掘 ──► 静态检查 ──► 可达性过滤 ──► 两人审查 ──► 动态验证（QEMU） ──► 确认缺陷 ──► 上游核对/报告
   (depmine)     (各检查线)     (reachgap 等)   (Claude+Codex)   (修复变异/对照变异)
                      │
                      └──► 提交级模式：对一个提交的前后两个版本各跑一遍，只报新引入的候选
```

1. **挖样本**：从近两万个历史修复里机械筛出“公共层依赖架构层效果”的修复，经两人标注得到依赖缺失样本和分类（P1～P6）。
2. **静态检查**：每类依赖写一条检查线，在历史样本上量召回，在当前内核上出候选。
   - 受限接口（P1）：受限接口调用前必须有 present 守卫；
   - 横纵两面（xvdom）：横向编出 8 个架构的真实编码表，纵向看公共代码有没有守卫；
   - 接口提升（xvlift）：参数没守卫的辅助函数，逐层向上查调用者；
   - 阶数族（orddom）：页大小派生的阶数要先夹到页缓存上限；
   - 位宽截断（widthtrunc）；
   - TLB/缓存钩子（tlbhook）。
3. **可达性过滤**：去掉走不到的候选，包括内核页表、调用者已守卫、返回值摘要、goto、死分支等，保证召回不降。
4. **两人审查**：Claude 和 Codex 分别盲判，算一致率后再裁定。
5. **动态验证**：
   - 对每个疑点构建修复变异和对照变异的内核，在 QEMU 里按“性质”判错，而不是看哪个架构“与众不同”；
   - 内核镜像用 `tools/kbuild/kbuild.py` 登记复用，避免重复构建。
6. **核对上游并报告**：查主线、linux-next、mm 树和 lore 邮件列表，确认还没修、也没人报过，再由作者本人发补丁或缺陷报告。
7. **提交级模式**：输入一个提交，在它的前后两个版本上各跑四个引擎（P1、横纵两面＋提升、阶数族、位宽截断），对两边的候选做多重集差，报告新引入的部分。

每一轮实验都先写判据并记录 SHA，再统计；改判据只能通过修订。实验目录和结果见 [experiments/README.md](experiments/README.md)。

## 目前进展（截至 2026-11-17）

**确认缺陷 5 个**（详见 [experiments/confirmed_bugs.md](experiments/confirmed_bugs.md)）：

| 内容 | 出错架构 | 上游状态 |
|---|---|---|
| smaps 读 THP 迁移项的 young/dirty | riscv、x86_64、arm64 | 别人在 11-11 提交了相同的修复补丁（我们属于独立重新发现） |
| 回收时把 device-exclusive 项改成坏交换项 | arm64 | 上游 11-02 已修（独立重新发现） |
| 上一条的 MGLRU 回收路径变体 | arm64 | 同上，同一个修复 |
| DAX 上的 uffd-wp 标记导致误报 SIGBUS、无限重试 | x86_64 | **11-17 已向上游提交缺陷报告** |
| shmem force 模式超过页缓存上限 | arm64 64K 页 | **11-17 已向上游提交修复补丁** |

另有一个 tlbhook 新疑点（riscv KASAN 影子映射漏标记），后来查到别人已在实机上复现并提交了补丁，说明这条静态判断是对的。

**各检查线在当前内核上的结果**：

| 检查线 | 当前版本候选 | 历史样本召回 | 说明 |
|---|---|---|---|
| P1 受限接口＋可达性过滤 | 53 | 15/15 | 直接产出 3 个确认缺陷 |
| 横纵两面＋接口提升 | 33＋23 | 编码表核对 10/10 | 能指出哪个架构出错、错成什么样 |
| 阶数族 | 59 | 4/5 | 产出 shmem 缺陷 |
| 位宽截断第三版 | 746 | 6/8（算调用点 7/8） | 疑点还没动态验证 |
| TLB/缓存钩子 | 23 | 5/5 | 噪声大，23 条里 21 条不成立 |

**提交级模式**：

| 数据集 | 有缺陷提交判可疑（召回） | 新候选落在后来修复的函数上（对位） | 正常提交误报 |
|---|---|---|---|
| 开发集（24 个有缺陷、44 个正常） | 19/24 | 14/24（人工核对改名后 17/24） | 3/44 |
| 留出集（28 个有缺陷、48 个正常） | 4/28 | 3/28 | 1/48 |

留出集的召回低，原因是检查覆盖的缺陷类型还不够：没对位的 25 个里，23 个属于还没做成检查的类型（刷缓存钩子、TLB 语义、调用上下文等）。误报在两个数据集上都很低。

**还不完善的地方**：
- 调用上下文检查还没推进；
- 六类依赖只做了 P1 一类；
- 位宽截断的疑点没有动态验证；
- 提交级模式对“新增一种状态，旧代码出错”这类缺陷抓不到。

**协作方式**：本项目由 Claude Code 与 GPT（Codex）轮流推进。
- 工作说明和当前进度在外层主文件夹的 `交接文档.md`，每次工作的记录在 `进度日志.md`；
- GPT 另读本仓库的 `AGENTS.md`，Claude 另读 `CLAUDE.md`；
- 在 WSL 中运行命令前先 `source tools/wsl_env.sh`。
- 大于 2MB 的中间产物（JSON、pickle、gz）只保留在本地，已列入 `.gitignore`，可用各轮的脚本重新生成。

## 以下是旧方向的历史记录


## 历史状态（2026-10-17）

研究保留两个待证方向：N1从架构提供路径与公共消费用途推导条件化接口要求；N2按契约选择合法、可比的架构对照。源码主分析使用Windows原生Claude Code＋AWS-Claude-Opus-5.5。大规模初筛继续由天宇重点推进。

本轮完成[公共消费者候选定位](experiments/case_taxonomy/core_consumer_qualification_20261017/README.md)及[两候选父版/修复复核](experiments/case_taxonomy/core_parent_analysis_20261017/README.md)：一项为初始化注解整理，另一项为已接触源码的拓扑空间契约开发例，均不计独立首次准备检出。区分架构差异、适用条件和修复新增策略，不能把已有内核检查或新版本政策当本项目的新规则。

新增[N2有限池选配与已选观测回放](experiments/case_taxonomy/contrast_selection_20261017/README.md)：28项方法测试通过，四个既有profile中选出一对，再回放选中的两格旧观测，连接同用途条件与局部架构差异。契约、合法性与提供者语义仍需外部审核；没有新增内核启动、确认缺陷或独立样本，也未证明选择增益。

后续已完成[N1事实受限接线](experiments/case_taxonomy/evidence_feature_bridge_20261017/README.md)，24项方法测试通过；局部调用/资格候选不能直接当准备效果，正式特征不足，实际选配0对。另补[旧两架构运行配置源码视图](experiments/case_taxonomy/runtime_evidence_alignment_20261017/README.md)：5次预处理、11登记区域＋1后补，原对象/镜像保持。这是已读案例补证，没有新增模型请求、对象编译、内核启动或独立检出。

随后完成[模型候选—程序绑定—语义核对](experiments/case_taxonomy/aligned_contract_candidates_20261017/README.md)：一次Opus完整输出、11方法测试，14文档/35结构化引用绑定。保留有条件的目标锁覆盖候选，降级online等价准备和整组语义推断；正式特征不回填，未新增确认或独立样本。观测代码有提示线索，不称独立自动发现。

下一步固定当前有限方法及新身份适配规则，转向未参与开发父版的资格与有限试用，再做同材料/同预算评价；不继续递归扩大当前helper解析器。R3继续暂缓，完整N1/N2及稳定未知问题检测尚未完成。后续每轮按完整研究小闭环推进，进度见工作区当前待办及[实验导航](experiments/README.md)。

## 历史研究进展（截至2026-10-15）

研究重点进一步聚焦：架构差异怎样破坏公共接口的隐含契约、经何处传播，以及为什么某架构未暴露而另一架构暴露；自动检查须附架构差异依据。
大规模初筛与吞吐优化由天宇重点推进，既有500条与三批试跑结果继续作为选例来源。
表示类已开展受限事实提取、用户态局部检查与有条件长度模板；独立同机制检出及完整接口裁定仍未完成。
当前继续入口为[跨架构契约研究规划](experiments/case_taxonomy/cross_arch_contract_plan_20261012.md)：先重审原八项因果链，优先die原生能力/fallback导出与shmem实际页几何/公共上限配对。Btrfs字段模板保留为辅助，暂缓通用控制流扩展；跨配置与设备模式不直接冒充CPU架构对照。
[合并架构因果卡](experiments/case_taxonomy/cross_arch_causal_cards.md)已完成8/8限定源码与范围复核：die、shmem、s390、arch_topology四项限定链，virtio/Btrfs/SMMU三项辅助及Hyper-V不足范围卡；不是八个已验证CPU跨架构缺陷。Hyper-V撤回错误架构消费者投影，virtio补出bounce改变实际DMA目标，Btrfs区分合法页/磁盘几何与挂载拒绝，SMMU单列设备协议。[die真实构建配对](experiments/case_taxonomy/die_arch_contract_20261013/README.md)随后完成六格Kconfig、完整预处理和目标对象：x86 SMP属性3→3、s390 SMP及x86无SMP3→0，独立验收通过；随后完成旧/修复×x86/s390四次真实历史内核sysfs，x86值保持、s390占位导出取消，普通属性正常。[shmem局部配对](experiments/case_taxonomy/shmem_arch_contract_20261012/README.md)保留三真实配置、15条选择对照及3次原xarray消费者执行。10/13新增四次die内核启动，模型调用0；同属一项已读案例，不增加缺陷数。10/13随后取得旧ARM64/64K一格真实shmem故障链：自然order13分配、同对象插入与打洞/拆分触发内部错误，系统调用却成功。观测补丁已独立源码审阅，运行日志独立复核被自动检测中断；当前主流程核对成立。R3配对尚未完成，用户10/13明确暂缓修复64K并保留停点。当前转R4；[s390实际配置/构建](experiments/case_taxonomy/s390_arch_contract_20261013/README.md)已完成旧/修复×s390/x86四组、14份完整预处理与14个目标对象，独立核对通过；公共消费相同而架构准备顺序/集合不同。随后四次普通双CPU历史内核初次启动及独立日志复核完成：旧s390首次消费mask缺self/实际锁0并告警，修复s390和两版x86满足窄self条件；真实SMT、热插拔和并发仍未证。当前转R5带架构见证的模型检查建议，R3单独暂缓。
I3C模式候选模板已完成；两项真实输入的适用性核查尚未建立独立同机制检测。
新增KUnit同版配置消费链与六组合成请求匹配：核验能检查已写出的要求，但不能补出遗漏要求。
六项非空基础请求对照已核对覆盖边界：核验按最终请求判断，覆盖是否合法仍需环境依据。
配置局部开发已收束为[选择依据—要求传递—消费满足机制卡](experiments/case_taxonomy/kunit_config_override_20261011/mechanism_card.md)。
NUMA现存材料已有限复核，接口ABI权威仍不足，保留为边界对照；当前优先按新规划核对架构因果链。
R5先完成登记门槛、状态关系提取和上下文连接，随后[补源与消费者反例](experiments/case_taxonomy/claude_contract_resume_20261015/README.md)新增同父版6段339行、原三函数五个用户态逻辑输入，独立复核通过。缺self可无WARN、含self仍可无有效leader告警，故成员关系／告警／充分正确性须分开；不证明真实可达或独立泛化。Claude短HTTP诊断正常，源码240秒超时、4096 length空、65536 stop1空，无新有效源码分析；累计285901含150612未知预占，未触1M。下一项将接口身份、初始化／leader、配置、架构准备资格及消费期限合并到候选卡；接口正文恢复单列，R3仍暂缓。
当前自动检测尚未具备稳定独立泛化；局部投影与真实内核/设备证据按各案例分别报告，未新增确认案例。
案例分类、实验与限制见[实验导航](experiments/README.md)。

程序、测试与实验保持原路径，候选文件、审计与运行数据仍由现有设置引用。
Windows外层工作区的汇报和每日记录分别由本地导航管理，不混入实验封存材料。

## 筛选阶段记录（2026-09-23）

当前优先使用 `screen_fast.py` 和 `DeepSeek-V4.1-Flash` 做有预算初筛，暂不自动生成详细报告。
原500条分层样本已完成初筛；新入口的50条试跑也已完成，保留2条候选。
这些是模型候选，不是确认缺陷。最新实现、实测数据及证据边界见
[2026-09-22进展](documents/研究总结/2026-09-22进展.md)。

另开展了不调用模型的[静态三信号分层与 100 条提交源码复核](experiments/stratified_review/RESULTS.md)，
用于评估候选排序和漏检风险。该试验不修改现有 DeepSeek 短判定流程，也不把初步标签当成专家真值。
本地 [Laya 吞吐与保留测试](experiments/laya_benchmark/RESULTS.md)进一步覆盖 100 条和独立的 60 条；
模型推理较快，但直接输出没有排除项，探索性分数门槛会漏掉一条范围争议项，因此尚未接入自动排除。
已冻结[组合信号分层与三批初筛计划](experiments/stratified_review/BATCH_PLAN.md)：
每批 275 条，包含高、中、低优先级和旧规则未入选对照。
[第一批 DeepSeek 短判定与源码抽查](experiments/stratified_review/BATCH1_RESULTS.md)已完成：
275 条中模型相关 44、不确定 31、不相关 200；抽查发现字节序表示问题的疑似漏保和准备性提交的疑似误保。
第二、三批也已完成短判定，原始结果保存在本机 `analysis_out/stratified-batches-20260923/`；
三批结果仍需按层复核，不能直接当作确认缺陷或总体相关率。
[模型前规则影子过滤实验](experiments/prefilter_shadow/RESULTS.md)显示，宽规则会错拦有研究价值的提交；
极窄的编辑性规则覆盖不足 1%，目前不启用自动跳过。
[80 条同样本材料压缩对照](experiments/material_ablation/RESULTS.md)显示，三种输入压缩虽然最多节省约 51% token，
但判断变化明显，其中关键片段版漏掉一条已有源码复核支持保留的案例。因此正式初筛仍使用原材料；
按预设质量门槛，暂缓在这些压缩配置上进行 8 并发付费试验。
[原材料并发提速试验](experiments/speed_benchmark/RESULTS.md)在同 50 条与两批各 275 条上完成，
已修复高并发下临时 token 预留导致的提前停止；短判定默认改为 16 路并发。
这只缩短已观察批次的运行时间，没有证明筛选准确率或全量长期吞吐。

目录按用途组织：`linux_bug_analyze/`为程序，`tests/`为测试，`experiments/`为可复现实验，
`documents/`为研究说明。根目录保留命令行入口；`analysis_out/`只保存本地运行数据并忽略提交。

本工具读取一组 Linux 内核 commit hash，提取提交说明、变更文件和 diff，再让 OpenAI
兼容模型按 [`documents/新·论文思路梳理.md`](documents/新·论文思路梳理.md) 中的研究定义完成：

- 判断提交是否属于“隐式语义假设错误”或“跨架构回归”；
- 输出经过规范化的一个或多个相关架构（例如 `arm32`、`arm64`、`x86`）；
- 标注语义来源架构、公共层 architecture-scope、断言充分性和可能的重构机制；
- 生成包含触发范围、边界、支持/反驳证据、修复层次和验证方式的语义卡片；
- 为每个提交生成独立 Markdown 报告，并生成有稳定链接的索引。

## 研究总结与契约实验

当前样本分析、初步 pattern、系统层机制和证据边界见
[研究总结](documents/研究总结/初步Pattern与系统层机制总结.md)及
[统一契约矩阵](experiments/CONTRACT_MATRIX.md)。各实验目录提供复现方法，
覆盖源码切片、大小端用户态执行和部分真实内核检查；这些验证层级不能混为硬件复现。
本机日志、密钥、设置和运行产物不提交到仓库。

## 只做初筛：并发与分级材料

新入口 `screen_fast.py` 默认使用 `DeepSeek-V4.1-Flash`，不启动详细分析。
API地址和仓库外密钥文件仍从settings读取；该入口的模型默认值独立于旧分析设置。

```bash
python screen_fast.py --settings settings.toml --hashes-file batch.txt \
  --outdir analysis_out/screen-batch-001 --max-items 500 \
  --workers 16 --max-requests 100 --token-budget 2000000
```

- 先解析完整提交hash去重，相同运行条件下复用已保存的阶段结果；恢复时预算累计，不清零。
- 先提供最多6000字符的补丁；只有不确定且仍有更多补丁的条目才扩充至20000字符。相关项直接进入候选队列。截断材料不能支持自动排除。
- 新入口优先要求1–8条证据，最多接收32条；每条仍检查整数、范围、唯一性和原文。旧入口保持8条上限。完整JSON代码围栏可无损去除，不修补错误JSON或伪造编号。
- 默认格式重试0次，临时HTTP错误最多重试1次；两类可分别设置。失败条目留在checkpoint中，不作为不相关项。
- 并发请求共享加锁的预算预留和持久账本；临时预留超出预算时等待在途请求结算，不能据此提前宣告额度耗尽。同一输出目录有进程锁。鉴权或余额错误停止派发，在途请求结束后保存结果。未知用量保留预留值，不当成零消耗。
- `dedup.json`记录短hash别名和stable patch-id分组。相同patch-id不证明不同内核版本的语义等价，因此不同提交仍独立筛选，不自动继承排除结论。

`selected_hashes.txt`只包含成功判定后需要保留的条目；`checkpoint.json`另列未完成或格式失败项。
`responses/`、`materials/`、`usage.json`保存复核材料；`stages/`用于断点复用。
`preparation.json`与`last_run.json`分别记录 Git 预处理和模型阶段/总耗时。
在同一目录执行相同命令可恢复，允许调整并发和提高预算。模型、材料级别或输入集合改变时使用新目录，防止混用旧结果。
预算以输出目录为单位，多目录实验须另外约束总支出。可加`--plan-only`检查输入和去重，不加载密钥、不调用模型。

先用小批验证平台限流、用量及保留情况，再扩大批量。分级策略可能因二次调用增加token，不能保证省费。
后续深入分析统一使用 **Windows原生Claude Code＋`AWS-Claude-Opus-5.5`**（用户于2026-10-16调整），沿同一ISRC平台的Anthropic Messages接口，根地址为`https://llmapi.isrc.ac.cn`。Sonnet／Kimi旧配置与结果保留为历史，不再作为当前主分析入口。

当前选择记在`analysis_out/current_analysis_backend.json`，项目协作约定见[AGENTS.md](../AGENTS.md)。该JSON是路由记录，不会让现有OpenAI兼容CLI自动转用Claude Code；研究调用须明确使用原生客户端。密钥仍在WSL仓库外，通过内存/子进程环境注入，返回信息放入已忽略的[Windows模型调用目录](../模型调用测试/2026-10-15/README.md)，每轮使用新ID并保留增量和最终正文。当前通用调用器为外层`模型调用测试/run_claude_review.py`，明确读取路由中的模型与独立凭证profile；不回退Sonnet。当前固定独立客户端2.1.301，保留旧版；新凭证与版本对照见外层`模型调用测试/2026-10-16/README.md`。新版两次短测成功，同源码请求交付部分正文但发生refusal，完整分析未通过；后续end_turn不能抵销拒绝。短测不代表源码分析稳定或质量。

本方案已在252行旧源码材料上完整交付7387字分析，但语义复核仍发现准备资格、其他leader与空集合等误读，因此完整返回及引用可定位不等于检查正确。R5的[分项检查卡](experiments/case_taxonomy/state_contract_refine_20261015/README.md)通过25项离线门控测试，仍属已读案例开发；模型、研究者和程序来源分别记录。初筛继续沿用DeepSeek入口；历史Claude/GPT/GLM/Kimi轮次及其预算不覆盖。

周报/讲稿优先复用Astra高推理文稿角色`/root/report_writer`，当前实际可选标识为`gpt-6-astra`、reasoning=`high`，由主智能体复核日期、统计与证据边界。

## 安装

需要 Python 3.10 或更高版本及 Git。使用 uv：

```bash
uv sync
```

也可以使用普通虚拟环境：

```bash
python -m venv .venv
python -m pip install -e .
```

## Settings 配置

首次使用时复制模板，并填写本机路径：

```bash
cp settings.example.toml settings.toml
```

Windows PowerShell：

```powershell
Copy-Item settings.example.toml settings.toml
```

至少设置：

```toml
linux_dir = "/data/linux"
hashes_file = "candidate_hashes.txt"
outdir = "analysis_out"
```

配置完成后不再需要位置参数：

```bash
python analyze_commits_with_llm.py
```

也可以选择其他配置文件：

```bash
python analyze_commits_with_llm.py --settings settings.remote.toml
```

settings 中的相对路径以该 TOML 文件所在目录为基准。命令行参数会覆盖 settings，
因此仍可临时执行：

```bash
python analyze_commits_with_llm.py /other/linux other_hashes.txt --workers 2
```

`settings.toml` 已被 Git 忽略。本地和远端 Linux 机器应分别维护自己的文件，仓库只提交
`settings.example.toml`。

## API 配置

API 配置优先级为：

1. `--api-key`、`--base-url`、`--model`
2. `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`
3. settings 中的 `[openai]` 配置
4. 项目根目录的 `OPENAI_API_KEY` 文件，以及代码中的默认 API 地址和模型名

不要把 API Key 本身写入 settings；只设置 `api_key_file`。`OPENAI_API_KEY` 和
`settings.toml` 均已被 `.gitignore` 忽略。

使用 DeepSeek 官方平台时，可在本机 settings 中配置：

```toml
[openai]
api_key_file = "/root/.config/linux-bug-analyze/api_key"
base_url = "https://api.deepseek.com"
model = "deepseek-v4-flash"
reasoning_effort = "high"
thinking = true
```

密钥文件应放在仓库外，路径按实际用户目录调整。`thinking` 会转换为接口的
`extra_body.thinking.type`，支持 `true` 和 `false`；未配置这两个可选参数时不发送，
以兼容其他模型服务。开启思考后，如分析输出达到 token 上限，可增大 `max_tokens`。

## 主流程

研究样本直接来自本地 Linux 主线 Git 历史，而不是 CVE 邮件集合：

```text
Linux 主线 Git 历史
  -> extract_commit_hashes.py（时间范围 + 高召回正则）
  -> candidate_hashes.txt
  -> analyze_commits_with_llm.py
  -> summarize_results.py
```

依次执行：

```bash
python extract_commit_hashes.py
python analyze_commits_with_llm.py
python summarize_results.py
```

hash 文件仍可人工提供，每行一个十六进制 commit hash；空行和以 `#` 开头的注释会被忽略。

```bash
python analyze_commits_with_llm.py /path/to/linux candidate_hashes.txt \
  --outdir analysis_out --workers 8
```

上述位置参数方式继续兼容，且优先于 settings 中的 `linux_dir` 和 `hashes_file`。

## 结构化分析输出与统计

模型响应使用“精简 JSON 分类头 + Markdown 正文”协议。程序会在写入成功报告前验证：

- 分类字段、枚举和字段间约束；
- Markdown 必需章节；
- API 的输出是否完整结束；
- 正文没有重复生成由程序负责的分类区块。

格式不正确或输出被截断时会进行一次格式重试；仍不合格则写为失败报告，后续运行可重试。
成功分析会生成两个文件：

```text
analysis_out/<完整 hash>.md
analysis_out/<完整 hash>.meta.json
```

Markdown 中的分类和作用域字段由程序根据 schema v3 元数据统一渲染，统计程序只读取 sidecar
JSON，不依赖 Markdown 的加粗、换行或列表样式。

分析完成后运行：

```bash
python summarize_results.py
```

默认读取根级 `outdir`，并在同一目录生成：

- `summary.json`：除相关性和架构外，还统计语义来源架构、公共层作用域、断言充分性和建议机制；
- `results.csv`：保存每个提交的全部结构化标注、标题、报告路径和数据来源；
- `related_hashes.txt`：所有判定为相关的提交 hash；
- `related_index.md`：只包含相关报告的可点击索引。
- `related_reports/`：相关报告的独立副本；新格式报告同时包含对应 `.meta.json`。

`related_reports/` 位于 `[result_summary].output_dir` 下；未配置时位于根级 `outdir` 下。
重复汇总会同步其中的相关报告，并删除汇总器生成但已不再相关的 `.md`/`.meta.json` 副本；
其他文件不会被清理，原始分析目录中的报告也不会被移动或删除。

也可以另设输入和输出目录：

```toml
[result_summary]
input_dir = "analysis_out"
output_dir = "analysis_summary"
```

```bash
python summarize_results.py /data/analysis_out --output-dir /data/summary
```

本轮分析使用 schema v3。旧结构化结果不会作为新结果沿用；建议把旧目录归档，并为本轮
设置新的 `outdir`。少量无 sidecar 的旧 Markdown 只保留只读识别能力，不参与格式迁移。

## 直接扫描 Linux 主线提交

主线入口通过一次流式 `git log` 读取指定时间范围内的提交说明和变更文件，然后复用
`[hash_filter]` 的高召回正则。它不会为每个提交分别启动多次 `git show`，适合扫描五年历史。

在 settings 中配置：

```toml
linux_dir = "/data/linux"
hashes_file = "candidate_hashes.txt"

[commit_source]
ref = "HEAD"
since = "5 years ago"
until = ""
no_merges = true
reverse = true
max_count = 0
shuffle = false
random_seed = 0
output_file = ""
audit_file = ""

[hash_filter]
fields = ["subject", "body", "files"]
match = "any"
case_sensitive = false
# 完整默认 include 见 settings.example.toml。
```

`since` 和 `until` 接受 Git 日期语法。探索时可使用 `5 years ago`；正式实验应固定为明确
日期，以便复现。默认排除 merge commit，并按旧到新输出。启用 `shuffle` 后会用
`random_seed` 确定性打乱候选，便于人工抽样。

审计文件只记录一条扫描汇总和被选中的提交，包含扫描范围、正则、命中字段和候选数量，
避免为数十万个未命中提交生成过大的审计文件。

## CVE 和邮件的角色

`linux-cve-announce` 不再决定研究样本总体。原有 `extract_cve_hashes.py` 仍保留为辅助工具，
但主要用途是对照实验；分析阶段若配置 `[cve_source].inbox_dir`，匹配到的 CVE 公告只作为
补充证据。提交中的 `Link:`/`Closes:` 仍可从 `[evidence].mail_inbox_dirs` 指向的本地
public-inbox 镜像提取讨论。

## 可选：筛选已有 hash 文件

`extract_commit_hashes.py` 已经应用 `[hash_filter]` 规则。只有手头已有其他来源的 hash
文件时，才需要独立筛选模块：

```toml
hashes_file = "filtered_hashes.txt"

[hash_filter]
source_file = "candidate_hashes.txt"
# 完整的高召回规则见 settings.example.toml；未配置 include 时也会使用同一组默认规则。
fields = ["subject", "body", "files"]
match = "any"
case_sensitive = false
```

然后执行：

```bash
python filter_hashes.py
```

或者完全使用命令行：

```bash
python filter_hashes.py /path/to/linux candidate_hashes.txt filtered_hashes.txt \
  --include '(?:^|/)arch/' \
  --include '\b(?:cross[- ]arch|multi[- ]arch|endianness|memory ordering)\b' \
  --fields subject body files
```

规则说明：

- `include` 和 `exclude` 都是正则数组，普通关键词也可直接使用；
- `match = "any"` 表示命中任一 include 即保留，`all` 表示必须全部命中；
- exclude 的优先级高于 include；
- 可筛选字段为 `subject`、`body`、`files` 和 `diff`；只有选择 `diff` 时才提取 diff；
- diff 筛选默认不截断；若显式设置 `max_diff_chars`，审计记录会标明截断状态；
- settings 中省略 include 时使用内置高召回规则；显式设置 `include = []` 时才保留所有未被 exclude 命中的提交；
- 输出使用完整 commit hash，并保持原输入顺序；
- 默认同时生成 `<输出文件>.audit.jsonl`，记录每个 hash 的决定、命中规则和错误。

筛选完成后，`analyze_commits_with_llm.py` 会直接读取根级 `hashes_file` 指向的结果。

常用选项：

- `--start-index` / `--end-index`：只处理一段输入；
- `--force`：重新分析已有成功报告；
- `--max-diff-chars 0`：不截断 diff；默认上限是 50000 字符，截断时保留首尾并要求模型降低置信度；
- `--evidence-dir evidence`：加入人工收集的补充证据。文件名应为完整 commit hash 加 `.md` 或 `.txt`；
- 分析时会自动加入 `Fixes:` 指向的引入提交；若配置 `[cve_source].inbox_dir`，也会匹配对应 CVE 公告；
- `[evidence].mail_inbox_dirs` 可配置其他 public-inbox v2 镜像。程序按提交中的 `Link:`/`Closes:`
  Message-ID 提取直接相关的邮件，不会把整个邮件列表送给模型。

证据长度和邮件镜像可在 settings 中控制：

```toml
[evidence]
mail_inbox_dirs = ["/data/lore/kvm", "/data/lore/linux-arm-kernel"]
include_fixes_commit = true
max_chars_per_source = 12000
max_total_chars = 36000
```

失败报告有显式状态标记，下次运行会自动重试。短 hash 会先转换成完整 hash，所以断点续跑和索引链接不会因 hash 长度不同而失效。

## 模块划分

- `git_repository.py`：Git 校验、hash 解析和提交事实提取；
- `commit_source.py` / `commit_cli.py`：流式扫描 Linux 主线提交并直接生成候选 hash；
- `analysis_protocol.py`：混合输出协议、分类枚举校验和标准分类区块渲染；
- `public_inbox.py` / `cve_source.py` / `cve_cli.py`：读取 CVE 邮件镜像、提取主线修复并生成审计；
- `hash_filter.py` / `filter_cli.py`：确定性候选筛选、命中审计和命令行入口；
- `evidence.py`：引入提交、CVE 公告、本地邮件讨论和人工材料的证据组合；
- `result_summary.py` / `summary_cli.py`：结构化结果统计和相关提交索引；
- `prompting.py`：与研究问题对齐的提示词；
- `llm.py`：模型接口和重试；
- `pipeline.py`：并发分析和单任务故障隔离；
- `reporting.py`：原子写入、断点状态和索引；
- `config.py` / `cli.py`：TOML settings、配置优先级、参数校验和流程编排。

主要入口为 `extract_commit_hashes.py` 和 `analyze_commits_with_llm.py`；安装后也可使用
`extract-mainline-hashes` 和 `linux-bug-analyze` 命令。
# 小批短判定与预算控制

2026-09-22 更新：`screen-v5` 将证据编号及保存引文的数量上限从3条调整为8条，
仍要求编号为有效、不重复的整数，并逐条提取和校验材料原文。500条试跑的95次
格式失败中，90次响应给出了4–8条证据；离线回放后89份响应通过全部格式校验，
另1份仍因语义边界枚举无效被拒绝。21条最终格式失败提交均至少有一份历史响应
可按新协议解析。这只说明协议兼容性改善，不证明语义结论正确，也不是实测的
新一轮调用节省比例。旧screen-v4试跑结果保持不变，新版使用独立输出目录。

2026-09-22 的深入分析试验使用用户指定的 `GLM-5.3`，接口及仓库外密钥沿用当时配置；
历史分析配置位于被忽略的 `analysis_out/glm-review-20260922/settings.toml`。
模型试分析与DeepSeek筛选结果分开保存，不能当作独立专家金标准。

2026-09-08 的 44 条试验发现：短判定存在把“仅修改 arch/”误当作不相关依据的问题，
相对助手源码复核的 7 条相关案例只保留 2 条。因此当前入口仅用于试验，
不建议直接用其排除结果驱动全量研究。助手复核不是人类专家金标准。

`screen-v2` 将纵向语义失配与横向回归分开判断：恢复公共接口既有契约也可相关，
不要求同时修改公共目录和架构目录；只有横向回归需要 A→共享行为→B 的因果证据。
范围或证据存在争议时保留为不确定。结果和用量账本记录 `prompt_version`，
实际缓存仍按完整提示词及材料指纹判断，旧版判定不会直接复用到新版。
评估时应先冻结源码复核参照，再调用模型；已知案例回归与未见样本结果分开报告。
相关案例保留率和不相关额外保留率需要同时检查，不能仅看总体分类一致率。

2026-09-09 的 v2 限额试验完成 14 条已知案例及 24 条新样本：已知相关保留 7/7，
争议案例保留 4/7；新样本相关保留 2/3，仍有漏检。参照为助手源码复核，且新集正例不足，
未通过预设验收。全量任务继续停止，排除结论仍需复核。

`screen-v3` 使用七字段模型响应：相关性、理由、证据行号、复核标记、纵向判断、
横向判断、排除依据。程序按行号提取原文，校验编号有效性，保存结果仍提供 `evidence` 引文。
两类边界未排除、排除依据不足或理由触发目录/接口变更等可疑表述检查时，
不相关结论转为不确定；保存 `model_decision`、`assessment` 和 `guard_flags` 供审计。
该检查是保守规则，可能增加误保留，也不能识别所有语义错误；引文存在不等于支持结论。
规则、协议或提示词变化时应更新 `PROMPT_VERSION`，避免复用旧检查结果。

2026-09-10 的 v3 对同38条已见样本回归：41次请求、193150 token，校验失败重试3次，
较 v2 的11次减少；旧开发组相关保留7/7、争议保留3/7，旧验证组相关保留2/3，
仍不满足筛选目标。保护规则额外保留4条不相关案例，尚不能可靠替代语义复核。
本轮不是独立验证，不宣称筛选质量整体提升。

`screen-v4` 改用提交说明与实际代码改动共同命中的语义线索，替代 v3 对模型理由的措辞匹配。
`source_signals` 保存线索类别、说明原文和改动行；它只保护复核队列，不自动确认漏洞。
当前覆盖页粒度、映射权限、域转换、compat表示、拓扑、能力描述和回溯，未命中不代表安全。
2026-09-12 定向试验输入20条已见样本，19条有效完成、12条保留、1条格式失败待复核，
累计25次请求及121090 token；从队列选8条完成探索性源码pattern分析，未进行内核运行验证。
这类按研究线索挑选的小批样本用于发现模式，不能据此估计全量准确率或漏洞比例。

离线IOMMU契约原型见 `experiments/iommu_contracts/README.md`：从固定修复提交与父版本
提取VT-d权限编码和SMMUv3控制流，编译C片段并检查权限和状态轨迹，不调用模型。
实验使用硬件/锁/分配测试替身，不能当作完整内核运行、硬件隔离或漏洞利用验证。

后续 VT-d 内核内测试见 `experiments/vtd_kunit/README.md`：已在QEMU启动真实x86内核，
KUnit与实际映射路径共用权限编码辅助函数。旧行为6项中仅第二级只写失败，修复行为6项通过，
其中第一级只写一项用于记录不支持边界。此测试不再使用用户态编码替身，但仍未执行完整映射、
IOTLB失效或设备DMA，不能当作硬件访问隔离验证。

以下为旧串行初筛入口 `screen_commits.py` 的使用说明；新批次优先使用上方 `screen_fast.py`。
旧入口不覆盖已有长报告，
也不会自动调用详细分析。默认单路、最多 50 条提交、60 次请求（含重试）、200000 token
预算、每次最多输出 1200 token。短判定关闭思考，模型及仓库外密钥路径取自 settings。
这些上限仅适用于新入口，原 `analyze_commits_with_llm.py` 尚无同样的预算保护。

```bash
python prepare_review.py --outdir analysis_out/review-pilot
python screen_commits.py --settings settings.toml \
  --hashes-file analysis_out/review-pilot/hashes.txt \
  --outdir analysis_out/screen-pilot \
  --max-items 50 --max-requests 60 --token-budget 200000
```

第一条命令只整理本地报告；第二条会调用付费 API。复核清单的旧模型标签不是人工真值，
请填入人工结论和证据后再评价短判定准确性。

短判定输出相关性、理由、材料原文短引文和复核标记。相关、不确定和要求复核的条目进入
`selected_hashes.txt`，可作为后续详细分析的输入；此文件仅代表当前小批已完成条目。
截断材料上的不相关结论保守转为不确定。结果保存在 `results/`，不会被长报告汇总器误当作完整分析。

`usage.json` 记录请求、重试、耗时和服务端 token 用量；`runs/` 保留每次运行账本。
运行账本下的 `responses/` 保存可用的模型原始响应，便于定位格式失败；不记录密钥。
每次启动获得独立预算，并非跨运行总预算。恢复时指定相同输出目录和相同输入，
只有提示词、证据、模型及输出上限指纹一致的成功短判定会复用。
每次最多尝试两次；连续失败、鉴权/余额错误或预算不足会停止，退出码 3；中断退出码 130。

发送前按 UTF-8 字节数加消息封装预留及输出上限进行保守估算，返回后按服务端实际 total_tokens 结算。
请求失败或用量缺失时保留预留额度，避免把未知支出记为零。此预算是本地 token 控制，
不是平台账单的金额硬上限；分词及服务端计费差异仍可能产生偏差，不据此承诺具体费用。
