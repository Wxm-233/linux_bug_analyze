# 验证疑点：RISC-V `patch_map`在`STRICT_MODULE_RWX`关闭时写不进BPF代码区（判据，构建之前写定）

## 疑点

来自`patch_rules_v2_20261105/`的模型审查，经我对照代码核实：
- 终点版本`df2908090cda`中，RISC-V的`patch_map`只在`IS_ENABLED(CONFIG_STRICT_MODULE_RWX)`时，才对vmalloc地址取页并建立fixmap映射，否则直接返回原地址；
- BPF的pack在`alloc_new_pack`中被`set_memory_rox`设成只读；
- 上游`2c9e5d4a0082`去掉了`BPF_JIT`对`MODULES`的依赖，而`STRICT_MODULE_RWX`依赖`MODULES`；
- arm64出过同样的问题，修复`b1480ed230ac`把判断改为`CONFIG_EXECMEM`。

**推断**：关闭`MODULES`时，RISC-V的`bpf_arch_text_copy`写入只读区失败，`bpf_jit_binary_pack_finalize`返回错误，每个BPF程序都会JIT失败，退回解释器执行，并且内核报警告。

## 一、三个内核

都从`df2908090cda`用`git archive`取源码，不改动内核仓库。配置都在`defconfig`的基础上打开`BPF_JIT`。

| 名称 | `MODULES` | 源码改动 | 预期 |
| --- | --- | --- | --- |
| **observe** | 关 | 无 | 疑点成立时：JIT失败 |
| **control** | 开（`STRICT_MODULE_RWX`随之开启） | 无 | JIT成功 |
| **fixed** | 关 | `patch_map`中`IS_ENABLED(CONFIG_STRICT_MODULE_RWX)`改为`IS_ENABLED(CONFIG_EXECMEM)`，与arm64的修复相同 | JIT成功 |

构建后记录`.config`中`MODULES`、`STRICT_MODULE_RWX`、`EXECMEM`、`BPF_JIT`、`BPF_SYSCALL`的取值。取值与上表不符时，停下来报告，不运行。

## 二、运行

QEMU riscv64 virt，4个核，1GB内存，用initramfs启动。`/init`是静态编译的测试程序，做以下几步：
1. 挂载`/proc`，把`/proc/sys/net/core/bpf_jit_enable`设为1；
2. 用`bpf()`系统调用加载一个最简单的socket filter程序（`r0 = 0; exit`），共加载3次；
3. 每次加载后，用`BPF_OBJ_GET_INFO_BY_FD`读出`jited_prog_len`，打印出来；
4. 关闭这些程序（会触发释放路径），等待1秒，然后关机。

控制台日志保存在`logs/<名称>.log`。

## 三、判定（看结果之前写定）

- **疑点成立**：同时满足以下三条——
  - observe中3次加载都成功，但`jited_prog_len`都为0，或者内核在JIT或释放路径上报出`WARNING`；
  - control中`jited_prog_len`都大于0，且没有上述警告；
  - fixed中`jited_prog_len`都大于0，且没有上述警告。
- **疑点不成立**：observe中`jited_prog_len`大于0，且没有警告。
- 其他情况，例如加载失败、启动失败、control也失败，记为“判断不了”，照实报告原因，本轮不改测试再试。

## 四、其他规定

- 只在本地运行。补丁只记录在本目录，不提交，不对外报告。
- 构建和运行各只做一次，不自动重试。
- 收尾用`round_close`。
