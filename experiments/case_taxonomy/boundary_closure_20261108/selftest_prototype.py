from common import *
from prototype import Unit,macros,callback_collect,callback_link

def main():
    check_criteria()
    expected=read(HERE/'prototype_src/expected.json')
    extra=read(HERE/'prototype_src/expected_extra.json')
    root=HERE/'prototype_src'
    units=[];macro_units=[]
    (HERE/'evidence/prototype').mkdir(parents=True,exist_ok=True)
    for file in ('arch/provider.c','public.c'):
        u=Unit(root/file,['-std=gnu11','-I'+str(root)],root,root)
        trace=u.preprocess(HERE/'evidence/prototype'/('fixture_'+Path(file).stem+'.i.gz'))
        macro_units.append(macros(u,trace))
        if file=='arch/provider.c':
            compact=macros(u,trace,compact=True)
            assert set(extra['compact_graph_required_names'])<={r['name'] for r in compact['definitions'].values()}
            assert all(r['pending_region'] for r in compact['outer_regions'])
        units.append(callback_collect(u))
    cb=callback_link(units)
    write('prototype_fixture_macros.json',macro_units)
    write('prototype_fixture_callbacks.json',cb)
    expansions=macro_units[0]['expansions']
    one=lambda name:next(e for e in expansions if e['name']==name)
    outer=one('OUTER')
    assert set(expected['outer_required_dependencies'])<=set(outer['dependency_names']),outer
    raw=[e['name'] for e in macro_units[0]['recorded_instantiations']]
    assert not set(expected['outer_not_exposed_nested_instantiations']) & set(raw),raw
    assert expected['parameter_must_not_depend_on'] not in one('PARAM')['dependency_names']
    for field in ('parameter_substitution_keeps_outer_pending','parameter_shadowing_keeps_outer_pending'):
        assert 'parameter_substitution_requires_expansion_context' in one(extra[field])['pending_reasons']
    for name in ('STR','CAT','CHOICE','USE_VANISHED','CYCLE'):
        assert one(name)['pending_region'] is not None,(name,one(name))
        assert one(name)['pending_reasons']
    assert len(cb['indirect_sites'])==expected['indirect_call_count'],cb['indirect_sites']
    label=lambda s:s['definition']['file']+':'+s['name']
    for site in cb['indirect_sites']:
        got={label(s) for s in site['type_candidates'] if s['defined']}
        assert got==set(expected['callback_compatible_definitions']),(site['name'],got)
        assert expected['callback_incompatible_definition'] not in got
        assert site['pending_region'] and not site['complete_target_set']
    initializers={r['object']:r for r in cb['initializers']}
    for obj,wanted in expected['initializer_targets'].items():
        got={label(s['target']) for s in initializers[obj]['targets']}
        assert got==set(wanted),(obj,got)
    assert initializers['active_ops']['form']=='designated'
    assert initializers['descriptions']['form']=='positional'
    assert 'function_pointer_cast' in initializers['cast_ops']['pending_reasons']
    assert any(r['name']==expected['runtime_assignment_pending'] for r in cb['runtime_assignments'])
    assert any(t['preprocessor']['undef_names'] for t in macro_units)
    checks=['outer_nested_object_and_function_macros','macro_parameter_shadowing','stringification',
            'token_pasting','redefinition','undef','recursion','ops_designated_initializer',
            'descriptor_positional_initializer','all_compatible_candidates','incompatible_signature',
            'same_name_static_identity','runtime_assignment_pending','cast_pending','unscanned_TUs_pending',
            'parameter_substitution_pending','compact_graph_retains_all_outer_regions']
    write('selftest_prototype_result.json',{'passed':True,'checks':checks,
        'fixture_TUs':2,'libclang_nested_dependencies_missing':expected['outer_not_exposed_nested_instantiations'],
        'outer_dependency_names':outer['dependency_names'],
        'indirect_calls':len(cb['indirect_sites']),
        'compatible_candidates_per_site':len(expected['callback_compatible_definitions']),
        'initializer_objects':len(initializers),'expected_sha256':sha(HERE/'prototype_src/expected.json')})
    print('prototype selftest passed',len(checks),'checks,',len(cb['indirect_sites']),'calls')

if __name__=='__main__':main()
