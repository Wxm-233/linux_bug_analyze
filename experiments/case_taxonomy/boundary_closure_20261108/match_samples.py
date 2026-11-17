"""V2 descriptive presence on the three revised runtime pools."""
from bisect import bisect_left
from collections import Counter, defaultdict
from common import *
from c_ranges import scrub

def compatible(a,b):
    return a==b  # In particular an enum type is not an enum constant.

def body_start(path, r):
    if r['kind']!='function': return r['start']
    fp=KSRC/path
    if not fp.is_file(): return r['end']+1
    text='\n'.join(fp.read_text(encoding='utf-8',errors='replace').splitlines()[r['start']-1:r['end']])
    clean=scrub(text)
    at=clean.find('{')
    return r['start']+clean[:at].count('\n') if at>=0 else r['end']+1

def stats(rows, arch=None):
    hit=lambda r: r['architectures'][arch]['hit'] if arch else r['hit']
    return {'total':len(rows),'hits':sum(hit(r) for r in rows),
            'by_check':{str(c):{'total':sum(r['check']==c for r in rows),
                                'hits':sum(r['check']==c and hit(r) for r in rows),
                                'hit_ids':[r['id'] for r in rows if r['check']==c and hit(r)],
                                'miss_ids':[r['id'] for r in rows if r['check']==c and not hit(r)]} for c in (1,2,3)},
            'empty_legacy_functions_hits':sum(not r['legacy_functions'] and hit(r) for r in rows),
            'new_vs_legacy_riscv_ids':[r['id'] for r in rows if hit(r) and not r['legacy_hit']],
            'lost_vs_legacy_riscv_ids':[r['id'] for r in rows if not hit(r) and r['legacy_hit']]}

def main():
    check_criteria()
    source=read(HERE/'evidence/sample_entities.json')
    ranges=read(HERE/'evidence/current_ranges.json')
    mappings=read(HERE/'history_mappings.json')
    target_files=set(ranges)
    for s in source:
        target_files.update(f['new_path'] for f in s['files'])
        target_files.update(f['old_path'] for f in s['files'])
    pools={}
    manifests={}
    for arch,d in revised().items():
        sf=d/f'symbols_runtime_{arch}.json'
        if not sf.exists(): sf=d/f'symbols_{arch}_runtime.json'
        if not sf.exists():
            sf=next(p for p in d.glob('*symbol*runtime*') if p.suffix=='.json')
        pf=d/f'boundary_runtime_{arch}.jsonl.gz'
        symbols=read(sf)
        by_file=defaultdict(list)
        for sym in symbols: by_file[sym['definition']['file']].append(sym)
        points=defaultdict(list)
        for r in lines(pf):
            if r['use']['file'] in target_files: points[r['use']['file']].append(r)
        pools[arch]=(symbols,by_file,points)
        manifests[arch]=inputs_manifest([sf,pf])
        print(arch,'loaded',len(symbols),'symbols and',sum(map(len,points.values())),'relevant points',flush=True)
    rows=[]
    for sample in source:
        s={k:v for k,v in sample.items() if k!='files'}
        s['architectures']={}
        s['resolved_entities']=[]
        for ent in s['entities']:
            specific=[m for m in mappings if m['id']==s['id'] and m['old_file']==ent['file'] and m['old_name']==ent['name']]
            nf,nn=(specific[0]['new_file'],specific[0]['new_name']) if specific else (ent['file'],ent['name'])
            nk=(specific[0].get('new_kind') or ent['kind']) if specific else ent['kind']
            found=[r for r in ranges.get(nf,{}).get('declarations',[]) if r['name']==nn and compatible(nk,r['kind'])]
            for r in found: r['body_start']=body_start(nf,r)
            s['resolved_entities'].append({'historical_file':ent['file'],'historical_name':ent['name'],
                'kind':ent['kind'],'current_kind':nk,'current_file':nf,'current_name':nn,'current_ranges':found,
                'mapping':specific[0] if specific else None})
        for arch,(symbols,by_file,points) in pools.items():
            evidence=[]
            for ent in s['resolved_entities']:
                f=ent['current_file']
                for r in ent['current_ranges']:
                    defs=[sym for sym in by_file.get(f,[]) if sym['name']==ent['current_name']
                          and compatible(ent['current_kind'],sym['kind']) and r['start']<=sym['definition']['line']<=r['end']]
                    uses=[p for p in points.get(f,[]) if r['body_start']<=p['use']['line']<=r['end']] if ent['current_kind']=='function' else []
                    if defs or uses:
                        evidence.append({'historical_file':ent['historical_file'],'historical_name':ent['historical_name'],
                                         'current_file':f,'current_name':ent['current_name'],'kind':ent['kind'],'range':r,
                                         'modes':(['boundary_provider'] if defs else [])+(['function_body_use'] if uses else []),
                                         'boundary_symbols':defs,'body_use_count':len(uses),'body_use_examples':uses[:5],
                                         'mapped':ent['mapping'] is not None})
            intersections=[]
            for f in sample['files']:
                paths={f['old_path'],f['new_path']}
                paths.update(v.get('alignment_current_path') for v in f['versions'] if v.get('alignment_current_path'))
                for path in sorted(paths):
                    if not by_file.get(path) and not points.get(path): continue
                    alignment=[(v,a) for v in f['versions'] if v.get('alignment_current_path')==path
                               for a in v.get('aligned_changed_lines',[])]
                    locations=[p['use']['line'] for p in points.get(path,[])]
                    locations.extend(sym['definition']['line'] for sym in by_file.get(path,[]))
                    distances=[min(abs(a['current']-n) for n in locations) for _,a in alignment]
                    min_distance=min(distances) if distances else None
                    intersections.append({'file':path,'use_points':len(points.get(path,[])),
                        'definition_symbols':len(by_file.get(path,[])), 'aligned_changed_lines':len(alignment),
                        'minimum_line_distance':min_distance,
                        'near_within_5':min_distance<=5 if min_distance is not None else None})
            known=[r['minimum_line_distance'] for r in intersections if r['minimum_line_distance'] is not None]
            s['architectures'][arch]={'hit':bool(evidence),'evidence':evidence,'file_intersections':intersections,
                'file_intersects':bool(intersections),'file_only':bool(intersections) and not evidence,
                'repair_line_near':min(known)<=5 if known else None,
                'file_intersection_but_far':bool(known) and min(known)>5,
                'file_intersection_alignment_unknown':bool(intersections) and not known}
        s['hit']=any(a['hit'] for a in s['architectures'].values())
        rows.append(s)
    summary={'method':'changed declarations recovered from full parent/fixed blobs; runtime provider or function body use; explicit mappings only',
             'scope':'cross-version descriptive presence; no defect detector or historical-trigger/config coverage claim',
             'criteria_sha256':check_criteria(),'by_arch':{a:stats(rows,a) for a in ARCHES},'union':stats(rows),
             'historical_defect_detection_recall':None}
    for arch in ARCHES:
        summary['by_arch'][arch]['file_intersection_without_entity_ids']=[r['id'] for r in rows if r['architectures'][arch]['file_only']]
        summary['by_arch'][arch]['file_intersection_far_ids']=[r['id'] for r in rows if r['architectures'][arch]['file_intersection_but_far']]
        summary['by_arch'][arch]['file_intersection_alignment_unknown_ids']=[r['id'] for r in rows if r['architectures'][arch]['file_intersection_alignment_unknown']]
        summary['by_arch'][arch]['hit_but_far_ids']=[r['id'] for r in rows if r['architectures'][arch]['hit'] and r['architectures'][arch]['file_intersection_but_far']]
    write('sample_match_v2.json',{'summary':summary,'samples':rows})
    write('evidence/runtime_input_manifest.json',manifests)
    md=['# 我按真正修改的实体重做匹配','', '命中只表示当前候选区域存在；文件相交和触发配置另列。','',
        '|样本|检查|RV/ARM/X86|修改实体|审计限制|','|---|---:|---|---|---|']
    for r in rows:
        flags='/'.join('是' if r['architectures'][a]['hit'] else '否' for a in ARCHES)
        entities='、'.join(f"{e['kind']}:{e['name']}" for e in r['entities']) or '未恢复C实体'
        md.append(f"|{r['id']}|{r['check']}|{flags}|{entities}|{r.get('audit_judgment') or '旧命中；不代表配置/语义已验证'}|")
    (HERE/'sample_match_v2.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({a:{'hits':summary['by_arch'][a]['hits'],'by_check':{c:v['hits'] for c,v in summary['by_arch'][a]['by_check'].items()}} for a in ARCHES}|{'union':summary['union']['hits']},ensure_ascii=False))

if __name__=='__main__': main()
