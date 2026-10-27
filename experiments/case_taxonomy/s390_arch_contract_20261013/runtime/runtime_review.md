# 四组原始运行日志的独立复核

2026-10-13。独立只读复核角色 btrfs_source_review 分别核对四组完整 QEMU stdout/stderr、commands.json、配置/autoconf、ELF材料与 verification.json，未修改文件、构建或启动。

复核结论：四格均为单次启动、退出0、stderr空，PID1与结束记录完整，两CPU最终在线。同架构实际配置仅LOCALVERSION不同，内核与静态PID1架构一致。

CPU1首次消费时四格均online=0、真实CPUHP调度阶段90。旧s390的self=0、实际锁次数0，原告警精确对应观察源码中的`WARN_ON_ONCE(!core_rq)`；修复s390与两版x86均self=1、实际锁次数1、无告警。旧s390在后续online_ready才得到正常mask，最终线程组正常不能替代早期状态。

支持的窄结论为：架构提供者的准备资格和时序不同，经相同公共CPUHP/调度入口传播，造成x86满足首次消费要求，而旧s390暴露缺口；完整修复满足相同要求。s390实际模式是SINGLE、facility=0、mtid=0。本轮不证明真实SMT分组、下线重入、并发安全、崩溃或自动检测泛化。

六种人为误导日志的拒绝仅是验收器核查。日志再解析的数组表示修正没有改内核或增加启动，四次运行仍为同一既有案例。
