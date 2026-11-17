"""Write observe.patch (prints only) and control.patch (prints, and local_irq_disable() moved after
smp_shutdown_nonboot_cpus()) for arch/riscv/kernel/machine_kexec.c at df2908090cda (plan.md). WSL.
"""
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
F = 'arch/riscv/kernel/machine_kexec.c'
W = Path('/root/work/kexec_verify/ptmp')

INC_OLD = '#include <linux/irq.h>\n'
INC_NEW = '#include <linux/irq.h>\n#include <linux/sched.h>\n'
CALL_OLD = '''#if defined(CONFIG_HOTPLUG_CPU)
	smp_shutdown_nonboot_cpus(smp_processor_id());
#endif
}'''
CALL_OBS = r'''#if defined(CONFIG_HOTPLUG_CPU)
	{
		unsigned long sw0 = current->nvcsw + current->nivcsw;

		pr_info("KEXEC-OBS before: irqs_disabled=%d switches=%lu\n", irqs_disabled(), sw0);
		smp_shutdown_nonboot_cpus(smp_processor_id());
		pr_info("KEXEC-OBS after: irqs_disabled=%d switches_delta=%lu\n", irqs_disabled(),
			current->nvcsw + current->nivcsw - sw0);
	}
#endif
}'''
IRQ_BEFORE = '''	local_irq_disable();

#if defined(CONFIG_HOTPLUG_CPU)
	{'''
IRQ_MOVED_FROM = '''#if defined(CONFIG_HOTPLUG_CPU)
	{'''
TAIL_OLD = '''	}
#endif
}'''
TAIL_NEW = r'''	}
#endif
	local_irq_disable();
	pr_info("KEXEC-OBS control: irqs_disabled=%d after shutdown\n", irqs_disabled());
}'''


def main():
    src = subprocess.run(['git', '-C', '/root/repos/linux', 'show', f'df2908090cda:{F}'],
                         capture_output=True, check=True).stdout.decode()
    assert src.count(INC_OLD) == 1 and src.count(CALL_OLD) == 1
    obs = src.replace(INC_OLD, INC_NEW).replace(CALL_OLD, CALL_OBS)
    assert obs.count(IRQ_BEFORE) == 1 and obs.count(TAIL_OLD) == 1
    ctl = obs.replace(IRQ_BEFORE, IRQ_MOVED_FROM).replace(TAIL_OLD, TAIL_NEW)
    for tag, text in (('a', src), ('o', obs), ('c', ctl)):
        p = W / tag / F
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    for name, tag in (('observe.patch', 'o'), ('control.patch', 'c')):
        diff = subprocess.run(['diff', '-u', f'a/{F}', f'{tag}/{F}'], cwd=W, capture_output=True).stdout
        (HERE / name).write_bytes(diff)
    print(ctl[ctl.index('void machine_shutdown'):ctl.index('void machine_shutdown') + 700])


if __name__ == '__main__':
    main()
