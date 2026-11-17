# 判据修订 2（2026-11-09，Claude，样本评估进行中）

## 发生了什么

A196 的修复前版本记为“构建失败”（`results/A196.json`）。查 `build.log` 发现，真正的错误是：

```
llvm-ar: error: arch/riscv/kernel/built-in.a: No such file or directory
make[4]: *** [scripts/Makefile.build:473: arch/riscv/built-in.a] Error 123
```

`eval_samples.py` 把修复文件所在的目录 `arch/riscv/kernel/probes/` 和范围目录 `arch/riscv/` 同时作为 make 目标。两个目标互相包含，并行构建时会抢着做：打包 `arch/riscv/built-in.a` 时，`arch/riscv/kernel/built-in.a` 还没生成。

这是我脚本的错误，不是这个内核版本本身编不过。判据第五节“构建失败就扣除、交给用户”针对的是后一种，所以不适用：应当修正后重跑。

## 修订条目

1. `eval_samples.py` 的 `fix_dirs`：已经落在第二节范围目录之内的修复目录，不再单独作为 make 目标。这些目录照样会被构建（它们在范围目录里），也照样在收集范围内，因为 `scope_list.py` 收集的是范围目录及其子目录下的全部 `.c`。
2. 删除 A196 的这次结果和构建目录，重跑。
3. 其余已完成的样本都构建成功（`status.txt` 为 success），所有单元解析干净（防护没有拦），结果有效，不重跑。它们也有修复目录与范围目录重叠的情况，但没有发生这个竞争错误，产物完整。

## 不变的部分

判据第三至六节、样本、命中规则、参考线全部不变。
