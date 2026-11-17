source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
python3 - "$@" <<'PY'
import re
import subprocess
import sys
rev = 'df2908090cda'
repo = '/root/repos/linux'
if sys.argv[1] == 'grep':
    result = subprocess.run(['git', '-C', repo, 'grep', '-n', '-E', sys.argv[2], rev, '--', *sys.argv[3:]], text=True, capture_output=True)
    print(result.stdout, end='')
    if result.returncode not in (0, 1):
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
else:
    for spec in sys.argv[1:]:
        path, selection = spec.split(':', 1)
        content = subprocess.run(['git', '-C', repo, 'show', f'{rev}:{path}'], text=True, capture_output=True, check=True).stdout
        lines = content.splitlines()
        print(f'===== {rev}:{path} =====')
        keep = set()
        if selection.startswith('@'):
            regex = re.compile(selection[1:])
            for i, line in enumerate(lines):
                if regex.search(line):
                    keep.update(range(max(0, i - 8), min(len(lines), i + 17)))
        else:
            for span in selection.split(','):
                ends = span.split('-')
                start, end = int(ends[0]), int(ends[-1])
                keep.update(range(start - 1, min(end, len(lines))))
        last = -2
        for i in sorted(keep):
            if i != last + 1:
                print('...')
            print(f'{i + 1:6} {lines[i]}')
            last = i
PY
