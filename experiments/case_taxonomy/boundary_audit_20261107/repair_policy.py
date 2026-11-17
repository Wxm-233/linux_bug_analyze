"""Policy changes only; frozen parser/cache format remains unchanged."""
from collections import defaultdict
from pathlib import PurePosixPath

STRONG = frozenset('ABCDGIRSTiu')
WEAK = frozenset('WV')

def choose(providers, final_types):
    """Never guess among equal-strength providers; check final ELF binding too."""
    providers=sorted(set(providers))
    strong=[p for p in providers if p[1] in STRONG]
    if len(strong)==1 and set(final_types)&STRONG:return strong[0]
    weak=[p for p in providers if p[1] in WEAK]
    if not strong and len(weak)==1 and set(final_types)&WEAK:return weak[0]
    return None

def binding_table(providers, final_types, source_by_object):
    rows={}
    for name, candidates in providers.items():
        chosen=choose(candidates,final_types.get(name,()))
        if chosen is None:continue
        obj,code=chosen
        source=source_by_object.get(obj)
        if source is None:continue
        rows[name]={'object':obj,'source':source,'nm_type':code,
                    'has_weak_competitor':bool(any(c in WEAK for _,c in candidates) and any(c in STRONG for _,c in candidates)),
                    'providers':[{'object':o,'nm_type':c} for o,c in sorted(set(candidates))],
                    'linked_nm_types':sorted(final_types[name])}
    return rows

def resolve_c(symbol, linked, definitions, by_object, weak_overrides, bindings, fallback):
    binding=bindings.get(symbol.link_name) if symbol.external and linked else None
    if binding and binding['has_weak_competitor']:
        candidates=by_object.get((binding['object'],symbol.kind,symbol.link_name),())
        if len(candidates)==1:return next(iter(candidates)),None
        return None,'linked_winner_without_unique_ast_definition'
    return fallback(symbol,linked,definitions,by_object,weak_overrides)

def asm_provider(symbol, linked, bindings):
    if not linked or not symbol.external:return None
    binding=bindings.get(symbol.link_name)
    if binding and PurePosixPath(binding['source']).suffix.lower()=='.s':return binding
    return None

def runtime_point(path, unit_sources):
    if path.startswith('@build/') and path.endswith('.mod.c'):return False
    return not any(s.removeprefix('@build/').startswith(('scripts/','tools/')) for s in unit_sources)
