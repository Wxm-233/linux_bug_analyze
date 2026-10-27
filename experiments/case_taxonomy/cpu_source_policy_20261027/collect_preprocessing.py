"""Read cached builds, run new CPP only; never invoke make or write old builds."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'die_arch_contract_20261013/runtime/profiles'
REPO = Path('/root/repos/linux')
PROFILES = ['old_x86_64', 'fixed_x86_64', 'old_s390', 'fixed_s390']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def need(value, reason):
    if not value:
        raise ValueError(reason)

def collect(profile):
    out = HERE / 'preprocessing' / profile
    out.mkdir(parents=True, exist_ok=False)
    build_file = BASE / profile / 'build.json'
    build = json.loads(build_file.read_bytes())
    root, source = Path(build['build_directory']), Path(build['source_tree'])
    paths = {'config': root / '.config', 'image': Path(build['image']),
             'autoconf': root / 'include/generated/autoconf.h', 'command': root / 'drivers/base/.topology.o.cmd',
             'object': root / 'drivers/base/topology.o'}
    before = {name: sha(path) for name, path in paths.items()}
    need(before['config'] == build['config_sha256'] == sha(BASE / profile / 'kernel.config'), 'configuration_identity_mismatch')
    need(before['image'] == build['image_sha256'], 'image_identity_mismatch')
    command_line = paths['command'].read_text().splitlines()[0]
    need(command_line.startswith('cmd_drivers/base/topology.o := '), 'unexpected_command_assignment')
    lex = shlex.shlex(command_line.split(' := ', 1)[1], posix=True, punctuation_chars=';&|')
    lex.whitespace_split = True
    tokens = list(lex)
    end = tokens.index(';') if ';' in tokens else len(tokens)
    argv = tokens[:end]
    need(not any(x in argv for x in ['&&', '||', '&', '|']), 'unexpected_shell_operator')
    need(argv[0] in ['gcc', 's390x-linux-gnu-gcc'], 'unexpected_compiler')
    need(argv.count('-c') == argv.count('-o') == 1, 'unexpected_compile_action')
    need(argv[-1] == str(source / 'drivers/base/topology.c'), 'unexpected_translation_unit')
    rebuilt, dropped = [], []
    for arg in argv:
        if arg.startswith('-Wp,-MMD,'):
            dropped.append(arg)
        else:
            need(not arg.startswith(('-MD', '-MMD', '-MF', '-MT', '-MQ')), 'unexpected_dependency_flag')
            rebuilt.append(arg)
    action = rebuilt.index('-c')
    rebuilt[action:action+1] = ['-E', '-dD', '-H']
    rebuilt[rebuilt.index('-o') + 1] = str(out / 'topology.i')
    rebuilt[0] = shutil.which(rebuilt[0])
    need(bool(rebuilt[0]), 'compiler_missing')
    env = os.environ.copy()
    removed = [key for key in ['CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH',
                              'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'DEPENDENCIES_OUTPUT', 'SUNPRO_DEPENDENCIES'] if key in env]
    for key in removed:
        env.pop(key, None)
    env['LC_ALL'] = 'C'
    version = subprocess.run([rebuilt[0], '--version'], env=env, capture_output=True, check=True, text=True).stdout
    (out / 'compiler_version.txt').write_text(version)
    save(out / 'command.json', {'archived_command': command_line, 'original_argv': argv, 'preprocess_argv': rebuilt,
                               'cwd': str(root), 'removed_dependency_flags': dropped, 'omitted_post_compile_tokens': tokens[end:],
                               'removed_environment_variable_names': removed, 'environment_is_new_not_historically_reconstructed': True})
    start = time.monotonic()
    with (out / 'stdout.log').open('xb') as stdout, (out / 'includes.stderr.log').open('xb') as stderr:
        done = subprocess.run(rebuilt, cwd=root, env=env, stdout=stdout, stderr=stderr, timeout=120)
    receipt = {'profile': profile, 'returncode': done.returncode, 'elapsed_seconds': round(time.monotonic()-start, 3),
               'revision': build['revision'], 'arch': build['arch'], 'source_tree': str(source), 'build_directory': str(root),
               'build_json_sha256': sha(build_file), 'before_sha256': before,
               'after_sha256': {name: sha(path) for name, path in paths.items()},
               'compiler_path': rebuilt[0], 'compiler_sha256': sha(Path(rebuilt[0])),
               'compiler_version_sha256': sha(out / 'compiler_version.txt'),
               'new_preprocessing': True, 'historical_effective_macro_closure_proved': False, 'new_build': False, 'new_boot': False}
    need(receipt['before_sha256'] == receipt['after_sha256'], 'original_build_mutated')
    if done.returncode == 0:
        receipt['preprocessed_sha256'] = sha(out / 'topology.i')
        marker = re.compile(r'^#\s+\d+\s+("(?:[^"\\]|\\.)*")')
        files = set()
        for line in (out / 'topology.i').read_text().splitlines():
            match = marker.match(line)
            if match:
                name = ast.literal_eval(match[1])
                if not name.startswith('<'):
                    file = Path(name)
                    files.add((root / file).resolve() if not file.is_absolute() else file.resolve())
        source_paths = sorted(str(path.relative_to(source)) for path in files if path.is_relative_to(source))
        listing = subprocess.run(['git', '-C', str(REPO), 'ls-tree', '-r', build['revision'], '--', *source_paths],
                                 capture_output=True, check=True, text=True).stdout
        git_ids = {line.split('\t', 1)[1]: line.split()[2] for line in listing.splitlines()}
        provenance = []
        for path in sorted(files):
            row = {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}
            if path.is_relative_to(source):
                relative = str(path.relative_to(source))
                row.update(kind='pinned_source', source_path=relative, git_blob=git_ids.get(relative), actual_blob=blob(path))
                row['matches_pinned_revision'] = row['git_blob'] == row['actual_blob']
            elif path.is_relative_to(root):
                row.update(kind='generated_build_input', build_path=str(path.relative_to(root)))
            else:
                row.update(kind='external_input')
            provenance.append(row)
        save(out / 'include_provenance.json', provenance)
        receipt['include_provenance_sha256'] = sha(out / 'include_provenance.json')
        receipt['included_file_counts'] = {kind: sum(row['kind'] == kind for row in provenance)
                                           for kind in ['pinned_source', 'generated_build_input', 'external_input']}
        receipt['all_source_inputs_match_revision'] = all(row['matches_pinned_revision'] for row in provenance if row['kind']=='pinned_source')
    save(out / 'receipt.json', receipt)
    need(done.returncode == 0, 'preprocessing_failed:' + profile)
    need(receipt['all_source_inputs_match_revision'], 'included_source_mismatch:' + profile)
    print(json.dumps({'profile': profile, 'returncode': done.returncode, 'elapsed_seconds': receipt['elapsed_seconds'],
                      'included_file_counts': receipt['included_file_counts']}), flush=True)
    return receipt

def main():
    need(not (HERE / 'collection.json').exists(), 'preserve_original_collection')
    results = [collect(profile) for profile in PROFILES]
    save(HERE / 'collection.json', {'profiles': results, 'new_preprocessing': len(results), 'new_builds': 0, 'new_boots': 0})

if __name__ == '__main__':
    main()
