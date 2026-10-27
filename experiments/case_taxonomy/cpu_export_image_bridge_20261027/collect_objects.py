"""Compile the previous frozen CPP only, never mutate historical build files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent/'cpu_source_policy_20261027'
BASE = HERE.parent/'die_arch_contract_20261013/runtime/profiles'
PROFILES = ['old_x86_64','fixed_x86_64','old_s390','fixed_s390']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def need(value,reason):
    if not value:
        raise ValueError(reason)

def collect(profile):
    out = HERE/'objects'/profile
    out.mkdir(parents=True,exist_ok=False)
    build = json.loads((BASE/profile/'build.json').read_bytes())
    source = PREVIOUS/'preprocessing'/profile
    receipt = json.loads((source/'receipt.json').read_bytes())
    command = json.loads((source/'command.json').read_bytes())
    root = Path(build['build_directory'])
    paths = {'image':Path(build['image']),'object':root/'drivers/base/topology.o',
             'config':root/'.config','autoconf':root/'include/generated/autoconf.h',
             'command':root/'drivers/base/.topology.o.cmd','vmlinux':root/'vmlinux'}
    before = {name:sha(path) for name,path in paths.items()}
    for name in ['image','object','config','autoconf','command']:
        need(before[name]==receipt['before_sha256'][name],'previous_identity_changed:'+name)
    need(sha(source/'topology.i')==receipt['preprocessed_sha256'],'frozen_CPP_changed')
    argv = command['original_argv']
    need(argv.count('-c')==argv.count('-o')==1,'unexpected_compile_options')
    filtered, removed, index = [],[],0
    while index < len(argv):
        arg=argv[index]
        if arg in ['-I','-include','-isystem','-iquote','-imacros']:
            removed.extend(argv[index:index+2]); index+=2; continue
        if arg.startswith(('-Wp,-MMD,','-I','-D','-U')) or arg=='-nostdinc':
            removed.append(arg); index+=1; continue
        filtered.append(arg); index+=1
    compiler=shutil.which(filtered[0]); need(compiler is not None,'compiler_missing')
    need(sha(Path(compiler))==receipt['compiler_sha256'],'compiler_changed_since_CPP')
    filtered[0]=compiler
    filtered[filtered.index('-o')+1]=str(out/'topology.o')
    need(filtered[-1]==build['source_tree']+'/drivers/base/topology.c','unexpected_TU')
    filtered[-1]=str(source/'topology.i')
    filtered[1:1]=['-x','cpp-output']
    env=os.environ.copy()
    for name in ['CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','DEPENDENCIES_OUTPUT','SUNPRO_DEPENDENCIES']:
        env.pop(name,None)
    env['LC_ALL']='C'
    save(out/'command.json',{'argv':filtered,'cwd':str(root),'removed_preprocessing_options':removed,
                              'input_kind':'frozen previously expanded GCC CPP','no_source_reread_or_make':True})
    for name,path in paths.items():
        if name in ['object','command']:
            shutil.copyfile(path,out/('archived_topology.o' if name=='object' else 'archived_topology.o.cmd'))
    start=time.monotonic()
    with (out/'compile.stdout.log').open('xb') as stdout,(out/'compile.stderr.log').open('xb') as stderr:
        done=subprocess.run(filtered,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=120)
    result={'profile':profile,'revision':build['revision'],'arch':build['arch'],'compile_returncode':done.returncode,
            'compile_seconds':round(time.monotonic()-start,3),'frozen_CPP_sha256':sha(source/'topology.i'),
            'before_sha256':before,'compiler_sha256':sha(Path(compiler)),
            'new_object_compilation':True,'new_kernel_build':False,'new_boot':False}
    if done.returncode==0:
        result['pre_objtool_sha256']=sha(out/'topology.o')
        tail=command['omitted_post_compile_tokens']
        if tail:
            need(tail==[';','./tools/objtool/objtool','orc','generate','--no-fp','--uaccess','drivers/base/topology.o'],'unreviewed_post_compile_step')
            objtool=[str(root/'tools/objtool/objtool'),*tail[2:-1],str(out/'topology.o')]
            save(out/'objtool_command.json',{'argv':objtool,'tool_sha256':sha(Path(objtool[0])),'modifies_only':str(out/'topology.o')})
            with (out/'objtool.stdout.log').open('xb') as stdout,(out/'objtool.stderr.log').open('xb') as stderr:
                post=subprocess.run(objtool,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=120)
            result['objtool_returncode']=post.returncode
        else:
            result['objtool_returncode']=None
        result['rebuilt_object_sha256']=sha(out/'topology.o')
        result['whole_object_byte_equal']=result['rebuilt_object_sha256']==before['object']
    result['after_sha256']={name:sha(path) for name,path in paths.items()}
    need(result['before_sha256']==result['after_sha256'],'old_build_mutated')
    save(out/'receipt.json',result)
    print(json.dumps(result),flush=True)
    return result

def main():
    need(not (HERE/'object_collection.json').exists(),'preserve_object_collection')
    rows=[collect(profile) for profile in PROFILES]
    save(HERE/'object_collection.json',{'rows':rows,'new_object_compilations':len(rows),'new_kernel_builds':0,'new_boots':0})

if __name__=='__main__':
    main()
