"""Source-derived expected matrix, written before harness output review."""
import itertools
import json
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    rows=[]
    for primary,le_capable,data_len,error in itertools.product((False,True),repeat=4):
        target=primary and data_len and not error
        stages=[1] if error else [1,2,3,4] if primary else [1,2]
        rows.append({'primary':primary,'lmp_le_capable':le_capable,'data_len_feature':data_len,
                     'init1_sync_error':error,'expected_target_add_attempts':int(target),
                     'expected_sync_call_stages':stages,'expected_return':'-EIO' if error else '0',
                     'injected_capability_consistency':'not_established_as_real_controller_state' if data_len and (not le_capable or not primary) else 'not_contradicted_by_these_three_flags'})
    result={'saved_at_utc':datetime.now(timezone.utc).isoformat(),
            'stage':'independent source expectation before reading harness outputs',
            'source_parent':'cef456cd354ef485f12d57000c455e83e416a2b6',
            'source_fix':'727ea61a5028f8ac96f75ab34cb1b56e63fd9227',
            'protocol_error_position':'__hci_req_sync init1 returns -EIO; not stage2 or all possible error locations',
            'conditional_target_predicate':'primary && data_len_feature && !init1_sync_error, with init2/init3 modeled successful and add recorder modeled successful',
            'full_source_target_add_predicate':'init1_sync_nonnegative && init2_sync_nonnegative && dev_type==HCI_PRIMARY && init3_sync_nonnegative && (le_features[0]&HCI_LE_DATA_LEN_EXT)',
            'local_init4_predicate':'le_features[0]&HCI_LE_DATA_LEN_EXT only; no explicit lmp_le_capable or device-type check in init4',
            'count_kind':'target hci_req_add call attempt; actual skb queueing additionally needs req->err==0 and successful allocation/copy',
            'scope':'source condition review only, not full kernel/configuration/firmware/hardware reachability',
            'rows':rows,'target_present_rows':sum(row['expected_target_add_attempts'] for row in rows),
            'unknowns':['real reachability of LE-capability false but DLE-feature true',
                        'device response side effects on injected capability/data-length values',
                        'real skb allocation/request errors and command completion',
                        'outer open/configuration paths and actual controller support',
                        'other stage errors and all HCI flags/configurations']}
    (HERE/'expected_matrix_pre_harness.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'expected_target_present_rows':result['target_present_rows'],'saved':True}))


if __name__=='__main__':main()
