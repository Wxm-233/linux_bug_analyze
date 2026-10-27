"""Prepare a new user-authorized source review; no historical model text."""
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'模型调用测试/2026-10-24/btrfs_interval_stability'
OUT.mkdir(parents=True,exist_ok=False)
inventory=json.loads((HERE/'inventory.json').read_text(encoding='utf-8'))
documents=[]
sections=[]
for version in inventory['versions']:
    for path,meta in version['files'].items():
        source=HERE/meta['artifact'];content=source.read_bytes()
        assert hashlib.sha256(content).hexdigest()==meta['sha256']
        lines=content.decode().splitlines()
        selected=set()
        for hit in version['hits']:
            if hit['path']==path: selected.update(range(max(1,hit['line']-24),min(len(lines),hit['line']+24)+1))
        if path.endswith('/disk-io.c'):
            for i,line in enumerate(lines,1):
                if re.search(r'open_ctree\(|btrfs_parse_options\(|btrfs_init_fs_info\(',line):
                    selected.update(range(max(1,i-30),min(len(lines),i+180)+1))
        if path.endswith('/super.c'):
            for i,line in enumerate(lines,1):
                if re.search(r'max_inline|btrfs_fill_super\(|btrfs_mount_root\(',line):
                    selected.update(range(max(1,i-25),min(len(lines),i+55)+1))
        docid=version['mode']+'_'+path.replace('/','__')
        spans=[]
        for line in sorted(selected):
            if spans and line==spans[-1][1]+1: spans[-1][1]=line
            else: spans.append([line,line])
        documents.append(dict(id=docid,revision=version['revision'],path=path,artifact=meta['artifact'],sha256=meta['sha256'],spans=spans))
        sections.append(f'\n## DOCUMENT {docid}\nrevision={version["revision"]}; path={path}; sha256={meta["sha256"]}\n')
        for lo,hi in spans:
            sections.append(f'### lines {lo}-{hi}\n'+ '\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1)))
observer=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/parent/super.observed.c'
lines=observer.read_text(encoding='utf-8').splitlines()
documents.append(dict(id='observer_super',revision='parent and fix identical observation patch',path='super.observed.c',
                      artifact=str(observer),sha256=hashlib.sha256(observer.read_bytes()).hexdigest(),spans=[[775,810]]))
sections.append('\n## DOCUMENT observer_super\n'+'\n'.join(f'{n}: {lines[n-1]}' for n in range(775,811)))
intro='''你是本项目Linux源码主分析者。本轮用户已明确授权重新开展Btrfs分析，不采用任何历史模型回答。请只输出可复核结论、依据和简洁解释，不输出隐藏思维过程。

研究对象是已读开发案例，不是独立检测：Linux5.14-rc7父版0d977e0eba234e01a60bdde27314dc21374201b3与修复6f93e834fa7c5faa0372e46828b4b2a966ac61d7。实际已运行ARM64 64K页/64K盘的新挂载，正max_inline请求2048/8192。插桩见observer_super：先保存请求与缓存，min并写回，再读info->super_copy的sectorsize并记录。父版消费缓存4096、后采样磁盘65536；修复均65536。打印发生在采样后，非原子快照。单CPU/用户单线程不能自动排除内核并发。所有运行事实是研究者提供；你不能自称重新运行或独立验证。

当前问题：在这个成功新挂载正max_inline路径的缓存消费至后采样区间，磁盘参考是否能证明稳定且属于正确对象？不是要求预设肯定结论。请完成：
1. 给出对象创建、super_copy赋值/复制、验证、公开/传递到parse_options的实际顺序；分别列出原件支持和缺少的调用者/别名材料。
2. 逐类检查super_copy指针替换、其sectorsize写入、整块复制、并发writer及启动时机；区分改变其他super字段与改变sectorsize。检索清单不是完整写者证明；不得把未见写入当不存在。
3. 给出本区间能成立的最强限定命题、必要前提、可反驳情况；区分初始化私有性、锁保护、字段不变量与实际运行观测。必须明确哪些依据足以/不足以把相邻参考用于消费期限；不得因修复后数值相同即判证明成立。
4. 列出原裁剪字段、观测保存值、super对象与挂载实例之间的局部关系，明确观测变换对原程序等价性的限制。当前whole_path不足，不要求扩成整个文件系统正确性。
5. 给出可执行检查的候选条件/事实字段和拒判条件，区分研究者提供的语义、可机械提取事实、仍需新增实验；只提最小缺失源码区间或运行证据，避免重复已有挂载网格。

格式：先给supported/conditional/insufficient结论表，再逐项证据；每个实质源码主张引用DOCUMENT ID及给定连续行号。最后列出最小缺失材料和机器判定准入建议。下列材料是有来源的节选，并非全文件：不连续行号之间有省略，不得假设省略内容。允许指出无法判断。
'''
prompt=intro+'\n'.join(sections)
(OUT/'prompt.md').write_text(prompt,encoding='utf-8')
(HERE/'model_materials.json').write_text(json.dumps(dict(documents=documents,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),prompt_utf8_bytes=len(prompt.encode()),output_directory=str(OUT)),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(documents=len(documents),prompt_bytes=len(prompt.encode()))))
