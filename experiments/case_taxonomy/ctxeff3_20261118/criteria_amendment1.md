# 判据修订 1（看过开发召回和当前版本对照之后、留出集复测之前写下）

2026-11-18，Claude。

**原因**：按原判据，第三版的开发召回从 2/2 降到 **1/2**（fb1cf0878328^ 漏报），当前版本也丢掉了一条第一版裁定为“可能”的候选（riscv `__kernel_map_pages` 的 X2，已做过动态验证）。两处原因相同：riscv `__kernel_map_pages` 开头是

```c
if (!debug_pagealloc_enabled())
	return;
```

H1 只看条件里是否出现 `debug_pagealloc` 等记号，**没区分方向**。这条语句的意思是“没开 debug_pagealloc 就返回”，真正往下执行的，恰好是开了 debug_pagealloc、在原子上下文里被调用的情况，并不是避让。arm64 的 `if (!linear_map_requires_bbml3 || is_kfence_address(…)) return 0;` 里，`is_kfence_address` 是正向出现的，才是真正的避让。

**改动**：H1 只在上下文谓词**正向出现**时生效：在提前返回的条件里，把条件按 `||` 和 `&&` 拆开，至少有一项含 G1 记号，并且这一项前面没有 `!`。

**说明**：这次改动是看到开发召回下降之后写的。留出集复测还没跑，它仍是独立检验。参考线不变。
