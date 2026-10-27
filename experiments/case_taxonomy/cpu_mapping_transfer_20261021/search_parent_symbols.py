from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
plan = json.loads((HERE / 'symbol_search_pre.json').read_bytes())
rows = []
for case in plan['cases']:
    assert len(case['symbols']) <= 6
    command = ['wsl.exe', '-d', 'Ubuntu', '--', 'git', '-C', '/root/repos/linux', 'grep', '-n', '-w']
    for symbol in case['symbols']:
        command += ['-e', symbol]
    command += [case['parent'], '--', *case['paths']]
    done = subprocess.run(command, capture_output=True, timeout=45)
    rows.append({'case': case['case'], 'argv': command, 'returncode': done.returncode,
                 'text': done.stdout.decode('utf-8'), 'stderr': done.stderr.decode('utf-8', 'replace')})
with (HERE / 'symbol_search.json').open('x', encoding='utf-8') as f:
    json.dump({'searches': rows, 'commands': len(rows), 'new_complete_files': 0}, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'commands': len(rows), 'statuses': [r['returncode'] for r in rows],
                  'match_lines': [len(r['text'].splitlines()) for r in rows]}))
