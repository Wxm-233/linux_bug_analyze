"""Assign each of the 135 cross-architecture samples (cross == 'C' in
cross_arch_sample_set_20261102/labels_v2_1.json) to one refined boundary-mismatch class, and record whether the three
checks of 跨架构缺陷bug Fuzz.docx (type consistency / implementation completeness / call context) cover it.
Judged by me from each sample's recorded reason, one primary class per sample. No model calls.
Output: labels.json, stats.json.
"""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'

CLASSES = {
    'V1': '值-位宽与符号', 'V2': '值-取值域', 'V3': '值-编码与布局', 'V4': '值-单位、基准与对齐',
    'P1': '前置-输入检查', 'P2': '前置-输入类别与含义', 'P3': '前置-对象已初始化',
    'Q1': '后置-空实现或常量', 'Q2': '后置-写缺失', 'Q3': '后置-公共调用缺失或实参不同', 'Q4': '后置-返回值集合',
    'E1': '环境-执行上下文', 'E2': '环境-硬件状态维护', 'E3': '环境-原子性与内存序', 'E4': '环境-阶段与步骤顺序',
    'B1': '绑定-Kconfig依赖', 'B2': '绑定-能力与默认实现选择', 'B3': '绑定-定义缺失',
    'T': '构建与工具链（不属运行时语义失配）',
}

# id: (class, doc check that covers it: 'type' / 'impl' / 'ctx' / '', note)
L = {
    # M1
    'A003': ('V2', '', '默认is_trap_insn认得的指令集合不含c.ebreak'),
    'A036': ('V2', '', '默认实现只处理PMD/PUD大小，不含NAPOT大小'),
    'A044': ('V2', '', '同上'),
    'A047': ('B2', '', '默认实现依赖__builtin_return_address(n>0)这一能力'),
    'A057': ('V2', '', '默认按单页算叶子大小'),
    'A089': ('V2', '', '架构常量ILLEGAL_POINTER_VALUE取默认值0'),
    'A115': ('P2', '', '__pa只接受线性映射地址，传入的是fixmap地址'),
    'A174': ('P2', '', '__pa传入percpu地址（可能在vmalloc区）'),
    'A200': ('V2', '', 'pgprot_dmacoherent默认取值不适合Svpbmt'),
    'A328': ('P2', '', '__pa传入fixmap地址'),
    'B455': ('V2', '', '配置使偏移为0，公共代码仍按留有空间写入'),
    'B485': ('Q1', 'impl', '架构不实现旧式回退'),
    'B498': ('T', '', '构建剥离.rela.dyn'),
    'B527': ('T', '', '编译器探测用x86助记符'),
    'B531': ('T', '', 'modpost剥离符号'),
    'B576': ('P2', '', '传入无效iov_iter，RISC-V实现解引用'),
    'B578': ('T', '', '排序脚本'),
    # M10
    'A013': ('E4', '', '影子调用栈须在开MMU后、进C前装载'),
    'A025': ('Q2', 'ctx', '恢复权限时没清执行位'),
    'A026': ('P1', 'ctx', 'arm64对.exit.text地址有判断，RISC-V没有'),
    'A043': ('Q2', 'ctx', '没清空批次CPU集合'),
    'A091': ('E4', '', 'IPI开启所处的CPU上线阶段'),
    'A101': ('Q4', '', '返回的映射上界语义不同'),
    'A112': ('Q3', 'ctx', '调用early_ioremap而非early_memremap'),
    'A113': ('T', '', 'vDSO编译选项'),
    'A155': ('Q3', 'ctx', '没登记保留区资源'),
    'A167': ('T', '', '内联汇编约束'),
    'A196': ('P1', 'ctx', '校验探测地址的方式不同'),
    'A202': ('E1', '', '回溯他任务栈须关KASAN检查（可插桩性）'),
    'A243': ('Q2', 'ctx', '架构提供的regset描述缺note名字段'),
    'A251': ('T', '', 'sigreturn跳板指令布局'),
    'A254': ('Q2', 'ctx', '跳板没把原始sp写入pt_regs（汇编）'),
    'A255': ('T', '', 'vDSO与LTO'),
    'A299': ('E4', '', '信号返回中恢复向量状态的先后'),
    'A301': ('Q3', 'ctx', 'JIT没生成调用统计函数'),
    'A310': ('Q2', 'ctx', '没把a0初值写成-ENOSYS'),
    'A336': ('Q3', 'ctx', '调用公共perf接口时实参disabled不同'),
    'A368': ('P1', 'ctx', 'arm64在脏页记录时不用大页，RISC-V没判断'),
    'A387': ('Q2', 'ctx', 'KVM_SET_GUEST_DEBUG没设置对应状态'),
    'B467': ('Q4', '', '返回错误码集合与其他实现不同'),
    'B492': ('T', '', '编译错误'),
    # M2
    'A143': ('P1', 'ctx', 'arm64先判断表项存在，RISC-V没有'),
    # M3
    'A029': ('E2', '', '释放页表须刷TLB'),
    'A035': ('E2', '', '先清后写并刷新'),
    'A042': ('E2', '', '释放页表须刷TLB'),
    'A055': ('E2', '', '先清后写无法满足'),
    'A078': ('E2', '', '改写代码后刷指令缓存'),
    'A087': ('E2', '', '同上'),
    'A094': ('E2', '', '同上'),
    'A162': ('E2', '', '同上'),
    'A380': ('Q2', '', '写保护只覆盖部分表项'),
    # M4
    'A046': ('E3', '', '切换mm须有完全屏障'),
    'A081': ('E3', '', 'xchg须完全有序'),
    'A188': ('E3', '', '取出并清空须原子'),
    'A197': ('E3', '', '同上'),
    'A305': ('E3', '', 'JIT生成的原子操作须完全有序'),
    'A321': ('E3', '', '同上'),
    'A350': ('E1', '', '遍历时须持有热插拔锁'),
    'B584': ('E3', '', '公共驱动缺屏障，没有显式边界（隐式依赖硬件内存模型）'),
    # M5
    'A002': ('E1', '', '异常入口不可被探测'),
    'A068': ('E1', '', 'RCU关闭时不可插桩'),
    'A069': ('E1', '', '使用期间不可迁移'),
    'A076': ('E1', '', '原子上下文中取睡眠锁'),
    'A083': ('E1', '', '不可插桩'),
    'A102': ('E1', '', '未开MMU时不可插桩'),
    'A118': ('E1', '', '异常处理中不可睡眠'),
    'A122': ('E1', '', '关中断时不能发IPI'),
    'A158': ('E1', '', '关中断访问用户内存'),
    'A175': ('E1', '', '须开中断'),
    'A309': ('E1', '', '中断上下文死锁'),
    'A327': ('E1', '', '关中断取mutex'),
    'A344': ('E1', '', '须开中断'),
    'B558': ('E1', '', '要求关中断调用'),
    'B580': ('E1', '', 'RCU关闭后不可跟踪'),
    # M6
    'A119': ('P3', '', '对象没构造过就调析构'),
    'A288': ('Q3', 'ctx', '调用公共分配时缺VM_FLUSH_RESET_PERMS'),
    'A339': ('E4', '', '卸载先后与公共kvm_exit'),
    'B414': ('E4', '', '资源插入早于父资源出现'),
    # M7
    'A027': ('V2', '', '常量与实际写入条数不一致'),
    'A058': ('V4', '', 'vmemmap基准没减内存起点'),
    'A062': ('V1', 'type', 'RV32上64位参数按类型截取'),
    'A065': ('V3', '', '零扩展与符号扩展约定'),
    'A079': ('V3', '', '栈顶须留出pt_regs的布局'),
    'A085': ('Q3', 'ctx', '没从memblock去掉线性映射外的内存'),
    'A123': ('V4', '', 'vmemmap基准对齐'),
    'A171': ('V2', '', 'TASK_SIZE_MAX取值'),
    'A181': ('V1', 'type', '写入宽度取自值的类型'),
    'A192': ('V1', 'type', 'u64传给unsigned long'),
    'A195': ('V3', '', '返回值符号扩展约定'),
    'A215': ('P1', 'ctx', '下标没做推测越界防护'),
    'A225': ('P1', 'ctx', '同上'),
    'A241': ('V3', '', 'MMIO有符号读的扩展'),
    'A247': ('P1', 'ctx', 'hugetlb路径缺边界检查'),
    'A261': ('V4', '', '对齐单位混用'),
    'A277': ('V3', '', '1、2字节参数符号扩展'),
    'A281': ('V4', '', '入口对齐'),
    'A303': ('V2', '', '末页地址落在ERR_PTR取值范围'),
    'A398': ('P1', 'ctx', 'memslot边界检查与其他架构不同'),
    'B435': ('P1', 'ctx', 'x86 JIT有用户地址防护，RISC-V没有'),
    'B444': ('V2', '', '架构过滤使随机偏移取值范围变小'),
    'B445': ('V2', '', '同上'),
    'B446': ('V3', '', 'compat入口的符号扩展'),
    'B494': ('P2', '', '公共按possible CPU，设备只按present注册'),
    'B524': ('V1', 'type', 'u64截断'),
    'B577': ('V4', '', '强制8字节对齐的长度'),
    # M8
    'A032': ('Q2', '', '缺页重试须写FAULT_FLAG_TRIED；所有架构同时漏，没有可对照的实现'),
    'A039': ('P1', 'ctx', 'x86按标志区分，RISC-V按func_addr区分'),
    'A086': ('V2', '', '试算大小与实际生成大小须一致'),
    'A106': ('T', '', 'EFI头标志'),
    'A142': ('V3', '', '返回桩栈布局须按ftrace_regs（汇编）'),
    'A190': ('P3', '', '架构调用公共函数前没初始化新字段'),
    'A191': ('P3', '', '同上'),
    'A211': ('P2', '', '标志含义被改错'),
    'A213': ('T', '', 'kbuild'),
    'A274': ('Q1', 'impl', '钩子退回返回0的桩'),
    'A313': ('V2', '', '公共返回值新增VM_FAULT_SIGSEGV，架构处理的取值集合不含它'),
    'A359': ('P2', '', 'vm_pgoff含义改变'),
    'A379': ('E4', '', 'sparse_init后移，早期使用时尚未就绪'),
    'A392': ('Q3', 'ctx', '没排除低端区间'),
    'A393': ('P1', 'ctx', '公共流程能处理空缓冲区，私有实现不能'),
    'B506': ('P3', '', '调用公共函数后须重置链表才能再用'),
    # M9
    'A006': ('B1', '', 'kexec_file与CRYPTO依赖'),
    'A019': ('B3', '', 'nommu下VA_BITS未定义'),
    'A034': ('B1', '', '没选INTERVAL_TREE'),
    'A105': ('B1', '', 'KASAN时栈大小'),
    'A238': ('T', '', '汇编函数CFI类型'),
    'A278': ('B2', '', '需要128位cmpxchg能力'),
    'A292': ('T', '', '编译器asm goto能力'),
    'A306': ('B2', '', 'debug_pagealloc要求页粒度映射'),
    'B425': ('B3', '', '两级页表下pud_leaf定义缺失'),
    'B432': ('T', '', 'rust与CFI'),
    'B519': ('B3', '', 'RV32不存在的系统调用号'),
    'B522': ('B1', '', '时间数据未按配置屏蔽'),
    'B525': ('T', '', 'rustc不支持kcfi'),
    'B590': ('B2', '', '关闭JIT时没有内联能力'),
}


# The user keeps exactly three checks (2026-11-06). Each refined class is folded into one of them:
# 1 data passed across the boundary, 2 what each implementation does, 3 the state in which the call happens.
CHECK_OF = {'V1': 1, 'V2': 1, 'V3': 1, 'V4': 1, 'P2': 1,
            'P1': 2, 'Q1': 2, 'Q2': 2, 'Q3': 2, 'Q4': 2, 'E2': 2, 'E3': 2, 'B1': 2, 'B2': 2, 'B3': 2,
            'E1': 3, 'E4': 3, 'P3': 3, 'T': 0}
# E4 normally concerns the phase at which a call happens; A299 is the order of steps inside one implementation.
CHECK_OVERRIDE = {'A299': 2}


def main():
    rows = [x for x in json.loads(SRC.read_text(encoding='utf-8')) if x['cross'] == 'C']
    assert {x['id'] for x in rows} == set(L), set(L) ^ {x['id'] for x in rows}
    out = []
    for x in rows:
        cls, doc, note = L[x['id']]
        assert cls in CLASSES and doc in ('', 'type', 'impl', 'ctx')
        out.append({'id': x['id'], 'commit': x['commit'], 'subject': x['subject'], 'mechanism': x['mechanism'],
                    'counterpart_kind': x['counterpart_kind'], 'class': cls,
                    'check': CHECK_OVERRIDE.get(x['id'], CHECK_OF[cls]), 'doc_check': doc, 'note': note})
    by_cls = Counter(r['class'] for r in out)
    stats = {
        'total': len(out),
        'by_check': {str(k): v for k, v in sorted(Counter(r['check'] for r in out).items())},
        'check_x_class': {str(k): dict(Counter(r['class'] for r in out if r['check'] == k)) for k in (1, 2, 3)},
        'by_class': {c: by_cls[c] for c in CLASSES},
        'by_group': {g: sum(by_cls[c] for c in CLASSES if c[0] == g) for g in 'VPQEBT'},
        'doc_checks': dict(Counter(r['doc_check'] or 'none' for r in out)),
        'mechanism_x_class': {m: dict(Counter(r['class'] for r in out if r['mechanism'] == m))
                              for m in sorted({r['mechanism'] for r in out}, key=lambda s: int(s[1:]))},
    }
    (HERE / 'labels.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == '__main__':
    main()
