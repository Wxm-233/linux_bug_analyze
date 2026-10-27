"""Materialize the next fixed 16 representation metadata records only."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
source=PROJECT/'analysis_out/stratified-20260921/manifest.json'
raw=source.read_bytes();data=json.loads(raw)
assert len(data['samples'])==500
records=[];order=0
for index,row in enumerate(data['samples'],1):
    if row['stratum']!='representation':continue
    order+=1
    if 17<=order<=32:records.append(dict(pool_order=len(records)+1,representation_order=order,original_manifest_index=index,commit=row['hash'],subject=row['subject'],stratum=row['stratum'],band=row['band']))
    if order==32:break
assert len(records)==16
target=HERE/'metadata_pool.json';assert not target.exists()
target.write_text(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),metadata_only=True,pool_count=16,representation_start=17,representation_end=32,model_results_used=False,records=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(pool_count=16,source_sha256=hashlib.sha256(raw).hexdigest(),metadata_pool_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),ensure_ascii=False))
