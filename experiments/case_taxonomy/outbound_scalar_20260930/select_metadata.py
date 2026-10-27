"""Save metadata only; never expose fresh commit bodies or patches."""
from pathlib import Path
from datetime import datetime, timezone
import subprocess, json, re

HERE=Path(__file__).resolve().parent
REPO='/root/repos/linux'

def git(*args):
    return subprocess.run(['git','-C',REPO,*args],capture_output=True,text=True,check=True).stdout

def main():
    dest=HERE/'metadata_pool.json'
    if dest.exists():
        raise RuntimeError('refusing to replace saved metadata pool')
    args=['log','--all','--no-merges','--since=2018-01-01',
          '--until=2026-09-30','--regexp-ignore-case','--extended-regexp',
          '--grep=endian|byte.?order|baud.?rate','--max-count=80',
          '--format=%H%x09%cs%x09%s','--','drivers/bluetooth','net/bluetooth']
    rows=[]
    for line in git(*args).splitlines():
        bits=line.split('\t',2)
        if len(bits)!=3 or not re.fullmatch('[0-9a-f]{40}',bits[0]):
            raise RuntimeError('unexpected metadata row')
        sha,date,title=bits
        paths=git('diff-tree','--no-commit-id','--name-only','-r',sha).splitlines()
        rows.append({'commit':sha,'date':date,'subject':title,'paths':paths})
    report={'saved_at_utc':datetime.now(timezone.utc).isoformat(),
            'query':args,'records':rows,'cap':80,
            'reading_scope':'Titles, dates, changed paths only. Git grep may internally match the body; no body/patch/source is exposed to selector.',
            'sampling_limit':'Purposeful recent matching history, not a random population sample. Distinct files and same mechanism still require review.'}
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('metadata saved:',len(rows),'records')

if __name__=='__main__':
    main()
