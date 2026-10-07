"""Concurrent screening; shared durable budget; conservative material tiers."""
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict, replace

from .git_repository import truncate_diff
from .reporting import write_text_atomic
from .screen_protocol import evidence_lines, exclusion_guard, parse_response
from .screening import SYSTEM, TASK, PROMPT_VERSION, StopRun, parse_screen
from .semantic_signals import source_signals

VERSION = 'fast-screen-v2'
FAST_TASK = TASK.replace('1–8 个整数行编号', '1–32 个整数行编号（优先选择1–8条最必要证据）')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def save(path, value):
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2)+'\n')

class SharedBudget:
    def __init__(self, output, max_requests, token_budget):
        self.path=output/'usage.json'
        self.lock=threading.RLock()
        self.stopped=threading.Event()
        self.max_requests,self.token_budget=max_requests,token_budget
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
            'requests':0,'charged_tokens':0,'reported_tokens':0,'records':[]}

    def persist(self):
        self.data.update(max_requests=self.max_requests,token_budget=self.token_budget)
        save(self.path,self.data)

    def reserve(self, amount, h, tier):
        with self.lock:
            if self.stopped.is_set():raise StopRun('本轮已停止派发')
            if self.data['requests']>=self.max_requests or self.data['charged_tokens']+amount>self.token_budget:
                self.stopped.set()
                raise StopRun('共享请求或token预算不足')
            self.data['requests']+=1;self.data['charged_tokens']+=amount
            r=dict(id=self.data['requests'],hash=h,tier=tier,reserved_tokens=amount,status='in_flight')
            self.data['records'].append(r);self.persist()
            return r

    def finish(self,r,total,**fields):
        with self.lock:
            if type(total) is int and total>=0:
                self.data['charged_tokens']+=total-r['reserved_tokens']
                self.data['reported_tokens']+=total;r['total_tokens']=total
            r.update(fields);self.persist()

class FastScreener:
    def __init__(self,client,output,*,model,context='',endpoint='',workers=4,
                 max_requests=100,token_budget=2000000,compact_chars=6000,
                 full_chars=20000,max_tokens=1200,format_retries=0,transport_retries=1):
        self.client,self.output,self.model,self.context=client,output,model,context
        self.workers,self.compact_chars,self.full_chars=workers,compact_chars,full_chars
        self.max_tokens=max_tokens
        self.format_retries,self.transport_retries=format_retries,transport_retries
        self.budget=SharedBudget(output,max_requests,token_budget)
        identity=dict(version=VERSION,protocol=PROMPT_VERSION,task=FAST_TASK,system=SYSTEM,
                      model=model,endpoint=endpoint,context=context,compact_chars=compact_chars,
                      full_chars=full_chars,max_tokens=max_tokens,format_retries=format_retries,
                      transport_retries=transport_retries)
        p=output/'identity.json'
        if p.exists() and json.loads(p.read_text(encoding='utf-8'))!=identity:
            raise ValueError('运行配置变化，请使用新输出目录')
        save(p,identity);self.identity=digest(identity)

    def stage(self,original,chars,tier):
        diff,shortened=truncate_diff(original.diff,chars)
        c=replace(original,diff=diff,diff_truncated=original.diff_truncated or shortened)
        signals=source_signals(original)
        material=(f'hash: {c.hash}\nsubject: {c.subject}\nbody:\n{c.body}\nfiles:\n'
                  +'\n'.join(c.files)+f'\ndiff_truncated: {c.diff_truncated}\ndiff:\n{c.diff}')
        lines=evidence_lines(material)
        prompt=FAST_TASK+'\n研究框架：\n'+self.context+'\n提交材料：\n'+'\n'.join(
            f'[{i}] {line}' for i,line in enumerate(lines,1))
        fp=digest([self.identity,asdict(c),signals,tier])
        path=self.output/'stages'/tier/(c.hash+'.json')
        if path.exists():
            old=json.loads(path.read_text(encoding='utf-8'))
            if old.get('fingerprint')==fp:
                parse_screen(json.dumps(old['decision']),material,max_evidence=32)
                return old
        fe=te=0
        while True:
            reservation=len((SYSTEM+prompt).encode())+self.max_tokens+1024
            r=self.budget.reserve(reservation,c.hash,tier)
            total=None;start=time.monotonic();fields={'status':'failure'}
            try:
                response=self.client.chat.completions.create(model=self.model,
                    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
                    max_tokens=self.max_tokens,timeout=120,extra_body={'thinking':{'type':'disabled'}})
                total=getattr(getattr(response,'usage',None),'total_tokens',None)
                choice=response.choices[0]
                save(self.output/'responses'/f"{r['id']}.json",dict(hash=c.hash,tier=tier,
                     fingerprint=fp,finish_reason=choice.finish_reason,content=choice.message.content))
                write_text_atomic(self.output/'materials'/f'{fp}.txt',prompt)
                if choice.finish_reason!='stop':raise ValueError('输出截断或未正常结束')
                d,audit=parse_response(choice.message.content,lines,max_evidence=32)
                d=parse_screen(json.dumps(d),material,max_evidence=32);raw=dict(d)
                d,flags=exclusion_guard(d,audit,signals)
                if c.diff_truncated and d['relevance']=='unrelated':
                    flags.append('truncated_negative')
                    d=dict(d,relevance='uncertain',needs_review=True,reason='材料未完整覆盖补丁，待补充。'+d['reason'][:550])
                result=dict(hash=c.hash,subject=c.subject,status='success',fingerprint=fp,tier=tier,
                    model=self.model,decision=d,model_decision=raw,assessment=audit,
                    guard_flags=flags,source_signals=signals,truncated=c.diff_truncated)
                save(path,result);fields['status']='success'
                return result
            except Exception as exc:
                status=getattr(exc,'status_code',None)
                fields.update(error_type=type(exc).__name__,http_status=status)
                if status in (400,401,402,403,404):
                    self.budget.stopped.set();raise StopRun(f'接口/鉴权/余额错误 {status}') from None
                if isinstance(exc,(ValueError,TypeError,AttributeError,IndexError)):
                    if fe>=self.format_retries:return dict(hash=c.hash,status='validation_failed',tier=tier)
                    fe+=1;prompt+='\n请仅返回合法七字段JSON，证据编号为材料中的1至32个不同整数，优先1至8条。'
                elif status in (408,409,429) or (status and status>=500):
                    if te>=self.transport_retries:return dict(hash=c.hash,status='transport_failed',tier=tier)
                    te+=1
                else:
                    self.budget.stopped.set();raise StopRun('调用异常 '+type(exc).__name__) from None
            finally:
                self.budget.finish(r,total,elapsed_seconds=round(time.monotonic()-start,3),**fields)
            if self.budget.stopped.wait(min(2**(fe+te),8)):raise StopRun('停止重试')

    def screen(self,c):
        result=self.stage(c,self.compact_chars,'compact')
        if (result['status']=='success' and result['decision']['relevance']=='uncertain'
                and self.full_chars>self.compact_chars and len(c.diff)>self.compact_chars):
            result=self.stage(c,self.full_chars,'expanded')
        save(self.output/'results'/(c.hash+'.json'),result)
        return result

    def run(self,commits):
        unique=list({c.hash:c for c in reversed(commits)}.values())[::-1]
        hashes=[c.hash for c in unique]
        by_hash={c.hash:c for c in unique}
        return self.run_hashes(hashes,by_hash.__getitem__,duplicates=len(commits)-len(unique))

    def run_hashes(self,hashes,load_commit,*,duplicates=0):
        """Load at most `workers` patches at a time, retaining the full input manifest."""
        original_count=len(hashes)
        hashes=list(dict.fromkeys(hashes))
        duplicates+=original_count-len(hashes)
        p=self.output/'input.json'
        if p.exists() and json.loads(p.read_text(encoding='utf-8'))!=hashes:raise ValueError('输入变化，请使用新目录')
        save(p,hashes);results={};iterator=iter(hashes)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            active={}
            def load_and_screen(h):
                if self.budget.stopped.is_set():raise StopRun('停止派发')
                commit=load_commit(h)
                if commit.hash!=h:raise ValueError('加载的提交与输入清单不一致')
                return self.screen(commit)
            def submit():
                if self.budget.stopped.is_set():return
                h=next(iterator,None)
                if h is not None:active[pool.submit(load_and_screen,h)]=h
            for _ in range(self.workers):submit()
            try:
                while active:
                    done,_=wait(active,return_when=FIRST_COMPLETED)
                    for f in done:
                        h=active.pop(f)
                        try:results[h]=f.result()
                        except StopRun:pass
                        except Exception:
                            self.budget.stopped.set();raise
                        self.export(hashes,results,duplicates)
                        if h in results:
                            print(h+': '+results[h].get('decision',{}).get('relevance',results[h]['status']),flush=True)
                        submit()
            except KeyboardInterrupt:
                self.budget.stopped.set();raise
            finally:
                # Join in-flight requests before exporting the durable checkpoint.
                pool.shutdown(wait=True)
                for h in hashes:
                    p=self.output/'results'/(h+'.json')
                    if p.exists():results[h]=json.loads(p.read_text(encoding='utf-8'))
                self.export(hashes,results,duplicates)
        return results

    def export(self,hashes,results,duplicates):
        counts={k:0 for k in ('related','uncertain','unrelated')};selected=[];pending=[];failed=0
        for h in hashes:
            r=results.get(h)
            if not r or r['status']!='success':
                pending.append(h)
                failed+=int(r is not None)
                continue
            d=r['decision'];counts[d['relevance']]+=1
            if d['relevance']!='unrelated' or d['needs_review']:selected.append(h)
        write_text_atomic(self.output/'selected_hashes.txt',''.join(h+'\n' for h in selected))
        save(self.output/'checkpoint.json',dict(pending=pending,selected=selected))
        save(self.output/'summary.json',dict(total=len(hashes),counts=counts,pending=len(pending),
            failed=failed,unprocessed=len(pending)-failed,
            duplicates_removed=duplicates,status='stopped' if self.budget.stopped.is_set() else 'completed' if not pending else 'partial'))
