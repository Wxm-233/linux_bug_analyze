# 召回样本的挖掘（判据四.5）

在 `v5.10..df2908090cda` 里，用 `git log -G` 找改动行里含有三组接口的修复提交（带 `Fixes:` 标签，或标题含 fix），并且同时新增了 present、none、softleaf 判断，或者改换了接口：SW（交换项接口）命中 20 个，MG（通用修改接口）命中 30 个（`mine_raw.txt`）。

逐个读了标题可疑的十几个提交的改动。只有一个属于“接口用错了项”：

- **`8f34f1eac382` mm/userfaultfd: fix uffd-wp special cases for fork()**：第 2 点说，`copy_huge_pmd()` 在分流迁移项 PMD 之前，就对 PMD 调用了只对 present 项有定义的 `pmd_clear_uffd_wp`（MG 组）；修复改成在迁移项分支里用 `pmd_swp_clear_uffd_wp`。

其余都不属于这一类：
- 漏带过软脏位或 uffd 位：`75cb1cca2c88`、`9658d698a8a8`、`14a762dd1977`、`099dd6878b9b`、`44f86392bdd1`、`0cef0bb836e3`；
- 语义调整：`27da93d8e6d5`、`f1eb1bacfba9`、`1462c52e9f2b`、`0e88904cb700`；
- 并发竞争：`c70dce4982ce`、`c11d34fa139e`；
- sparc64、loongarch 上 `pte_mkdirty` 会带上写位的架构语义问题：`624a2c94f5b7`、`e833bc50340`、`96a9c287e25d`。这是跨架构差异，但不是用错了项；
- 已经在 P1 召回集里（R 组）：`43e7f189769c`、`bf983108be0e`、`65529295607f`；
- 其余是新功能或重构。

旧版本里接口的名字不同（`*_uffd_wp`），召回时按改名对应到现在的 `*_uffd`（`xvdom.py` 的 `OLD`）。
