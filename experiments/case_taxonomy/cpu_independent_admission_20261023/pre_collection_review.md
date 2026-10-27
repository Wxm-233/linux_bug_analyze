# N2.24 父版材料采集前独立有限复核

2026-10-23。助手研究侧角色，只读协议、固定选择、元数据路径可用性、采集脚本及既有接触记录；没有读取新候选正文/diff/源码/旧模型assessment，没有执行本轮采集、编译、模型或内核。以下门控只允许取得固定父版材料以审资格，不认可独立正/正常真值，也不认可完整检测器已冻结。

## 选择及材料计划

唯一组的prospective issue为`f9a82544c7174851f5c7524622f5966dcafd3a47`，固定父版`18a4e5cf633fad5c40ac9d936c51bf38db68796d`；normal只预选同父版原生x86的同公共SMT控制用途。标题与变更路径只是目的性定位信息，不能据标题中的Fix认定既有缺陷，亦不能把x86视为当然正常。

500元数据摘要、selection→source_plan摘要及两侧父版身份均匹配。两侧各8完整文件，去重12；路径存在性取自限定文件名的`ls-tree --name-only`，没有从正文自适应挑文件。x86旧topology.c不存在后，按事前`first available`顺序选setup.c，不属于读源后换样。共享四文件复用同一父版，后续可比性仍需各自配置/路径条件，不能因共用源码而视为相同保证。

该集合足以开始有界源码资格审查：包含公共消费/注册、入口及两侧提供者与配置线索。它不保证包含全部hook、配置依赖、非空合法实例或正常保证；缺失时按协议不足收束，不自动追helper或更换候选。

## 接触史：不能沿用旧“尚未读”印象

全500池已接触历史DeepSeek短筛，不是全局未见样本。10/17 exposure_index将f9标为not_found_in_scanned_records，同时明确global_non_exposure_proved=false；这不能证明至今没有源码或方法接触。

已核的较晚背景重叠包括：

- `new_input_contract_trial_20261017/supplement_sources.json`登记F的`arch/arm64/kernel/smp.c`全文，父版`d2e9f53ac5dd76dadc0b5f04f6c27640604ce2af`；该路径不能称从未接触。
- 同stage `initial_sources.json`登记E的`kernel/cpu.c`，父版`6eaae198076080886b9e7d57f4ae06fa782f90ef`；`core_parent_analysis_20261017/parent_files.json`及`cpu_mapping_transfer_20261021/documents_I.json`也有公共CPU路径接触。
- `cpu_domain_qualification_20261022/documents_P01.json`登记父版`0af2f6be1b4281385b618cb86ad946eded089ac8`的`arch/x86/kernel/setup.c`，正常参考并非整包全新。

这些是路径/版本接触证据，不足以自行证明本轮目标函数或修复家族曾用于开发，也不能反向证明其独立。父版材料取得后须单列目标函数、同修复家族、规则开发使用与仅共享背景；若不满足当前独立准入，应明确降级/不足，不强保独立标签。

7202/f1c已有`contract_protocol_20261016`及`state_contract_refine_20261015`研究引用，旧索引本就保留接触深度未决；本轮没有以它们补正/正常。没有为本组读取其他新候选正文或补充第二组。

## 采集脚本和边界

`collect_parent_material.py collect`只向现有本地内核Git请求固定`git show <父版>:<登记路径>`blob，以argv执行，不取commit message/diff/修复版，不触发网络、编译或模型。新`parent_sources/`必须不存在，首份source_manifest禁止覆盖；失败保存stopped与已收文件，不自动重试。文件名均为当前固定相对路径，写入本stage。

source_plan SHA256：`585eb67f0c023bad1abd852493f85b369d1072447283b91a2c2bb85fcd965d87`。执行前记录的摘要文字已纠正，计划文件未改。

采集器已在子进程环境固定`GIT_NO_LAZY_FETCH=1`及`GIT_OPTIONAL_LOCKS=0`，缺本地对象即失败，不以Git部分克隆的隐式获取扩展网络。仍只采固定父版blob，无新增路径或正文筛选。

上述计划及支持域审查不等于实际配置、正常性、N1要求自动取得或N2对照收益已经成立；N2.23四profile日志适配器不可改名用于新源码。取得材料后先审provider/common consumer、对象/阶段、接口依据及合法非空正常保证；任一关键条件不足则本组收束，正式独立评价0/0不变，随后进入已排表示接口。R3仍暂缓。

PARENT_COLLECTION_GATE: PASS
