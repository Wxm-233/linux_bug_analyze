"""Only sync/add request boundary excerpts from the already read revisions."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
REVISIONS=['cef456cd354ef485f12d57000c455e83e416a2b6','727ea61a5028f8ac96f75ab34cb1b56e63fd9227']
PATH='net/bluetooth/hci_request.c'


def main():
    records=[]
    for revision in REVISIONS:
        source=subprocess.check_output(['git','-C','/root/repos/linux','show',revision+':'+PATH],text=True)
        blob=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',revision+':'+PATH],text=True).strip()
        lines=source.splitlines()
        records.append({'revision':revision,'path':PATH,'git_blob':blob,
            'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'snippets':[{'start_line':start,'end_line':end,'text':'\n'.join(f'{i+1}: {lines[i]}' for i in range(start-1,end))} for start,end in [(192,230),(239,266),(312,346)]]})
    (HERE/'request_evidence.json').write_text(json.dumps({'scope':'sync/add error and actual queue boundary only','records':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(records),'saved':'request_evidence.json'}))


if __name__=='__main__':main()
