# Btrfs历史内核真实挂载和文件布局对照

2026-10-23，用户在新实验对话明确恢复。详见[本轮结论与下一步](conclusion.md)、[事前协议](protocol_pre.md)、[原始观察汇总](results.json)及[失败准备记录](attempts.md)。

| 页/磁盘扇区 | 请求max_inline | 父版/修复实际值 | 6144与8192字节文件：父版→修复 |
|---|---:|---|---|
| 64K/64K | 8192 | 4096 / 8192 | regular → inline |
| 64K/64K | 2048 | 2048 / 2048 | regular → regular |
| 4K/4K | 8192 | 4096 / 4096 | regular → regular |
| 4K/4K | 2048 | 2048 / 2048 | regular → regular |
| 64K/4K | 2048、8192 | 2048、4096，两版相同 | regular → regular；内核标experimental |

1024字节正常参照在页/扇区相等时均inline，subpage时均regular。共4历史内核构建、6次启动、12次读写挂载、12次只读重挂和36文件，持久读回全部一致。原生max_inline日志与/proc/mounts核对有效值，离线树按inode和文件名确定实际类型；st_blocks不作inline判据。同页两版配置及测试程序相同。

固定父版`0d977e0eba234e01a60bdde27314dc21374201b3`，修复版`6f93e834fa7c5faa0372e46828b4b2a966ac61d7`，均Linux5.14-rc7。内核不加观测补丁；ARM64 QEMU virt/max，1CPU/1GiB，VirtIO块设备，单盘512MiB、nodesize64K、无压缩，关闭free-space-tree。源码由本地Git archive取得。btrfs-progs6.6.3创建磁盘，工具和编译器版本在environment.json。

证据目录相对代码根为`analysis_out/btrfs-mount-resume-20261023/`：commands保留所有命令、耗时、返回码；每格保留config/build.json、boot.log、super.txt、tree.txt、result.json。内核Image和最终磁盘在WSL `/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/`，哈希在构建/结果收据。核验器重新读取原始输出、比较配置并检查Image/磁盘哈希；不是独立评审或独立检测集。

执行入口：`python3 run.py 64 4`，验证：`python3 verify.py`。run.py为本轮固定目录的执行脚本，已有磁盘/boot保留、不覆盖重跑；新重复试验须使用新目录并先登记。恢复已完成格不会新启动该格，不得重计运行次数。

本轮证明固定几何条件下的实际选项与持久布局差异，不测性能，不证明完整生命周期和资源/并发路径，不是CPU ISA对照、自动发现或泛化。下一步先同一修复内核4096/8192直接干预，随后接入受限事实核验和独立评价。模型请求为0；旧模型拒绝记录不变。
