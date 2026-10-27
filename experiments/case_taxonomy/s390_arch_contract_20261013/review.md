# R4独立只读复核

2026-10-13，复用`/root/btrfs_source_review`作为独立审阅者。审阅者未执行make、启动或修改材料；主流程保存本记录。

核对范围：四profile实际kernel.config/autoconf.h、commands与ELF/符号日志、主/补充预处理摘录、限定历史来源、构建与补证脚本。最终复核通过，未发现影响本轮窄结论的实质问题。

- 四格实际配置及生成头一致，NR_CPUS=4、目标架构正确；同profile两版仅LOCALVERSION不同。
- 48条命令均attempt1/finished/exit0；14个ELF64 REL目标的架构和大小端正确，目标编译stderr为空。
- 两版同架构公共入口及mask wrapper摘录相同；x86提供者两版相同。
- `notify_cpu_starting`调用CPUHP范围分派，SCHED_STARTING表项绑定`sched_cpu_starting`；首次rq锁集合已经读取SMT mask，随后才进行singleton判断与leader选择。
- x86先准备mask再通知；旧s390先通知，online后更新且按online过滤；修复s390按setup成员资格先更新再通知，并在下线时清online/setup后更新。
- 缓存复用增加revision及限定产物身份核对；88项绑定只属本轮配置/摘录/日志/.i/.o，没有新增make或启动。

可支持：“架构准备阶段与公共首次消费之间的隐含契约失配”。不能据此证明运行时mask、硬件SMT分组、并发安全、真实调度崩溃或检测泛化。产物绑定只能证明材料身份/一致性，不能替代语义或运行证据。

下一项须在同CPU通知入口、SCHED_STARTING及首次锁边界观察mask/self成员资格、online和准备资格，并确认实际到达CPUHP阶段；下线重入另观察清理/重新准备。不能按PID1过滤、以最终sysfs非空或后续无新WARN代替窗口证据。普通双CPU可验证准备契约，共享leader结论仍需实际SMT条件。本项新增内核启动/案例/独立检测阳性均0。
