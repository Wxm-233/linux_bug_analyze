"""Post-parent-output bounded review of fe39; no rule mutation or new selection."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINUX = Path('/root/repos/linux')
OLD = 'a3172b7eb4a2719711187cfca12097d2326e85a7'
NEW = 'fe39c7b2dacf7fd4dcddc26704d01315ab92b7cb'
SPECS = {
    'include/net/bluetooth/hci.h': [r'^struct hci_cp_le_start_enc', r'^struct hci_ev_le_ltk_req'],
    'include/net/bluetooth/hci_core.h': [r'^struct smp_ltk', r'^struct smp_ltk \*hci_find_ltk', r'^void hci_le_start_enc', r'^struct hci_request'],
    'include/net/bluetooth/mgmt.h': [r'\b(?:rand|random)\b'],
    'net/bluetooth/hci_conn.c': [r'^void hci_le_start_enc'],
    'net/bluetooth/hci_core.c': [r'^struct smp_ltk \*hci_find_ltk\(', r'^struct smp_ltk \*hci_add_ltk\(', r'^static struct sk_buff \*hci_prepare_cmd\(', r'^void hci_req_add\(', r'^void hci_send_cmd\('],
    'net/bluetooth/hci_event.c': [r'^static void hci_le_ltk_request_evt'],
    'net/bluetooth/smp.c': [r'cpu_to_le64', r'le64_to_cpu', r'\b(?:rand|random|randval|rand\[)\b'],
    'net/bluetooth/smp.h': [r'\b(?:rand|random)\b'],
}


def git(*args):
    proc = subprocess.run(['git', *args], cwd=LINUX, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    records = []
    for revision in (OLD, NEW):
        for path, patterns in SPECS.items():
            code, source, error = git('show', f'{revision}:{path}')
            if code:
                records.append({'revision':revision,'path':path,'error':error})
                continue
            blob = git('rev-parse',f'{revision}:{path}')[1].strip()
            lines = source.splitlines()
            ranges = []
            for pattern in patterns:
                for index, line in enumerate(lines):
                    if re.search(pattern,line):
                        start, end = max(0,index-3), min(len(lines),index+36)
                        if path.endswith('.h'):
                            start, end = max(0,index-2), min(len(lines),index+16)
                        if path.endswith('smp.c'):
                            start, end = max(0,index-4), min(len(lines),index+7)
                        ranges.append((start,end))
            merged=[]
            for start,end in sorted(ranges):
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0],max(end,merged[-1][1]))
                else:
                    merged.append((start,end))
            records.append({'revision':revision,'path':path,'git_blob':blob,
                'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                'snippets':[{'start_line':start+1,'end_line':end,'text':'\n'.join(f'{i+1}: {lines[i]}' for i in range(start,end))} for start,end in merged]})
        code, _, error = git('cat-file','-e',f'{revision}:net/bluetooth/hci_request.c')
        records.append({'revision':revision,'path':'net/bluetooth/hci_request.c','exists':code==0,'error':error if code else None})
    patches=[]
    for path in ('net/bluetooth/hci_conn.c','net/bluetooth/hci_event.c','net/bluetooth/smp.c','net/bluetooth/smp.h','include/net/bluetooth/mgmt.h'):
        code,patch,error=git('show','--format=','--no-ext-diff',NEW,'--',path)
        patches.append({'path':path,'code':code,'patch':patch,'error':error or None})
    result={'saved_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'post-freeze/post-parent-preservation fe39 Bluetooth representation paths only; no selection change',
            'revisions':[OLD,NEW],'records':records,'bounded_patches':patches}
    (HERE/'source_review_fe39_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(records),'patches':len(patches),'output':'source_review_fe39_evidence.json'}))


if __name__=='__main__':
    main()
