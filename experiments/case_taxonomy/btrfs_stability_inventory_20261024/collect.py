"""Mechanical git-source inventory only; no writer completeness inference."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
REPO=Path('/root/repos/linux')
REVISIONS={'parent':'0d977e0eba234e01a60bdde27314dc21374201b3',
           'fix':'6f93e834fa7c5faa0372e46828b4b2a966ac61d7'}
PATTERNS=['super_copy','btrfs_set_super_sectorsize','btrfs_super_sectorsize']

def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args])

def main():
    out=HERE/'source_inventory'
    if out.exists(): raise RuntimeError('preserve existing inventory')
    out.mkdir()
    manifest={'kind':'lexical_inventory_not_semantic_analysis','patterns':PATTERNS,'scope':'fs/btrfs',
              'limitations':['No alias/callgraph/CFG analysis','No exhaustive writer or publication proof',
                             'No model call; no use of refused partial analysis'], 'versions':[]}
    for mode,revision in REVISIONS.items():
        assert git('rev-parse',revision+'^{commit}').decode().strip()==revision
        args=['grep','-n','-F']
        for pattern in PATTERNS: args+=['-e',pattern]
        raw=git(*args,revision,'--','fs/btrfs')
        (out/(mode+'.grep.txt')).write_bytes(raw)
        hits=[]
        files={}
        for line in raw.decode('utf-8').splitlines():
            commit,path,number,text=line.split(':',3)
            assert commit==revision
            hits.append(dict(path=path,line=int(number),text=text))
            files[path]=None
        folder=out/mode;folder.mkdir()
        for path in files:
            content=git('show',revision+':'+path)
            target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            lines=content.decode('utf-8').splitlines()
            files[path]=dict(blob=git('rev-parse',revision+':'+path).decode().strip(),
                sha256=hashlib.sha256(content).hexdigest(),lines=len(lines),artifact=str(target.relative_to(HERE)))
        for hit in hits:
            lines=(folder/hit['path']).read_text().splitlines()
            assert lines[hit['line']-1]==hit['text']
        manifest['versions'].append(dict(mode=mode,revision=revision,files=files,hits=hits,
            hit_lines=len(hits),file_count=len(files),grep_sha256=hashlib.sha256(raw).hexdigest()))
    (HERE/'inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:v[k] for k in ('mode','revision','hit_lines','file_count')} for v in manifest['versions']]))

if __name__=='__main__':main()
