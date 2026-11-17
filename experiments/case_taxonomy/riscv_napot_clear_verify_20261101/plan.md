# RISC-V NAPOT大页清除不在内存的表项：运行验证（方案与判定标准，运行前写定）

## 要验证的疑点

来源：`mech_state_size_inventory_20261101/README.md`，读代码所得。

终点版本`df2908090cda`中，RISC-V的`huge_pte_clear`和`huge_ptep_get_and_clear`先用`pte_napot(表项内容)`判断是不是NAPOT大页。不在内存的表项（swap项、迁移项、标记项）不带NAPOT位，所以只清第一个表项。而`set_huge_pte_at`对不在内存的表项会按大小参数写满整组。

推测：一个64KB的NAPOT大页被写成中毒标记后解除映射，会留下15个残留标记。

## 环境

- 源码：`git archive df2908090cda`解出的独立目录，不改动`/root/repos/linux`。
- 构建：`riscv64-linux-gnu-gcc`，`defconfig`，另开`CONFIG_USERFAULTFD`；`CONFIG_HUGETLBFS`与`CONFIG_RISCV_ISA_SVNAPOT`在defconfig中已开启，构建后核对`.config`。
- 运行：QEMU 8.2 `virt`机型，`-cpu rv64,svnapot=on`，1GB内存；内核参数`hugepagesz=64K hugepages=16`。
- 用户态：一个静态链接的测试程序作为initramfs中的`/init`，跑完后关机。

## 测试程序

在一个按2MB对齐的地址A附近，保证测试区所在的页表页一直存在：A处保留一段普通匿名映射，并先访问一次，让它和测试区共用同一张页表。

| 场景 | 步骤 | 关注点 |
| --- | --- | --- |
| P（疑点，解除映射路径） | 在A+64K映射一个64KB的hugetlb页（`MAP_HUGETLB\|MAP_HUGE_64KB`）；登记userfaultfd，用`UFFDIO_POISON`写入中毒标记；`munmap`；再在同一地址用`MAP_FIXED`建64KB普通匿名映射，逐个读16个4KB页 | 读到零还是收到SIGBUS |
| M（疑点，mremap路径） | 同P，但写入标记后不`munmap`，而用`mremap`把这64KB移到别处；再在原地址建普通映射，逐个读16个4KB页 | 同上 |
| C（对照，在内存的大页） | 同P，但不写标记，而是先写一次让大页真正分配，再`munmap`，建普通映射，读16页 | 应全部读到零，检验测试程序本身 |

每个场景前，程序先核对64KB大页确实可用（`/sys/kernel/mm/hugepages/hugepages-64kB`存在，`mmap`成功）。场景P和M在写标记后，还先读一次大页本身，确认标记生效（应收到SIGBUS）。

另构建一个**对照内核**：只去掉这两个函数中的`pte_napot`门槛，与arm64的`49c87f76`一致，即无条件按大小参数处理整组。补丁原样存入本目录。

## 判定标准（事先写定）

- **疑点成立**：原版内核上，场景P或M中第2到16页至少有一页收到SIGBUS；同时场景C全部读到零；并且对照内核上P、M的16页全部读到零。
- **疑点被否定**：原版内核上，场景P、M的16页全部读到零。
- **无法判定**：前提检查失败（64KB大页不可用、`UFFDIO_POISON`不可用、标记没有生效），或场景C出现异常，或对照内核仍有SIGBUS。这时如实记录，不改场景硬凑结果。

只运行一次。不因结果不理想而改方案；若必须改，作为修订写进本文件并说明原因。

## 不做的事

不调用模型，不对外报告。即使疑点成立，也只记录，是否向上游报告由用户决定。
