"""Depth-three same-side callee reachability over existing resolved call tables."""
from collections import Counter, defaultdict, deque
import gzip
from common import *

DEPTH=3

def bfs(seeds, edges, depth=DEPTH):
    distance={n:0 for n in seeds}
    parent={n:None for n in seeds}
    queue=deque(sorted(seeds))
    while queue:
        n=queue.popleft()
        if distance[n]==depth: continue
        for m in sorted(edges.get(n,())):
            if side(n[2])!=side(m[2]): continue
            if m not in distance:
                distance[m]=distance[n]+1
                parent[m]=n
                queue.append(m)
    return distance,parent

def run(arch,d,samples):
    sf=d/f'symbols_runtime_{arch}.json'
    syms=read(sf)
    by_id={s['id']:s for s in syms}
    seeds={key(s) for s in syms if s['kind']=='function'}
    nodes={key(s):s for s in syms if s['kind']=='function'}
    reasons={n:{'boundary_provider'} for n in seeds}
    points=set()
    for p in lines(d/f'boundary_runtime_{arch}.jsonl.gz'):
        if p['action']=='call' and by_id[p['symbol_id']]['kind']=='function':
            u=p['use']
            points.add((u['file'],u['line'],u['column'],key(by_id[p['symbol_id']])))
    edges=defaultdict(set)
    evidence={}
    cp=d/f'direct_calls_{arch}.jsonl.gz'
    source_kind='revised'
    if not cp.exists(): cp=OLD/cp.name; source_kind='old_binding_limitations'
    relation_count=0
    for row in lines(cp):
        relation_count+=1
        a,b=key(row['caller']),key(row['callee'])
        nodes[a]=row['caller']; nodes[b]=row['callee']
        edges[a].add(b)
        evidence[(a,b)]={'example_use':row['example_use'],'unit':row['unit']}
        u=row['example_use']
        if (u['file'],u['line'],u['column'],b) in points:
            seeds.add(a)
            reasons.setdefault(a,set()).add('caller_of_runtime_boundary_call')
    distance,parent=bfs(seeds,edges)
    frontier=sum(1 for a,v in distance.items() if v==DEPTH for b in edges.get(a,())
                 if side(a[2])==side(b[2]) and b not in distance)
    counts=Counter(distance.values())
    stats={'call_table':str(cp),'binding_source':source_kind,'input_sha256':sha(cp),
           'resolved_call_relations':relation_count,'graph_nodes':len(nodes),'seed_functions':len(seeds),
           'depth_limit':DEPTH,'new_nodes_by_depth':{str(k):counts[k] for k in range(4)},
           'cumulative_nodes_by_depth':{str(k):sum(v<=k for v in distance.values()) for k in range(4)},
           'candidate_functions':len(distance),'added_functions':len(distance)-len(seeds),
           'candidate_files':len({n[2] for n in distance}),
           'by_side':dict(Counter(side(n[2]) for n in distance)),
           'truncated_same_side_edges':frontier,
           'candidates_without_recorded_outgoing_calls':sum(not edges.get(n) for n in distance),
           'candidate_body_lines':None,'unresolved_or_indirect_calls_in_region':None}
    out=HERE/f'closure_nodes_{arch}.jsonl.gz'
    with gzip.open(out,'wt',encoding='utf-8') as f:
        for n,depth in sorted(distance.items(),key=lambda x:(x[1],x[0])):
            row={'symbol':nodes[n],'depth':depth,'seed_reasons':sorted(reasons.get(n,())),
                 'parent':nodes[parent[n]] if parent[n] is not None else None}
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    by_name=defaultdict(list)
    for n in distance: by_name[(n[2],nodes[n]['name'])].append(n)
    results=[]
    for s in samples:
        found=[]
        for ent in s['resolved_entities']:
            if ent['current_kind']!='function': continue
            for n in by_name.get((ent['current_file'],ent['current_name']),[]):
                if not any(r['start']<=n[3]<=r['end'] for r in ent['current_ranges']): continue
                chain=[]; p=n
                while p is not None:
                    chain.append({'symbol':nodes[p],'edge_to_next':evidence.get((p,chain[-1]['key'])) if chain else None,'key':p})
                    p=parent[p]
                chain.reverse()
                for v in chain: v.pop('key')
                found.append({'entity':{k:ent[k] for k in ('historical_file','historical_name','current_file','current_name')},
                              'depth':distance[n],'path':chain})
        direct=s['architectures'][arch]['hit']
        results.append({'id':s['id'],'check':s['check'],'direct_v2_hit':direct,
                        'closure_hit':bool(found),'combined_hit':direct or bool(found),
                        'closure_only':not direct and bool(found),
                        'new_internal_entity_matches':[r for r in found if r['depth']>0],
                        'matches':found})
    stats['samples_combined_hits']=sum(s['combined_hit'] for s in results)
    stats['samples_closure_only_ids']=[s['id'] for s in results if s['closure_only']]
    stats['by_check']={str(c):{'combined_hits':sum(s['check']==c and s['combined_hit'] for s in results),
                              'closure_only_ids':[s['id'] for s in results if s['check']==c and s['closure_only']]} for c in (1,2,3)}
    return stats,results

def main():
    check_criteria()
    samples=read(HERE/'sample_match_v2.json')['samples']
    all_stats={}; all_results={}
    for arch,d in revised().items():
        st,rs=run(arch,d,samples)
        all_stats[arch]=st; all_results[arch]=rs
        write(f'closure_{arch}.json',{'summary':st,'samples':rs})
        print(arch,json.dumps(st,ensure_ascii=False),flush=True)
    union=[]
    for i,s in enumerate(samples):
        union.append({'id':s['id'],'check':s['check'],
                      'combined_hit':any(all_results[a][i]['combined_hit'] for a in ARCHES),
                      'closure_only':not s['hit'] and any(all_results[a][i]['closure_hit'] for a in ARCHES)})
    write('closure_stats.json',{'depth':DEPTH,'architectures':all_stats,
        'union_combined_hits':sum(r['combined_hit'] for r in union),
        'union_closure_only_ids':[r['id'] for r in union if r['closure_only']],
        'union_by_check':{str(c):sum(r['check']==c and r['combined_hit'] for r in union) for c in (1,2,3)},
        'A081':'It modifies outer arch_xchg* macros as well, so V2 already hits the sample. __arch_xchg_masked is a macro, not a C call-graph node; its implementation requires macro dependency closure.'})

if __name__=='__main__': main()
