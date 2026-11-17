"""Append one completed-architecture handoff record from measured artifacts."""
import json
from datetime import datetime
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
arch = sys.argv[1]
assert arch in ("riscv", "arm64", "x86_64")
result = json.loads((HERE / f"result_{arch}.json").read_text(encoding="utf-8"))
timings = [json.loads(line) for line in (HERE / "execution/timings.jsonl").read_text().splitlines()]
seconds = sum(t["elapsed_seconds"] for t in timings if t["args"][1] == arch)
if arch == "riscv":
    seconds += sum(t["seconds"] for t in json.loads((HERE / "execution/initial_timings.json").read_text())["batches"])
next_step = {"riscv": "batch.sh scan arm64 --jobs 16 --limit 1024", "arm64": "batch.sh scan x86_64 --jobs 16 --limit 1024", "x86_64": "执行 summarize.py 和 report.py，核验产物并更新交接文档"}[arch]
merge_command = f"merge-staged {arch} 1024（重复至全部完成）" if any(t["args"][:2] == ["merge-staged", arch] for t in timings) else f"merge {arch}"
text = f"""
## {datetime.now():%Y-%m-%d %H:%M} GPT boundary_enum_20261106 {arch} 枚举完成
- 做了什么：前台分批扫描所有 C 单元，逐单元原子落盘并续跑；完成跨单元定义解析、去重及 nm/链接补充。
- 改了哪些文件：{HERE}/{{boundary_{arch}.jsonl.gz,symbols_{arch}.json,units_{arch}.json.gz,object_evidence_{arch}.json.gz,direct_calls_{arch}.jsonl.gz,result_{arch}.json}}；{HERE}/execution/ 下的日志与 timings.jsonl。辅助脚本位于同目录 batch.py、batch.sh、summarize.py、report.py、record_stage.py、monitor.sh；自测额外键回归在 selftest/key_verify.py、key_verify.sh。缓存位于 /root/work/boundary_build/enumeration/{arch}/，摘要见批次日志；内核源码未修改。
- 运行的命令与结果：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_enum_20261106/batch.sh scan {arch} --jobs 16 --limit 1024（重复分批，最后一批自动取余量）；然后同入口 {merge_command}。C 单元成功 {result['parsed_units']}、失败 {result['parse_failed_units']}，边界符号 {result['symbols']}，边界点 {result['points']}。实测执行时间合计 {seconds:.3f} 秒，不含批次间停顿；RISC-V 初始 576 单元不含启动核验时间。
- 种类分布（符号/点）：{json.dumps(result['by_kind'], ensure_ascii=False)}。
- 方向分布（符号/点）：{json.dumps(result['by_direction'], ensure_ascii=False)}。
- nm 补充：{json.dumps(result['object_evidence'], ensure_ascii=False)}。AST 未解析引用 {result['unresolved_refs']}，原因 {json.dumps(result['unresolved_by_reason'], ensure_ascii=False)}；这些未解析项没有冒充零边界。
- 停在哪里：{arch} 扫描与合并完成，架构阶段产物已保存。
- 下一步：{next_step}。所有 WSL 命令仍经第一行 source tools/wsl_env.sh 的 .sh 前台运行。
- 没有验证或不确定的：尚未完成最终三架构产物一致性复核和样本总汇；未解析引用、间接调用目标、未暴露嵌套宏、未编译配置仍属于局限。没有执行三类缺陷检查或模糊测试，没有新确认缺陷。
"""
with (HERE.parents[3] / "进度日志.md").open("a", encoding="utf-8") as stream:
    stream.write(text)
print(text)
