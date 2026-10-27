# N2.6 原始父版输入适配独立方法审查（2026-10-17）

审查限于协议、固定选例和文件计划、适配器代码、合成方法测试与文件元数据；未读取 E/F 新父版正文、child 消息／补丁、旧模型回答或结果真值。`selection.json` 的 E/F 各有一个精确父版，仍是研究用位置选择，两个样本的机制和正常／缺陷身份均待源码审查。选前接触过程及非预期看到一行旧评价的事实另记于 `contact_review.md`，该评价未参与排序。

初审的实质缺口是：原 `bind_documents()` 只校验 packet 与 source row 内部一致，合成输入把父版、自身 source row 和摘要一起换成另一 40 位值时仍可返回 `source_bound`。正式入口已增加 `validate_material_identity()` 与 manifest 门控：将单一 case 的 parent 锁到固定 `selection.json`，将初始文件路径锁到 `initial_material_plan.json`，补源只能来自另外登记且同选例绑定的有限计划；限制每案总文件数，并核每个 source artifact 的 baseline／计划摘要。独立合成探针现确认自洽换父版、换未选路径、换 case 均被拒。纯 `bind_documents()` 仍只是内部原文字节／记录一致性函数，不能绕过正式入口单独宣称“已选材料绑定”。

最终 `adapter_baseline.json` 已统一收集器、打包器和检查器的门禁名称，并固定 5 个方法文件加 `selection.json`、`initial_material_plan.json` 的 SHA-256；我逐项重算均匹配。封存文件时间早于 `initial_sources.json` 的创建时间，初轮 `method_baseline.json` 的 11 项记录保留为历史。对最终适配器独立运行 12 项合成方法测试均通过，包含原文件字节改变、父版／材料组错绑、函数唯一定位和全文件行号映射、指令保留、强制未配置身份、嵌套实参和语义不足。N2.5 的调用锚点程序、既有函数定位器与 `preprocessed_evidence.py` 摘要未改变。

正式输出仍标记 `raw_source_only`，配置、镜像和预处理身份均为 null；材料组 `E_parent`／`F_parent` 只表示来源，不证明架构分支、配置合法性或运行。定位器只接受其支持的完整唯一函数；原文件行号转换为函数片段行号后再复用原词法锚点，并在结果保留原坐标。找不到函数、重复定义、片段内未支持的条件编译或调用形态应保持 `insufficient`。即使词法先后被核实，也不证明控制流、可达性、对象效果、首次实际消费或正常性。选例父版和文件计划的摘要保证本轮材料追溯；它们本身不是内核接口规范或源码内容真实效果的自动认证。
