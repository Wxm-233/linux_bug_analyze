"""Bounded adapter for registered Btrfs mount/extent experiments, not source inference.

The caller supplies the planned requests and sizes. Missing, ambiguous or conflicting
evidence raises EvidenceError. Same filesystem/inode identity is an archive binding,
not a proof of kernel pointer identity or the first-consumption state.
"""
import re
import hashlib


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def one(pattern, text, label):
    matches = list(re.finditer(pattern, text, re.M))
    require(len(matches) == 1, 'missing/ambiguous ' + label)
    return matches[0]


def project(boot, superblock, tree, *, requests, sizes, context_id):
    require(len(set(requests)) == len(requests) and len(set(sizes)) == len(sizes), 'duplicate protocol input')
    require(context_id and requests and sizes, 'empty protocol input')
    one(r'^EXPERIMENT_DONE failures=0$', boot, 'completion')
    require(not any(x in boot for x in ['ERROR step=', 'Kernel panic', 'Oops:', 'WARNING:', 'BUG:']), 'failed runtime')
    page = int(one(r'^PAGE_SIZE=(\d+)$', boot, 'page size')[1])
    fsid = one(r'^fsid\s+([0-9a-f-]+)$', superblock, 'super fsid')[1]
    tree_ids = set(re.findall(r'^fs uuid ([0-9a-f-]+)$', tree, re.M))
    one(r'^fs tree key \(FS_TREE ROOT_ITEM 0\)\s*$', tree, 'root5 tree identity')
    boot_ids = set(re.findall(r'BTRFS: device fsid ([0-9a-f-]+)', boot))
    require(tree_ids == boot_ids == {fsid}, 'filesystem UUID mismatch')
    sector = int(one(r'^sectorsize\s+(\d+)$', superblock, 'sector size')[1])
    node = int(one(r'^nodesize\s+(\d+)$', superblock, 'node size')[1])
    actual = [int(x) for x in re.findall(r'^MOUNT request=(\d+) rc=0 errno=0$', boot, re.M)]
    require(actual == list(requests), 'mount order/count differs from registered input')
    effective = [int(x) for x in re.findall(r'BTRFS info \(device vda\): max_inline at (\d+)', boot)]
    mounts = re.findall(r'^/dev/vda /mnt btrfs (.*)$', boot, re.M)
    require(len(effective) == len(mounts) == len(requests), 'missing/extra option observation')
    for value, line in zip(effective, mounts):
        require('subvolid=5,' in line and line.startswith('rw,'), 'unexpected mount root/mode')
        displayed = re.search(r'max_inline=(\d+)', line)
        require(int(displayed[1]) == value if displayed else value == 2048, 'mount option disagreement')
    limit = dict(zip(requests, effective))
    observed = re.findall(r'^FILE option=(\d+) size=(\d+) inode=(\d+) blocks=(\d+) readback=1$', boot, re.M)
    persisted = re.findall(r'^PERSISTED option=(\d+) size=(\d+) equal=1$', boot, re.M)
    require(len(re.findall(r'^FILE ', boot, re.M)) == len(observed), 'malformed/failed file observation')
    require(len(re.findall(r'^PERSISTED ', boot, re.M)) == len(persisted), 'malformed/failed persistence observation')
    frames = re.split(r'^MOUNT request=\d+ rc=0 errno=0$', boot, flags=re.M)[1:]
    for request, frame in zip(requests, frames):
        pairs = re.findall(r'^(?:FILE|PERSISTED) option=(\d+) size=(\d+)', frame, re.M)
        require(len(pairs) == 2 * len(sizes) and all(int(o) == request for o, _ in pairs), 'file record belongs to another mount interval')
    planned = {(o, s) for o in requests for s in sizes}
    require(len(observed) == len(planned) and {(int(x[0]), int(x[1])) for x in observed} == planned, 'missing/duplicate file observation')
    require(len(persisted) == len(planned) and {(int(o), int(s)) for o, s in persisted} == planned, 'missing/duplicate persistence observation')
    require(len({x[2] for x in observed}) == len(observed), 'inode reused across distinct files')
    items = list(re.finditer(r'^\s*item \d+ key \(([^\n]+)\)(.*?)(?=\n\s*item \d+ key |\Z)', tree, re.M | re.S))
    files = []
    for opt, size, inode, blocks in observed:
        opt, size = int(opt), int(size)
        refs = [m for m in items if re.fullmatch(inode + r' INODE_REF \d+', m[1])]
        ext = [m for m in items if re.fullmatch(inode + r' EXTENT_DATA \d+', m[1])]
        info = [m for m in items if m[1] == inode + ' INODE_ITEM 0']
        require(len(refs) == len(ext) == len(info) == 1, 'missing/ambiguous inode/ref/extent')
        require(ext[0][1] == inode + ' EXTENT_DATA 0', 'unsupported extent offset')
        name = one(r'name: ([^\n]+)$', refs[0][2], 'file name')[1]
        require(name == f'option{opt}_size{size}', 'file identity mismatch')
        actual_size = int(one(r'\s*generation \d+ transid \d+ size (\d+) nbytes \d+', info[0][2], 'inode size')[1])
        require(size == actual_size, 'inode size mismatch')
        kind = one(r'\s*generation \d+ type (\d+) \((\w+)\)', ext[0][2], 'extent type')
        require((kind[1], kind[2]) in [('0', 'inline'), ('1', 'regular')], 'unsupported extent type')
        require('compression 0 (none)' in ext[0][2], 'compressed/unknown extent')
        if kind[2] == 'inline':
            ilen = one(r'\s*inline extent data size (\d+) ram_bytes (\d+)', ext[0][2], 'inline size')
            require(int(ilen[1]) == int(ilen[2]) == size, 'inline length mismatch')
        files.append({'request': opt, 'effective_limit': limit[opt], 'size': size, 'inode': int(inode),
                      'object_id': f'{context_id}:{fsid}:root5:inode{inode}', 'name': name,
                      'extent': kind[2], 'persisted_equal': True,
                      'tree_lines': [tree.count('\n', 0, ext[0].start()) + 1, tree.count('\n', 0, ext[0].end()) + 1]})
    return {'context_id': context_id, 'basis': 'archived_runtime', 'origin': 'program_projection',
            'fsid': fsid, 'page_size': page, 'sector_size': sector, 'node_size': node,
            'requests': list(requests), 'effective_limits': limit, 'files': files,
            'evidence_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in [('boot', boot), ('super', superblock), ('tree', tree)]},
            'first_consumption_binding': 'insufficient', 'whole_path': 'insufficient'}


def local_checks(facts):
    """Human-selected predicates; no converse promise that eligible implies inline."""
    caps = [{'request': r, 'effective': v, 'reference': min(r, facts['sector_size']),
             'satisfied': v == min(r, facts['sector_size'])} for r, v in facts['effective_limits'].items()]
    bounds = [{'object_id': f['object_id'], 'status': ('satisfied' if f['size'] <= f['effective_limit'] else 'violated')
               if f['extent'] == 'inline' else 'not_applicable'} for f in facts['files']]
    return {'rule_origin': 'researcher_authored', 'scope': 'registered uncompressed single-extent development workload',
            'effective_cap': caps, 'inline_length_necessary_condition': bounds,
            'first_consumption': 'insufficient', 'whole_path': 'insufficient', 'automatic_requirement_inference': False}
