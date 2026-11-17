from datetime import datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
OUTER=ROOT.parent
def record(stage,body):
    p=OUTER/'进度日志.md'
    title=f'GPT boundary_audit_20261107 {stage}'
    if title in p.read_text(encoding='utf-8'):return
    with p.open('a',encoding='utf-8',newline='\n') as stream:
        stream.write(f'\n## {datetime.now():%Y-%m-%d %H:%M} {title}\n{body.strip()}\n')
if __name__=='__main__':
    record('问题3：生成文件统计完成', '''
- 做了什么：固定审计判据并记录 SHA256=a2a23f31e0c7e7509c2e940751fda9f361f3cf18c2348be12376b1bdc6a87ba2；只读取三架构既有边界明细，按使用位置与定义位置分别统计生成文件，并读取真实生成文件。未改旧轮次产物、未构建、未全量扫描。
- 改了哪些文件：新增 D:\\homework\\software\\linux_bug_analyze\\linux_bug_analyze\\experiments\\case_taxonomy\\boundary_audit_20261107\\{criteria.md,criteria_sha256.txt,criteria_amendment1.md,generated.py,generated_analysis.json,run.sh,record.py,evidence/generated_riscv.json,evidence/generated_arm64.json,evidence/generated_x86_64.json}；同目录其他问题的分析脚本和证据仍在进行。
- 运行的命令与结果：wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/run.sh generated.py，退出0。@build 使用位置：riscv 241符号/601点、arm64 264/613、x86_64 419/794；仅这些位置贡献232/256/406个符号。系统调用生成头贡献227符号/375点、252/383、407/604，保留。模块元数据分别8符号/14点、6/16、0/0，单列并从运行时接口候选排除后会少5/4/0个独占符号。其他生成代码211/213/189点及timeconst各1点，按真实来源保留；不能一律排除O=。旧layer()并非把所有@build归架构，而是去前缀后按arch/判断。
- 停在哪里：问题3的数字与归层建议完成；问题1逐样本和问题2引用抽样还在分析，稍后另记。问题3的来源规则证据与最终README仍将补齐。
- 下一步：继续本轮样本证据与16单元未解析引用核查；无需Claude现在启动扫描，最终交接将给具体可运行命令。
- 没有验证或不确定的：没有重算修改归层后的全集，没有做缺陷检查或模糊测试。generated_definition统计与use统计是两套口径；各组符号不可直接相加。''')
