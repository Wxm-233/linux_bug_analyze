from collect import *

def group(path):
    if path.endswith('.mod.c'): return 'module_metadata'
    p=path.removeprefix('@build/')
    if p.startswith('arch/') and '/generated/' in p: return 'arch_generated_interface'
    if p.startswith('include/generated/'): return 'public_generated'
    return 'other_generated'

def main():
    out={}
    for arch in e.ARCHES:
        syms={s['id']:s for s in read(OLD/f'symbols_{arch}.json')}
        groups=defaultdict(lambda:{'points':0,'ids':set(),'by_direction':Counter(),'by_kind':Counter(),'files':Counter(),'examples':[]})
        nongenerated=set(); defpoints=Counter(); uses=Counter()
        with gzip.open(OLD/f'boundary_{arch}.jsonl.gz','rt') as stream:
            for line in stream:
                r=json.loads(line);sid=r['symbol_id'];s=syms[sid];f=r['use']['file']; uses[sid]+=1
                if s['definition']['file'].startswith('@build/'): defpoints[group(s['definition']['file'])]+=1
                if not f.startswith('@build/'):
                    nongenerated.add(sid);continue
                g=groups[group(f)];g['points']+=1;g['ids'].add(sid);g['files'][f]+=1;g['by_direction'][r['direction']]+=1;g['by_kind'][s['kind']]+=1
                if len(g['examples'])<8:g['examples'].append(r|{'symbol':s})
        generated_ids=set().union(*(g['ids'] for g in groups.values()))
        packed={}
        for k,g in groups.items():
            exclusive=g['ids']-nongenerated-set().union(*(v['ids'] for kk,v in groups.items() if kk!=k))
            packed[k]={**g,'ids':sorted(g['ids']),'symbols':len(g['ids']),'exclusive_symbols':len(exclusive),'exclusive_ids':sorted(exclusive),'files':dict(g['files'])}
        out[arch]={'original_symbols':len(syms),'original_points':sum(uses.values()),'generated_use_symbols':len(generated_ids),
                   'generated_use_points':sum(g['points'] for g in groups.values()),'only_generated_use_symbols':len(generated_ids-nongenerated),
                   'groups':packed,'generated_definition_symbols':dict(Counter(group(s['definition']['file']) for s in syms.values() if s['definition']['file'].startswith('@build/'))),
                   'generated_definition_points':dict(defpoints)}
        print(arch,json.dumps({k:v for k,v in out[arch].items() if k!='groups'}))
        print({k:{f:v for f,v in g.items() if f in ['symbols','points','exclusive_symbols','by_direction','by_kind']} for k,g in packed.items()})
        # Read content and generating rules for every generated use file; limit saved contents to 160 lines.
        evidence=[]
        build=BASE/f'{arch}_defconfig'
        for f in sorted(set().union(*(g['files'].keys() for g in groups.values()))):
            fp=build/f.removeprefix('@build/')
            evidence.append({'file':f,'sha256':e.sha256(fp),'content':context(fp,list(range(1, min(160,len(fp.read_text(errors='replace').splitlines()))+1)),0)})
        write(f'evidence/generated_{arch}.json',evidence)
    write('generated_analysis.json',{'architectures':out,'interpretation':{'module_metadata':'单列构建元数据；不作为运行时接口候选，源模块正文中的引用仍保留。其层与模块源路径一致，不能全算架构。','arch_generated_interface':'保留；系统调用入口与ABI表含真实接口关系。','public_generated':'按公共来源处理；不能因为在O=中就归架构。','other_generated':'单列核查，宿主工具应排除，运行时生成实现按生成规则归层。'}})
if __name__=='__main__':main()
