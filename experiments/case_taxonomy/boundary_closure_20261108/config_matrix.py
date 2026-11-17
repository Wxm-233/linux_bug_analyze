"""A finite, sample-driven build proposal; generating a plan is not building it."""
from common import *

def profile(name,arch,requests,samples,deps,limits='',expect=None,status='planned'):
    return {'name':name,'arch':arch,'requests':requests,'expect':expect or requests.copy(),
            'samples':samples.split(),'dependencies':deps,'remaining_limits':limits,
            'status':status,'olddefconfig_verified':None,'kernel_build_verified':None,
            'output':f'/root/work/boundary_build/closure_20261108_{name}'}

def main():
    c=read(HERE/'evidence/compiler_capabilities.json')
    support={n:git('grep','-n',f'select {n}','--','arch/riscv/Kconfig','arch/arm64/Kconfig','arch/x86/Kconfig',optional=True)
             for n in ('ARCH_SUPPORTS_SHADOW_CALL_STACK','ARCH_SUPPORTS_CFI')}
    write('evidence/architecture_capabilities.json',support)
    profiles=[
      profile('rv64_bpf','riscv',{'BPF_SYSCALL':'y','BPF_JIT':'y'},
              'A039 A065 A086 A195 A211 A277 A278 A301 A305 A321 B435 B590',
              'BPF_SYSCALL selects BPF; BPF_JIT depends on BPF and HAVE_EBPF_JIT/HAVE_CBPF_JIT; RISC-V selects HAVE_EBPF_JIT. 保留解释器以对照JIT不可用分支。',
              'JIT生成指令、arena位宽、内存序需另建模型；旧emit_atomic已演变，不靠配置补名字。',
              expect={'BPF':'y','BPF_SYSCALL':'y','BPF_JIT':'y','HAVE_EBPF_JIT':'y'}),
      profile('rv32_abi','riscv',{'NONPORTABLE':'y','ARCH_RV64I':'n','ARCH_RV32I':'y','BINFMT_FLAT':'y'},
              'A062 A303 B425 B455 B524 B577',
              'RV32需要NONPORTABLE；ARCH_RV32I选择32BIT，PGTABLE_LEVELS默认2；MMU保留y。BINFMT_FLAT依赖ARCH_HAS_BINFMT_FLAT，RISC-V已select。',
              '用RV32展开SC_RISCV_REGS_TO_ARGS和折叠页表；字宽/布局仍需分析，BPF/JIT trampoline不与RV64等价。',
              expect={'ARCH_RV32I':'y','ARCH_RV64I':'n','32BIT':'y','64BIT':'n','MMU':'y','PGTABLE_LEVELS':'2','BINFMT_FLAT':'y'}),
      profile('rv32_nommu','riscv',{'NONPORTABLE':'y','ARCH_RV64I':'n','ARCH_RV32I':'y','MMU':'n','BINFMT_FLAT':'y'},
              'A019 B455', 'RV32与!MMU单独分支；KEXEC/CRASH支持受包围条件控制，不能直接强开CRASH_DUMP证明A019。',
              'A019历史CRASH_DUMP/VMCORE_INFO组合是否当前可满足仍待检查。',expect={'ARCH_RV32I':'y','MMU':'n','BINFMT_FLAT':'y'}),
      profile('rv64_kexec','riscv',{'KEXEC':'y','KEXEC_FILE':'y','CRASH_DUMP':'y','CRYPTO':'y','CRYPTO_SHA256':'y'},
              'A006 A019 A190 A191 A281 A309 A392 A393 B414',
              'KEXEC依赖ARCH_SUPPORTS_KEXEC；KEXEC_FILE依赖ARCH_SUPPORTS_KEXEC_FILE（RISC-V为64BIT且处于MMU分支），选择CRYPTO_LIB_SHA256/KEXEC_CORE；CRASH_DUMP依赖KEXEC_CORE和ARCH_SUPPORTS_CRASH_DUMP。',
              'A006旧CRYPTO=m依赖修复不能用当前单个y配置评估；A392旧函数消失仍需历史映射。'),
      profile('rv64_trace','riscv',{'KPROBES':'y','FUNCTION_TRACER':'y','FUNCTION_GRAPH_TRACER':'y'},
              'A002 A047 A068 A078 A083 A087 A142 A196 A254 B558',
              'HAVE_KPROBES/HAVE_FUNCTION_TRACER/HAVE_FUNCTION_GRAPH_TRACER来自架构；KPROBES→KRETPROBES→KRETPROBE_ON_RETHOOK→RETHOOK。DYNAMIC_FTRACE由依赖和默认值生效。',
              'mcount/rethook汇编、noinstr/__cpuidle和进入/退出上下文仍需段与属性模型。',
              expect={'KPROBES':'y','KRETPROBES':'y','KRETPROBE_ON_RETHOOK':'y','RETHOOK':'y','FUNCTION_TRACER':'y','DYNAMIC_FTRACE':'y','FUNCTION_GRAPH_TRACER':'y'}),
      profile('rv64_mm','riscv',{'TRANSPARENT_HUGEPAGE':'y','MEMORY_HOTPLUG':'y','MEMORY_HOTREMOVE':'y'},
              'A058 A119 A188 A197 A247 A261 A368',
              'THP依赖HAVE_ARCH_TRANSPARENT_HUGEPAGE和!PREEMPT_RT；热插拔依赖64BIT、SPARSEMEM_VMEMMAP、ARCH_ENABLE_MEMORY_HOTPLUG；HOTREMOVE位于HOTPLUG条件内，选择MIGRATION。',
              '同一文件包含不代表宏依赖与分支都恢复；RV32不能套用热插拔配置。'),
      profile('rv64_pagealloc','riscv',{'DEBUG_KERNEL':'y','DEBUG_PAGEALLOC':'y','DEBUG_PAGEALLOC_ENABLE_DEFAULT':'y','HIBERNATION':'n'},
              'A076 A306', 'DEBUG_PAGEALLOC依赖DEBUG_KERNEL；与hibernation的关系依ARCH_SUPPORTS_DEBUG_PAGEALLOC，独立配置主动禁用HIBERNATION。',
              '运行时开关与best_map_size分支需记录。'),
      profile('rv64_kasan','riscv',{'KASAN':'y','KASAN_GENERIC':'y'},'A105',
              'KASAN需架构支持、Clang nosanitize_address能力、SYSFS和!SLUB_TINY；GENERIC选择SLUB_DEBUG/CONSTRUCTORS。',
              '线程栈大小生成值及宏数据依赖未建模；KASAN与KFENCE分成独立实验以便归因。'),
      profile('rv64_kfence','riscv',{'KFENCE':'y'},'A122',
              'KFENCE依赖HAVE_ARCH_KFENCE并选择STACKTRACE/IRQ_WORK；无需强开隐藏HAVE符号。'),
      profile('rv64_ptdump','riscv',{'DEBUG_KERNEL':'y','DEBUG_FS':'y','PTDUMP_DEBUGFS':'y'},'A350',
              'PTDUMP_DEBUGFS依赖DEBUG_KERNEL、DEBUG_FS、ARCH_HAS_PTDUMP，选择PTDUMP。'),
      profile('rv64_rvmon','riscv',{'RV':'y','RV_PER_TASK_MONITORS':'4','RV_MON_RTAPP':'y','RV_MON_SLEEP':'y'},'B519',
              'RV_MON_SLEEP依赖RV、HAVE_SYSCALL_TRACEPOINTS和RV_MON_RTAPP；RTAPP要求RV_PER_TASK_MONITORS>=3，故明确设4。',
              '监控器依赖与执行上下文仍需检查三规则。'),
      profile('rv64_kcfi','riscv',{'CFI':'y'},'A243 B522 B576',
              '当前符号为CFI，CFI_CLANG只是transitional；依赖ARCH_SUPPORTS_CFI及-fsanitize=kcfi（Clang18探测成功）。',
              '用于回调类型/上下文对照，不能代替A243所需用户态RISCV_USER_CFI；B522/B576还需回调流。'),
      profile('rv64_user_cfi','riscv',{'RISCV_USER_CFI':'y'},'A243',
              '需64BIT、MMU、RISCV_ALTERNATIVE以及-march=rv64ima_zicfiss_zicfilp -fcf-protection=full；当前Clang18按Kconfig原样探测失败。',
              '保持阻塞，不添加实验扩展参数、不安装新编译器、不假装开关生效。',status='blocked_existing_compiler' if c['riscv_user_cfi']['exit_code'] else 'planned'),
      profile('rv64_scs','riscv',{'SHADOW_CALL_STACK':'y'},'A013',
              'SHADOW_CALL_STACK依赖ARCH_SUPPORTS_SHADOW_CALL_STACK、MMU，并与FUNCTION_GRAPH_TRACER的动态参数保存能力有关。',
              'RISC-V仅在HAVE_SHADOW_CALL_STACK时选择ARCH_SUPPORTS_SHADOW_CALL_STACK；要核对工具链和架构条件，不能强开隐藏能力。',
              status='blocked_arch_support' if not support['ARCH_SUPPORTS_SHADOW_CALL_STACK'] or 'arch/riscv/Kconfig:' not in support['ARCH_SUPPORTS_SHADOW_CALL_STACK'] else 'planned'),
      profile('rv64_mlx5','riscv',{'NET':'y','NETDEVICES':'y','ETHERNET':'y','INET':'y','PCI':'y','NET_VENDOR_MELLANOX':'y','MLX5_CORE':'y','MLX5_CORE_EN':'y'},
              'B584', 'NET/NETDEVICES/ETHERNET/INET/PCI及Mellanox父菜单；MLX5_CORE另依PTP_1588_CLOCK_OPTIONAL、MLXFW/HWMON/PCI_HYPERV_INTERFACE的tristate约束。',
              '为当前arm64已编译实现补riscv对照；publication race仍需硬件内存序规格。'),
    ]
    # Two matched JIT peers support comparison of the same feature, not a claim of full Cartesian coverage.
    for name,arch in [('arm64_bpf','arm64'),('x86_64_bpf','x86_64')]:
        profiles.append(profile(name,arch,{'BPF_SYSCALL':'y','BPF_JIT':'y'},'A039 A065 A086 A195 A211 A277 A278 A301 B435 B590',
                                '同rv64_bpf的公共BPF/JIT依赖；架构需提供HAVE_EBPF_JIT。','配对比较，不自动映射RISC-V专用函数。'))
    existing=[{'name':'arm64_defconfig','arch':'arm64','samples':['B444','B445','B506','B584'],
               'purpose':'已有输入，不需重建；V2已找到相应修改函数体。IOMMU_DMA是ARM64/X86/S390的def_bool，不能把riscv的RISCV_IOMMU当作同一实现。'},
              {'name':'x86_64_defconfig','arch':'x86_64','samples':['B506'],'purpose':'已有IOMMU_DMA公共实现对照，不需重建。'}]
    audit=read(AUDIT/'sample_miss_analysis.json')['samples']
    a_ids={s['id'] for s in audit if s['primary_category']=='a'}
    covered={s for p in profiles+existing for s in p['samples']}
    assert len(a_ids)==32 and a_ids<=covered,sorted(a_ids-covered)
    label={r['id']:r['check'] for r in read(BASE/'boundary_taxonomy_20261106/labels.json')}
    for p in profiles:
        p['checks']=sorted({label[s] for s in p['samples']})
        p['kconfig_evidence']={n:read(HERE/'evidence/kconfig_stanzas.json').get(n) for n in set(p['requests'])|set(p['expect'])}
    obj={'profiles':profiles,'existing_inputs':existing,'audit_a_count':len(a_ids),
         'audit_a_mapping':{s:[p['name'] for p in profiles+existing if s in p['samples']] for s in sorted(a_ids)},
         'blocked_profiles':[p['name'] for p in profiles if p['status'].startswith('blocked')],
         'limitations':'Finite feature configurations, not all combinations or repair-before trigger coverage.'}
    write('config_matrix.json',obj)
    md=['# 我建议补充的配置矩阵','',
        '这张表表示需要采集的输入，不能将计划或成功开启配置当作样本已覆盖。32条a类均有安排，包括已有arm64/x86输入以及当前版本/编译器不可用的分支。CFI要区分内核kCFI（当前配置名CFI）和RISC-V用户态CFI。','',
        '|配置|架构|请求项|对应样本|依赖与剩余限制|状态|','|---|---|---|---|---|---|']
    for p in profiles:
        md.append('|'+ '|'.join([p['name'],p['arch'],', '.join(f'{k}={v}' for k,v in p['requests'].items()),', '.join(p['samples']),p['dependencies']+' '+p['remaining_limits'],p['status']])+'|')
    md+=['','## 已有输入与逐条对账','']
    md += [f"- {p['name']}：{','.join(p['samples'])}。{p['purpose']}" for p in existing]
    md += ['','32条a类逐条安排：','']+[f"- {s}：{', '.join(names)}" for s,names in obj['audit_a_mapping'].items()]
    md += ['','## 执行规则','',
           '先运行 `config.sh <名称> prepare`，它会做defconfig、scripts/config、olddefconfig并核对全部请求/预期项；失败立即停，不静默删除开关。随后由Claude运行 `config.sh <名称> build`。`list`列出可执行与阻塞项；阻塞项不执行构建。输出仅在新O=目录。',
           '', '我本轮只验证rv64_bpf的olddefconfig，所有其他配置的实际生效和构建结果为null；具体结果见config_validation/。CONFIG_RISCV_USER_CFI的工具链探测失败是已知负结果；不尝试通过修改编译参数绕过Kconfig。']
    (HERE/'config_matrix.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('profiles',len(profiles),'a mapped',len(a_ids),'blocked',obj['blocked_profiles'])

if __name__=='__main__': main()
