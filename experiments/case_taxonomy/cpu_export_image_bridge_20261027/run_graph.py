"""Analyze the four copied ELF pairs. Preserve failed per-profile diagnostics."""
from pathlib import Path
import json

from elf64 import ELF64
from link_graph import analyze

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'cpu_source_policy_20261027/analysis_attempt2'
PROFILES=['old_x86_64','fixed_x86_64','old_s390','fixed_s390']

def main():
    out=HERE/'linked_graphs_final'; out.mkdir(exist_ok=False)
    rows=[]
    for profile in PROFILES:
        proof=json.loads((PREVIOUS/(profile+'_effective_source.json')).read_bytes())
        arrays={name:value['members'] for name,value in proof['projection']['evidence']['arrays'].items()}
        try:
            obj=ELF64(HERE/'objects'/profile/'topology.o')
            image=ELF64(HERE/'images'/profile/'vmlinux')
            graph=analyze(obj,image,arrays)
        except (ValueError,KeyError,IndexError) as exc:
            graph={'status':'insufficient','error':str(exc)}
        graph['profile']=profile
        (out/(profile+'.json')).write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        row={'profile':profile,'status':graph['status'],'functions':len(graph.get('functions',[])),
             'data_objects':len(graph.get('data_objects',[])),'error':graph.get('error')}
        rows.append(row); print(json.dumps(row),flush=True)
    (HERE/'graph_results_final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
