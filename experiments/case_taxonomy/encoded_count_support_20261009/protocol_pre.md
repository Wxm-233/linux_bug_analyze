# 编码长度机制：新接口有限支持检查

日期2026-10-09。此轮仅检验未参与本研究规则开发的父版接口能否形成可用输入，不执行检测器/来源门控，不读取修复patch。元数据来自既有固定500的analysis_out/stratified-20260921/manifest.json；不用模型判断结果或825批次。

## 第一冻结：元数据与选样

按manifest原samples顺序取stratum=representation的第17–32项（1-based）。上一数值比较试验已使用第1–16项，此轮接续固定16，不替补第33项。曝光审计限定现有case_taxonomy的源码/结果/审阅/台账记录，逐条区分标题或元数据提及、源码/patch曾审阅、参与开发及无证据。未找到引用不代表全球盲测；历史模型短判定可能读过材料，独立性仅针对定义的本地研究/规则开发记录。

候选标题必须大小写不敏感命中endian|byte[ -]?order|(?:le|be)(?:16|32|64)|convert|conversion。先从未见源码开发/审阅证据的匹配项中，按原顺序选择首个又命中\b(?:len|length|size|count|bytes)\b的项；若该组为空，仅取匹配项中的首项。这个元数据优先级只是提高同机制支持机会，不是相关真值。至多一项；队列确定后不因源码不支持而换样。

协议、16池、逐项曝光审计/证据、选样、脚本及旧encoded_length_check.py/来源门控/其本地Python依赖先冻结，独立审阅通过后才能检索新父版。零可选就在此停止。

## 固定父版取证额度

仅使用WSL现有/root/repos/linux Git。固定selected fix SHA，一次cat-file -p只解析原commit头直到空行的parent；完整原stdout保存但不显示/解读message，这不构成完全提交正文盲封。要求恰一个parent；merge/缺失停止，不换项。一次diff-tree --no-commit-id --name-only -r fix获取路径名，不读取patch。

在变更路径中按字典序预定首个.c，先保存选择/路径再导出父版；无.c或文件missing停止，不取第二个。最多另取该C内原顺序首两条literal quoted include，按C目录归一，不能出树；若不足两条就取现有条数，不补angle header/第三quote/标准包装头。第一次C保存后，固定两header请求清单再执行；missing保留，完成固定请求即停止，不替代。最多3文件请求；parents/path_names/C/header batch共最多4Git命令，二进制cat-file响应、退出码/stdin/stdout/stderr/实际blob及SHA保存。

此设计支持范围窄，固定首C/前两quote未必含契约声明；其不足属于选样与取证范围的限制，不计假阴性或确认不相关，也不能宣称可自动发现全部问题。

## 父版支持判断（不运行规则）

只读取上述保存C/headers。按源码顺序查直接struct指针的端序标量字段进入局部整型长度赋值，局部变量被直接用于memcpy/memmove第3参数、skb_put第2参数或skb_tailroom比较；raw或已转换均可作为支持输入，不按期待告警挑选。字段/局部类型与声明在固定材料内可见，宏/alias/多版本/对象来源歧义保留。不支持首形状可继续在同C寻找最早支持函数，不能换C/header/样本。显式记录首线索与最早支持函数/正常对照，不声称词法顺序为CFG。

来源门控还需完整literal token→reviewed搜索根→wrapper literal include→同版direct struct字段的源见证；若该额外链不在固定材料中，分开记“检测器形状支持”和“门控来源不足”，不能倒用标准声明。所选标题不一定是长度机制，人工父版复核可能完全无所查形状，如实保存。

完成：固定元数据/暴露审计/选择，真实父版原物及支持/不足卡，两份独立方法与源审阅，核验/封存/停点，今日唯一日志及Windows/WSL待办。支持成立后另冻结实际输入/首站点/规则执行，再决定补丁解封，本轮不自动跨阶段。新确认/独立阳性0，固定12条6/5/1不变；不编译、联网、模型、余额、Word、GitHub。
