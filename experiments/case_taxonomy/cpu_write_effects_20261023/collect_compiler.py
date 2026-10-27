"""Collect three first-attempt GCC projections; never execute prior matrices."""
from pathlib import Path
import hashlib
import base64
import json
import os
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.name == 'posix', 'run in the existing WSL compiler environment'
    result_path = HERE / 'compiler_execution.json'
    assert not result_path.exists(), 'preserve first compiler collection'
    manifest = json.loads((HERE / 'input_manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['sha256'].items():
        assert sha(HERE / name) == digest, name
    gate = (HERE / 'pre_execution_review.md').read_text(encoding='utf-8')
    assert 'EXECUTION_GATE: PASS' in gate
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    rows = []
    result = {'task': 'N2.22', 'status': 'running', 'commands': rows, 'profiles': [],
              'collector_sha256': sha(Path(__file__)), 'input_manifest_sha256': sha(HERE / 'input_manifest.json'),
              'paid_model_requests': 0, 'kernel_builds': 0, 'kernel_boots': 0,
              'prior_projection_runs': 0, 'new_kernel_material': 0}

    def save():
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    def invoke(argv):
        before = time.monotonic()
        try:
            done = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', timeout=30,
                                  env=dict(os.environ, LC_ALL='C', LANG='C'))
            row = {'argv': argv, 'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr}
        except subprocess.TimeoutExpired as exc:
            row = {'argv': argv, 'returncode': None, 'error': repr(exc),
                   'partial_stdout_base64': base64.b64encode(exc.stdout or b'').decode('ascii'),
                   'partial_stderr_base64': base64.b64encode(exc.stderr or b'').decode('ascii')}
        except OSError as exc:
            row = {'argv': argv, 'returncode': None, 'error': repr(exc)}
        row['elapsed_seconds'] = round(time.monotonic()-before, 6)
        rows.append(row)
        save()
        if row['returncode'] != 0:
            raise RuntimeError('stop on first compiler/environment command failure')
        return row['stdout']

    save()
    try:
        result['gcc_version'] = invoke(['gcc', '--version']).splitlines()[0]
        result['gcc_target'] = invoke(['gcc', '-dumpmachine']).strip()
        for profile in protocol['profiles']:
            out = HERE / profile['id']
            out.mkdir(exist_ok=False)
            defines = ['-D'+value for value in profile['defines']]
            source = str(HERE / 'setter_projection.c')
            invoke(['gcc', '-std=gnu11', *defines, '-E', '-dD', source, '-o', str(out/'setter.i')])
            invoke(['gcc', '-std=gnu11', '-O0', '-Wall', '-Wextra', '-Wno-unused-value', *defines,
                    '-fdump-tree-gimple-lineno='+str(out/'setter.gimple'),
                    '-fdump-tree-cfg-lineno='+str(out/'setter.cfg'), '-c', source, '-o', str(out/'setter.o')])
            raw = (out/'setter.cfg').read_text(encoding='utf-8')
            headers = list(re.finditer(r'(?m)^;; Function ([A-Za-z_]\w*) \(', raw))
            hits = [i for i, match in enumerate(headers) if match[1] == protocol['query_function']]
            assert len(hits) == 1, 'require one exact function record'
            index = hits[0]
            first = headers[index].start()
            last = headers[index+1].start() if index+1 < len(headers) else len(raw)
            selected = raw[first:last]
            assert re.search(r'(?m)^;;\s*\d+ succs \{', selected), 'compiler metadata missing'
            locations = re.findall(r'\[' + re.escape(protocol['fragment']['path']) + r':(\d+):\d+\]', selected)
            assert any(protocol['fragment']['first_line'] <= int(line) <= protocol['fragment']['last_line']
                       for line in locations), 'original setter source locus missing'
            (out/'selected.cfg').write_text(selected, encoding='utf-8')
            result['profiles'].append({'id': profile['id'], 'files_sha256': {
                p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                'selected_start_offset': first, 'selected_end_offset': last,
                'source_function': protocol['query_function']})
            save()
        result['status'] = 'completed'
    except Exception as exc:
        result['status'] = 'stopped'
        result['error'] = repr(exc)
        save()
        raise
    save()
    print(json.dumps({'status': result['status'], 'profiles': len(result['profiles']),
                      'host_object_builds': len(result['profiles']), 'kernel_boots': 0}))


if __name__ == '__main__':
    main()
