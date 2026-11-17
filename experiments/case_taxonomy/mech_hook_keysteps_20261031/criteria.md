# 方法一第二版：只比较有语义的关键步骤（判据，实现前写定）

## 背景

方法一第一版（`mech_hook_consensus_20261031/`）以公共钩子为锚，比较所有架构的实现。结果如下：

- 回溯召回只有10%，判为无用；
- 但多数做法的补上率是对照的3.3倍，召回到的都是真问题；
- 主要问题是拿全部调用名比较，混进了大量写法差异，例如`pte_val`、`kfree`、内联汇编。

大页上有效的比较，比的是少数有语义的关键步骤，例如“先清空并刷新”“区分是否在内存”。本版只比较一小组**事先定义好的约定步骤类别**，并且按类别比较，而不按名字比较。这样，“RISC-V用`local_flush_tlb_page`、别人用`flush_tlb_page`”会被视为同一类步骤，不算缺失。

## 关键步骤词表（事先写定）

每类既看调用名（函数或宏），也看函数体中的汇编助记符（出现在字符串里）。

| 类别 | 调用名（正则） | 汇编助记符 |
| --- | --- | --- |
| K1 内存屏障与原子 | `smp_(r\|w)?mb\w*`、`(r\|w)?mb`、`dma_(r\|w)?mb`、`\w*_acquire`、`\w*_release`、`(try_)?cmpxchg\w*`、`xchg\w*`、`atomic\w*_(xchg\|cmpxchg\|fetch_\w+\|add_return\w*\|sub_return\w*\|inc_return\w*\|dec_return\w*)` | `fence`、`dmb`、`dsb`、`mfence`、`sfence`、`lfence`、`lwsync`、`hwsync`、`eieio`、`membar`、`amoswap`、`lr\.`、`sc\.` |
| K2 TLB与缓存刷新 | `(local_)?flush_tlb\w*`、`__flush_tlb\w*`、`flush_(i\|d)?cache\w*`、`__flush_(i\|d)?cache\w*`、`update_mmu_cache\w*`、`tlb_flush\w*`、`sync_icache\w*`、`flush_icache\w*` | `sfence\.vma`、`tlbi`、`invlpg`、`tlbie`、`ic\s+ivau`、`dc\s+c` |
| K3 有效性与存在检查 | `\w+_present`、`\w+_none`、`\w+_bad`、`pfn_valid`、`virt_addr_valid`、`access_ok`、`\w+_leaf` | — |
| K4 加锁、关中断与上下文保护 | `(raw_)?spin_(try)?lock\w*`、`(raw_)?spin_unlock\w*`、`mutex_(try)?lock\w*`、`mutex_unlock`、`local_irq_\w+`、`preempt_disable\w*`、`preempt_enable\w*`、`rcu_read_(un)?lock\w*`、`mmap_\w*lock\w*`、`local_bh_\w+`、`lockdep_assert\w*`、`guard`、`scoped_guard`、`ftrace_test_recursion_\w+`、`(down\|up)_(read\|write)\w*` | — |
| K5 释放与引用计数 | `k(v)?free\w*`、`vfree`、`(__)?free_pages?\w*`、`put_page`、`folio_put\w*`、`\w+_put`、`put_\w+`、`memblock_free\w*`、`(early_)?memunmap`、`iounmap` | — |

## 定义

- **钩子**：与第一版相同。即RISC-V和另外至少3个架构都有同名函数定义、并且公共代码引用的函数名。
- **实现的步骤类别**：函数体，加上**两层**同文件被调函数，其中出现的上述类别。比第一版多展开一层。
- **多数类别**：在实现该钩子的其他架构中，至少50%、且不少于3个架构的实现含有的类别。
- **标记**：RISC-V的实现不含某个多数类别，记一条“钩子×类别”。
- **少数类别（对照）**：只有1到2个其他架构含有、RISC-V不含的类别。

## 评价（与第一版相同）

1. **回溯召回（主指标）**：
   - 真值：v5.10到终点之间，带`Fixes:`的RISC-V提交中，修复后某个钩子的RISC-V实现**新含有**某个类别，而修复前没有。每个“提交×钩子×类别”算一条。
   - 召回：修复前这个类别已经是该钩子多数类别的比例。
2. **v6.6标记的去向**：v6.6的多数类别标记，到终点时RISC-V补上的比例，与少数类别对照。
3. **当前代码**：终点版本的全部多数类别标记。不超过40条时全部人工核对，否则用`random.Random(20261031)`抽40条。归为三类：
   - (a) 疑似RISC-V该做而未做；
   - (b) 有合理原因；
   - (c) 判断不了。

   (a)类只记录、不对外报告；如有，优先安排运行验证。

## 事先写定的判断标准

- **有用**：回溯召回≥30%，**并且**v6.6标记的补上比例≥10%、且至少是对照的2倍，**并且**终点标记不超过60条。
- **无用**：召回<15%，或补上比例不高于对照。
- **介于两者之间**：分析原因。
- 真值少于15条时，召回只作描述。

## 不做的事

- 不调用模型，不构建或运行内核，不对外报告。
