"""Declare and apply only two observational locations in the isolated archive."""
import difflib
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=Path('/root/.cache/linux-bug-analyze/shmem-contract-20261012/runtime')
REV='3390916aca7af1893ed2ebcdfee1d6fdb65bb058'
def edit_function(text,name,old,new):
    start=text.index(name);end=text.index('\n}',start)+2
    body=text[start:end]
    assert body.count(old)==1,(name,old)
    return text[:start]+body.replace(old,new,1)+text[end:]

def instrument(original):
    """Same observational statements for either historical shmem base."""
    text=original.decode()
    text=edit_function(text,'static struct folio *shmem_alloc_hugefolio(',
        '\tmpol_cond_put(mpol);\n',
        '\tmpol_cond_put(mpol);\n'
        '\t/* Lab-only observation; allocation and return behavior are unchanged. */\n'
        '\tif (current->pid == 1)\n'
        '\t\ttrace_printk("SC_ALLOC page=%px order=%u requested=%u\\n",\n'
        '\t\t\tpage, page ? folio_order(page_folio(page)) : 0,\n'
        '\t\t\t(unsigned int)HPAGE_PMD_ORDER);\n')
    fields='"SC_INSERT folio=%px mapping=%px index=%lu fmap=%px findex=%lu order=%u rc=%d\\n"'
    text=edit_function(text,'static int shmem_add_to_page_cache(',
        '\t\treturn xas_error(&xas);\n',
        '\t\tif (current->pid == 1)\n'
        '\t\t\ttrace_printk('+fields+',\n'
        '\t\t\t\tfolio, mapping, index, folio->mapping, folio->index,\n'
        '\t\t\t\tfolio_order(folio), xas_error(&xas));\n'
        '\t\treturn xas_error(&xas);\n')
    text=edit_function(text,'static int shmem_add_to_page_cache(',
        '\treturn 0;\n',
        '\tif (current->pid == 1)\n'
        '\t\ttrace_printk('+fields+',\n'
        '\t\t\tfolio, mapping, index, folio->mapping, folio->index,\n'
        '\t\t\tfolio_order(folio), 0);\n'
        '\treturn 0;\n')
    return text.encode()


def main():
    source=BASE/'old/linux/mm/shmem.c'
    assert (BASE/'old/source_revision').read_text().strip()==REV
    original=subprocess.check_output(['git','-C','/root/repos/linux','show',REV+':mm/shmem.c'])
    observed=instrument(original)
    if source.read_bytes() not in [original,observed]:raise RuntimeError('Unexpected source change')
    saved=BASE/'old/shmem.c.original'
    if saved.exists(): assert saved.read_bytes()==original
    else: saved.write_bytes(original)
    image=BASE/'old_arm64_64k/build/arch/arm64/boot/Image'
    prior=image.with_name('Image.unobserved')
    if not prior.exists():shutil.copyfile(image,prior)
    for name in ['error.json','probe_symbols.json','source_identity.json']:
        p=HERE/'old_arm64_64k'/name
        target=p.with_name(p.stem+'_attempt1.json')
        if p.exists() and not target.exists():target.write_bytes(p.read_bytes())
    patch=''.join(difflib.unified_diff(original.decode().splitlines(True),observed.decode().splitlines(True),
                                    fromfile='a/mm/shmem.c',tofile='b/mm/shmem.c'))
    (HERE/'observation.patch').write_text(patch)
    source.write_bytes(observed)
    receipt={'revision':REV,'changed_path':'mm/shmem.c',
             'original_sha256':hashlib.sha256(original).hexdigest(),
             'observed_sha256':hashlib.sha256(observed).hexdigest(),
             'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),
             'uninstrumented_image_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),
             'scope':'PID1-only allocation and insertion facts; original branches/returns/allocator preserved'}
    (BASE/'old/observation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (HERE/'observation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
