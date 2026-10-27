"""Development-only independent synthetic probes; never reads held-out source."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULES = HERE.parent
sys.path.insert(0, str(MODULES))
import structured_hci_single_revision as module
import outbound_scalar_single_revision as scalar
from outbound_scalar_single_revision_test import REQUEST, SKBUFF

HCI = "#ifndef HCI_H\n#define HCI_H\nstruct command { __le16 value; } __packed;\n#endif\n"
CORE = "#ifndef CORE_H\n#define CORE_H\nstruct device { __u16 value; };\nstruct encoded_device { __le16 value; };\ntypedef struct encoded_device encoded_dev;\n#endif\n"
INCLUDES = '#include <net/bluetooth/hci.h>\n#include <net/bluetooth/hci_core.h>\n'
BASE = INCLUDES + 'void send(struct device *dev) { struct command cp; cp.value=dev->value; hci_req_add(req,OP,sizeof(cp),&cp); }'


def report(source, hci=HCI, core=CORE):
    return module.analyze_files('driver.c', {
        'driver.c': source, module.HCI: hci, module.HCI_CORE: core,
        scalar.REQUEST: REQUEST, scalar.SKBUFF: SKBUFF})


def main():
    cases = [
        ('baseline_host_candidate', BASE, None, 'candidate'),
        ('matching_conversion', BASE.replace('=dev->value;', '=cpu_to_le16(dev->value);'), None, 'matched_conversion'),
        ('typedef_array_source_shadow', INCLUDES + 'void send(struct device *dev) { { encoded_dev dev[1]={{.value=cpu_to_le16(7)}}; struct command cp; cp.value=dev->value; hci_req_add(req,OP,sizeof(cp),&cp); } }', None, 'insufficient'),
        ('inactive_include', BASE.replace('#include <net/bluetooth/hci.h>', '#if 0\n#include <net/bluetooth/hci.h>\n#endif'), None, 'insufficient'),
        ('unknown_include', BASE.replace('#include <net/bluetooth/hci.h>', '#ifdef CONFIG_X\n#include <net/bluetooth/hci.h>\n#endif'), None, 'insufficient'),
        ('parenthesized_member_preencoding', BASE.replace('struct command cp;', 'struct command cp; (dev)->value=cpu_to_le16(7);'), None, 'insufficient'),
        ('member_encoded_via_opaque_pointer_call', BASE.replace('struct command cp;', 'struct command cp; encode_member(dev);'), None, 'insufficient_or_explicit_conditional_provenance'),
        ('nested_field_write', BASE.replace('cp.value=dev->value;', '{ cp.value=dev->value; }'), None, 'insufficient'),
        ('payload_compound_write', BASE.replace('cp.value=dev->value;', 'cp.value=dev->value; cp.value|=1;'), None, 'insufficient'),
        ('payload_parenthesized_alias', BASE.replace('cp.value=dev->value;', 'cp.value=dev->value; adjust(&(cp));'), None, 'insufficient'),
        ('field_array_target', BASE, HCI.replace('__le16 value;', '__le16 value[1];'), 'insufficient'),
        ('duplicate_scope_struct_tag', BASE.replace('struct command cp;', 'struct command { __u16 value; }; struct command cp;'), None, 'insufficient'),
    ]
    outputs = []
    for name, source, hci, expected in cases:
        result = report(source, hci or HCI)
        outputs.append({'name': name, 'expected': expected, 'source': source,
                        'counts': result['counts'], 'findings': result['findings'],
                        'sites': result['sites']})
    doc = {'scope':'development synthetic audit only; no held-out source or patches read',
           'module_sha256': hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
           'test_sha256': hashlib.sha256((MODULES/'structured_hci_single_revision_test.py').read_bytes()).hexdigest(),
           'outputs': outputs}
    output_name = sys.argv[1] if len(sys.argv) > 1 else 'method_audit_probe_results.json'
    if Path(output_name).name != output_name or not output_name.endswith('.json'):
        raise ValueError('output must be one JSON filename within this audit directory')
    (HERE/output_name).write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'module_sha256': doc['module_sha256'], 'cases': [{'name': item['name'], 'expected': item['expected'], 'counts': item['counts']} for item in outputs]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
