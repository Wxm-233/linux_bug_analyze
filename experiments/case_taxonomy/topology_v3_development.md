# topology 版本化证据提取 v3：已读样本开发记录

本轮仅重新读取此前已解封的 `f1045056`、`a62247e1`、`b40d8ed4` 及其父版。代码见 [`topology_v3_versioned.py`](topology_v3_versioned.py)，逐条条件、理由与历史源码定位见 [`topology_v3_development.json`](topology_v3_development.json)。这是**解封后开发数据**，不能取代 v2 的冻结结果，也不能据此声称独立验证成功。未读取新的留出提交。

v2 在 `a62247e1` 的 12 条冻结条件记录中有 12 条 `runner_error`：无条件读取当时尚不存在的 `include/linux/arch_topology.h`。v3 先检查历史版本的实际包含关系；未被公共头包含的缺失文件是“可选缺席”，被包含却缺失才拒判。构建规则新增 `obj-$(CONFIG_SMP) += topology.o` 的有界识别，并将 `CONFIG_SCHED_TOPOLOGY` 在旧 s390 Kconfig 中不存在的请求配置标成 `not_applicable`。属性入口分别识别 2010 年的 `SYSDEV_ATTR`、2016 年的 `DEVICE_ATTR_RO` 和已开发的现代 `DEVICE_ATTR_RO`/`BIN_ATTR_RO`；旧版还核对生成 show 函数的宏是否调用对应 `topology_*` 提供者。每种都要求提供者 ID 与 cpumask、Kconfig 守卫、声明/数组、sysfs group 注册链配对后，才给出受限源码层面的行为结论。旧 x86 分支的 Kconfig 来源图没有完整建立，保守拒判。

| 已读提交及父版 | v3 开发网格（每组 16 条） | 解释 |
|---|---:|---|
| `f1045056` | 12 `normal`、4 `insufficient` | 现代形状重用未修改的 v2 提取器，和此前开发矩阵一致；s390 配置未知时拒判。 |
| `a62247e1` | 4 `normal`、8 `insufficient`、4 `not_applicable` | 可确证的 4 条都是 s390 book 父/提交版 × 明确开关配置；drawer 在父版尚无消费属性；修订版 drawer 的 Kconfig/提供者可达性未建立。 |
| `b40d8ed4` | 2 `insufficient`、14 `not_applicable` | 识别 SMP 条件构建与 SYSDEV 模板，但提交时 `CONFIG_SCHED_TOPOLOGY` 尚未定义；把该较晚配置强加给 2010 年内核是不适用条件。book 的其余配置也未建立完整 Kconfig 来源，不能判正常。 |

严格按 v2 原冻结的**24 条条件网格**（不含本轮新增的 s390 配置未知档）重新切片，是 4 `normal`、6 `insufficient`、14 `not_applicable`；该数字只是 v3 **开发回放**，不能把先前 12 个错误和 12 个拒判改写为留出成功。`normal` 意味着已支持源码形状中的构建、配置、原生提供者、消费者与注册链配对，**不是**完整历史内核构建、真实 sysfs 或硬件语义验证。`not_applicable` 只指当前条件下驱动没有该属性或请求了不存在的旧版配置，不等于提交不相关。未识别条件一律保留具体 `insufficient` 理由，未用标题或修复后源码补齐证据。

测试覆盖 SMP 条件构建、可选头缺席、时代不匹配的配置、缺提供者的注入 `hit`、注册链不完整时拒判、旧 x86 Kconfig 图拒判；注入 `hit` 只是单测，不是历史真实错误。`python -m unittest tests.test_topology_contract_extract tests.test_topology_v3_versioned -q` 为 22/22 通过。冻结 v2 提取器 SHA-256 仍为 `74543284b92b429fee4ad598787d11c8fe8588f22f022a3395209795017f3ba7`。v3 代码 SHA-256 `72889e2c9bfa1bf716c44ba0141c2b9ea663d3f4c486989847ab4be1d6b5ae5c`；开发 JSON SHA-256 `c3cf7872fbe94390f7ab288e456cf75f50cb6ecd5efadfc64ddaba3f62587452`。

下一步需冻结 v3 代码和协议，在真正未读的修订上检验覆盖、拒判与误报；已读三提交不能再用作盲测。对 `insufficient` 要区分 Kconfig 来源、宏展开、导出动态可见性等缺失证据，逐项扩展，而不是统一转成 `normal`。本原型仍不会自动断定拓扑 ID 的硬件含义或 ABI 权威。
