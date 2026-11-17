"""Part 1 (criteria.md): the researcher's label for each of the 121 single-function RISC-V fixes, in the order of
candidates_dump.txt (sorted by date), with C (requirement shared with common code or another architecture) or R
(RISC-V only) and a one-line reason. Output: labels.json and a printed summary.
"""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
L = [
    ('X1', 'R', 'kprobe模拟指令写x0'), ('M1', 'C', '页表级数名按编译期级数，RISC-V运行时降级'),
    ('M7', 'C', 'kexec入口须按启动协议对齐（arm64同有）'), ('X1', 'R', '未对齐访问测速重复探测'),
    ('X1', 'R', 'DT中禁用hart的hartid读取'), ('M7', 'R', 'strncat差一'), ('X1', 'R', '压缩指令解码（OpenSBI同修）'),
    ('X2', 'R', 'sparse注解'), ('M1', 'R', 'lm_alias只适用于内核映射'),
    ('M6', 'C', '卸载模块须恢复线性映射权限（x86、arm64同用VM_FLUSH_RESET_PERMS）'), ('X2', 'R', '缩进'),
    ('M7', 'R', 'sizeof层级错'), ('M6', 'R', 'kfree顺序致释放后使用'), ('M9', 'C', '编译器asm goto输出支持'),
    ('X2', 'R', 'sparse类型'), ('X2', 'R', 'sparse类型'), ('X1', 'R', 'online与present'), ('X2', 'R', '日志级别'),
    ('X1', 'R', 'APLIC读语义'), ('X1', 'R', 'APLIC写语义'),
    ('X1', 'C', '信号返回恢复向量状态的顺序（arm64 FPSIMD惰性状态有同类规则）'), ('M7', 'R', 'GENMASK(-1)'),
    ('X1', 'C', 'BPF trampoline运行统计（arm64 JIT同类修复）'), ('X1', 'R', 'PMU重复计数'),
    ('M7', 'C', '32位末页与ERR_PTR重叠（公共约定）'), ('X1', 'R', '子集检查下标'),
    ('M4', 'C', 'BPF原子操作须完全有序'), ('M9', 'C', 'debug_pagealloc须页粒度线性映射（arm64同）'),
    ('X2', 'R', '标签名'), ('X2', 'R', '误合入后回退'), ('M5', 'C', '中断上下文中kexec崩溃路径死锁（说明中对比arm64）'),
    ('X1', 'C', '系统调用号为-1时a0须为-ENOSYS（公共ptrace约定）'), ('M7', 'R', '栈帧对齐'), ('X1', 'R', '内部扩展被丢'),
    ('M8', 'C', '公共缺页代码返回VM_FAULT_SIGSEGV须由架构处理'), ('X1', 'R', 'sbiret初始化'), ('M7', 'R', '数组下标-1'),
    ('M6', 'R', '释放前访问致空指针'), ('M9', 'R', 'nommu配置'), ('M6', 'R', 'of_node引用'), ('X2', 'R', '格式符'),
    ('X1', 'R', '热插拔CPU的未对齐检查'), ('M4', 'C', 'BPF CMPXCHG须完全有序'), ('X1', 'R', 'APLIC'),
    ('X2', 'R', '弃用API'), ('M7', 'R', '数组越界'), ('M7', 'R', '指针算术宽度'), ('X1', 'R', 'csr_write与csr_set'),
    ('M5', 'C', '早期启动关中断时不能取mutex'), ('M1', 'R', '__pa只适用于线性映射（dtb在fixmap）'),
    ('M9', 'R', '替代补丁前就用扩展检查'), ('X1', 'R', '信号帧大小'), ('M7', 'R', 'bitmap比较越界'),
    ('X1', 'R', 'SBI错误码'), ('X1', 'R', 'SBI IPI'), ('X1', 'R', 'HSM状态'), ('M6', 'R', '未释放页'),
    ('X1', 'C', 'perf计数器创建时须禁用（arm64 KVM PMU同）'), ('X1', 'R', '向量未对齐探测'),
    ('X2', 'R', '原子改非原子，无功能问题'), ('M6', 'C', '卸载顺序须与公共kvm_exit一致'), ('X1', 'R', '重定位类型'),
    ('X1', 'R', 'smstateen复位'), ('X1', 'R', 'PLT条目'), ('M7', 'R', '重定位越界'),
    ('M5', 'C', '来自用户态的陷入处理中访问用户内存须开中断'), ('M9', 'R', '无Supm扩展'), ('M9', 'R', '无Supm扩展'),
    ('M4', 'R', '锁错了对象'), ('X1', 'R', 'SBI HFENCE'), ('X1', 'R', 'SBI SFENCE'), ('X1', 'R', 'vstimecmp'),
    ('M7', 'R', '符号扩展'), ('M7', 'R', '栈缓冲区溢出'), ('X1', 'R', 'G-stage IO映射属性'), ('X2', 'R', '日志'),
    ('M5', 'R', 'vCPU迁移后读错CPU的CSR'), ('X2', 'R', '不可达的未初始化'), ('M9', 'R', 'DT缺属性'),
    ('M8', 'C', '公共vfio改变vm_pgoff语义'), ('M6', 'R', 'kvrealloc失败泄漏'), ('M9', 'R', '固件SRST'),
    ('X2', 'R', '冗余赋值'), ('M4', 'R', 'RV32两次写64位CSR'), ('M6', 'R', '状态未初始化'), ('M6', 'R', '状态未初始化'),
    ('M6', 'R', '状态未初始化'), ('M6', 'R', '缺锁致释放后使用'), ('X1', 'C', '脏页记录时须强制页粒度（arm64 KVM同）'),
    ('M6', 'R', '状态未初始化'), ('M7', 'R', '差一'), ('M6', 'R', '缺锁致释放后使用'), ('M7', 'R', '对齐校验'),
    ('M6', 'R', '缺锁致释放后使用'), ('M7', 'R', 'RV32地址'), ('M6', 'R', '分配失败泄漏'), ('M6', 'R', '双重释放'),
    ('M7', 'R', '整数溢出'), ('X1', 'R', 'pmm状态'), ('M8', 'C', '公共sparse_init后移（arm64同修8d09e2d569f6）'),
    ('M3', 'C', '大页写保护须覆盖整块'), ('M7', 'R', '移位越界'), ('X2', 'R', '&&与&'), ('M9', 'R', 'CFI vDSO'),
    ('X1', 'R', 'SBI错误'), ('X1', 'R', 'SBI错误'), ('X1', 'R', '不存在的vcpu'),
    ('X1', 'C', 'KVM_SET_GUEST_DEBUG语义（公共KVM接口）'), ('X1', 'R', '计时器恢复'), ('X1', 'R', 'CSR脏标记'),
    ('M6', 'R', '引用泄漏'), ('M6', 'R', '失败路径残留状态'), ('M8', 'C', 'crashkernel低端区间排除（arm64先做）'),
    ('M8', 'C', 'IMA产生空buf'), ('M6', 'R', 'JIT释放泄漏'), ('M7', 'R', '掩码未初始化'), ('X2', 'R', '计数未递减'),
    ('X1', 'R', 'AIA地址字段'), ('M7', 'C', 'memslot边界（与其他架构一致）'), ('M4', 'R', '原子读改写宽度'),
    ('X1', 'R', 'xfence掩码'),
]


def main():
    cands = sorted(json.loads((HERE.parent / 'mixed_sample_llm_assist_20261101' / 'samples.json')
                              .read_text(encoding='utf-8'))['candidates'], key=lambda c: c['date'])
    assert len(cands) == len(L) == 121
    rows = [{'n': k, 'commit': c['commit'], 'function': c['function'], 'class': a, 'cross': b, 'reason': r}
            for k, (c, (a, b, r)) in enumerate(zip(cands, L))]
    cls = Counter(r['class'] for r in rows)
    m = [r for r in rows if r['class'].startswith('M')]
    real = [r for r in rows if r['class'] != 'X2']
    summary = {'by_class': dict(sorted(cls.items())), 'M_total': len(m),
               'M_share': round(len(m) / len(rows), 3), 'M_share_excluding_X2': round(len(m) / len(real), 3),
               'C_total': sum(r['cross'] == 'C' for r in rows),
               'C_by_class': dict(sorted(Counter(r['class'] for r in rows if r['cross'] == 'C').items())),
               'C_outside_catalog': [r['reason'] for r in rows if r['cross'] == 'C' and not r['class'].startswith('M')]}
    (HERE / 'labels.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n',
                                      encoding='utf-8', newline='\n')
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
