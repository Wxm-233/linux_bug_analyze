# 交给Claude执行的命令

我已完成已有数据的匹配和3层内部调用闭包；不要重新运行旧轮的汇总覆盖产物。以下命令均由新脚本进入WSL，第一行source环境脚本，前台执行，不使用nohup或后台符号。每完成一项追加外层日志，实质性失败停下交用户。

## 1. 先构建已验证的新配置

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv64_bpf build --jobs 20
```

它只使用新的 `O=/root/work/boundary_build/closure_20261108_rv64_bpf`，构建成功后生成compile_commands.json与本轮build_validation记录。没有构建成功，不运行依赖它的扫描。

## 2. 其余配置逐项准备再构建

先读 `config_matrix.md`，用list核对状态：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh list
```

对下列15个未验证、未阻塞名称逐个执行prepare；只有请求值全部生效，才执行build：`rv32_abi`、`rv32_nommu`、`rv64_kexec`、`rv64_trace`、`rv64_mm`、`rv64_pagealloc`、`rv64_kasan`、`rv64_kfence`、`rv64_ptdump`、`rv64_rvmon`、`rv64_kcfi`、`rv64_scs`、`rv64_mlx5`、`arm64_bpf`、`x86_64_bpf`。例如：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv32_abi prepare
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/config.sh rv32_abi build --jobs 20
```

`rv64_user_cfi` 由于当前Clang18按原始Kconfig能力测试失败而阻塞，不执行它，不改编译器参数绕过，不安装软件。SCS和其他配置的生效尚未验证，准备失败时也不能强开隐藏HAVE符号。

## 3. 宏/回调原型的全量证据采集

下面每条每批最多扫512个未缓存单元，以4个worker并行，同一命令前台重复，直到complete。`--limit`只控制本批单元数，不控制内存中的并行数量；每个单元独立进程、原子落盘，可续跑。Claude无单条命令时限，512个单元可减少反复启动与校验缓存的开销。三个架构依次前台执行，不同时启动三批。

有-j20后台构建的情况下，建议先用 `--jobs 4`。最终4个riscv验证单元中，单worker峰值约269MiB（VmHWM），预处理子进程约142MiB；保守相加约411MiB/worker，16份约6.4GiB。采样整个验证进程树峰值915MiB，系统MemAvailable最低12.95GiB。按样本大小16份能容纳，但未测大单元和arm64，不能据此保证全量安全，也没有实际运行16worker。后台构建结束后，可先用 `--jobs 8 --limit 32` 观察大单元资源，再决定是否扩大；当前交接命令统一保留已验证的4。原型自测17项、调度自测15项通过，真实4TU标准化存储元数据后逐字段相同、轨迹解压字节相同，jobs4为142.9秒、jobs1为433.5秒。详见 [并行验证记录](parallel_validation.md)。全量耗时/磁盘规模仍为null。

代码已改变输入摘要：旧17个riscv缓存仍在 `prototype_scan/riscv_defconfig/34db2d428b48bd340af614ad9ecb1f9e437e721f5cb572cffd7fb6c2bb07c828/`，不得删除或复制到新摘要下。新代码从新目录开始，同版代码更改jobs/limit不改变摘要。真实4单元对照放在 `evidence/parallel/real/`，未混入生产扫描缓存。

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh riscv --jobs 4 --limit 512
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh arm64 --jobs 4 --limit 512
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh x86_64 --jobs 4 --limit 512
```

相应架构全部完成后分别汇总：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py riscv
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py arm64
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py x86_64
```

rv64_bpf构建成功后，还可采集对应的新配置证据并在complete后汇总：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/prototype_batch.sh riscv --profile rv64_bpf --jobs 4 --limit 512
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh prototype_summary.py riscv --profile rv64_bpf
```

其他配置替换profile并使用匹配arch。每次在本轮目录形成新摘要缓存，不写旧轮、不复用不兼容检查点。扫描失败会保存失败状态，停止派发，等待在途worker完成落盘后非零退出；已完成结果保留，下次遇到失败记录仍停止。不要删除失败记录后自动重试。精确预处理器事件、指针数据流，以及把新配置边界池/宏/回调与样本匹配统一的工具还需后续开发，不能把这里的类型候选数当作新边界全集或缺陷数。

## 4. 可重跑的小验证

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh selftest_match.py
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh selftest_closure.py
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh selftest_prototype.py
```

本轮无需重跑这三项：已通过，除非后续代码改变或出现新问题。`verify_round.py`用于最终静态和跨产物对账。
