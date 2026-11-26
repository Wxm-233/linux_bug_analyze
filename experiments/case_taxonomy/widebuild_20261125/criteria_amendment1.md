# 判据修订 1：配置项可用性改为“allyesconfig 并上实际构建的配置”；改正一个校准用例的文件名（widebuild_20261125）

2026-11-25，Claude。**本修订写于第一次运行、看到结果之后。**

## 发现的问题

1. **G1 配置校准 7/8**：`TRANSPARENT_HUGEPAGE` 被判成了“只在部分架构上有”的配置项，因为 arm 的 allyesconfig 里根本没有它。查原因：
   - arm 的 allyesconfig 打开了 `ARCH_MULTI_V6`，ARMv6 不支持 LPAE；
   - 没有 LPAE 就不会选上 `HAVE_ARCH_TRANSPARENT_HUGEPAGE`，THP 这一项也就不会出现。

   可我们实际的 arm 构建（multi_v7 + LPAE）是开着 THP 的。也就是说，allyesconfig 只是每个架构的一个配置样本。对原来三个架构，它大致等于“这个架构能开的全部配置”；对 arm，它少了一整支（LPAE）。

   第一轮的规则原意是“这个架构能不能开这一项”。只看 allyesconfig，会把“这个样本里没开”当成“这个架构开不了”。这样连带的后果是：THP 下面所有 `#ifdef` 都会被算成架构相关，G2 里新增的大量标签变化，有一大部分来自这里。
2. **G1 新增第 6 项写错了文件**：`kmap_local_page` 定义在 `include/linux/highmem-internal.h`，不在 `highmem.h`。这是我写判据时的错误，函数本身没有问题。

## 修订

1. 每个架构“有哪些配置项”，改为它的 allyesconfig **并上**本轮这个架构的实际构建配置（`out/.config` 里出现过的符号）。“架构相关配置项”的定义不变：这些架构中，有的有、有的没有。
2. G1 新增第 6 项改为 `include/linux/highmem-internal.h` 中的 `kmap_local_page`，要求“至少被 arm 编入”不变。
3. 其余规则和关口都不变。

预处理记行与配置判定无关，不重跑；重跑的是配置判定、分层和核对三步。第一次的结果保留为 `*_run1.*`。
