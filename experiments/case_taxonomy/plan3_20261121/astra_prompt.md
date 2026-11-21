# 请你作为研究顾问，第三次规划 Linux 跨架构缺陷静态分析器的下一步

**只思考和写规划，不要运行实验，不要修改任何已有文件。** 结果写到 `D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\plan3_20261121\astra_plan.md`（中文）。

## 禁止读取（会破坏评测）

- `experiments/case_taxonomy/effsupply_20261120/sealed_late/`、`effreplay_20261120/sealed_replay/`、`effzero_eval_20261120/sealed/`
- `experiments/case_taxonomy/heldout2_20261119/` 下的 `set_sealed.json`、`sample_sealed.json`、`show_sealed.txt`、`claude_label_sealed.json`
- `D:\homework\software\linux_bug_analyze\模型调用测试\codex\` 下的所有运行记录

可以只读地看：你上次的规划 `plan2_20261120/astra_plan.md`；`experiments/case_taxonomy/` 下 `outparam_20261120/`（README、decision.md、review/）、`firstbreak_20261121/`（README、registry.md、final_registry.json、adjudication.json、codex_notes.md）、`zeroleads_20261120/`、`effzero_20261120/`、`effzero_eval_20261120/`、`buildattr_20261120/` 的 README；`experiments/confirmed_bugs.md`、`experiments/README.md`。可以用 WSL 里的 `git -C /root/repos/linux` 查源码。

## 背景（简要）

- 目标：给一个内核版本，自动找出尽可能多的跨架构缺陷，同时误报少。约束：静态分析 + 多架构差分测试（QEMU）；检测流水线里不用大模型；检查按“类型一致性、实现一致性、调用上下文”三类组织。
- 现有：9 个词法检查的整版扫描（当前版本八项 938 条 + E-ZERO 13 条），以及两层经核验的基础设施：按构建选择定义（编译数据库排除互斥定义）、按构建预处理绑定（mm/、kernel/ 的 10 万个调用点，抽查 24 个全对）。
- 已确认缺陷 6 个（`confirmed_bugs.md`）：5 个是新发现，其中 2 个补丁已被维护者认可或收下；1 个（arm32 原子 DMA 池不清零）是上游已知但未合入。

## 你上次规划之后的结果

1. **第一步：输出参数比较**（`outparam_20261120`）。绑定层第一次核验 30/31 没过（调用点被 `#ifdef` 掉仍绑定），修正后两组 31/31、33/33。但输出参数比较两个榜单前 8 条（共 9 条）两人盲审 9/9 排除：5 条调用方已初始化，2 条是功能关闭时的空桩（合法差异），2 条是分析器自身问题。最重要的观察：同一调用点在不同构建下选中不同实现，绝大多数来自**功能开关**，不是**架构差异**。按门槛停掉。
2. **第 4～5 天：分析侧逐例登记第一个断点**（`firstbreak_20261121`，我和 Codex 两人标注，第一个断点一致 15/21，κ 0.61，已裁定）。21 例：
   - 具备自动化前提 7、只缺构建覆盖 7、只能人工核验 7、非跨架构 0；
   - 不看构建覆盖时 14 例“检查写得出来但没写”，分属约 10 种形态（地址类别、ABI 位宽、能力判断不一致 3、架构能力横向比较、指令可见性 2、清零、同族函数只覆盖了一部分、访问函数副作用、上下文约束 2、非普通页表项），每种 1～3 例；
   - 只能人工的：并发/内存模型 3、运行时环境 1、ops 分派 2、需修复才引入的钩子 1；
   - 构建覆盖是最大断点（9 例）：功能在三个 defconfig 里没开（BTF、zswap、ftrace、KASAN HW_TAGS），或架构不在（sparc64、LoongArch、powerpc）。
3. 此前：E-ZERO 晚期回放 0/4；新评测集整版召回去掉曾用后仍为 0/23；规则 A、B 在独立样本上 0/25、1/10。

## 想请你回答

1. **诊断**：这些结果对“这个分析器还能怎么提升”说明了什么？请直接说你认为最有希望的方向，以及哪些方向该放弃。
2. **下一步**（约 1～2 周）：给出具体做法、输入输出、事先写定的继续或放弃条件、工作量。可以考虑但不限于：
   - 扩大构建覆盖（更多配置、更多架构，或用功能全开的配置）；
   - 不再按形态逐条写规则，改为某种更通用的跨实现比较或规格挖掘；
   - 把“当前版本找新缺陷”作为主产出，围绕审查效率改进排序和证据；
   - 把静态做不了的几类交给动态差分测试；
   - 新评测集的口径是否要调整。
3. **评测**：下一阶段用什么数据回答什么问题、怎么避免泄漏。
4. 如果你认为整体方法有根本问题，请直接说。

请写得具体、能直接落地。
