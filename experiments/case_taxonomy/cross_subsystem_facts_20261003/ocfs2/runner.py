"""Read-only Git evidence and frozen development replay; all writes stay here.

Run through: wsl -d Ubuntu -- python3 /mnt/d/homework/software/linux_bug_analyze/
linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/ocfs2/runner.py PHASE
PHASE is prepare, evidence, or replay. No compilation, grid, model, or execution
of kernel code is performed. The original analyzer is never edited.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAXONOMY = HERE.parent.parent
LINUX = Path('/root/repos/linux')
SCRIPT = TAXONOMY / 'endian_consumer_single_revision.py'
PROTOCOL = HERE.parent / 'protocol_pre.md'
FIX = 'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4'
REVISIONS = {'parent': FIX + '^', 'fix': FIX}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def execute(name: str, argv: list[str], cwd: Path = LINUX, stdout_path: Path | None = None) -> bytes:
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=True)
    out = stdout_path or raw / (name + '.stdout')
    err = raw / (name + '.stderr')
    out.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(argv, cwd=cwd, capture_output=True, check=False)
    out.write_bytes(process.stdout)
    err.write_bytes(process.stderr)
    manifest_path = HERE / 'commands.json'
    records = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    records.append({'name': name, 'argv': argv, 'cwd': str(cwd), 'returncode': process.returncode,
                    'stdout': str(out.relative_to(HERE)), 'stdout_sha256': sha(process.stdout),
                    'stderr': str(err.relative_to(HERE)), 'stderr_sha256': sha(process.stderr)})
    dump(manifest_path, records)
    if process.returncode:
        raise RuntimeError(f'{name} failed: see {err}')
    return process.stdout


def save_source(label: str, revision: str, path: str) -> dict:
    destination = HERE / 'sources' / label / path
    content = execute(label + '_show_' + path.replace('/', '_'),
                      ['git', 'show', f'{revision}:{path}'], stdout_path=destination)
    blob = execute(label + '_blob_' + path.replace('/', '_'),
                   ['git', 'rev-parse', f'{revision}:{path}']).decode('ascii').strip()
    if len(blob) != 40 or any(c not in '0123456789abcdef' for c in blob):
        raise ValueError('not a Git blob ID')
    return {'revision': revision, 'path': path, 'saved_path': str(destination.relative_to(HERE)),
            'blob': blob, 'sha256': sha(content), 'line_count': len(content.splitlines())}


def dependency_state() -> dict:
    source = SCRIPT.read_bytes()
    tree = ast.parse(source.decode('utf-8'))
    modules = sorted({node.module.split('.')[0] for node in ast.walk(tree)
                      if isinstance(node, ast.ImportFrom) and node.module and node.module != '__future__'} |
                     {alias.name.split('.')[0] for node in ast.walk(tree)
                      if isinstance(node, ast.Import) for alias in node.names})
    dependencies = []
    for module in modules:
        spec = importlib.util.find_spec(module)
        origin = spec.origin if spec else None
        item = {'module': module, 'origin': origin, 'standard_library': module in sys.stdlib_module_names}
        if origin and origin not in ('built-in', 'frozen'):
            origin_path = Path(origin)
            if origin_path.is_file():
                item['sha256'] = sha(origin_path.read_bytes())
        dependencies.append(item)
    return {'script': str(SCRIPT), 'script_sha256': sha(source),
            'protocol': str(PROTOCOL), 'protocol_sha256': sha(PROTOCOL.read_bytes()),
            'imports': dependencies, 'python_executable': sys.executable,
            'python_version': sys.version, 'platform': platform.platform(),
            'subprocess_external_dependency': 'git; its version is captured in raw/git_version.stdout',
            'kernel_execution': False, 'compilation': False, 'new_python_dependencies': False}


def prepare() -> None:
    if (HERE / 'prepared.json').exists():
        raise RuntimeError('prepare is one-shot; preserve the prior record')
    dump(HERE / 'tool_before.json', dependency_state())
    execute('git_version', ['git', '--version'])
    execute('python_version', [sys.executable, '--version'], cwd=HERE)
    records = []
    resolved = {}
    for label, revision in REVISIONS.items():
        resolved[label] = execute(label + '_revision', ['git', 'rev-parse', revision]).decode('ascii').strip()
        old_manifest = json.loads((TAXONOMY / f'endian_consumer_ocfs2_{label}.json').read_text(encoding='utf-8'))
        # The existing development manifest fixes the original tool's source/include
        # inputs; it supplies no caller, data-flow, ABI, or reachability assertions.
        paths = [entry['path'] for entry in old_manifest['files_read']]
        paths += ['fs/ocfs2/Kconfig', 'fs/ocfs2/Makefile',
                  'fs/Kconfig', 'include/linux/byteorder/generic.h',
                  'include/uapi/linux/byteorder/big_endian.h',
                  'include/uapi/linux/byteorder/little_endian.h',
                  'include/uapi/linux/types.h']
        for path in dict.fromkeys(paths):
            records.append(save_source(label, revision, path))
        execute(label + '_consumer_search', ['git', 'grep', '-n', '-e', 'ocfs2_dinode_has_extents',
                                             revision, '--', 'fs/ocfs2'])
        execute(label + '_disk_read_search', ['git', 'grep', '-n', '-e', 'ocfs2_read_inode_block',
                                              '-e', 'ocfs2_read_blocks', revision, '--',
                                              'fs/ocfs2/inode.c', 'fs/ocfs2/buffer_head_io.c',
                                              'fs/ocfs2/buffer_head_io.h', 'fs/ocfs2/filecheck.c'])
    dump(HERE / 'source_manifest.json', records)
    dump(HERE / 'prepared.json', {'resolved_revisions': resolved,
          'phase': 'prepared; no analyzer invocation yet',
          'primary': {'function': 'ocfs2_dinode_has_extents', 'field': 'i_flags'},
          'selected_normal_control': {'function': 'ocfs2_dinode_has_extents', 'field': 'i_size',
                                      'parent_line': 208, 'kind': 'zero/nonzero presence read'},
          'supporting_same_function_normal': {'field': 'i_clusters', 'parent_line': 208,
                                             'kind': 'comparison with zero'},
          'scope': 'Known development replay; all-file counts only background, other candidates excluded'})
    dump(HERE / 'tool_after_prepare.json', dependency_state())
    print(json.dumps({'phase': 'prepare', 'resolved_revisions': resolved,
                      'sources_saved': len(records), 'script_sha256': dependency_state()['script_sha256']}))


def evidence() -> None:
    """Only manually selected caller/disk-read source paths after saved search review."""
    records = json.loads((HERE / 'source_manifest.json').read_text(encoding='utf-8'))
    for label, revision in REVISIONS.items():
        for path in ['fs/ocfs2/buffer_head_io.c', 'fs/ocfs2/filecheck.c',
                     'arch/powerpc/Kconfig', 'arch/powerpc/include/uapi/asm/byteorder.h']:
            records.append(save_source(label, revision, path))
        execute(label + '_target_predecessor_search', ['git', 'grep', '-n', '-e', 'ocfs2_iget(',
                   '-e', 'ocfs2_read_inode(', revision, '--', 'fs/ocfs2/inode.c', 'fs/ocfs2/namei.c'])
        execute(label + '_flag_write_search', ['git', 'grep', '-n', '-E',
                   r'i_flags.*(cpu_to_le32|OCFS2_(CHAIN|DEALLOC|LOCAL_ALLOC|SUPER_BLOCK)_FL)',
                   revision, '--', 'fs/ocfs2'])
        execute(label + '_config_source_search', ['git', 'grep', '-n', '-e', 'OCFS2_FS',
                   '-e', 'OCFS2_DEBUG_FS', revision, '--', 'fs/Kconfig', 'fs/ocfs2/Makefile',
                   'fs/ocfs2/Kconfig'])
    dump(HERE / 'source_manifest.json', records)
    print(json.dumps({'phase': 'evidence', 'sources_saved_total': len(records)}))


def replay() -> None:
    if (HERE / 'replay.json').exists():
        raise RuntimeError('replay is one-shot; preserve raw output')
    before = dependency_state()
    dump(HERE / 'tool_before_replay.json', before)
    results = {}
    for label, revision in REVISIONS.items():
        output = HERE / 'raw' / f'{label}.json'
        execute(label + '_analyzer', [sys.executable, str(SCRIPT), '--linux-dir', str(LINUX),
                '--revision', revision, '--source', 'fs/ocfs2/inode.c'], cwd=TAXONOMY,
                stdout_path=output)
        report = json.loads(output.read_text(encoding='utf-8'))
        primary = [row for row in report['findings'] if row['function'] == 'ocfs2_dinode_has_extents'
                   and row['field'] == 'i_flags']
        control = [row for row in report['findings'] if row['function'] == 'ocfs2_dinode_has_extents'
                   and row['field'] in ('i_size', 'i_clusters')]
        if len(primary) != 1 or len(control) != 2:
            raise RuntimeError('preselected primary/control did not uniquely resolve')
        results[label] = {'raw_output': str(output.relative_to(HERE)),
                          'raw_output_sha256': sha(output.read_bytes()),
                          'background_whole_file_counts': report['counts'],
                          'primary': primary[0], 'normal_control_reads': control}
        # Save every actual source read by the tool, not merely a prior guess.
        by_path = {entry['path']: entry for entry in json.loads((HERE / 'source_manifest.json').read_text(encoding='utf-8'))
                   if entry['revision'] == revision}
        for entry in report['files_read']:
            if entry['path'] not in by_path or entry['sha256'] != by_path[entry['path']]['sha256']:
                raise RuntimeError('actual tool input differs from saved evidence')
    after = dependency_state()
    dump(HERE / 'tool_after_replay.json', after)
    if before != after or before['script_sha256'] != json.loads((HERE / 'tool_before.json').read_text(encoding='utf-8'))['script_sha256']:
        raise RuntimeError('frozen tool/dependency state changed')
    dump(HERE / 'replay.json', {'results': results, 'tool_and_dependencies_unchanged': True,
                              'known_development_replay': True,
                              'no_new_candidates_promoted': True})
    print(json.dumps({'phase': 'replay', 'tool_and_dependencies_unchanged': True,
                      'counts': {label: entry['background_whole_file_counts'] for label, entry in results.items()}}))


def supporting_headers() -> None:
    """Complete only the already selected byteorder/config and sysfs edges."""
    records = json.loads((HERE / 'source_manifest.json').read_text(encoding='utf-8'))
    for label, revision in REVISIONS.items():
        for path in ['include/linux/byteorder/big_endian.h',
                     'include/linux/byteorder/little_endian.h',
                     'arch/powerpc/platforms/Kconfig.cputype', 'fs/ocfs2/super.c']:
            records.append(save_source(label, revision, path))
        execute(label + '_filecheck_registration_search', ['git', 'grep', '-n',
                    '-e', 'ocfs2_filecheck_create_sysfs', '-e', 'ocfs2_filecheck_remove_sysfs',
                    revision, '--', 'fs/ocfs2/super.c', 'fs/ocfs2/filecheck.c'])
    dump(HERE / 'source_manifest.json', records)
    dump(HERE / 'final_tool_state.json', dependency_state())
    print(json.dumps({'phase': 'supporting_headers', 'sources_saved_total': len(records)}))


if __name__ == '__main__':
    {'prepare': prepare, 'evidence': evidence, 'replay': replay,
     'supporting_headers': supporting_headers}[sys.argv[1]]()
