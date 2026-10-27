"""Materialize only the pre-registered 16-entry existing metadata pool."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
SOURCE=PROJECT/'analysis_out/stratified-20260921/manifest.json'

if __name__=='__main__':
    data=json.loads(SOURCE.read_text(encoding='utf-8'))
    assert len(data['samples'])==500
    selected=[]
    for i,row in enumerate(data['samples'],1):
        if row['stratum']!='representation':continue
        selected.append(dict(pool_order=len(selected)+1,original_manifest_index=i,
                             commit=row['hash'],subject=row['subject'],stratum=row['stratum'],band=row['band']))
        if len(selected)==16:break
    assert len(selected)==16
    result=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                metadata_only=True,pool_count=16,records=selected,model_results_used=False)
    p=HERE/'metadata_pool.json';assert not p.exists()
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in selected:print(json.dumps(row,ensure_ascii=False))
