from pathlib import Path
import ast, hashlib, json, re, posixpath

HERE=Path(__file__).resolve().parent
STAGE=HERE.parent
ROOT=STAGE.parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))

result=load(STAGE/'retrieval_manifest.json')
selection=load(STAGE/'selection_pre.json')
pool=load(STAGE/'metadata_pool.json')
freeze=load(STAGE/'freeze_pre.json')
method=load(STAGE/'audit_method/review.json')
frozen_checks=0
for row in freeze['files']:
    assert sha(Path(row['path']))==row['sha256'], row['path']
    frozen_checks+=1
assert method['ready_for_retrieval'] is True
assert method['freeze_sha256']==sha(STAGE/'freeze_pre.json')
assert method['script_sha256']==sha(STAGE/'prepare.py')
assert method['metadata_pool_sha256']==sha(STAGE/'metadata_pool.json')
assert method['exposure_audit_sha256']==sha(STAGE/'audit_exposure/exposure_audit.json')
assert method['selection_sha256']==sha(STAGE/'selection_pre.json')
assert result['queue_size']==len(selection['queue'])==1
assert result['git_commands']==2
assert len(result['observations'])==1
ob=result['observations'][0]
selected=selection['queue'][0]
assert all(ob[k]==v for k,v in selected.items())
assert ob['commit']=='7a2bccd1a27f0c8fc87e4ed56abd6ea9fa7314a6'

receipt_checks=[]
payloads={}
for label,args in [('commit',['cat-file','-p',ob['commit']]),('path',['diff-tree','--root','-m','--no-commit-id','--name-only','-r','-z',ob['commit']])]:
    rp=STAGE/ob[label+'_receipt']
    receipt=load(rp)
    assert receipt['argv']==['wsl','-d','Ubuntu','--','git','-C','/root/repos/linux',*args]
    assert receipt['returncode']==0
    for channel in ['stdout','stderr']:
        saved=Path(receipt[channel]).resolve()
        assert saved.is_relative_to(STAGE/'raw')
        assert sha(saved)==receipt[channel+'_sha256']
    payloads[label]=Path(receipt['stdout']).read_bytes()
    receipt_checks.append({'receipt':rp.relative_to(STAGE).as_posix(),'sha256':sha(rp),
        'argv':receipt['argv'],'returncode':receipt['returncode'],
        'stdout_bytes':len(payloads[label]),'stdout_sha256':receipt['stdout_sha256'],
        'stderr_bytes':Path(receipt['stderr']).stat().st_size,'stderr_sha256':receipt['stderr_sha256']})

raw=payloads['commit']
object_sha1=hashlib.sha1(b'commit '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
assert object_sha1==ob['commit']
header,sep,message=raw.partition(b'\n\n')
assert sep
header_lines=header.splitlines()
tree=[line[5:].decode('ascii') for line in header_lines if line.startswith(b'tree ')]
parents=[line[7:].decode('ascii') for line in header_lines if line.startswith(b'parent ')]
assert len(tree)==1 and re.fullmatch('[0-9a-f]{40}',tree[0])
assert parents==[ob['parent']]==['7ff730ca458e841dbcdc87f264d7afe3eaed525e']
lines=message.decode('utf-8').splitlines()
assert lines[0]==ob['message_subject']==selected['subject']

# Independently split paragraphs and remove only trailing all-known-trailer paragraphs.
paragraphs=[]
current=[]
for index,line in enumerate(lines[1:],2):
    if line.strip(): current.append((index,line))
    elif current: paragraphs.append(current);current=[]
if current: paragraphs.append(current)
keys={'signed-off-by','reviewed-by','acked-by','tested-by','reported-by','suggested-by','co-developed-by','fixes','link','cc','closes','stable-dep-of','message-id'}
def pure_trailers(paragraph):
    preceding_key=False
    for _,line in paragraph:
        if line[:1].isspace():
            if not preceding_key: return False
            continue
        match=re.match(r'^([^:]+):\s*(.*)$',line)
        if match is None or match.group(1).lower() not in keys: return False
        preceding_key=True
    return bool(paragraph)
cut=len(paragraphs)
while cut and pure_trailers(paragraphs[cut-1]):cut-=1
body=[{'message_line':index,'text':line} for paragraph in paragraphs[:cut] for index,line in paragraph]
trailers=[{'message_line':index,'text':line} for paragraph in paragraphs[cut:] for index,line in paragraph]
assert body==ob['body_lines'] and trailers==ob['removed_trailer_lines']
assert [q['message_line'] for q in body]==[3,4,6]
assert [q['message_line'] for q in trailers]==[8,9,10,11]
count_regex=r'(?<![A-Za-z0-9])(?:len|length|size|count|bytes)(?![A-Za-z0-9])'
assert pool['count_regex']==count_regex
assert [q for q in body if re.search(count_regex,q['text'],re.I)]==ob['count_hint_lines']==[]
assert payloads['path']==b'drivers/i3c/master/mipi-i3c-hci/core.c\0'
paths=[s.decode('utf-8') for s in payloads['path'].split(b'\0') if s]
assert paths==ob['paths']
for p in paths:assert not p.startswith('/') and posixpath.normpath(p)==p and not p.startswith('../')
assert ob['classified']==[{'path':paths[0],'category':'potential_kernel_c'}]
assert ob['status']=='message_and_paths_available'
assert result['selected_path'] is None and result['stop_reason']=='no_body_count_and_implementation_in_fixed_queue'
zero_keys=['new_source_requests','rule_runs','gate_runs','patch_exports','new_confirmed_cases','independent_positive_cases']
for key in zero_keys:assert result[key]==0
assert not (STAGE/'sources').exists()
assert len(list((STAGE/'raw').rglob('receipt.json')))==2

verifier=STAGE/'verify_saved.py'
source=verifier.read_text(encoding='utf-8')
tree_ast=ast.parse(source)
imports=[]
for node in ast.walk(tree_ast):
    if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
    elif isinstance(node,ast.ImportFrom):imports.append(node.module)
assert set(imports)=={'pathlib','hashlib','json','posixpath','re'}
for node in ast.walk(tree_ast):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
        assert node.func.attr not in {'write_bytes','write_text','mkdir','unlink','rmdir','system','run','Popen'}
static_notes=[
    'Static import/call inspection finds no Git, subprocess, detector/gate import, model access or mutation in verify_saved.py.',
    'Root verifier validates quote coverage/text and COUNT hints but does not independently recompute the known-trailer paragraph boundary. This audit separately recomputes that exact boundary for the sole actual saved message.',
    'Root verifier has simplified branches for hypothetical non-single-parent/unavailable observations; this one-item successful single-parent result does not exercise those branches.'
]
report={'date':'2026-10-09','auditor':'/root/body_path_exposure','review_passed':True,
    'retrieval_manifest_sha256':sha(STAGE/'retrieval_manifest.json'),
    'freeze_sha256':sha(STAGE/'freeze_pre.json'),'prepare_script_sha256':sha(STAGE/'prepare.py'),
    'metadata_pool_sha256':sha(STAGE/'metadata_pool.json'),'selection_sha256':sha(STAGE/'selection_pre.json'),
    'verifier_sha256':sha(verifier),'frozen_file_checks':frozen_checks,
    'queue_size':1,'saved_git_commands':2,'commit_object_sha1':object_sha1,'parent':ob['parent'],
    'body_message_lines':[q['message_line'] for q in body],'trailer_message_lines':[q['message_line'] for q in trailers],
    'message_quote_checks':len(body)+len(trailers),'count_hint_count':0,
    'changed_paths':paths,'implementation_path_selected':False,'receipt_checks':receipt_checks,
    'static_verifier_notes':static_notes,'blocked_findings':[],
    'new_git_commands_during_audit':0,'new_source_reads_during_audit':0,'new_patch_reads_during_audit':0,
    **{key:0 for key in zero_keys},
    'interpretation':'正文报告的是配置符号名称线索，没有COUNT词；唯一C路径不满足已冻结组合选例条件。未读实现与补丁，不认定新缺陷或机制，不将未入选当阴性。'}
(HERE/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md='''# 提交说明与路径独立结果复核

2026-10-09。只读复核已保存原字节、收据、冻结材料和根验证脚本；未调用 Git、源码、patch、检测器、来源门控或模型。

复核通过。固定队列1项，保存Git命令2条，53个冻结文件指纹与方法批准身份相符。commit原字节以Git对象SHA-1核对为 `7a2bccd1a27f0c8fc87e4ed56abd6ea9fa7314a6`，恰一父版 `7ff730ca458e841dbcdc87f264d7afe3eaed525e`。

独立按空段重建提交正文与尾部已知trailer段：实际正文位于message第3、4、6行，trailer位于第8–11行，7条引用均逐字对应原物。提交正文说明 `BIG_ENDIAN` 配置名不存在、CPU端序符号应为 `CPU_BIG_ENDIAN`；该作者解释只是取证线索，未通过源码核实。冻结COUNT正则无匹配。

路径原物为唯一 `drivers/i3c/master/mipi-i3c-hci/core.c` 加NUL结尾，完整argv/退出码/stdout和stderr指纹均相符。路径可列为潜在内核C，但缺少正文COUNT提示，因此没有选入实现取证。没有来源文件/规则/门控/patch运行，也没有新增确认或独立阳性。

根 verify_saved.py 的静态导入及调用检查未发现取证、模型、规则或写操作。其引用覆盖验证本身不独立重建trailer边界；本审计已对唯一实际消息独立重建并确认。其简化失败分支不影响本轮单父成功取证，不等于那些分支经过试验。

本结果不能证明 i3c 提交不相关、不是缺陷或源码无长度问题。仅表明它未满足本轮目的性选例条件。应保留不足并结束标题/正文扩池路线，不替换新标题追求阳性。

retrieval_manifest SHA-256：`RESULT`。
freeze SHA-256：`FREEZE`。
review JSON SHA-256：`REVIEW`。
'''.replace('RESULT',report['retrieval_manifest_sha256']).replace('FREEZE',report['freeze_sha256']).replace('REVIEW',sha(HERE/'review.json'))
(HERE/'review.md').write_text(md,encoding='utf-8')
print(json.dumps({'review_passed':True,'review_sha256':sha(HERE/'review.json'),'retrieval_manifest_sha256':report['retrieval_manifest_sha256'],'freeze_sha256':report['freeze_sha256'],'checks':{'frozen_files':frozen_checks,'quotes':len(body)+len(trailers),'receipts':len(receipt_checks)}},ensure_ascii=False))
