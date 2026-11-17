import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
lo=int(sys.argv[1]) if len(sys.argv)>1 else 0
hi=int(sys.argv[2]) if len(sys.argv)>2 else 100
rows=read(HERE/'evidence/sample_inputs.json')
for r in rows[lo:hi]:
    print('\n###',r['id'],r['check'],r['subject'],r['reason'])
    print('FUNCTIONS',r['functions'])
    for f in r['current']:
        print('CURRENT',f['file'],'exists',f['exists'],'compiled',[u['id'] for u in f['compiled_units']],'uses',f['boundary_use_count'])
        for s in f['searches']: print(s['command'],s['exit_code'],s['stdout'].strip())
        # Full build evidence is preserved in sample_inputs.json.
    patch=(HERE/r['patch']).read_text()
    print('\n'.join(l for l in patch.splitlines() if l.startswith(('@@','diff ','+','-'))))
