from pathlib import Path
p = Path('archscan.py'); s = p.read_text(encoding='utf-8')
def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b, 1)
rep('"""Per-architecture definitions at one revision (effdep2 I3, amendment 2; effdep3 J2, 二.1, 二.2). WSL, read-only on /root/repos/linux.',
    '"""Per-architecture definitions at one revision (effdep2 I3, amendment 2; effdep3 J2, 二.1, 二.2; effdep6 二: body calls). WSL, read-only.')
rep('''              "selects": {arch: [Kconfig symbols selected / def_bool y]}}''',
    '''              "selects": {arch: [Kconfig symbols selected / def_bool y]},
              "calls": {name: {arch: [names called in the nontrivial arch definition body, one level]}}}  (effdep6)''')
rep('''SYM = re.compile(r"\bCONFIG_([A-Za-z0-9_]+)")''', '''SYM = re.compile(r"\bCONFIG_([A-Za-z0-9_]+)")
CALLNAME = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
BODYCALLS = {}  # effdep6: name -> arch -> set of called names


def body_calls(name, arch, body):
    if arch == "generic":
        return
    names = {n for n in CALLNAME.findall(body) if n not in KEYW and n != name}
    if names:
        BODYCALLS.setdefault(name, {}).setdefault(arch, set()).update(names)''')
rep('''        triv = triv_body(text[b0 + 1:b1])
        put(defs, name, arch, triv)''', '''        triv = triv_body(text[b0 + 1:b1])
        put(defs, name, arch, triv)
        if not triv:
            body_calls(name, arch, text[b0 + 1:b1])''')
rep('''            triv = bool(TRIV_MACRO.match(body))
            put(defs, name, arch, triv)''', '''            triv = bool(TRIV_MACRO.match(body))
            put(defs, name, arch, triv)
            if not triv:
                body_calls(name, arch, body)''')
rep('''               "selects": {a: sorted(s) for a, s in selects.items()}}, gzip.open(out, "wt"))''',
    '''               "selects": {a: sorted(s) for a, s in selects.items()},
               "calls": {n: {a: sorted(v) for a, v in d.items()} for n, d in BODYCALLS.items() if n in only}}, gzip.open(out, "wt"))''')
p.write_text(s, encoding='utf-8', newline='\n')
print('ok')
