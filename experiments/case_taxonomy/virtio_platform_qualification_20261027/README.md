# virtio平台可行性与真实ARM64 guest运行

## 10月27日 最新进展：virtio可行性核查后补齐四格真实guest证据

用户追问转CPU的目的后，纠正“阶段评审后直接切换”的依据不足：本轮先实际核查virtio关键补证的成本和平台能力，并执行当前环境可做的部分。20逻辑CPU、约16GiB内存及可用磁盘支持最小构建；旧Btrfs缓存仅5.14且VIRTIO_INPUT关闭，不能替当前6.19案例。没有停留在目录整理或继续堆局部替身。

从固定父版db191ba0c8564ff84877e5b1c9553e991feca239归档完整源码，在独立/root/.cache/linux-bug-analyze/virtio-platform-20261027构建ARM64/4K最小内核，启用原virtio-input/evdev/MMIO，加入只读布局/平台/映射/回收日志。核实修复95c7b0ad6c69d1c0608ff0bbd358a546856beaf3仅改该driver的头文件和组首尾标注，完整应用后用同配置增量构建。原/修复镜像及vmlinux均保留，探针diff及SHA公开；printk改变时序，不能用来证明并发安全。两次成功Image构建，另一次make调用因显式gen_init_cpio目标不被新版支持而失败并保留；三次前置守卫/锚点假设修正不算内核缺陷。

QEMU8.2.2 virt/cortex-a57运行父/修复×ACCESS_PLATFORM关/开四格，均完成QMP注入A按下/释放→virtio-input真实接收4个事件→evdev用户态4项读回→正常关机。客体内核为6.19.0-rc2-lba-virtio-platform。关闭access时观察到bypass，无unmap；开启时普通DMA API、custom=0、父设备ops=NULL，配置无IOMMU支持，为direct分支提供配置/源码依据；返回DMA地址与原SG guest物理地址一致，且观察到unmap后读取再映射。地址域是guest虚拟/物理，不是宿主硬件DMA。该有限队列读回不是完整所有权生命周期或所有后端安全证明。

真实ARM64布局：旧sizeof744、align8、evts[224,736)、lock736；修复sizeof896、align128、evts[256,768)、lock768。四格实际基址满足所需对齐，raw/safe CTR均0x8444c004，DminLine步长64、CWG64、dma_get_cache_alignment64，ARCH_DMA_MINALIGN128和KMALLOC_MINALIGN8单列。由此当前四格的ABI/基址/CTR/协商特性不再只有宿主替身假设；仅限这一配置，不扩到全部ARM64。

关键适用性：四格父设备dma_coherent=1，旧布局几何共享而修复隔离，两者事件功能都正常。此为已读开发案例的coherent正常控制，不是旧代码在非一致平台也安全的证明。此前“没有真实virtio设备路径运行”的描述从本轮起过时；现在有真实guest内核及QEMU虚拟设备路径，仍没有物理DMA或非一致缓存损坏证据。

平台成本和边界已有依据：同版QEMU上游target/arm/helper.c 5107—5135将DC_IVAC/CVAC/CIVAC登记为ARM_CP_NOP，并明确不模拟缓存。当前WSL x86+QEMU TCG路线不能填补该非一致缓存效果缺口；移除DT coherent标志只改变guest分支，不产生所需缓存模型。上游参考https://raw.githubusercontent.com/qemu/qemu/v8.2.2/target/arm/helper.c；本机Ubuntu发行构建并非已核同blob源码，不伪称全二进制来源证明。剩余目标需合格非一致DMA平台，或明确实现该缓存/设备交互的验证环境，当前尚未取得。

新增实际guest日志适配器绑定镜像/config/console SHA，核布局指针、协商与route、64项初始map/4项回收再map、QMP接受及用户态事件。4格均通过，6种错镜像、缺unmap、顺序、对象基址、access矛盾及缺释放事件控制均拒判，共10次assess。它只支持本轮登记探针，不是通用trace语义；whole_path保持非一致契约不足。整个程序运行7次QEMU：4格有效；2次初始无显式串口虽exit0但无可用观察/未注入，1次挂载目录并发读日志errno61中断，全部保留而不算有效格。改为ext4采集后归档解决观察器问题。

下一步决策：现在有根据将“当前环境可补的真实guest路径”与“需不同缓存效果平台的缺口”分开。virtio继续挂账非一致硬件/并发、其他布局/后端及独立评价；可转既有CPU来源资格/版本政策机制，且该切换依据是本轮平台实测和能力边界，不是仅因阶段文档写完。后续若有合格平台再恢复目标效果实验，不继续增加相同TCG组合。表示/R3暂缓、VT-d后置不变。Kimi长任务输出限制仍单独挂账，本轮无付费模型调用。

统计与证据：2次成功内核Image构建、1个PID1编译、4格合格guest运行，另3次观察器失败/不足单列；0个新Linux缺陷，独立正例/正常0/0。linux_bug_analyze/experiments/case_taxonomy/virtio_platform_qualification_20261027/保存构建/探针/镜像身份、四格console与receipt、checker/runtime_results、controls、platform_capability及失败原件；WSL cache位置见delivery_manifest。规划、当日日志、待办、进展和交接同轮更新，三份WSL镜像以notes_sync成功收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

