# 第二步：审查 R1 的 QEMU 动态验证（不是盲判）

你在上一步对 R1（arm LPAE 迁移项页帧号截断）的判断与第一审查人一致。第一审查人另外在 QEMU 上做过动态验证，现在请你**挑这个实验的毛病**：找出可能让结论不成立的设计漏洞、混淆因素或日志里对不上的地方。仍然只读、只判断，不需要写利用代码或补丁。

## 可以读（本步起解除对它的限制）

- `experiments/case_taxonomy/lpaeqemu_20261122/` 整个目录：`README.md`（第一审查人的结论）、`criteria.md`、`criteria_amendment1.md`、`init.c`、`run.sh`、`build.sh`、`kernel_nohighpte.config`、`kernel_base.config`、`logs/`（正式结果是 `logs/run_nohighpte_test.log`、`logs/run_nohighpte_ctrl.log`，其余是诊断）。
- 内核源码同上一步（`df2908090cda`）。
- 其余“不要读”的限制照旧（`claude_review.json`、主文件夹的交接文档/进度日志/日志、封存材料、`模型调用测试/codex/` 运行记录）。

## 请回答

1. 实验组的失败（拆分后 pagemap 仍是交换类条目、`leafops.h:400` 告警、进程卡在 `migration_entry_wait`）能否用“迁移项页帧号被截断”以外的原因解释？例如：`mem=` 造成的内存空洞、关掉 `HIGHPTE`、`VMSPLIT_2G`、flatmem 的 `mem_map` 跨度、QEMU 本身的问题、第二段内存只有 512MB 等。对照组能排除哪些、排除不了哪些？
2. 日志里的数值是否自洽：拆分前的页帧号、拆分后 pagemap 条目（例如 `0x600000000001401e`）解码出的类型和偏移、与“截断到 24 位”的预测是否一致？请自己解码核对。
3. 第一审查人在调试中发现 `HIGHPTE=y` 时 4GB 以上的用户页会让 exec 缺页死循环，于是关掉了 `HIGHPTE`。这会不会影响结论的适用范围？
4. 如果要让结论更硬，你建议补做什么对照（只说设计，不用实现）？
5. 总评：确认 / 基本确认（有可补的漏洞）/ 不能确认，并给理由。

## 输出

写到 `experiments/case_taxonomy/swaprev_20261122/review/codex_qemu_review.md`（结构按上面 5 点），并在 `experiments/codex_worklog.md` 追加一行。
