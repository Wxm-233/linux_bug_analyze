"""Bounded GCC original-tree declaration checks for a generated projection.

This verifies the generated producer's record/field references, not those in a
full historical kernel translation unit. Plain typedefs do not check endian
semantics. Unsupported GCC graph shapes raise, never silently pass.
"""
from pathlib import Path
import re

def verify_bindings(path: Path, program: dict) -> dict:
    contract = program['compiler_binding_contract']
    function_name = contract['actual_function']
    raw = path.read_text(encoding='utf-8')
    parts = re.split(r'(?m)^;; Function ', raw)
    selected = [part for part in parts[1:] if part.split(' ', 1)[0] == function_name]
    if len(selected) != 1:
        raise ValueError('actual producer function missing/ambiguous in GCC dump')
    nodes = {match.group(1):dict(kind=match.group(2), body=match.group(3))
        for match in re.finditer(r'(?m)^@(\d+)\s+(\w+)\s+(.*?)(?=\n@|\Z)', selected[0], re.S)}

    def ref(node, label):
        match = re.search(re.escape(label)+r'\s*:\s*@(\d+)', nodes[node]['body'])
        if not match:
            raise ValueError('GCC link absent: @'+node+':'+label)
        return match.group(1)

    def name(node):
        if nodes[node]['kind'] == 'identifier_node':
            match = re.search(r'strg:\s*(\S+)\s+lngt:', nodes[node]['body'])
            if match:
                return match.group(1)
        if nodes[node]['kind'] in ('type_decl', 'field_decl', 'var_decl', 'parm_decl', 'record_type'):
            return name(ref(node, 'name'))
        raise ValueError('unsupported GCC name node: '+nodes[node]['kind'])

    def root(node):
        # Only the exact generated direct object or one pointer dereference.
        if nodes[node]['kind'] == 'indirect_ref':
            node = ref(node, 'op 0')
        if nodes[node]['kind'] not in ('var_decl', 'parm_decl'):
            raise ValueError('unsupported GCC member root: '+nodes[node]['kind'])
        value_type = ref(node, 'type')
        if nodes[value_type]['kind'] == 'pointer_type':
            value_type = ref(value_type, 'ptd')
        if nodes[value_type]['kind'] != 'record_type':
            raise ValueError('member root is not a record')
        return dict(declaration_node='@'+node, variable=name(node), struct=name(value_type),
                    record_type_node='@'+value_type)

    def member(node):
        if nodes[node]['kind'] != 'component_ref':
            raise ValueError('expected GCC component_ref')
        result = root(ref(node, 'op 0'))
        field = ref(node, 'op 1')
        result.update(field=name(field), field_decl_node='@'+field,
                      type_alias=name(ref(ref(field, 'type'), 'name')))
        return result

    def rhs_members(node, seen=None):
        seen = set() if seen is None else seen
        if node in seen:
            return []
        seen.add(node)
        kind = nodes[node]['kind']
        if kind == 'component_ref':
            return [member(node)]
        if kind.endswith('_decl') or kind in ('identifier_node', 'integer_cst'):
            return []
        edges = re.findall(r'(?:op\s+\d+|args|valu|chan|fn|\b\d+)\s*:\s*@(\d+)', nodes[node]['body'])
        found = []
        for edge in edges:
            found.extend(rhs_members(edge, seen))
        return found

    bindings = []
    for ident, node in nodes.items():
        if node['kind'] != 'modify_expr':
            continue
        left = ref(ident, 'op 0')
        if nodes[left]['kind'] != 'component_ref':
            continue
        target = member(left)
        if target['variable'] != contract['target_object']:
            continue
        sources = rhs_members(ref(ident, 'op 1'))
        bindings.append(dict(store_node='@'+ident, target=target, sources=sources))
    fields = program['fields']
    if len(bindings) != len(fields):
        raise ValueError('GCC target write count differs from complete field plan')
    for field in fields:
        matches = [binding for binding in bindings if binding['target']['field'] == field['name']]
        if len(matches) != 1:
            raise ValueError('GCC target field not written exactly once: '+field['name'])
        binding = matches[0]
        target = binding['target']
        expected_type = '__'+field['endian']+str(field['bits'])
        if target['struct'] != program['payload_struct'] or target['type_alias'] != expected_type:
            raise ValueError('GCC target record/type differs from schema')
        sources = binding['sources']
        if len(sources) != 1:
            raise ValueError('actual RHS does not bind to exactly one source field')
        source = sources[0]
        if (source['variable'] != field['source_pointer'] or source['struct'] != field['source_struct']
                or source['field'] != field['source_field'] or source['type_alias'] != field['source_type']):
            raise ValueError('GCC RHS declaration differs from field plan')
    return dict(actual_function=function_name, bindings=bindings, status='projection_bindings_verified',
                scope='Generated reduced TU only; original kernel preprocessing/configuration and endian semantics unproved.')
