# 组合信号分层与分批初筛计划（2026-09-23）

数据仍是 Linux 主线提交。旧的宽候选列表保留为召回基线；[旧规则审计](AUDIT.md)说明了各条宽规则的命中贡献。新规则先按提交说明与文件路径给候选排序，再从高、中、低层和旧规则未入选层按固定种子抽样，不把静态低分自动当作无关。随后仍由现有 `screen_fast.py` 和 DeepSeek-V4.1-Flash 作短判定，相关、不确定与需复核项按原流程保留；完整分析不在这一步启动。

静态信号 v2：

- 缺陷或退化：`Fixes:`、修复、回归、崩溃、错误结果、性能下降等。`Fixes:` 从完整提交说明读取；版本修订记录不作为架构差异或缺陷证据。
- 架构差异：特定架构条件、位宽、字节序、内存序、页大小等措辞。署名邮箱不作为架构名称；`arch/` 只看真实变更路径。
- 公共层/接口边界：通用路径、回调、能力、假设与通用/架构路径交界等线索。
- 高层要求“缺陷＋明确差异”或“缺陷＋架构＋边界”；中层要求“缺陷＋架构或边界”；其他旧候选进低层。性能退化词可提供缺陷信号；纯性能优化仍留在低层抽样，并未被丢弃。

该规则是线索排序，不能证明提交相关或无关。不要求两个架构名称、不要求同时修改公共层与 `arch/`，也不把后续语义性质词表设为入选门槛。对旧试验的 100 条已见样本作离线回放，v2 将 11 条初判无关项降到低层，未移动 16 条初判相关和 12 条范围待定项；这只是已见样本上的检查，不能证明独立泛化。

在旧审计冻结的 118,997 条候选中，v2 分为高 9,309、中 21,657、低 88,031。WSL 重建日期窗口扫描 404,460 条，而旧审计为 404,475 条；一条旧候选不在 WSL 当前日期窗口，已单独补入候选分层。原未入选对照在本次重扫中分为有修复词 99,629、其他 185,835。对照总体与旧审计不是完全相同的日期窗口，不能据其直接计算旧筛选的漏检率。

已在被 Git 忽略的 `analysis_out/stratified-batches-20260923/` 冻结三批：每批高 100、中 100、低 50、原未入选对照有修复词 13、其他 12，总计 275 条。三批共 825 条，哈希无重复。`manifest.json` 保存种子、版本、旧审计及候选列表 SHA-256、Linux HEAD、总体层大小、批次配额和每条静态信号；`batch-001.txt` 至 `batch-003.txt` 是送入短判定的提交列表。抽样有意不按层大小比例分配，且排除了本地已见样本，结果不能直接推断总体相关率或时间趋势。

在 WSL 中重新生成（完整历史扫描约需数分钟）：

```bash
python experiments/stratified_review/prepare.py \
  --linux-dir /root/repos/linux \
  --outdir analysis_out/stratified-batches-20260923 \
  --signal-version v2 --seed 20260923 \
  --batch-quotas high=100,medium=100,low=50,outside_defect=13,outside_other=12 \
  --batches 3
```

无模型预检已通过，第一批 275 条均能被当前短判定 CLI 读取：

```bash
python screen_fast.py --settings settings.toml \
  --batch-manifest analysis_out/stratified-batches-20260923/manifest.json \
  --batch-number 1 \
  --outdir analysis_out/stratified-batches-20260923/dryrun-batch-001 \
  --plan-only
```

正式调用时使用**新的输出目录**，例如：

```bash
python screen_fast.py --settings settings.toml \
  --batch-manifest analysis_out/stratified-batches-20260923/manifest.json \
  --batch-number 1 \
  --outdir analysis_out/stratified-batches-20260923/deepseek-batch-001 \
  --max-requests 300 --token-budget 2000000 --workers 4
```

预算耗尽或中断时可用同一输出目录恢复；提高请求或 token 上限需要另行核定。不同批次使用不同输出目录。CLI 会拒绝截断批次配额、哈希文件被改动、Linux HEAD 改变或把另一个批次混入同一输出目录；运行目录另存 `batch_source.json`，记录计划和批次指纹、层大小、名义抽样比例。执行时按层轮流派发，使预算中途停止时仍能覆盖五层；冻结文件本身的顺序和成员不变。名义比例以层总体为分母，实际抽样排除了先前已见样本，不应当作总体估计权重。

第一批已按上述预算完成 DeepSeek 短判定和分层抽查，结果及边界案例见 [BATCH1_RESULTS.md](BATCH1_RESULTS.md)。第二、三批随后在相同材料协议下以 16 路并发完成短判定，分别保存在本机 `analysis_out/stratified-batches-20260923/deepseek-batch-002-16w/` 和 `deepseek-batch-003-16w/`；两批均无待处理项，但尚未完成分层源码抽查。并发实验和用量见 [RESULTS.md](../speed_benchmark/RESULTS.md)。
