from pathlib import Path
import copy,hashlib,json,re,sys,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.model_candidate import parse_model_candidate
from linux_bug_analyze.event_citation import check_event_citations
from linux_bug_analyze.candidate_parts import inspect_parts
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=HERE/n;assert not p.exists(),n
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
old=HERE.parent/'btrfs_typed_model_20261025'
for p,h in read(old/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
notes=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in notes}))
shutil.copyfile(old/'sync_work_notes.py',HERE/'sync_work_notes.py')
docs=read(HERE.parent/'btrfs_model_candidate_20261025/documents.json')
raw=ROOT/'模型调用测试/2026-10-25/btrfs_typed_model/final.md'
ingested=parse_model_candidate(raw.read_text(encoding='utf-8'),docs);candidate=ingested['candidate']
lines=Path(docs['observer']['path']).read_text(encoding='utf-8').splitlines()
registry=dict(origin='researcher_registered',interface_id=candidate['interface_id'],revision=candidate['contract']['revision'],events={
 label:dict(document='observer',start_line=n,end_line=n,quote=lines[n-1].strip())
 for label,n in [('cache_capture',788),('min_consumption',789),('result_write',793),('disk_sample',795)]})
save('event_registry.json',registry)
audit=check_event_citations(candidate,ingested['citations'],registry,docs)
assert audit['status']=='insufficient' and audit['matches'][0]['registered_events']==['result_write']
save('event_audit.json',audit)
archive=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=read(archive/'manifest.json');source=HERE.parent/'btrfs_mount_resume_20261023/init.c'
text=source.read_text(encoding='utf-8');needle='mount("/dev/vda","/mnt","btrfs",0,option)'
assert text.count(needle)==1 and 'int opts[]={2048,8192};' in text
source_line=next(i for i,l in enumerate(text.splitlines(),1) if needle in l)
contrasts=[]
for entry in manifest:
 assert entry['baseline_build']['init_source_sha256']==sha(source)
 for name in ['boot.log','super.txt','kernel.config']:
  assert sha(archive/entry['mode']/name)==entry['artifacts'][name]
 boot=(archive/entry['mode']/'boot.log').read_text(encoding='utf-8')
 assert re.findall(r'^MOUNT request=(\d+) rc=0 errno=0$',boot,re.M)==['2048','8192']
 assert 'EXPERIMENT_DONE failures=0' in boot and 'ERROR step=' not in boot
 for line in boot.splitlines():
  if 'LBA_CLAMP' in line:contrasts.append(dict(mode=entry['mode'],revision=entry['revision'],observation=line))
rows=[]
for row in read(old/'results.json')['rows']:
 facts=copy.deepcopy(row['facts'])
 facts['mount_flags']=dict(value=0,origin='program_projection',context_id=row['context_id'],event_kind='harness_syscall_argument',
  evidence=[dict(path=str(source.relative_to(ROOT)),sha256=sha(source),start_line=source_line,end_line=source_line),
   dict(path=str((archive/'manifest.json').relative_to(ROOT)),sha256=sha(archive/'manifest.json'),binding='archived init source binding; not a fresh binary reproduction')])
 d=inspect_parts(candidate,read(old/'role_registry.json'),facts,context_id=row['context_id'])
 assert d['summary']['scope']==dict(satisfied=6,violated=0,insufficient=1)
 assert 'selected_profile' not in facts and 'disk_at_deadline' not in facts
 rows.append(dict(context_id=row['context_id'],facts=facts,diagnostics=d))
save('results.json',dict(rows=rows,event_status=audit['status'],model_calls=0,new_boots=0,independent_positive=0,independent_normal=0,formal_core_executions=0,
 remaining_scope='selected_profile includes applicability beyond verified syscall flags; no automatic true',
 flags_boundary='User harness syscall flags only; no claim about post-LSM or internal VFS flags'))
save('contrast_evidence.json',dict(rows=contrasts,role='retrospective development evidence, not automatic prospective selection',
 target='geometry preparation before max_inline consumption',
 discriminating_request=8192,control_request=2048,
 rationale='2048 is below both 4096 and 65536: equal arithmetic results cannot distinguish cache readiness; 8192 can distinguish clipping results.',
 limits=['parent/fix differ by revision; not same-version architecture pair','neither clipping result nor adjacent sample supplies disk_at_deadline','no N2 gain or defect count inferred']))
pins=[raw,source,archive/'manifest.json',HERE/'event_registry.json',HERE/'run.py',ROOT/'linux_bug_analyze/linux_bug_analyze/event_citation.py']
save('frozen_inputs.json',{str(p.relative_to(ROOT)):sha(p) for p in pins})
print('Event citation rejected as result_write; scope 6 satisfied / 1 insufficient per old context; deadline still missing')
