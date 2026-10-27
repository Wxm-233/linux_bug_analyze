"""Seal the independent source oracle before any harness/results are read."""
import datetime
import hashlib
import json
import pathlib

STAGE = pathlib.Path(__file__).resolve().parent
OUTPUT = STAGE / 'expected_matrix_pre_harness.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to overwrite sealed pre-harness oracle')
manifest = json.loads((STAGE / 'source_manifest_pre_harness.json').read_text(encoding='utf-8'))
lookup = {(x['version'], x['source_path']): x for x in manifest['files']}

def evidence(version, path, start, end, claim):
    source = lookup[(version, path)]
    return {
        'version': version,
        'revision': source['revision'],
        'path': path,
        'blob_sha1': source['blob_sha1'],
        'sha256': source['sha256'],
        'lines': {'start': start, 'end': end},
        'claim': claim,
    }

references = []
for version in ('parent', 'fixed'):
    references += [
        evidence(version, 'net/bluetooth/hci_core.c', 789, 862,
                 'init4 target branch only checks DLE at 842; builds cp at 845-846 and calls add at 847; returns 0 at 861'),
        evidence(version, 'net/bluetooth/hci_request.c', 285, 309,
                 'prepare allocates 3+plen at 292; NULL exits at 293-294; header built at 296-298; plen bytes copied via skb_put_data at 300-301'),
        evidence(version, 'net/bluetooth/hci_request.c', 311, 346,
                 'add_ev rejects nonzero req.err before prepare; NULL sets -ENOMEM; successful command sets flags/event then calls queue_tail; add is a real wrapper function passing event=0'),
        evidence(version, 'include/net/bluetooth/hci.h', 1547, 1551,
                 'target opcode is 0x2024; packed two __le16 fields have four-byte payload'),
        evidence(version, 'include/linux/skbuff.h', 2212, 2220,
                 'original skb_put_data appends storage then memcpy(tmp,data,len); no payload endian conversion'),
    ]
references += [
    evidence('parent', 'net/bluetooth/hci_core.c', 879, 890,
             'normal init orchestration requires HCI_PRIMARY before calling init3 and init4; the isolated init4 function does not enforce this gate'),
    evidence('parent', 'include/net/bluetooth/hci_core.h', 269, 274,
             'le_max_tx_len and le_max_tx_time are native __u16 fields'),
    evidence('parent', 'include/net/bluetooth/hci_core.h', 1165, 1165,
             'LMP_LE capability is features[0][4] & LMP_LE; target init4 branch is DLE-gated, not additionally LMP_LE-gated'),
    evidence('parent', 'include/net/bluetooth/hci.h', 396, 396, 'LMP_LE mask 0x40'),
    evidence('parent', 'include/net/bluetooth/hci.h', 435, 435, 'DLE feature mask 0x20'),
    evidence('parent', 'include/net/bluetooth/hci.h', 2253, 2261, 'packed HCI command header has little endian opcode and one byte plen; header size3'),
    evidence('parent', 'net/bluetooth/hci_request.h', 28, 36, 'request contains hdev, command queue and stored error int'),
    evidence('parent', 'include/net/bluetooth/bluetooth.h', 306, 306, 'HCI_REQ_START is BIT(0)'),
    evidence('parent', 'include/net/bluetooth/bluetooth.h', 335, 343, 'real bt_skb_alloc adds reserve and allocates SKB; later harness allocator may only model outcome'),
    evidence('parent', 'include/linux/byteorder/generic.h', 90, 90, 'cpu_to_le16 aliases __cpu_to_le16'),
    evidence('parent', 'arch/x86/include/uapi/asm/byteorder.h', 5, 5, 'x86 selects little endian definitions'),
    evidence('parent', 'arch/s390/include/uapi/asm/byteorder.h', 5, 5, 's390 selects big endian definitions'),
    evidence('parent', 'include/uapi/linux/byteorder/little_endian.h', 35, 35, '__cpu_to_le16 uses identity native16 on little endian'),
    evidence('parent', 'include/uapi/linux/byteorder/big_endian.h', 35, 35, '__cpu_to_le16 swaps native16 on big endian'),
    evidence('parent', 'include/uapi/asm-generic/errno-base.h', 9, 16, 'EIO=5; ENOMEM=12'),
]

payload_by_variant = {
    'parent/x86_64': '1b004801',
    'parent/s390x': '001b0148',
    'fixed/x86_64': '1b004801',
    'fixed/s390x': '1b004801',
}
conditions = []
for initial_err in (0, -5):
    for configured_allocation in ('success', 'failure'):
        actual_allocation = initial_err == 0
        copied = actual_allocation and configured_allocation == 'success'
        final_err = initial_err if initial_err else (0 if copied else -12)
        variants = []
        for variant, payload in payload_by_variant.items():
            version, arch = variant.split('/')
            variants.append({
                'version': version,
                'architecture': arch,
                'constructed_cp_payload_hex': payload,
                'copied_payload_hex': payload if copied else None,
                'queued_stub_packet_hex': '242004' + payload if copied else None,
                'copied_payload_little_endian_values': ([6912, 18433] if variant == 'parent/s390x' else [27, 328]) if copied else None,
                'copied_payload_format_status': ('wrong_endian' if variant == 'parent/s390x' else 'matches_expected_little_endian') if copied else 'not_evaluated',
            })
        conditions.append({
            'condition_id': f'err_{initial_err}_allocation_{configured_allocation}',
            'initial_req_err': initial_err,
            'allocation_configured_outcome': configured_allocation,
            'init4_return': 0,
            'target_add_call_attempts': 1,
            'hci_req_add_is_real_source_function': True,
            'hci_req_add_ev_call_attempts': 1,
            'hci_prepare_cmd_calls': int(actual_allocation),
            'allocator_actually_called': actual_allocation,
            'allocator_call_count': int(actual_allocation),
            'allocator_input_command_bytes': 7 if actual_allocation else None,
            'allocator_outcome_observed': configured_allocation if actual_allocation else 'not_called',
            'final_req_err': final_err,
            'stored_error_status': 'preserved_EIO' if initial_err else ('none' if copied else 'set_ENOMEM'),
            'payload_memcpy_performed': copied,
            'skb_put_data_call_count': int(copied),
            'payload_memcpy_count': int(copied),
            'payload_memcpy_bytes': 4 if copied else 0,
            'header_storage_created': copied,
            'header_hex': '242004' if copied else None,
            'skb_put_call_count': 2 if copied else 0,
            'queue_empty_check_count': int(copied),
            'queue_tail_observation_count': int(copied),
            'queue_tail_observation_is_kernel_transport_execution': False,
            'observed_req_event': 0 if copied else None,
            'observed_req_start_bit': 1 if copied else None,
            'variants': variants,
        })

oracle = {
    'schema': 'independent-source-oracle-pre-harness-v1',
    'sealed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_exported_at_utc': manifest['exported_at_utc'],
    'task_day': '2026-10-02',
    'independence_statement': 'Only the two specified Git source revisions and raw source files have been read. No experimental runner, C harness, result JSON or stdout has been read before this file is sealed.',
    'conditions_count': 4,
    'variant_observations_count': 16,
    'revisions': manifest['revisions'],
    'fixed_configuration': {
        'entry': 'hci_init4_req',
        'dev_type': 'HCI_PRIMARY',
        'features_0_4': 'LMP_LE (0x40)',
        'le_features_0': 'HCI_LE_DATA_LEN_EXT (0x20)',
        'commands': 'all zero',
        'other_features_flags_quirks': 'all disabled',
        'initial_cmd_queue': 'empty',
        'le_max_tx_len': 27,
        'le_max_tx_time': 328,
        'opcode': '0x2024',
        'payload_length': 4,
        'command_bytes_without_transport_packet_type': 7,
    },
    'source_sequence': [
        'init4 constructs cp (native endian in parent, cpu_to_le16 in fixed)',
        'init4 calls real hci_req_add wrapper once for 0x2024',
        'wrapper calls hci_req_add_ev with event=0',
        'hci_req_add_ev returns immediately for nonzero req.err',
        'with req.err=0, hci_prepare_cmd calls allocator for 3+4 command bytes',
        'NULL allocation skips header/payload creation and queue; add_ev stores -ENOMEM',
        'successful allocation creates header and invokes original skb_put_data',
        'original skb_put_data memcpy copies four existing cp bytes without endian conversion',
        'add_ev checks empty queue, adds START flag, sets event and calls queue_tail',
        'init4 returns 0 independently of the stored req.err',
    ],
    'interpretation_limits': [
        'A target add call attempt does not establish queue_tail reached.',
        'Local cp construction still occurs when existing req.err prevents any allocation or payload copy.',
        'When no payload copy occurs, format is not_evaluated, never format_normal.',
        'Successful source path reaches queue_tail; in a harness this is a queue stub observation, not actual device transmission.',
        'The queue observation should inspect copied SKB storage, not merely the address or bytes of the stack cp argument.',
        'hci_init4_req returns 0; -EIO/-ENOMEM remain req.err. No hci_req_run or top-level error propagation is exercised.',
        'HCI_PRIMARY and LMP_LE are fixed contextual capabilities. The direct init4 target branch itself is controlled by DLE alone.',
    ],
    'source_evidence': references,
    'conditions': conditions,
}
raw = (json.dumps(oracle, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
OUTPUT.write_bytes(raw)
receipt = {
    'sealed_at_utc': oracle['sealed_at_utc'],
    'file': OUTPUT.name,
    'sha256': hashlib.sha256(raw).hexdigest(),
    'byte_count': len(raw),
    'harness_read_before_seal': False,
}
(STAGE / 'oracle_seal_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt))
