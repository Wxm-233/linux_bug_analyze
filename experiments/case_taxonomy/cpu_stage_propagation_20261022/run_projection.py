"""Single-attempt execution of the preregistered 24 host projection records."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import time

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt_path = HERE / 'execution.json'
    if receipt_path.exists() or (HERE / 'execution_started.json').exists():
        raise RuntimeError('preserve original execution; do not rerun')
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    review = (HERE / 'pre_execution_review.md').read_text(encoding='utf-8')
    assert 'EXECUTION_GATE: PASS' in review
    frozen = json.loads((HERE / 'execution_pre.json').read_text(encoding='utf-8'))
    for name, expected in frozen['sha256'].items():
        assert digest(HERE / name) == expected, name
    (HERE / 'execution_started.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'protocol_sha256': digest(HERE / 'protocol_pre.json'),
        'execution_pre_sha256': digest(HERE / 'execution_pre.json')}, indent=2) + '\n')
    builds, runs = [], []
    bins = HERE / 'bin'
    bins.mkdir(exist_ok=False)
    result = {'task': 'N2.21', 'kind': 'instrumented_host_source_projection',
              'builds': builds, 'runs': runs, 'status': 'running',
              'paid_model_requests': 0, 'kernel_builds': 0, 'kernel_boots': 0}

    def save():
        receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def invoke(argv):
        before = time.monotonic()
        try:
            done = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', timeout=30)
            row = {'argv': argv, 'returncode': done.returncode,
                   'stdout': done.stdout, 'stderr': done.stderr}
        except subprocess.TimeoutExpired as error:
            import base64
            row = {'argv': argv, 'returncode': None, 'exception': repr(error),
                   'stdout': '', 'stderr': '',
                   'partial_stdout_base64': base64.b64encode(error.stdout or b'').decode('ascii'),
                   'partial_stderr_base64': base64.b64encode(error.stderr or b'').decode('ascii')}
        except OSError as error:
            row = {'argv': argv, 'returncode': None, 'exception': repr(error),
                   'stdout': '', 'stderr': ''}
        row['elapsed_seconds'] = round(time.monotonic() - before, 6)
        return row

    try:
        for version in protocol['versions']:
            for profile, cfg in protocol['profiles'].items():
                exe = bins / (version + '_' + profile)
                argv = ['gcc', '-std=gnu11', '-O0', '-Wall', '-Wextra', '-Werror',
                        '-Wno-sign-compare', '-DCONFIG_X86_LOCAL_APIC',
                        '-DNR_CPUS=' + str(cfg['NR_CPUS'])]
                if cfg['FORCE']:
                    argv.append('-DCONFIG_FORCE_NR_CPUS')
                if cfg['MPPARSE']:
                    argv.append('-DCONFIG_X86_MPPARSE')
                argv += [str(HERE / ('projection_' + version + '.c')), '-o', str(exe)]
                row = invoke(argv)
                row.update({'version': version, 'profile': profile})
                builds.append(row)
                save()
                if row['returncode'] != 0:
                    result['status'] = 'stopped_first_build_failure'
                    return
        for case in protocol['cases']:
            for version in protocol['versions']:
                exe = bins / (version + '_' + case['profile'])
                argv = [str(exe), case['id'], case['mode'], str(case['acpi_disabled']),
                        str(case['acpi_noirq']), str(case['setup_max_cpus']),
                        str(case['possible_cap']), str(case['preexisting_apic_disabled']), version]
                row = invoke(argv)
                row.update({'case': case['id'], 'version': version, 'profile': case['profile']})
                runs.append(row)
                save()
                if row['returncode'] != 0:
                    result['status'] = 'stopped_first_execution_failure'
                    return
                # Preserve stdout even if parsing fails. Failure stops, no retry.
                row['observation'] = json.loads(row['stdout'])
                save()
        assert len(runs) == protocol['max_execution_records'] == 24
        result['status'] = 'all_preregistered_host_records_completed'
    except Exception as error:
        result['status'] = 'stopped_first_exception'
        result['exception'] = repr(error)
        raise
    finally:
        result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({'status': result['status'], 'builds': len(builds), 'records': len(runs)}))


if __name__ == '__main__':
    main()
