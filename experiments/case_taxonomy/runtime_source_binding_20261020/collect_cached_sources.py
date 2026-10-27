"""Read a bounded, already cached set; never run compiler or kernel tools."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'die_arch_contract_20261013'
PROFILES = ('old_x86_64', 'fixed_x86_64', 'old_s390', 'fixed_s390')
FILES = ('include/linux/topology.h', 'arch/x86/include/asm/topology.h',
         'arch/s390/include/asm/topology.h', 'drivers/base/topology.c')


def load(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    destination = HERE / 'cached_source_packet.json'
    if destination.exists(): raise RuntimeError('Preserve previous collection')
    sources, runs = {}, {}
    for profile in PROFILES:
        folder = BASE / 'runtime/profiles' / profile
        build = load(folder / 'build.json')
        tree, output = Path(build['source_tree']), Path(build['build_directory'])
        revision = build['revision']
        assert (tree.parent / 'source_revision').read_text().strip() == revision
        assert sha(folder / 'kernel.config') == build['config_sha256']
        assert sha(output / '.config') == build['config_sha256']
        origin = {r['path']: r for r in build['source_identity']}
        for name in FILES:
            file = tree / name; data = file.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert origin[name]['matches'] is True and origin[name]['git_blob'] == blob
            key = revision + ':' + name
            record = {'revision': revision, 'path': name, 'cached_path': str(file), 'git_blob': blob,
                      'sha256': hashlib.sha256(data).hexdigest(), 'text': data.decode('utf-8'), 'whole_direct_file': True}
            if key in sources: assert sources[key] == record
            else: sources[key] = record
        cmd = output / 'drivers/base/.topology.o.cmd'
        command = {'present': cmd.is_file(), 'historical_digest_available': False,
                   'meaning': 'current cached command record, not an independently archived runtime-TU macro proof'}
        if cmd.is_file():
            raw = cmd.read_text()
            lines = raw.splitlines()
            command.update(sha256=sha(cmd), compilation_lines=[x for x in lines if '.o :=' in x],
                           direct_dependency_mentions=[name for name in FILES if name in raw])
        autoconf = output / 'include/generated/autoconf.h'
        runs[profile] = {'revision': revision, 'arch': build['arch'], 'config_sha256': sha(folder / 'kernel.config'),
                         'cached_config_matches_archive': True,
                         'archived_autoconf_sha256': sha(folder / 'autoconf.h'),
                         'cached_autoconf_matches_archive': sha(autoconf) == sha(folder / 'autoconf.h'),
                         'autoconf_independent_historical_digest': None, 'command_record': command,
                         'source_keys': [revision + ':' + name for name in FILES]}
    packet = {'scope': 'N2.16 bounded current-cache source binding, all sources checked against archived build blobs',
              'sources': sources, 'runs': runs, 'new_preprocessing': 0, 'new_builds': 0, 'new_boots': 0,
              'runtime_effective_macro_closure_proved': False}
    with destination.open('x', encoding='utf-8') as f:
        json.dump(packet, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps({'sources': len(sources), 'runs': len(runs), 'new_commands_executed': 0}))


if __name__ == '__main__': main()
