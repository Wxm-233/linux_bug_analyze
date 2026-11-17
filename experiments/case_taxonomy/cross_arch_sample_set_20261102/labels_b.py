"""Researcher's labels for the source-B commits (criteria.md section 3), written as data. Output: labels/bB.json."""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
U = '无关'


def R(m, reason, fl=''):
    return [m, 'R', '', '', '', '', fl, reason]


def Z(reason):
    return ['X2', 'R', '', '', '', '', U, reason]


def C(m, k, loc, s, mk, reason, fl=''):
    return [m, 'C', k, loc, s, mk, fl, reason]


L = {
    'B401': R('X2', 'bpf自测缺RISC-V系统调用前缀（测试代码）'), 'B402': R('X2', 'libbpf取系统调用参数（工具代码）'),
    'B403': R('X2', 'bpf自测（测试代码）'), 'B404': R('M5', 'SBI PMU启动计数器时关中断广播'), 'B405': Z('cifs'),
    'B406': R('X2', '工具编译告警', '构建错误'), 'B407': R('X2', '工具编译告警', '构建错误'),
    'B408': R('M7', 'find_first_bit返回值作下标越界'), 'B409': Z('iwlwifi'), 'B410': R('X2', '设备树绑定', '非C代码'),
    'B411': Z('驱动Kconfig依赖'), 'B412': R('X2', 'KVM自测（测试代码）'), 'B413': R('X2', '设备树绑定说明', '非C代码'),
    'B414': C('M8', 'K3', 'kernel/crash_reserve.c（通用crashkernel预留插入资源的时机）', 'S2', '0',
              '改用通用crashkernel预留后，RISC-V与arm64的/proc/iomem父资源消失'),
    'B415': Z('cxl格式符'), 'B416': R('X2', 'cbo自测（测试代码）'), 'B417': R('X1', 'PLIC不能对已屏蔽中断做EOI'),
    'B418': R('M7', 'AX45MP缓存回写未按缓存行对齐'), 'B419': R('X1', 'SBI控制台默认启用', '非C代码'),
    'B420': Z('新增cpu_dcache_is_aliasing接口'), 'B421': R('X1', 'INTC在AIA下的低层处理函数'),
    'B422': R('X1', '旧式PMU能力标志'), 'B423': R('X1', '旧式PMU缺ctr_get_width'), 'B424': R('X1', '初始化时stimecmp无默认值'),
    'B425': C('M8', 'K3', 'include/asm-generic/pgtable-nopmd.h:pud_leaf', 'S2', '0',
              'x86清理时删掉了公共nopmd中的pud_leaf定义，arm64与RISC-V两级页表构建失败', '构建错误'),
    'B426': R('X1', 'RV32上AIA中断32-63'), 'B427': R('X1', 'perf分支采样未支持'), 'B428': R('X2', 'wireguard自测配置'),
    'B429': Z('hexagon链接脚本'), 'B430': Z('BPF验证器arena（与架构无关）'), 'B431': R('X2', 'cbo自测'),
    'B432': C('M9', 'K3', 'init/Kconfig:RUST（与CFI_CLANG互斥）', 'S2', '0',
              '开启CFI_CLANG时加载rust模块崩溃，arm64、RISC-V、x86同', '非C代码'),
    'B433': R('X2', '未用变量告警', '构建错误'), 'B434': R('X1', 'IMSIC未设初始有效亲和性'),
    'B435': C('M7', 'K2', 'arch/x86/net/bpf_jit_comp.c（x86 JIT早有用户地址防护）', 'S1', '4',
              'BPF_PROBE_MEM可能读到用户态地址；x86 JIT自带防护，RISC-V等没有，改由验证器统一加'),
    'B436': Z('LoongArch callchain'), 'B437': R('X2', 'gitignore'), 'B438': R('X2', '合并冲突', '构建错误'),
    'B439': R('X2', '合并冲突', '构建错误'), 'B440': R('M6', 'INTC初始化失败未释放fwnode'), 'B441': R('X2', 'KVM自测', '构建错误'),
    'B442': R('X2', '文档', '非C代码'), 'B443': R('M9', 'clang下AMD显示FP栈帧过大', '构建错误'),
    'B444': C('M7', 'K3', 'include/linux/randomize_kstack.h（各架构熵位过滤）', 'S2', '0',
              '各架构对栈随机化熵的过滤实际减少了混入的位数，RISC-V同'),
    'B445': C('M7', 'K3', 'include/linux/randomize_kstack.h（各架构熵位过滤）', 'S2', '0', '同上（同一补丁另一份）'),
    'B446': C('M10', 'K1', 'arch/parisc/kernel/syscalls/syscall.tbl（compat_sys_io_pgetevents_time64）', 'S1', '4',
              'compat下io_pgetevents须用compat入口做符号扩展；parisc早已修，RISC-V等仍用原生入口'),
    'B447': R('X2', '文档', '非C代码'), 'B448': R('X1', 'SBI PMU溢出时事件数据被覆盖'), 'B449': R('X2', '自测'),
    'B450': R('X2', 'MAINTAINERS', '非C代码'), 'B451': R('X2', 'perf事件名（工具）'), 'B452': R('X2', 'KVM自测', '构建错误'),
    'B453': R('X1', '旧式PMU选计数器未查类型'), 'B454': Z('uretprobe系统调用号'),
    'B455': C('M1', 'K3', 'fs/binfmt_flat.c（不偏移数据段时仍初始化共享库指针数组）', 'S3', '2',
              'RISC-V专用的FLAT变体不留共享库指针空间，公共代码仍写入，破坏代码段末尾'),
    'B456': R('X2', '自测'), 'B457': R('X1', 'APLIC改源配置后需重新触发MSI'), 'B458': R('X2', '自测'),
    'B459': R('X1', 'D1平台PLIC须早探测'), 'B460': R('M6', 'cpuidle-riscv-sbi of_node_put'), 'B461': R('M6', 'APLIC IS_ERR判断'),
    'B462': R('X2', '自测'), 'B463': R('M6', 'K210复位驱动节点泄漏'), 'B464': R('M5', '可抢占上下文中用smp_processor_id'),
    'B465': R('X1', 'JH7110时钟切换'), 'B466': R('X2', '自测'),
    'B467': C('M10', 'K2', 'drivers/perf/arm_pmu.c（不支持的事件类型返回-ENOENT）', 'S1', '0',
              '不支持的perf事件类型应返回-ENOENT，其他实现如此，RISC-V返回别的错误码'),
    'B468': R('X2', '日志文字'), 'B469': R('X2', '自测构建'), 'B470': R('X2', 'libbpf构建'), 'B471': Z('USB驱动Kconfig'),
    'B472': Z('9p构建'), 'B473': Z('sdhci竞争（与架构无关）'), 'B474': R('M7', 'SMP=n时RINTC静态数组按NR_CPUS太小'),
    'B475': Z('iio Kconfig'), 'B476': Z('perf工具'), 'B477': Z('perf工具'), 'B478': R('X2', '宏名'),
    'B479': R('M6', 'APLIC先于IMSIC探测时空指针'), 'B480': R('M6', 'cpuidle节点释放'),
    'B481': Z('fw_devlink中断父节点（与架构无关，在RISC-V板上观察到）'), 'B482': R('X2', '工具构建'), 'B483': R('X2', '自测'),
    'B484': R('M6', '未初始化返回值'),
    'B485': C('M1', 'K3', 'drivers/pci/msi/msi.c:pci_msi_setup_msi_irqs（无父域时走旧式回退并告警）', 'S0', '1',
              '公共PCI/MSI假设没有MSI父域时可走旧式回退，RISC-V用层次化中断域不实现该回退'),
    'B486': Z('hugetlb PMD共享计数（与架构无关）'), 'B487': R('X2', '自测'), 'B488': R('X2', '自测'),
    'B489': R('X2', 'RISC-V IOMMU告警', '构建错误'), 'B490': R('X2', 'cpufreq Kconfig endif位置', '非C代码'),
    'B491': R('X2', 'rseq自测'),
    'B492': C('M10', 'K2', 'arch/arm64/include/asm/memory.h:untagged_addr', 'S1', '2',
              'RISC-V的untagged_addr对数组参数强制转换报错，其他架构不报', '构建错误'),
    'B493': R('X2', '误提交的文件'),
    'B494': C('M7', 'K2', 'drivers/cpuidle/cpuidle-psci.c（同样按possible遍历）', 'S2', '2',
              'cpuidle驱动按possible CPU初始化而CPU设备只按present注册；nosmp时出错'),
    'B495': Z('thinkpad'), 'B496': Z('genirq迁移（ia64）'), 'B497': Z('SLUB_TINY'),
    'B498': C('M8', 'K3', 'scripts/Makefile.vmlinux（剥离.rela.dyn）', 'S3', '1',
              '公共构建剥离了RISC-V可重定位内核运行时需要的.rela.dyn，kexec无法加载', '非C代码'),
    'B499': R('X2', '自测'), 'B500': R('X2', '自测'), 'B501': R('X2', 'COMPILE_TEST构建', '构建错误'), 'B502': R('X2', '自测'),
    'B503': Z('m_can'), 'B504': R('X2', 'Makefile', '非C代码'), 'B505': R('X1', 'IMSIC同步定时器CPU'),
    'B506': C('M8', 'K3', 'drivers/iommu/iommu-pages.c:iommu_put_pages_list（不再逐项删除）', 'S0', '0',
              '公共iommu改动后调用者须自行重置链表，RISC-V IOMMU的栈上链表未跟上'),
    'B507': Z('hisi_sas'), 'B508': R('X2', '设备树绑定', '非C代码'), 'B509': Z('ACPI platform_profile'), 'B510': R('X2', '文档'),
    'B511': R('X1', 'raid6向量汇编缺clobber'), 'B512': Z('ipv6'), 'B513': Z('fscrypt'), 'B514': Z('erofs'), 'B515': Z('nbd'),
    'B516': Z('eventpoll'), 'B517': R('X2', '无用头文件'), 'B518': R('M6', 'IMSIC先解引用后判空'),
    'B519': C('M9', 'K3', 'kernel/trace/rv/monitors（假设存在32位time_t系统调用）', 'S3', '2',
              'RV32只有64位time_t系统调用，公共rv监视器引用了不存在的调用号', '构建错误'),
    'B520': R('X1', 'FFH CPPC错误码'), 'B521': R('M6', 'RISC-V IOMMU空指针'),
    'B522': C('M9', 'K3', 'lib/vdso/datastore.c（总是分配时间数据页）', 'S3', '2', 'RV32不用通用gettimeofday，公共vDSO仍分配时间数据'),
    'B523': Z('arm64 kexec_buf（对应A190）'),
    'B524': C('M7', 'K3', 'kernel/fork.c:copy_sighand（unsigned long标志）', 'S2', '2', 'clone3后标志为64位，公共copy_*在32位架构上截断'),
    'B525': C('M9', 'K3', 'arch/Kconfig:HAVE_CFI_ICALL_NORMALIZE_INTEGERS_RUSTC', 'S2', '0',
              'rustc目标在RISC-V上不支持kcfi，公共配置未检查', '构建错误'),
    'B526': R('X1', 'PLIC中断号0保留'),
    'B527': C('M1', 'K3', 'init/Kconfig:CC_HAS_ASM_GOTO_OUTPUT（测试用x86助记符jmp）', 'S3', '1',
              '公共编译器探测用x86指令助记符，在arm、RISC-V等上误判为不支持', '非C代码'),
    'B528': R('X2', 'Kconfig依赖', '非C代码'), 'B529': Z('工具构建'), 'B530': Z('perf工具'),
    'B531': C('M8', 'K3', 'scripts/Makefile.vmlinux（剥离模块设备表符号）', 'S3', '1',
              '公共modpost改动后，RISC-V可重定位且开KASAN时剥离符号失败', '构建错误'),
    'B532': R('X2', '未用函数告警', '构建错误'), 'B533': R('X2', 'kunit测试跳过'), 'B534': Z('drm NOMMU randconfig'),
    'B535': R('M6', 'INTC缺free回调'), 'B536': R('X2', '工具头文件'), 'B537': R('X1', '向量汇编占用帧指针s0'), 'B538': Z('tee'),
    'B539': R('M9', 'RZ/Five缺select', '非C代码'), 'B540': R('X2', 'gitignore'), 'B541': Z('rtl8xxxu'),
    'B542': R('X2', '设备树绑定', '非C代码'), 'B543': R('M6', 'K230 pinctrl空指针'), 'B544': R('M4', 'RV32分两次写stimecmp须按三步'),
    'B545': R('M9', 'gen-btf在RISC-V+LTO下', '构建错误'), 'B546': R('X2', 'KVM自测'), 'B547': R('X2', '文档'),
    'B548': R('X2', 'Kconfig帮助'), 'B549': Z('perf工具'), 'B550': Z('perf工具'), 'B551': R('M3', 'RISC-V IOMMU更新目录表后须失效缓存'),
    'B552': R('X2', '旧gcc在RISC-V上误报编译期断言', '构建错误'), 'B553': R('X1', 'IOMMU用MSI时无连线中断'),
    'B554': R('M6', 'AX45MP节点引用泄漏'), 'B555': Z('perf工具'), 'B556': R('X1', 'IOMMU命令队列出错仍轮询'),
    'B557': R('M9', 'IOMMU缺GENERIC_MSI_IRQ', '构建错误'),
    'B558': C('M5', 'K1', 'include/linux/randomize_kstack.h（要求关中断关抢占调用）；x86在关中断的退出路径中调用', 'S1', '0',
              '栈随机化偏移按per-cpu维护，要求关中断调用；arm64、LoongArch、RISC-V在开中断时调用'),
    'B559': R('X1', 'RIMT关机顺序'), 'B560': R('X2', '自测'), 'B561': Z('drm imagination'), 'B562': R('M6', 'APLIC探测失败仍清依赖'),
    'B563': R('M6', 'APLIC重复注册syscore'), 'B564': R('M6', 'RPMI邮箱通道泄漏'), 'B565': R('M7', 'IOMMU无符号比较'),
    'B566': R('M7', 'IOMMU失效范围溢出'), 'B567': R('X1', 'APLIC在ACPI下的genpd通知'), 'B568': R('X2', 'KVM自测'),
    'B569': R('X1', 'SG2042根端口ASPM'), 'B570': R('X2', '文档'), 'B571': R('X2', '设备树绑定', '非C代码'), 'B572': Z('kunit'),
    'B573': R('X1', 'IMSIC下线时中断迁移状态'), 'B574': Z('kprobes测试（与架构无关）'), 'B575': R('M7', 'RV32上BIT()不够宽', '构建错误'),
    'B576': C('M1', 'K3', 'sound/core/pcm_lib.c:interleaved_copy（对NULL数据构造iov_iter）', 'S0', '3',
              '公共PCM静音路径构造了无效iov_iter，多数架构碰巧无事，RISC-V空指针'),
    'B577': C('M7', 'K3', 'kernel/trace/ring_buffer.c:rb_calculate_event_length（RB_FORCE_8BYTE_ALIGNMENT）', 'S2', '2',
              '强制8字节对齐的架构事件长度多算4字节'),
    'B578': C('M1', 'K3', 'scripts/sorttable.c（假设mcount地址等于函数符号地址）', 'S3', '1',
              'RISC-V的可修补NOP区在函数符号前8字节，公共排序脚本按符号范围检查出错'),
    'B579': R('X2', 'perf工具寄存器名'),
    'B580': C('M5', 'K3', 'drivers/acpi/processor_idle.c:acpi_idle_lpi_enter（未标__cpuidle）', 'S2', '0',
              'RCU关闭后的LPI进入函数可被跟踪；arm64、RISC-V的ACPI LPI同受影响'),
    'B581': R('M6', 'IMSIC早期初始化fwnode泄漏'), 'B582': R('X1', 'RIMT延迟配置'), 'B583': Z('sun4i定时器'),
    'B584': C('M4', 'K3', 'drivers/net/ethernet/mellanox/mlx5（发布指针无屏障）', 'S2', '3',
              '发布新条目与计数之间无屏障；x86强序遮住，弱序的RISC-V、arm64才出错'),
    'B585': R('X1', 'SpacemiT K3时钟'), 'B586': Z('nova-core GPU中的RISC-V核'), 'B587': Z('nova-core GPU中的RISC-V核'),
    'B588': Z('perf构建'), 'B589': R('X2', 'rseq自测'),
    'B590': C('M9', 'K3', 'kernel/bpf/verifier.c:bpf_do_misc_fixups（依赖JIT内联helper）', 'S2', '2',
              '实现bpf_jit_inlines_helper_call的架构在关闭JIT时helper调用号未改写'),
    'B591': R('M6', 'ACPI依赖未检查返回'), 'B592': R('X1', 'ACPI依赖循环'), 'B593': R('X1', 'ACPI依赖循环终止'),
    'B594': Z('drm imagination'), 'B595': Z('exec循环计数（与架构无关）'), 'B596': Z('自测脚本'), 'B597': Z('s390 BPF（对应A276）'),
    'B598': R('M7', 'MPXY通知长度未校验'), 'B599': Z('LoongArch KVM'), 'B600': Z('LoongArch BPF符号扩展'),
    'B601': Z('LoongArch kprobes'), 'B602': Z('arm64 BPF arena'),
}


def main():
    ids = {i['id'] for i in json.loads((HERE / 'items.json').read_text(encoding='utf-8')) if i['source'] == 'B'}
    assert ids == set(L), ids ^ set(L)
    rows = [[k] + L[k] for k in sorted(L)]
    (HERE / 'labels' / 'bB.json').write_text(json.dumps(rows, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(len(rows), Counter(r[2] for r in rows), sum(r[7] == U for r in rows))


if __name__ == '__main__':
    main()
