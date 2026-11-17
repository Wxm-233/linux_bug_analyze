import sys, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import enumerate as e
w=Path(os.environ['KBUILD'])/'enumeration/selftest'
for entry in e.load_entries(w/'compile_commands.json')[:3]:
 os.chdir(entry.directory)
 tu=e.cindex.Index.create().parse(str(entry.source), args=e.parse_args(entry), options=e.DETAIL_RECORD)
 for c in tu.cursor.walk_preorder():
  if c.kind in (e.K.VAR_DECL,e.K.DECL_REF_EXPR,e.K.CALL_EXPR):
   r=c.referenced; d=r.get_definition() if r else None
   print(c.kind,c.spelling,c.location.line,c.location.column,'hash',c.hash,'ref',r.kind if r else None,'link',r.linkage if r else None,'def',d.location if d else None, 'isdef',c.is_definition())
