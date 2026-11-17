"""附加检查（已失败，保留审计）：假定所有探针值均为整数。

结果见 tests/supplemental_probe_failure.json；不属于已通过的必做回归。
编译探针 C 到汇编，不构建内核。
"""
import json
from pathlib import Path

import macro_values as mv
import settings as S

names=['NR_syscalls','TASK_SIZE_MAX']
expected_path=Path('/root/work/static2/values/CUR.json')
expected=json.loads(expected_path.read_text()) if S.TARGET=='riscv' else None
out={}
for arch,build in S.builds_for('CUR').items():
    vals,err=mv.probe(build,names,{n:'macro' for n in names})
    if err: raise RuntimeError(arch+': '+err)
    assert all(isinstance(vals[n],int) for n in names), (arch,vals)
    if expected is not None:
        assert vals=={n:expected[arch][n] for n in names},(arch,vals)
    out[arch]=vals
path=S.HERE/'tests'/f'probe_{S.TARGET}.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(out,indent=2))
print(S.TARGET,'probe',out)
