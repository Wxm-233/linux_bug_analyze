"""本轮统一配置。TARGET 在进程启动时选择；切换目标须启动新进程。"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = os.environ.get('TARGET', 'riscv')
if TARGET not in ('riscv', 'loongarch'):
    raise ValueError('TARGET 只能是 riscv 或 loongarch')
ARCHS = (TARGET, 'arm64', 'x86_64')
ARCH_PREFIX = f'arch/{TARGET}/'
KERNEL_PREFIX = ARCH_PREFIX + 'kernel/'
BASE = ('kernel/', 'mm/', 'fs/', 'net/', 'ipc/', 'lib/', KERNEL_PREFIX, ARCH_PREFIX + 'mm/')
DRIVER_PATTERN = {'riscv': 'riscv|sifive|-sbi', 'loongarch': 'loongarch|loongson'}[TARGET]
DRV = re.compile(r'^drivers/.*(' + DRIVER_PATTERN + r')')
RANK_DRV = re.compile(r'(^|/)drivers/.*(' + DRIVER_PATTERN + r')')
ARCH_MAC_FILE = re.compile(r'(^|/)(arch/' + re.escape(TARGET) + r'/|include/asm-generic/)')
BOUNDARY_POOL = os.environ.get('BOUNDARY_POOL', 'existing' if TARGET == 'riscv' else 'none')
if BOUNDARY_POOL not in ('existing', 'none'):
    raise ValueError('BOUNDARY_POOL 只能是 existing 或 none')
if TARGET == 'loongarch' and BOUNDARY_POOL != 'none':
    raise ValueError('LoongArch 没有边界池，禁止加载 RISC-V 名单；请设置 BOUNDARY_POOL=none，仅使用 I1')


def boundary_names():
    # 留出集纪律：LoongArch 没有边界池，不借用 RISC-V 的名单，只靠 I1 本树边界。
    if BOUNDARY_POOL == 'none':
        return {'kind': {}, 'macro': [], 'nonmacro': []}
    return json.loads(Path(os.environ.get('BOUNDARY_NAMES', HERE / 'boundary_names.json')).read_text())


def builds_for(group):
    path = Path(os.environ.get('PIPELINE_BUILDS', HERE / 'builds.json'))
    data = json.loads(path.read_text())
    try:
        builds = data[TARGET][group]
        return {a: builds[a] for a in ARCHS}
    except KeyError as e:
        raise ValueError(f'{path} 缺少 TARGET={TARGET} group={group} 的三架构构建目录') from e


def require_values(vals):
    missing = [a for a in ARCHS if a not in vals]
    if missing:
        raise ValueError(f'取值文件缺少 {missing}，不能混用其他目标架构的取值')


def temp_dir():
    path = HERE / 'tmp' / TARGET
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
