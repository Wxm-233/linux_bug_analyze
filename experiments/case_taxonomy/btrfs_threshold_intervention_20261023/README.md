# Btrfs阈值直接干预和事实适配器

2026-10-23。[执行前协议](protocol_pre.md)、[结论/限制/下一项](conclusion.md)、[程序提取结果](results.json)。

复用上一轮修复版ARM64/64K内核，在相同空白磁盘的两个克隆上按相反顺序测试max_inline=4096/8192。2次新启动、4读写挂载、4只读重挂、28文件；持久读回一致，两个顺序的布局相同。

| 文件长度 | max_inline=4096 | max_inline=8192 |
|---|---|---|
| 1024、4095、4096 | inline | inline |
| 4097、6144、8192 | regular | inline |
| 8193 | regular | regular |

同一内核仅改变阈值即可产生所测差异，支持此前版本差异的阈值机制解释；不是逐行补丁消融，也未验证资源压力/并发/性能。

新增代码根`linux_bug_analyze/btrfs_runtime_facts.py`，用于有限实验输出的事实提取：UUID、root5、挂载区间、inode/文件名/长度、持久读回和extent联合核对。原始输入的hash及树行号随事实保存。人工给定判据和程序提取值分列，精确消费时刻及完整路径继续不足；尚未接通通用契约核心，不冒充N1自动推导或N2自动选配。

`analyze.py`同时重提旧六格36记录，旧运行不计新增。10个内存损坏证据控制全部拒判。新28+旧36是事实记录量，不是64个样本。正式独立正/正常仍0/0。

原始证据在代码根`analysis_out/btrfs-threshold-intervention-20261023/`，manifest记录Image、config、initrd、源文件和磁盘身份；commands保存全部调用。WSL缓存为`/root/.cache/linux-bug-analyze/btrfs-threshold-intervention-20261023/`。`python3 run.py`为一次性执行入口，完成manifest存在时拒绝覆盖；`python3 analyze.py`重新核验归档，不启动内核。

研究者选定的有效上限参照使用真实磁盘几何；这不会证明程序已自动知道何时应读取哪个fs_info。只观察effective=4096不足以倒推出消费时cache=4096（例如request=4096会掩盖差异）。下一步先明确并冻结源码到事实的绑定协议，再决定能进入通用核心的证据范围。
