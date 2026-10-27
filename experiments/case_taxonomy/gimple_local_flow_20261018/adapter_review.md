# N2.12 适配器冻结前审查（2026-10-18）

只读 `run_real_sources.py`、`compare_source_checks.py` 和已登记协议；未读 `reference/source_truth_checks.json` 或任何新方法结果。运行适配器将固定两片段的原文字节、身份和绑定摘要传给方法，不传预期事件/契约；首个结果文件禁止覆盖。比较器只在事后读取独立角色的 source-truth 检查，用于既知开发源码的忠实度复核，不能形成 Linux 泛化率。

冻结前有三项小边界应关闭或明确限制：

1. 比较器读取 `program_results.json` 后，还应核其中 `method_baseline_sha256` 与当前 baseline 一致、profile 集恰为协议中的两项、各项 `input_sha256`/`binding_sha256` 与协议一致。现有代码只记录结果文件摘要，未核被比较 packet 自身身份；若文件替换或过期会使来源绑定变弱。
2. `selected()` 当前只以 source line 锚定，不含源路径。若不同源文件同号注解共存，应支持路径精确匹配或将此查询判不足；否则行号相同可能误选。`relevant_opaque` 的相关范围也应与同一源位置一致。`event_count` 在有相关 opaque 且观察数不超过预期时保守不足是合理的，不能为提高通过数删去 opaque。
3. `label()` 对 GCC 定义式 `<D.80225>:` 不能归一到 `D.80225`，应以有限规范测试 `D.80225`、`<D.80225>`、`<D.80225>:`，只修文本形式，不用相似名称替代精确目标事件绑定。当前 explicit-edge 比较的是显示目标集合，不含 true/false 极性、可达性或未知调用的返回保证。

依赖检查的 BFS 固定于 use 的 region，且“unresolved”要求同一 use event 与相关变量，方向较保守；最终还需核方法是否真的在 call/asm/label/store 等屏障切断 region，不能只由比较器补救方法的跨屏障错误。

复核修订版：上述三项具体边界已关闭。`compare_source_checks.py` 现核 method baseline、恰好两项协议输入、每项原文与 binding 的 SHA；`selected` 和 opaque 关联支持源路径并对无路径歧义保守判不足；`label` 可有限归一 GCC 尖括号及末尾冒号。`adapter_development_reviewed.json` 记录六项合成适配器测试通过。这只确认比较器的身份/锚点边界；真实 GIMPLE 事实仍须方法生成后核对，显式边不含极性与可达性。
