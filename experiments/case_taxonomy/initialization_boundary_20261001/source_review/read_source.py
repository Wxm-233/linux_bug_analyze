"""Independent bounded source gate review; no harness output is read."""
import hashlib
import json
import re
import subprocess
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
LINUX=Path('/root/repos/linux')
REVISIONS=['cef456cd354ef485f12d57000c455e83e416a2b6','727ea61a5028f8ac96f75ab34cb1b56e63fd9227']
PATHS={'net/bluetooth/hci_core.c':[r'\bhci_init[1-4]_req\s*\(',r'\bhci_init_req\s*\(',r'\bhci_init_sync\s*\(',r'\b__hci_init\s*\(',r'HCI_OP_LE_READ_MAX_DATA_LEN'],
       'include/net/bluetooth/hci_core.h':[r'^#define lmp_le_capable'],
       'include/net/bluetooth/hci.h':[r'^#define HCI_(?:PRIMARY|AMP|LE_DATA_LEN_EXT|OP_LE_WRITE_DEF_DATA_LEN)\b',r'^struct hci_cp_le_write_def_data_len']}


def git(*args):
    p=subprocess.run(['git',*args],cwd=LINUX,capture_output=True,text=True,check=True)
    return p.stdout


def main():
    records=[]
    for revision in REVISIONS:
        for path,patterns in PATHS.items():
            source=git('show',f'{revision}:{path}');lines=source.splitlines()
            ranges=[]
            for i,line in enumerate(lines):
                if any(re.search(pattern,line) for pattern in patterns):
                    start=max(0,i-3);end=min(len(lines),i+65 if path.endswith('.c') else i+14)
                    ranges.append((start,end))
            merged=[]
            for start,end in ranges:
                if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
                else:merged.append((start,end))
            records.append({'revision':revision,'path':path,'git_blob':git('rev-parse',f'{revision}:{path}').strip(),
                'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                'snippets':[{'start_line':start+1,'end_line':end,'text':'\n'.join(f'{j+1}: {lines[j]}' for j in range(start,end))} for start,end in merged]})
    result={'saved_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'independent historical init source-condition review before reading harness results; no hardware/run claim',
            'records':records}
    (HERE/'evidence_complete.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'saved':'source_review/evidence_complete.json','records':len(records)}))


if __name__=='__main__':main()
