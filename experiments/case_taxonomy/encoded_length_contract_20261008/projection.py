"""Fixed integer/byte representation model, not C or buffer execution."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
LENGTHS=[0,1,8,255,256,257,0x1234,0xffff]
HEADER_LENGTH=4

def run():
    rows=[]
    for host_order in ['little','big']:
        for length in LENGTHS:
            storage=length.to_bytes(2,'big')
            raw=int.from_bytes(storage,host_order)
            decoded=int.from_bytes(storage,'big')
            expected=length+HEADER_LENGTH  # Mathematical input contract, independent of raw host read.
            variants=dict(raw_plus_header=raw+HEADER_LENGTH,
                          decode_plus_header=decoded+HEADER_LENGTH,
                          decode_without_header=decoded)
            rows.append(dict(host_order=host_order,length_input=length,encoded_storage_hex=storage.hex(),
                raw_host_read=raw,expected_byte_count=expected,variants=variants,
                mismatches={name:value!=expected for name,value in variants.items()}))
    counts={order:{name:sum(r['mismatches'][name] for r in rows if r['host_order']==order)
                   for name in rows[0]['variants']} for order in ['little','big']}
    assert counts=={'little':{'raw_plus_header':5,'decode_plus_header':0,'decode_without_header':8},
                    'big':{'raw_plus_header':0,'decode_plus_header':0,'decode_without_header':8}}
    assert next(r for r in rows if r['host_order']=='little' and r['length_input']==8)['variants']['raw_plus_header']==2052
    result=dict(model='unsigned_BE16_storage_to_native_integer_then_byte_count',header_length=HEADER_LENGTH,
        lengths_prelocked=LENGTHS,cases=rows,mismatch_counts=counts,
        experimental_unit='16 synthetic value/host-order combinations of one source contract',
        execution_limits=dict(c_executed=False,kernel_executed=False,device_executed=False,
                              source_reachability_certified=False,actual_buffer_bounds_certified=False,
                              c_preprocessing_certified=False,external_protocol_certified=False,
                              automatic_detector_executed=False,independent_positive_cases=0))
    p=HERE/'projection_results.json';assert not p.exists()
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(rows),mismatch_counts=counts),ensure_ascii=False))
if __name__=='__main__':run()
