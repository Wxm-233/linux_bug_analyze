"""Bounded metadata selection, locked parent CLI outputs, then patch unseal.

Runs in WSL. No model, compiler or kernel execution. Rules remain unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
ROOT = RULES.parents[2]
LINUX = Path('/root/repos/linux')
TOOLS = {
    'consumer': ('endian_consumer_single_revision.py', '71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c'),
    'producer': ('endian_producer_single_revision.py', '5f0a2823c0a3cc7eec501ab0f4478fb4c578e4a561becc61326e6a46880fe786'),
}
EXCLUDE_PREFIXES = ('fs/ocfs2/', 'fs/bcachefs/', 'fs/btrfs/', 'drivers/pwm/', 'drivers/firmware/')
EXCLUDE_FRAGMENTS = ('hisi_sas', 'mpt3sas', 'dw_mmc', 'idpf', 'fsl_raid', 'dw-axi', 'tegra241')


def now():
    return datetime.now(timezone.utc).isoformat()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


class Capture:
    def __init__(self, phase):
        self.phase = phase
        self.records = []

    def run(self, argv, acceptable=(0,)):
        number = len(self.records) + 1
        started = now()
        completed = subprocess.run(argv, cwd=LINUX, capture_output=True, check=False)
        item = dict(argv=argv, cwd=str(LINUX), started_at_utc=started,
                    completed_at_utc=now(), returncode=completed.returncode)
        for stream in ('stdout', 'stderr'):
            relative = f'commands/{self.phase}/{number:03d}.{stream}.bin'
            path = HERE / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as output:
                output.write(getattr(completed, stream))
            item[stream] = relative
            item[stream + '_sha256'] = sha(path)
        self.records.append(item)
        require(completed.returncode in acceptable, 'command failure: ' + repr(argv))
        return completed

    def finish(self):
        save(HERE / ('commands_' + self.phase + '.json'), self.records)


def tools_unchanged():
    for name, digest in TOOLS.values():
        require(sha(RULES / name) == digest, 'old rule changed: ' + name)


def check_lock(filename):
    lock = read(HERE / filename)
    for item in lock['files']:
        path = (HERE / item['path']).resolve()
        require(path.is_relative_to(RULES.resolve()) and sha(path) == item['sha256'], 'pre-lock changed')
    return lock


def seal(filename, paths, **fields):
    save(HERE / filename, dict(sealed_at_utc=now(), **fields,
        files=[dict(path=p.relative_to(HERE).as_posix() if p.is_relative_to(HERE) else '../' + p.name,
                    sha256=sha(p)) for p in sorted(set(paths))]))


def prepare():
    tools_unchanged()
    cap = Capture('prepare_complete')
    cap.run(['git', '--version'])
    cap.run(['python3', '--version'])
    search_program = 'rg' if shutil.which('rg') else 'grep'
    cap.run([search_program, '--version'])
    head = cap.run(['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
    require(re.fullmatch('[0-9a-f]{40}', head), 'canonical HEAD')
    pools, selected = {}, []
    roots = [str(x) for x in (RULES, ROOT / 'documents', ROOT / 'linux_bug_analyze/documents',
                              ROOT / '日志', ROOT / '当前代办.md') if x.exists()]
    for channel, role in (('fs', 'consumer'), ('drivers', 'producer')):
        argv = ['git', 'log', head, '--no-merges', '--since=2020-01-01T00:00:00+00:00',
                '--until=2024-12-31T23:59:59+00:00', '-n', '32', '--regexp-ignore-case',
                '--extended-regexp', '--grep=endian|byte.?order', '--format=%H%x09%P%x09%cI%x09%s',
                '--', channel]
        output = cap.run(argv).stdout.decode('utf-8')
        entries = []
        for line in output.splitlines():
            commit, parents, date, subject = line.split('\t', 3)
            item = dict(commit=commit, parents=parents.split(), committer_date=date, subject=subject,
                        selection_signal='title+path metadata only', exposure='not queried yet')
            require(re.fullmatch('[0-9a-f]{40}', commit) and len(item['parents']) == 1, 'nonmerge identity')
            search = (['rg', '-l', '-F', '-e', commit, '-e', commit[:12],
                       '--glob=!**/' + HERE.name + '/**', '--glob=!**/__pycache__/**',
                       '--glob=!**/.git/**', *roots] if search_program == 'rg' else
                      ['grep', '-R', '-l', '-F', '-e', commit, '-e', commit[:12],
                       '--exclude-dir=' + HERE.name, '--exclude-dir=__pycache__',
                       '--exclude-dir=.git', '--binary-files=without-match', *roots])
            scan = cap.run(search, acceptable=(0, 1))
            hits = scan.stdout.decode('utf-8').splitlines()
            item['prior_record_matches'] = hits
            item['exposure'] = 'prior_local_record_mention' if hits else 'no_match_in_defined_local_record_roots'
            if hits:
                item['selection_status'] = 'excluded_prior_mention'
            elif not re.search(r'\bfix(?:es)?\b', subject, re.I):
                item['selection_status'] = 'excluded_title_rule'
            elif any(x['role'] == role for x in selected):
                item['selection_status'] = 'not_selected_after_first_qualifying'
            else:
                files = cap.run(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit]).stdout.decode().splitlines()
                all_c_files = sorted(x for x in files if x.endswith('.c'))
                c_files = sorted(x for x in files if x.startswith(channel + '/') and x.endswith('.c'))
                item['changed_paths'] = files
                item['all_c_files'] = all_c_files
                item['channel_c_files'] = c_files
                allowed = [x for x in c_files if not x.startswith(EXCLUDE_PREFIXES) and
                           not any(fragment in x for fragment in EXCLUDE_FRAGMENTS)]
                if not (1 <= len(all_c_files) <= 3) or not allowed or c_files[0] not in allowed:
                    item['selection_status'] = 'excluded_path_or_c_file_count_rule'
                else:
                    item['selection_status'] = 'selected'
                    selected.append(dict(role=role, channel=channel, commit=commit, parent=item['parents'][0],
                                         source_file=c_files[0], subject=subject, exposure=item['exposure'],
                                         preassigned_positive_label=False))
            entries.append(item)
        pools[channel] = entries
    cap.finish()
    save(HERE / 'pool_metadata.json', dict(head=head, pools=pools, count=sum(map(len, pools.values())),
        record_scan_scope=roots, search_program=search_program,
        scan_caveat='No recorded match is not certification of all human exposure.'))
    save(HERE / 'selection.json', dict(selected_at_utc=now(), selected=selected, max_inputs=2,
        no_source_or_patch_read=True, purpose='fixed, title-informed new-input scope validation',
        not_population_random_sample=True))
    paths = [HERE / 'protocol_pre.md', HERE / 'run_holdout.py', HERE / 'pool_metadata.json',
             HERE / 'selection.json', HERE / 'commands_prepare_complete.json']
    paths += [HERE / item[stream] for item in cap.records for stream in ('stdout', 'stderr')]
    paths += [RULES / name for name, _ in TOOLS.values()]
    seal('freeze_pre.json', paths, scope='Pre-parent rules, metadata, selection and protocol lock',
         source_or_patch_read_before_seal=False, selected_count=len(selected), independent_runtime_test=False)
    print(json.dumps(dict(pool_count=sum(map(len, pools.values())), selected=selected), ensure_ascii=False))


def parents():
    tools_unchanged()
    pre = check_lock('freeze_pre.json')
    selected = read(HERE / 'selection.json')['selected']
    cap = Capture('parents')
    summaries, paths = [], []
    for item in selected:
        relative = f"{item['role']}/raw/parent.json"
        out = HERE / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        result = cap.run(['python3', '-B', str(RULES / TOOLS[item['role']][0]), '--linux-dir', str(LINUX),
                         '--revision', item['parent'], '--source', item['source_file'], '--output', str(out)],
                         acceptable=(0, 1, 2))
        summary = dict(role=item['role'], returncode=result.returncode, raw_path=relative if out.exists() else None,
                       raw_sha256=sha(out) if out.exists() else None, attempted_before_patch_unseal=True)
        if out.exists():
            summary['counts'] = read(out)['counts']
            paths.append(out)
        summaries.append(summary)
    cap.finish()
    paths += [HERE / 'commands_parents.json', HERE / 'freeze_pre.json']
    paths += [HERE / item[stream] for item in cap.records for stream in ('stdout', 'stderr')]
    check_lock('freeze_pre.json')
    seal('parents_lock.json', paths, pre_freeze_sha256=sha(HERE / 'freeze_pre.json'),
         summaries=summaries, patch_unsealed=False, count=len(summaries))
    print(json.dumps(summaries, ensure_ascii=False))


def unseal():
    tools_unchanged()
    check_lock('freeze_pre.json')
    parent_lock = check_lock('parents_lock.json')
    cap = Capture('unseal')
    manifest, summaries = [], []
    for item in read(HERE / 'selection.json')['selected']:
        role = item['role']
        patch = cap.run(['git', 'show', '--format=fuller', '--no-ext-diff', item['commit']]).stdout
        dest = HERE / role / 'patch_unsealed.txt'
        with dest.open('xb') as output:
            output.write(patch)
        out = HERE / role / 'raw/fixed.json'
        result = cap.run(['python3', '-B', str(RULES / TOOLS[role][0]), '--linux-dir', str(LINUX),
                         '--revision', item['commit'], '--source', item['source_file'], '--output', str(out)],
                         acceptable=(0, 1, 2))
        summaries.append(dict(role=role, returncode=result.returncode, counts=read(out)['counts'] if out.exists() else None,
                              raw_sha256=sha(out) if out.exists() else None,
                              patch_sha256=sha(dest), parent_locked_before_unseal=True))
        for label, rev in (('parent', item['parent']), ('fixed', item['commit'])):
            raw = HERE / role / 'raw' / (label + '.json')
            paths = [x['path'] for x in read(raw)['files_read']] if raw.exists() else [item['source_file']]
            for source_path in paths:
                content = cap.run(['git', 'show', rev + ':' + source_path]).stdout
                saved = HERE / role / 'sources' / label / source_path
                saved.parent.mkdir(parents=True, exist_ok=True)
                with saved.open('xb') as output:
                    output.write(content)
                manifest.append(dict(role=role, label=label, revision=rev, source_path=source_path,
                    saved_path=saved.relative_to(HERE).as_posix(), sha256=sha(saved), bytes=len(content),
                    blob_sha1=hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()))
    cap.finish()
    save(HERE / 'source_manifest.json', manifest)
    save(HERE / 'unseal_manifest.json', dict(completed_at_utc=now(), parent_lock_sha256=sha(HERE / 'parents_lock.json'),
                                          summaries=summaries, no_rule_or_sample_changes=True))
    check_lock('freeze_pre.json')
    check_lock('parents_lock.json')
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'parents', 'unseal'))
    args = parser.parse_args()
    {'prepare': prepare, 'parents': parents, 'unseal': unseal}[args.phase]()
