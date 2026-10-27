"""Validate each archived boot image's payload against its cached linked ELF."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zlib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'die_arch_contract_20261013/runtime/profiles'
PROFILES=['old_x86_64','fixed_x86_64','old_s390','fixed_s390']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def need(value,reason):
    if not value:
        raise ValueError(reason)

def collect(profile):
    out=HERE/'images'/profile; out.mkdir(parents=True,exist_ok=False)
    build=json.loads((BASE/profile/'build.json').read_bytes())
    root=Path(build['build_directory']); image=Path(build['image']); vmlinux=root/'vmlinux'
    before={'image':sha(image),'vmlinux':sha(vmlinux)}
    need(before['image']==build['image_sha256'],'boot_image_changed')
    for src,name in [(image,'boot_image'),(vmlinux,'vmlinux')]:
        shutil.copyfile(src,out/name)
    if build['arch']=='x86_64':
        argv=['objcopy','-R','.comment','-S',str(out/'vmlinux'),str(out/'expected_payload')]
    else:
        argv=['s390x-linux-gnu-objcopy','-O','binary','--remove-section=.comment','--remove-section=.vmlinux.info','-S',str(out/'vmlinux'),str(out/'expected_payload')]
    tool=shutil.which(argv[0]); need(tool is not None,'objcopy_missing'); argv[0]=tool
    with (out/'objcopy.stdout.log').open('xb') as stdout,(out/'objcopy.stderr.log').open('xb') as stderr:
        done=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=60)
    need(done.returncode==0,'payload_transform_failed')
    raw=(out/'boot_image').read_bytes(); expected=(out/'expected_payload').read_bytes()
    candidates=[]; start=0
    while True:
        position=raw.find(b'\x1f\x8b\x08',start)
        if position<0:
            break
        start=position+1
        try:
            dec=zlib.decompressobj(16+zlib.MAX_WBITS)
            payload=dec.decompress(raw[position:],128*1024*1024)
            need(dec.eof and not dec.unconsumed_tail,'gzip_not_complete_within_limit')
            consumed=len(raw)-position-len(dec.unused_data)
            row={'offset_in_image':position,'compressed_bytes':consumed,'decompressed_bytes':len(payload),
                 'decompressed_sha256':hashlib.sha256(payload).hexdigest(),'matches_transformed_vmlinux':payload==expected}
            if row['matches_transformed_vmlinux']:
                (out/'actual_payload').write_bytes(payload)
                (out/'payload.gz').write_bytes(raw[position:position+consumed])
        except (zlib.error,ValueError) as exc:
            row={'offset_in_image':position,'valid_complete_stream':False,'error_type':type(exc).__name__}
        candidates.append(row)
    good=[row for row in candidates if row.get('matches_transformed_vmlinux')]
    need(len(good)==1,'unique_image_payload_not_established')
    after={'image':sha(image),'vmlinux':sha(vmlinux)}
    need(before==after,'historical_image_inputs_changed')
    # Preserve pinned build-rule sources as provenance, not shell instructions.
    rules=['arch/'+('x86' if build['arch']=='x86_64' else 's390')+'/boot/compressed/Makefile','scripts/link-vmlinux.sh']
    rule_rows=[]
    for name in rules:
        path=Path(build['source_tree'])/name; content=path.read_bytes()
        wanted=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',build['revision']+':'+name],text=True).strip()
        actual=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        need(wanted==actual,'pinned_build_rule_mismatch')
        target=out/'rules'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
        rule_rows.append({'path':name,'git_blob':actual,'sha256':sha(path)})
    result={'profile':profile,'revision':build['revision'],'arch':build['arch'],'before_sha256':before,'after_sha256':after,
            'objcopy_argv':argv,'objcopy_sha256':sha(Path(tool)),'payload_candidates':candidates,'payload':good[0],
            'payload_matches_linked_kernel':True,'rules':rule_rows,'new_build':False,'new_boot':False}
    save(out/'receipt.json',result)
    print(json.dumps({'profile':profile,'payload_matches':True,'payload_bytes':good[0]['decompressed_bytes']}),flush=True)
    return result

def main():
    need(not (HERE/'image_collection.json').exists(),'preserve_image_collection')
    rows=[collect(profile) for profile in PROFILES]
    save(HERE/'image_collection.json',{'rows':rows,'new_image_payload_extractions':len(rows),'new_boots':0})

if __name__=='__main__':
    main()
