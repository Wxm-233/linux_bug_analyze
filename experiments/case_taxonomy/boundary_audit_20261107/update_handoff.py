"""Replace only section IV; byte-verify the rest of the handoff stays unchanged."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    target=HERE.parents[3]/'交接文档.md'
    before=target.read_bytes()
    start=before.index('## 四、当前进度'.encode('utf-8'))
    end=before.index('## 五、每轮实验怎么做'.encode('utf-8'))
    section=(HERE/'handoff_section4.md').read_bytes()
    if b'\r\n' in before:section=section.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    target.write_bytes(before[:start]+section+before[end:])
    after=target.read_bytes();new_end=after.index('## 五、每轮实验怎么做'.encode('utf-8'))
    assert after[:start]==before[:start] and after[new_end:]==before[end:]
    report={'target':str(target),'only_section_4_changed':True,
        'prefix_sha256':digest(before[:start]),'suffix_sha256':digest(before[end:]),
        'section_4_sha256':digest(section)}
    (HERE/'evidence/handoff_update_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
