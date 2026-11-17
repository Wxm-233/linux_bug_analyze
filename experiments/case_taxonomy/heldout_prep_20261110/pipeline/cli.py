"""各脚本的输入/输出参数；目标选择统一使用环境变量 TARGET。"""
import argparse


def parse(task):
    p = argparse.ArgumentParser(description='静态流水线（TARGET=riscv 或 loongarch；构建映射 PIPELINE_BUILDS）')
    if task == 'extract':
        for n in ('compile_commands', 'root', 'out'): p.add_argument(n)
        p.add_argument('--jobs', type=int, default=14)
        p.add_argument('--only', default=None, help='编译单元路径正则')
    elif task == 'hints':
        for n in ('facts', 'values', 'config', 'out'): p.add_argument(n)
        p.add_argument('--group')
    elif task in ('macro', 'macro2', 'layouts'):
        p.add_argument('group'); p.add_argument('facts')
        p.add_argument('--out', required=True)
        if task == 'macro2': p.add_argument('--base-values', required=True)
    elif task == 'vocab':
        p.add_argument('group')
        for n in ('facts','values','out'): p.add_argument('--'+n, required=True)
    else:
        raise ValueError(task)
    return p.parse_args()
