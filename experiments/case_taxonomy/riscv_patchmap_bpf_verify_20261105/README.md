# 验证疑点：RISC-V `patch_map`在`STRICT_MODULE_RWX`关闭时写不进BPF代码区

## 结论

**疑点成立，已在QEMU中运行确认。** 在终点版本`df2908090cda`上：
- 关闭`MODULES`、打开`BPF_JIT`时，RISC-V的BPF JIT对每个程序都失败，内核每次报一条`WARNING`，程序退回解释器执行；
- 打开`MODULES`时正常；
- 按arm64的修复改一行之后，关闭`MODULES`也正常。

这是此前用规则和复核没有发现、在第二部分审查迁移补丁时由模型带出的问题，属于**M8 演进落后**：公共代码去掉了`BPF_JIT`对`MODULES`的依赖（`2c9e5d4a0082`），arm64随后修了`patch_map`（`b1480ed230ac`），RISC-V没有跟上。

按约定只在本地记录，没有对外报告。另外，本机内核仓库只到`df2908090cda`，之后上游有没有修过，我没有查（需要下载）。

## 疑点的来历

`patch_rules_v2_20261105/`中，模型审查prog_pack迁移补丁时指出：`patch_map`只在`IS_ENABLED(CONFIG_STRICT_MODULE_RWX)`时，才给vmalloc地址建立可写的fixmap映射，否则直接返回原地址；而BPF的pack已经被`set_memory_rox`设成只读。

我对照代码核实了：
- `STRICT_MODULE_RWX`依赖`MODULES`；
- `2c9e5d4a0082`之后，`BPF_JIT`不再依赖`MODULES`；
- arm64在同样配置下出过问题，修复把判断改为`CONFIG_EXECMEM`；
- RISC-V终点版本仍是旧写法。

| 文件 | 说明 | SHA |
| --- | --- | --- |
| `criteria.md` | 判据，构建之前写定 | 见`criteria_sha256.txt` |
| `bpf_test.c` | initramfs中的`/init`：打开JIT，加载3次最简单的socket filter，读出`jited_prog_len` | 同上 |
| `build.sh`、`fixed.patch` | 构建三个内核；修复版只改`patch_map`中的一行 | 同上 |
| `run.sh` → `logs/` | QEMU运行，4个核，1GB内存 | 见`delivery_manifest.json` |
| `extract.py` → `results.json` | 从日志中提取结果并按判据判定 | 同上 |

## 三个内核

都从`df2908090cda`用`git archive`取源码，在`defconfig`基础上打开`BPF_JIT`。构建后的配置与判据一致：

| 名称 | `MODULES` | `STRICT_MODULE_RWX` | `EXECMEM` | 源码改动 |
| --- | --- | --- | --- | --- |
| observe | 关 | 关 | 开 | 无 |
| control | 开 | 开 | 开 | 无 |
| fixed | 关 | 关 | 开 | `patch_map`中`IS_ENABLED(CONFIG_STRICT_MODULE_RWX)`改为`IS_ENABLED(CONFIG_EXECMEM)` |

## 运行结果

| 名称 | 3次加载 | `jited_prog_len` | 内核警告 |
| --- | --- | --- | --- |
| **observe** | 都成功 | **0, 0, 0**（没有JIT，退回解释器） | **3条**：`WARNING: arch/riscv/net/bpf_jit_core.c:156 at bpf_int_jit_compile`，调用栈为`bpf_prog_load` → `bpf_check` → `bpf_int_jit_compile` |
| control | 都成功 | 34, 34, 34 | 无 |
| fixed | 都成功 | 34, 34, 34 | 无 |

第156行是`WARN_ON(bpf_jit_binary_pack_finalize(...))`：finalize要通过`bpf_arch_text_copy`把代码写进只读的pack，而`patch_map`没有建立可写映射，写入失败。

按判据第三节，三条同时满足，记为“疑点成立”。

**说明**：串口日志中，内核消息和测试程序的输出交错在一起。`extract.py`先去掉内核消息（`[时间] ...`），再读测试程序的输出；警告按原始日志计数。

## 影响

- **触发条件**：RISC-V内核打开`BPF_JIT`，同时关闭`MODULES`，或者在`ARCH_OPTIONAL_KERNEL_RWX`下手动关闭`STRICT_MODULE_RWX`。
- **后果**：
  - 所有BPF程序都不能JIT，只能用解释器执行，性能下降；
  - 每加载一个程序报一次警告，开启`panic_on_warn`的系统会因此崩溃；
  - 如果同时开启`BPF_JIT_ALWAYS_ON`，没有解释器可退，程序会加载失败（按代码推断，本轮没有运行这种配置）。
- **修复**：与arm64相同，改一行即可（`fixed.patch`），本轮已运行确认有效。

## 对研究的意义（只作描述）

- 这个缺陷是在**第二部分**审查一组迁移补丁时，由模型带出的**第一部分**问题：迁移补丁调用了`patch_map`，审查材料按固定规则附上了它的实现，模型对照`set_memory_rox`看出了矛盾。两部分接起来之后，检查补丁时也能顺带检查补丁所依赖的已有代码。
- 它是一个典型的“公共改动—参照架构跟进—RISC-V未跟进”的M8案例，有上游的参照修复，修法可以直接照搬。这也再次符合M8的修复策略：查各架构对同一约定的实现，照先跟上的架构改。
- 此前此项目中经运行确认的RISC-V缺陷有两个（NAPOT大页清除、`machine_shutdown`），这是第三个。

## 统计

模型调用0次；构建3次（每个内核1次）；QEMU运行3次；新确认缺陷1（RISC-V `patch_map`，只在本地记录，未对外报告）；新疑点0。
