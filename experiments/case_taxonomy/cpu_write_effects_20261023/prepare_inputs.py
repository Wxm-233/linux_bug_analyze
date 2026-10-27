"""Prepare the bounded N2.22 inputs before compiler evidence is collected."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
PRIOR = HERE.parent / 'cpu_stage_propagation_20261022'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    path = HERE / name
    if path.exists():
        raise RuntimeError('preserve existing input: ' + name)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    names = ['当前代办.md', '当前研究方向与进展.md', '项目研究与文档写作交接说明.md']
    windows = {name: sha((OUTER / name).read_bytes()) for name in names}
    code = "from pathlib import Path;import hashlib,json;names=json.loads(input());print(json.dumps({n:hashlib.sha256((Path('/root')/n).read_bytes()).hexdigest() for n in names},ensure_ascii=False))"
    done = subprocess.run(['wsl.exe', '-d', 'Ubuntu', '--', 'python3', '-c', code],
                          input=json.dumps(names, ensure_ascii=False).encode('utf-8'), capture_output=True, timeout=30)
    if done.returncode:
        raise RuntimeError(done.stderr.decode('utf-8', errors='replace'))
    wsl = json.loads(done.stdout.decode('utf-8'))
    if windows != wsl:
        raise RuntimeError('working note mirrors differ before this round')
    save('notes_before.json', {'before_sha256': windows, 'wsl_before_sha256': wsl})
    packet = json.loads((PRIOR / 'source_fragments.json').read_text(encoding='utf-8'))
    fragment = next(row for row in packet['fragments'] if row['id'] == 'setter_and_binding')
    assert sha(fragment['text'].encode('utf-8')) == fragment['fragment_sha256']
    save('protocol_pre.json', {
        'task': 'N2.22', 'date': '2026-10-23',
        'purpose': 'source-bound direct scalar write facts under selected compile-time branches',
        'prior_source_packet_sha256': sha((PRIOR / 'source_fragments.json').read_bytes()),
        'fragment': fragment,
        'profiles': [
            {'id': 'dynamic4', 'defines': ['NR_CPUS=4'], 'binding_expected': 'extern_object', 'direct_write_expected': True},
            {'id': 'force4', 'defines': ['NR_CPUS=4', 'CONFIG_FORCE_NR_CPUS=1'], 'binding_expected': 'macro_constant', 'direct_write_expected': False},
            {'id': 'single1', 'defines': ['NR_CPUS=1'], 'binding_expected': 'macro_constant', 'direct_write_expected': False}],
        'query_function': 'set_nr_cpu_ids', 'query_scalar': 'nr_cpu_ids',
        'human_inputs': ['selected source range', 'three compile-time profiles', 'query function and scalar',
                         'expected binding and direct-write facts', 'diagnostic macro replacement'],
        'diagnostic_replacement': 'WARN_ON conditionally increments an observable warning counter; not the historical kernel WARN_ON implementation',
        'scope': 'host GCC early compiler representation only; no Kconfig legality or original diagnostic-effects proof',
        'stop': ['first compiler failure', 'nonunique function or missing original source locus',
                 'unsupported CFG/alias/cross-procedure fact remains insufficient'],
        'no_prior_matrix_rerun': True, 'new_kernel_material': False,
        'paid_model_requests': 0, 'kernel_builds': 0, 'kernel_boots': 0,
        'independent_positive': 0, 'independent_normal': 0})
    text = ('/* N2.22 finite compiler projection; not a kernel translation unit. */\n'
            '#define __always_inline inline __attribute__((always_inline))\n'
            'unsigned int n222_warning_count;\n'
            '#define WARN_ON(condition) ((condition) ? (++n222_warning_count, 1) : 0)\n'
            f'#line {fragment["first_line"]} "{fragment["path"]}"\n' + fragment['text'] +
            '\n#line 1 "n222_observation_wrapper.c"\n'
            'void n222_observe(unsigned int n) { set_nr_cpu_ids(n); }\n')
    path = HERE / 'setter_projection.c'
    if path.exists():
        raise RuntimeError('preserve projection')
    path.write_text(text, encoding='utf-8')
    save('input_manifest.json', {'sha256': {'protocol_pre.json': sha((HERE/'protocol_pre.json').read_bytes()),
                                         'setter_projection.c': sha(path.read_bytes()),
                                         'prepare_inputs.py': sha(Path(__file__).read_bytes())}})
    print(json.dumps({'prepared_profiles': 3, 'working_note_mirrors': len(names), 'new_kernel_sources': 0}))


if __name__ == '__main__':
    main()
