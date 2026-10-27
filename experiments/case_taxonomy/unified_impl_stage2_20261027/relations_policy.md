# 第二阶段复现用关系登记

2026-10-27。本文件登记复现专用检查器结论时使用的v2关系，供账本引用。关系沿用各原轮已审核的语义，只改变表达方式，不新增规范主张。

- SMMU qtest：观测资格为“请求按 payload写→读回→基址配置→使能→使能确认→PROD写→状态读 的顺序出现，无未登记请求，各类计数符合布局，回复与读回无异常，消费者状态受支持”；关系为“保留编码命令数为0”。资格不成立判不足，不判违反。原专用检查器：smmu_review_20261026/checker.py。
- virtio普通split：每个对象代次内 attempt→map/bypass→barrier→publish→add_ok→used→unmap→token→cpu_read 有序、至多一次，失败路径 attempt→map_fail→add_fail；publish与add_fail、add_ok与add_fail互斥；代次不重叠；cpu_read/publish/add_ok/used/token触发相应前置完整；route=0只用bypass且无map/unmap，route≠0需map与unmap。资格为可解析、存在FINAL且尝试/映射/解除映射/读取/屏障计数与FINAL一致。原专用检查器：virtio_add_recycle_20261027/checker.py。
- SPARC编译对象（compiled_object层）：NR_CPUS>64时IRQ栈循环界与possible计数宽度均为运行时nr_cpu_ids，≤64时均为常数64，且预处理展开一致。原专用检查器：sparc_identity_objects_20261027/check_objects.py。
- 算术：virtio事件组首字节对齐到维护粒度且组末不晚于锁所在维护行起点（floor_to）；Btrfs有效上限等于min(请求, 离线磁盘几何)。原结论：virtio_platform_qualification_20261027/runtime_results.json、btrfs_method_20261026/results.json。
