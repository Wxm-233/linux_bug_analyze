# 新输入前冻结的原始源码适配器

`run_raw_candidate_checks.py` 是本轮新harness，未改N2.5或核心。它原样导入旧 `parse_final`、`evidence_spans`、`_lex`、`_function_body`、`_anchor` 和旧采集器的 `complete_function`，不执行导入模块的main。

文档层为 `raw_source_file`。profile只表示 `case_parent` 材料组；case、精确parent/revision、原Git路径、完整文件UTF-8字节散列和source artifact的JSON pointer分别绑定。configuration/image/preprocessed身份必须显式为null。材料身份自洽不够，正式入口还核对事前冻结的selection和initial_material_plan；补源只能来自单独登记、由packet manifest摘要绑定且符合文件预算的计划。来源artifact头及其每条记录也须与具体采集计划对应。计划和散列不是语义真值。

局部关系由模型指定函数名，旧定位器必须返回唯一完整函数；完整文件锚点行号转换为切片本地行号后，调用旧词法检查，输出同时保留两套坐标。完整文件和函数内部的所有指令原样保留；片段中存在不支持的条件编译／指令、声明形式、重复定义或调用形状就不足。函数外层条件编译不因抽到函数片段而成立，整个结果仍不证明配置适用、CFG、调用效果或有效准备。

CLI为 `--documents --manifest --final --output`，后两项receipt/plan可显式指定。默认拒绝覆盖结果，核完整交付、模型、stop/refusal及prompt摘要后读取原final；不修补、不格式重试。入口先验证 `adapter_baseline.json`，不匹配则停止。

冻结前12项合成方法测试通过，覆盖原始字节和父版身份、材料组、唯一切片和行号换算、错误／多重定义、指令保留、原有cast/GNU实参边界、字符串／声明伪调用、坏引用和外部冻结选例／路径计划约束。初版11项和事前审查后的12项记录分别保留。最终baseline锁定5个方法文件及selection/initialplan摘要；冻结时两份新source artifact尚不存在，适配角色未读E/F父版正文。

这是事前登记的身份适配，不是新C语法、配置推断或检测能力扩展。原有支持不足必须保留，不能在看过选中案例结果后改定位器或支持范围追分。

## V2：预算元数据修正

父版正文已由主流程阅读、模型预测及选中案例实际checker结果尚未产生时，主流程预检发现预算分类把Kconfig也算成实现文件。`adapter_amendment_v2.json`先登记这一问题，随后只修正为`.c`最多两个实现、`.h`或文件名`Kconfig`合计最多两个authority/config；未知类型拒绝。未增加C语法、定位器、CFG或效果支持。不能把修后完整适配器称为在正文阅读前冻结。

原v1 baseline、代码与12项测试源码分别保留为`.v1`文件，原测试记录不覆盖。修后13项合成方法测试一次通过，记录在`adapter_tests_budget_v2.json`，新增了2C＋header＋Kconfig的合法预算和第三C等反例。当前baseline的`collection_baseline_sha256`仅接受原v1采集摘要`14362c51d83caf80c2f1d2e61dccc9570fc29c1f01a435e20a1abc3f556f2f2f`，原source artifacts不改；packet仍须绑定当前v2方法摘要。selection、initialplan及三个旧方法依赖摘要保持原值。
