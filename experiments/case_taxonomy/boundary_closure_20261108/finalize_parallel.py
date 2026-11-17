"""Record the completed small parallelism task; preserve handoff outside section 4."""
import ast
from datetime import datetime, timedelta, timezone
from common import *

def parts(data):
    start=data.index('## 四、当前进度'.encode())
    end=data.index('## 五、每轮实验怎么做'.encode(),start)
    return data[:start],data[start:end],data[end:]

def main():
    evidence=HERE/'evidence/parallel'
    assert not (evidence/'final_verification.json').exists(),'Already finalized'
    report=read(evidence/'real_result.json');plan=read(evidence/'real_plan.json')
    original=read(HERE/'selftest_prototype_result.json')
    scheduler=read(evidence/'scheduler_result.json')
    fixture=read(HERE/'prototype_batch_selftest_result.json')
    assert report['passed'] and len(report['units'])==4 and report['old_cache_bytes_unchanged']
    assert original['passed'] and len(original['checks'])==17
    assert scheduler['passed'] and len(scheduler['checks'])==15
    assert fixture['passed'] and fixture['typed_callback_candidates_checked']
    assert report['input_digest']==plan['input_digest']
    assert plan['tools']=={name:sha(HERE/name) for name in plan['tools']}
    assert check_criteria()==plan['criteria_sha256']
    assert sha(HERE/'criteria_amendment1.md')==plan['amendment_sha256']
    assert not git('status','--porcelain=v1')
    for name in ('prototype_batch.py','selftest_prototype_batch.py','parallel_verify.py','finalize_parallel.py'):
        ast.parse((HERE/name).read_text(encoding='utf-8'))
    for name in ('prototype_batch.sh','run.sh','parallel_probe.sh'):
        subprocess.run(['bash','-n',str(HERE/name)],check=True)
    parallel=report['parallel_metrics'];serial=report['serial_metrics']
    speed=serial['elapsed_seconds']/parallel['elapsed_seconds']
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    handoff=HERE.parents[3]/'交接文档.md';before=(evidence/'handoff_before.md').read_bytes()
    current=handoff.read_bytes();prefix,section,suffix=parts(current)
    assert (prefix,suffix)==(parts(before)[0],parts(before)[2])
    section=section.decode('utf-8');newline='\r\n' if '\r\n' in section else '\n'
    old_intro=next(line for line in section.splitlines() if line.startswith('**2026-11-08 10:28'))
    intro=f'**{stamp}（GPT）停点：prototype_batch.py 的 --jobs 小任务已完成。原型17项、调度15项及4个真实TU串并行对照通过；建议先 --jobs 4 --limit 512，由Claude继续全量证据采集。旧17个缓存保留，代码变化进入新摘要目录；后台构建未改动。**'
    section=section.replace(old_intro,intro,1)
    addition=f'''### 本次并行执行补充（2026-11-08）

- 我只改prototype_batch.py的逐单元调度；默认jobs1保持串行，jobs>1用spawn新进程逐TU释放内存，大结果原子落盘，父进程只接收短状态。失败后停止派发，等待在途单元落盘，保留已完成结果；失败缓存仍拒绝续跑。长错误/异常退出均有夹具覆盖。
- 原criteria.md保持冻结；新增criteria_amendment1.md，SHA256={plan['amendment_sha256']}，只补执行方式。最终4个真实riscv单元27/28/29/30对照通过：全部字段（仅标准化路径/gzip存储元数据）和轨迹解压字节相同，jobs4={parallel['elapsed_seconds']:.3f}秒，jobs1={serial['elapsed_seconds']:.3f}秒，本批{speed:.2f}倍。详见本轮parallel_validation.md、evidence/parallel/real_result.json。
- 最终worker峰值VmHWM=275496KiB（269MiB），预处理子进程峰值145264KiB（142MiB），整个验证进程树峰值936924KiB（915MiB），MemAvailable最低12.95GiB，未用swap。16份按样本预算约6.4GiB，但未测大TU/其他架构，不建议与-j20构建同时直接开16；当前jobs4，构建结束后可先jobs8/limit32评估。
- 旧riscv缓存17/3935仍保留于prototype_scan/riscv_defconfig/34db2d428b48bd340af614ad9ecb1f9e437e721f5cb572cffd7fb6c2bb07c828，35个文件SHA未变。新版输入摘要为{plan['input_digest']}；真实验证位于evidence/parallel/real/1794107542982233126/，没有写入生产目录，不能把旧缓存复制成新版兼容结果。jobs/limit不参与同版摘要。
- Claude下一步按claude_commands.md第3节，原三架构依次 prototype_batch.sh <arch> --jobs 4 --limit 512，前台重复至complete，再run.sh prototype_summary.py <arch>；成功新配置加--profile。不要同时再启动构建、不要重跑claude_build_all.sh。本次没有核对后台构建完成/失败状态，下面旧配置状态沿用10:28记录。
- 本次4个不同真实TU共16次解析（含IPC修正前后的各一轮串并行）；全量扫描0、内核构建0、模型接口0、新内核缺陷/疑点0；全量速度/最大内存/磁盘规模仍null。最终静态与文档保护核对见evidence/parallel/final_verification.json。

'''
    section=section.replace('### 固定背景与已经完成的输入',addition.replace('\n',newline)+'### 固定背景与已经完成的输入',1)
    section=section.replace('prototype_batch.sh riscv --limit 8','prototype_batch.sh riscv --jobs 4 --limit 512')
    updated=prefix+section.encode('utf-8')+suffix
    assert (parts(updated)[0],parts(updated)[2])==(prefix,suffix)
    handoff.write_bytes(updated)
    log=HERE.parents[3]/'进度日志.md';log_before=log.read_bytes()
    note=f'''
## {stamp} GPT boundary_closure_20261108 并行小任务完成与最终交接
- 做了什么：最终版--jobs默认1、正整数校验、多进程spawn逐单元调度、短状态IPC、原子缓存、失败停止派发/等待在途落盘、异常退出失败记录全部完成。原语义原型、输入筛选、候选/未知区域与汇总算法未改。先冻结执行补充，修正一次自己的长错误回传潜在死锁后，所有真实对照用最终代码重新运行；原期望集合未改。
- 改了哪些文件：唯一生产代码修改为 D:\\homework\\software\\linux_bug_analyze\\linux_bug_analyze\\experiments\\case_taxonomy\\boundary_closure_20261108\\prototype_batch.py；同目录修改claude_commands.md第3节，新增criteria_amendment1.md、criteria_amendment1_sha256.txt、selftest_prototype_batch.py、parallel_verify.py、parallel_probe.sh、parallel_validation.md、finalize_parallel.py和evidence/parallel/下的原码快照、计划、结果、资源/哈希/最终核对记录。原型自测和夹具汇总重跑更新同轮prototype_fixture_macros.json、prototype_fixture_callbacks.json、selftest_prototype_result.json、prototype_batch_selftest_result.json、evidence/prototype/fixture_*.i.gz及prototype_scan/fixture新摘要目录。外层 D:\\homework\\software\\linux_bug_analyze\\交接文档.md仅改第四节； D:\\homework\\software\\linux_bug_analyze\\进度日志.md只追加。
- 运行的命令与结果：全部WSL命令由第一行source tools/wsl_env.sh的本轮.sh进入。wsl -u root -- bash {HERE}/run.sh selftest_prototype.py，17项通过；同入口 selftest_prototype_batch.py，15项通过，覆盖真实解析失败、256KiB错误、退出码23、退出码0无回传，失败均保留1失败+3成功、未派发另4个、续跑拒绝失败记录。prototype_batch.sh riscv --fixture --jobs 4 --limit 1，再默认串行--limit 1，0/2→1/2→2/2；run.sh prototype_summary.py riscv --fixture预期候选通过。--jobs 0按预期拒绝。最后 run.sh finalize_parallel.py 进行语法、冻结摘要、源码干净、交接保护与本记录追加。
- 最终真实验证命令：run.sh parallel_verify.py prepare；run.sh parallel_verify.py run --jobs 4；run.sh parallel_verify.py run --jobs 1；run.sh parallel_verify.py compare，全部退出0。只选四个旧缓存外单元27/28/29/30，最终jobs4={parallel['elapsed_seconds']:.3f}秒、jobs1={serial['elapsed_seconds']:.3f}秒，约{speed:.2f}倍；逐字段（只标准化输出路径/已分别验证的gzip存储SHA）和轨迹解压字节均相同。最终明细evidence/parallel/real_result.json，目录real/1794107542982233126/；初版对照real/1794106994653253827/标为superseded，均保留，不混入最终验收。4个不同真实TU合计16次解析，不是全量扫描。
- 内存依据与建议：最终worker getrusage最大273840KiB、VmHWM最大275496KiB（269MiB）；预处理子进程最大145264KiB（142MiB）；进程树并发最大936924KiB（915MiB），可用内存最低13577428KiB（12.95GiB），未用swap。串行同一进程采样VmHWM最大354668KiB、进程树441088KiB。16份按样本峰值相加约6.4GiB，但未知大TU/arm64等会放大，且有-j20构建，当前推荐jobs4/limit512；构建结束后可先jobs8/limit32评估，不直接宣称16安全。
- 停在哪里：用户本次小任务完成；原17个缓存及其轨迹/inputs共35文件大小与SHA均未变。最终生产摘要{plan['input_digest']}，生产目录未放真实结果，旧17个不跨码复用；同版jobs/limit变化可续跑。原criteria SHA={plan['criteria_sha256']}；补充SHA={plan['amendment_sha256']}。没有改后台claude_build_all.sh或/root/work/boundary_build/closure_20261108_*，未构建、未全量扫描、未模型调用、未commit/push/切分支或结束他人进程。
- Claude下一步具体命令：wsl -u root -- bash {HERE}/prototype_batch.sh riscv --jobs 4 --limit 512，前台重复至complete；然后 wsl -u root -- bash {HERE}/run.sh prototype_summary.py riscv。arm64/x86_64依次替换arch；成功新配置两条均加--profile <名称>。完整命令已更新claude_commands.md第3节。不要同时启动三个架构批次，不重启后台构建，不删除失败记录自动重试；每个阶段完成立即记日志。
- 没有验证或不确定的：未跑16worker、arm64/x86_64真实单元、新配置原型或全量扫描；全量耗时/磁盘规模/全架构最大内存仍null。没有读取后台构建日志判定其完成/失败。三类缺陷检查器及宏/回调/配置统一接线仍是原未完成项，本任务没有扩展研究范围。最终文档字节统计的一次Windows管道中文编码命令写错，已改用Unicode转义后只读重查，不涉及实验失败。
'''
    with log.open('ab') as f:f.write(note.encode('utf-8'))
    assert log.read_bytes()[:len(log_before)]==log_before
    result={'passed':True,'completed_at':stamp,'original_selftest_checks':17,'scheduler_checks':15,
            'real_units_compared':4,'old_cache_files_unchanged':35,'kernel_source_worktree_clean':True,
            'criteria_sha256':check_criteria(),'amendment_sha256':plan['amendment_sha256'],
            'input_digest':plan['input_digest'],'jobs_recommended':4,'batch_limit_recommended':512,
            'parallel_seconds':parallel['elapsed_seconds'],'serial_seconds':serial['elapsed_seconds'],'speed_ratio':speed,
            'handoff_outside_section4_unchanged':True,'handoff_outside_section4_sha256':hashlib.sha256(prefix+suffix).hexdigest(),
            'log_prior_bytes_unchanged':True,'log_prior_bytes':len(log_before),
            'tools_and_docs':{name:sha(HERE/name) for name in ('prototype_batch.py','selftest_prototype_batch.py','parallel_verify.py','finalize_parallel.py','claude_commands.md','parallel_validation.md')},
            'full_scan_seconds':None,'all_architectures_maximum_rss_kib':None}
    write('evidence/parallel/final_verification.json',result)
    print('finalized: 17+15 checks, 4 real units, old cache unchanged, handoff section 4 only')

if __name__=='__main__':main()
