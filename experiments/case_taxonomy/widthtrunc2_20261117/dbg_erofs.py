import sys; sys.argv=["x"]
import widthtrunc2 as M
rows,_,_=M.analyze("2d8c7edcb661^")
for r in rows:
    if "erofs/zmap" in r["file"]: print({k:r.get(k) for k in ("line","func","form","where","expr","only64")})
