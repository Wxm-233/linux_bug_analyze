from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
prior=ROOT/'模型调用测试/2026-10-24/btrfs_interval_stability'
receipt=json.loads((prior/'receipt.json').read_text(encoding='utf-8'))
assert receipt['status']=='complete_final_received' and not receipt['refusal_observed']
assert receipt['conservative_accounted_tokens']+200000<=1000000
out=ROOT/'模型调用测试/2026-10-24/btrfs_interval_stability_supplement';out.mkdir(exist_ok=False)
base=HERE/'source_inventory/parent/fs/btrfs'
items=[('super',base/'super.c',[(550,1010),(1340,1375),(1535,1559),(1640,1755)]),
       ('disk',base/'disk-io.c',[(2500,2740),(2988,3015),(3080,3700),(3750,3830)]),
       ('ctree',base/'ctree.h',[(220,290),(680,710),(1030,1045),(1615,1648),(2385,2415)]),
       ('vfs',HERE/'supplement_source/fs/super.c',[(120,150),(190,295),(370,432),(570,650),(1480,1535)]),
       ('minmax',HERE/'supplement_source/include/linux/minmax.h',[(1,200)]),
       ('observer',ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/parent/super.observed.c',[(780,805)])]
intro='''这是上一轮已完整结束的源码分析的新增材料复核，不是拒绝恢复。用户已授权继续本项。仅针对Linux父版0d977e0eba234e01a60bdde27314dc21374201b3成功新挂载正max_inline消费区间，主分析由你完成。全部新增源码有DOCUMENT ID与原始行号，以下附上一轮完整报告作为待审候选而非真值。

主智能体初核要求纠正：上一轮C5说788→795没有函数调用，但795有btrfs_super_sectorsize调用，应检查inline getter和宏定义后限定结论；两份super.c同SHA不能证明整个版本仅disk-io.c不同；guard和min两处读取不要混淆为原min必然重复求值；写回793并非sectorsize观察期限，不能不加论证就将disk加载移到793之前认作违反。请逐项接受/否定这些纠正并引用原件。

新增材料补齐parse_options、validate_super、对象绑定、VFS alloc/sget/grab语义、后续线程与sysfs启动、超级块布局和getter、min宏、read_dev_super。请据此消除由节选缺失造成的不足，但不要以单线程/未见写入假装全局稳定性。

输出：1.修订结论表（之前C1-C10哪些保留/弱化/撤回）；2.父版新挂载从发布/锁到parse的有限路径证据，指出无法排除的真实入口或尚未分析入口；3.区间内sectorsize参考稳定性最强可支持命题，明确源码级与机器指令时刻区别，是否真的需要反汇编或观察点才可作条件性检查；4.给检查器的精确准入前提和仍须不足的项目；5.只列必要的剩余材料/实验，避免不必要的追加日志。不得宣称形式化证明、独立发现或原程序并发等价。只给可复核结论与简洁理由，不输出隐藏思维过程。
'''
sections=[];docs=[]
for name,path,spans in items:
    raw=path.read_bytes();lines=raw.decode().splitlines()
    spans=[(lo,min(hi,len(lines))) for lo,hi in spans]
    docs.append(dict(id=name,path=str(path),sha256=hashlib.sha256(raw).hexdigest(),spans=spans))
    sections.append('\n## DOCUMENT '+name+'\n')
    for lo,hi in spans: sections.append('\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1)))
prompt=intro+'\n## 上一轮完整报告（待审核候选）\n'+(prior/'final.md').read_text(encoding='utf-8')+'\n'+'\n'.join(sections)
(out/'prompt.md').write_text(prompt,encoding='utf-8')
(HERE/'supplement_materials.json').write_text(json.dumps(dict(documents=docs,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),prompt_utf8_bytes=len(prompt.encode()),prior_visible_tokens=receipt['visible_reported_tokens'],reservation=200000,output_directory=str(out)),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(bytes=len(prompt.encode()),documents=len(docs),prior_accounted=receipt['conservative_accounted_tokens'],total_reserved=receipt['conservative_accounted_tokens']+200000)))
