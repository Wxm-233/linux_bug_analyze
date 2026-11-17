# 编码表核对

## 与 p1dyn 实测对照

- S1 arm64 pmd_young(写迁移项)=1：编码表 1，对
- S1 arm64 pmd_dirty(写迁移项)=0：编码表 0，对
- S1 riscv pmd_young(写迁移项)=0：编码表 0，对
- S1 riscv pmd_dirty(写迁移项)=1：编码表 1，对
- S1 x86_64 pmd_young(写迁移项)=0：编码表 0，对
- S1 x86_64 pmd_dirty(写迁移项)=1：编码表 1，对
- S2 arm64 pte_mkold 改变 device-exclusive：编码表 1，对
- S2 riscv pte_young(device-exclusive)=0：编码表 0，对
- S2 x86_64 pte_young(device-exclusive)=0：编码表 0，对
- S2 x86_64 pte_mkold 不改变 device-exclusive：编码表 0，对

合计 10/10（判据的 6 项实测展开为 10 个具体值）

## P1 样本出错的架构

- 26e7888a0c89 loongarch pmd_leaf 对迁移项 PMD 读成 1：解释得了；各架构 {'x86_64': [], 'arm64': [], 'riscv': [], 'loongarch': ['mig_r', 'mig_w', 'dp_w'], 'powerpc': ['mig_r', 'mig_w', 'dp_w'], 's390': [], 'arm': [], 'mips': []}
- 43e7f189769c x86_64 pmd_write 对带软脏的 device-private PMD 读成 1：解释得了；各架构 {'x86_64': [1, 'unknown'], 'arm64': [0, 0], 'riscv': ['unknown', 0], 'loongarch': [0, 0], 'powerpc': [0, 0], 's390': [0, 0], 'arm': ['n/a', 'n/a'], 'mips': ['n/a', 'n/a']}
- bd1f2b2ace84 x86_64 pte_write 对带软脏的 device-exclusive 读成 1：解释得了；各架构 {'x86_64': [1, 1], 'arm64': [0, 0], 'riscv': ['unknown', 0], 'loongarch': [0, 0], 'powerpc': [1, 0], 's390': [1, 1], 'arm': ['n/a', 'n/a'], 'mips': ['n/a', 'n/a']}
- 65529295607f 同上（try_to_unmap_one 的 pte_dirty/pte_pfn）：解释得了；各架构 {'x86_64': [1, 0], 'arm64': [0, 'unknown'], 'riscv': ['unknown', 'unknown'], 'loongarch': [0, 0], 'powerpc': [0, 1], 's390': [1, 1], 'arm': ['n/a', 'n/a'], 'mips': ['n/a', 'n/a']}
- 3faa3ebc89c1 arm64 pte_mkold 改变 device-exclusive：解释得了；各架构 {'x86_64': 0, 'arm64': 1, 'riscv': 0, 'loongarch': 0, 'powerpc': 0, 's390': 0, 'arm': 'n/a', 'mips': 'n/a'}

合计 5/5
