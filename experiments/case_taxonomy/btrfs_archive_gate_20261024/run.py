"""Replay frozen external reviews through the artifact-integrity gate."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contract_archive import ArchiveError, load_verified_archive

def digest(data): return hashlib.sha256(data).hexdigest()
def save(name,data): (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    pins=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8-sig'))
    for p,h in pins.items():
        if digest((ROOT/p).read_bytes())!=h: raise ArchiveError('frozen dependency changed: '+p)
    # Load core only after verifying its frozen bytes.
    from linux_bug_analyze.contract_protocol import evaluate_contract
    relative='linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/registered_inputs.json'
    archive=ROOT/relative
    bundles,snapshots=load_verified_archive(archive,pins[relative])
    results=[evaluate_contract(b['contract'],b['ledger'],b['record']) for b in bundles]
    previous=json.loads((archive.parent/'results.json').read_text(encoding='utf-8'))['evaluations']
    assert results==previous and len(results)==12
    assert all(r['relation_at_deadline']==r['whole_path']=='insufficient' for r in results)
    # Controls modify only private byte maps; no original evidence is written.
    baseline={p:Path(p).read_bytes() for p in snapshots}
    baseline[str(archive)]=archive.read_bytes()
    source=bundles[0]['ledger']['documents']['source']['path']
    review=bundles[0]['ledger']['documents']['review']['path']
    boot=bundles[0]['ledger']['documents']['boot']['path']
    controls=[]
    names=('changed_source','changed_boot','changed_review','missing_source','changed_registry',
           'changed_source_and_local_hash','out_of_actual_lines','reference_overflow','unknown_document','wrong_revision')
    for name in names:
        memory=dict(baseline);items=copy.deepcopy(bundles);expected=pins[relative]
        if name in ('changed_source','changed_boot','changed_review'):
            path={'changed_source':source,'changed_boot':boot,'changed_review':review}[name]
            memory[path]+=b'\nCONTROL CORRUPTION\n'
        elif name=='missing_source': del memory[source]
        elif name=='changed_registry': memory[str(archive)]+=b' '
        elif name=='changed_source_and_local_hash':
            memory[source]+=b'\nCONTROL CORRUPTION\n'
            for b in items:
                for doc in b['ledger']['documents'].values():
                    if doc['path']==source: doc['sha256']=digest(memory[source])
            memory[str(archive)]=json.dumps(items).encode()
        else:
            # Explicitly trusted synthetic registries exercise structural validation,
            # separately from fixed-real-registry digest rejection.
            if name=='out_of_actual_lines': items[0]['ledger']['documents']['source']['end_line']=10**9
            elif name=='reference_overflow': items[0]['ledger']['claims']['authority']['references'][0]['end_line']=10**9
            elif name=='unknown_document': items[0]['ledger']['claims']['authority']['references'][0]['document']='absent'
            elif name=='wrong_revision': items[0]['ledger']['documents']['source']['context_revision']='other'
            memory[str(archive)]=json.dumps(items).encode();expected=digest(memory[str(archive)])
        try:
            load_verified_archive(archive,expected,read_bytes=lambda p: memory[p])
        except ArchiveError as exc:
            controls.append(dict(name=name,basis='synthetic_memory_mutation',
                integrity='rejected',relation_at_observation='insufficient',reason=str(exc),
                synthetic_trust_anchor=name in names[6:]))
        else: raise AssertionError('accepted '+name)
    save('results.json',dict(replayed_events=4,evaluations=results,verified_snapshots=snapshots,
        negative_controls=controls,new_boots=0,model_calls=0,independent_positives=0,independent_normals=0,
        boundary='Integrity of pinned review bytes and referenced snapshots only; not semantic truth or future immutability.'))
    print(f'12 unchanged evaluations; {len(snapshots)} verified reference snapshots; {len(controls)} corruption controls rejected; 0 model calls')

if __name__=='__main__': main()
