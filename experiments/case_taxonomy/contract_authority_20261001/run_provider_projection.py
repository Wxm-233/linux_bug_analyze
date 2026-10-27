"""Known-source response -> host members -> payload -> Linux reader projection.

This is a development harness with injected responses and completion context,
not a controller or kernel run. Original provider/reader functions are copied;
producer assignments come from the previously validated generation plans.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
OUT = HERE/'provider_projection'
PRIOR = HERE.parent/'contract_assertions_20261001/final_run_01'
VALUES = [(27,328,27,328), (251,2120,251,2120), (37,901,41,1003)]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def validate_extraction(record, commands):
    for block in (record['function'], record['structure']):
        argv = ['git','-C','/root/repos/linux','show',record['revision']+':'+block['file']]
        source = subprocess.check_output(argv, text=True)
        commands.append(argv)
        assert hashlib.sha256(source.encode()).hexdigest() == block['sha256']
        lines = source.splitlines()
        quote = block['quote'].splitlines()
        assert lines[block['line']-1:block['line']-1+len(quote)] == quote
        blob_argv = ['git','-C','/root/repos/linux','rev-parse',record['revision']+':'+block['file']]
        blob = subprocess.check_output(blob_argv, text=True).strip()
        commands.append(blob_argv)
        assert blob == record['files'][block['file']]['git_blob']


def create_c(provider, consumer, plans):
    code = r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
typedef uint8_t __u8;
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BT_DBG(...) do {} while (0)
#define HCI_OP_LE_WRITE_DEF_DATA_LEN 0x2024
static __u16 le16_to_cpu(__le16 v) {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
 return v;
#else
 return __builtin_bswap16(v);
#endif
}
static __le16 cpu_to_le16(__u16 v) { return le16_to_cpu(v); }
struct hci_dev { char name[16]; __u16 le_max_tx_len,le_max_tx_time,le_max_rx_len,le_max_rx_time;
 __u16 le_def_tx_len,le_def_tx_time; };
struct sk_buff { unsigned char *data; };
static void *sent_data;
static void *hci_sent_cmd_data(struct hci_dev *hdev, unsigned opcode) {
 (void)hdev; return opcode == HCI_OP_LE_WRITE_DEF_DATA_LEN ? sent_data : NULL;
}
'''
    code += provider['structure']['quote']+'\n'+consumer['structure']['quote']+'\n'
    code += provider['function']['quote']+'\n'+consumer['function']['quote']+'\n'
    for name, plan in plans.items():
        assert len(plan['programs']) == 1
        program = plan['programs'][0]
        assert program['payload_struct'] == 'hci_cp_le_write_def_data_len'
        assert [(f['name'],f['bits'],f['endian']) for f in program['fields']] == [('tx_len',16,'le'),('tx_time',16,'le')]
        assert program['payload_declaration']['text'] == consumer['structure']['quote']
        code += 'static void produce_'+name+'(struct hci_dev *hdev, unsigned char *out) {\n'
        code += ' struct hci_cp_le_write_def_data_len cp = {0};\n'
        code += '\n'.join(' '+field['original_assignment'] for field in program['fields'])+'\n'
        code += ' memcpy(out, &cp, sizeof(cp));\n}\n'
    code += r'''
static void state(const char *kind, const char *variant, unsigned i, struct hci_dev *hdev, unsigned char *payload) {
 printf("{\"kind\":\"%s\",\"variant\":\"%s\",\"index\":%u,\"host_values\":[%u,%u,%u,%u],\"reader_values\":[%u,%u],\"payload\":\"",
 kind,variant,i,hdev->le_max_tx_len,hdev->le_max_tx_time,hdev->le_max_rx_len,hdev->le_max_rx_time,hdev->le_def_tx_len,hdev->le_def_tx_time);
 if(payload) for(size_t n=0;n<sizeof(struct hci_cp_le_write_def_data_len);n++) printf("%02x",payload[n]);
 puts("\"}");
}
int main(void) {
 const __u16 values[][4] = {'''
    code += ','.join('{'+','.join(map(str,vector))+'}' for vector in VALUES)
    code += r'''};
 printf("{\"kind\":\"layout\",\"host_endian\":\"%s\",\"rp_size\":%zu,\"cp_size\":%zu,\"cp_offsets\":[%zu,%zu]}\n",'''
    code += r'''
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
 "little",
#else
 "big",
#endif
 sizeof(struct hci_rp_le_read_max_data_len),sizeof(struct hci_cp_le_write_def_data_len),
 offsetof(struct hci_cp_le_write_def_data_len,tx_len),offsetof(struct hci_cp_le_write_def_data_len,tx_time));
 for(unsigned i=0;i<3;i++) {
  unsigned char response[sizeof(struct hci_rp_le_read_max_data_len)]={0};
  for(unsigned j=0;j<4;j++) { response[1+2*j]=(unsigned char)values[i][j]; response[2+2*j]=(unsigned char)(values[i][j]>>8); }
  for(unsigned v=0;v<2;v++) {
   struct hci_dev hdev={.le_max_tx_len=27,.le_max_tx_time=328,.le_max_rx_len=27,.le_max_rx_time=328,.le_def_tx_len=51,.le_def_tx_time=801};
   struct sk_buff skb={response};
   hci_cc_le_read_max_data_len(&hdev,&skb);
   struct hci_cp_le_write_def_data_len sent;
   if(v==0) produce_parent(&hdev,(unsigned char *)&sent); else produce_fix(&hdev,(unsigned char *)&sent);
   sent_data=&sent; unsigned char status=0; struct sk_buff complete={&status};
   hci_cc_le_write_def_data_len(&hdev,&complete);
   state("chain",v==0?"parent":"fix",i,&hdev,(unsigned char *)&sent);
  }
 }
 struct hci_dev hdev={.le_max_tx_len=27,.le_max_tx_time=328,.le_max_rx_len=27,.le_max_rx_time=328,.le_def_tx_len=51,.le_def_tx_time=801};
 unsigned char response[sizeof(struct hci_rp_le_read_max_data_len)]={1,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88};
 struct sk_buff skb={response}; hci_cc_le_read_max_data_len(&hdev,&skb);
 state("provider_error","none",0,&hdev,NULL);
 struct hci_cp_le_write_def_data_len sent={cpu_to_le16(251),cpu_to_le16(2120)};
 sent_data=&sent; unsigned char status=1; struct sk_buff complete={&status};
 hci_cc_le_write_def_data_len(&hdev,&complete); state("reader_error","none",0,&hdev,NULL);
 status=0; sent_data=NULL; hci_cc_le_write_def_data_len(&hdev,&complete);
 state("reader_missing_sent","none",0,&hdev,NULL);
 return 0;
}
'''
    return code


def verify_rows(rows, endian):
    assert rows[0] == dict(kind='layout',host_endian=endian,rp_size=9,cp_size=4,cp_offsets=[0,2])
    assert len(rows) == 10
    seen = set()
    summaries = {'parent':{'vectors':0,'format_mismatch_vectors':0}, 'fix':{'vectors':0,'format_mismatch_vectors':0}}
    for row in rows[1:]:
        key = row['kind'],row['variant'],row['index']
        assert key not in seen
        seen.add(key)
        if row['kind'] == 'chain':
            values = list(VALUES[row['index']])
            assert row['host_values'] == values
            domain = endian if row['variant']=='parent' else 'little'
            expected_bytes = b''.join(v.to_bytes(2,domain) for v in values[:2])
            actual = bytes.fromhex(row['payload'])
            assert actual == expected_bytes
            expected_read = [int.from_bytes(actual[n:n+2],'little') for n in (0,2)]
            assert row['reader_values'] == expected_read
            mismatch = actual != b''.join(v.to_bytes(2,'little') for v in values[:2])
            summaries[row['variant']]['vectors'] += 1
            summaries[row['variant']]['format_mismatch_vectors'] += int(mismatch)
        else:
            assert row['kind'] in ('provider_error','reader_error','reader_missing_sent')
            assert row['host_values'] == [27,328,27,328]
            assert row['reader_values'] == [51,801] and row['payload'] == ''
    assert len(seen) == 9
    assert all(summary['vectors']==3 for summary in summaries.values())
    return summaries


def main():
    if (OUT/'results.json').exists():
        raise RuntimeError('preserve completed projection')
    provider, consumer = read(OUT/'source.json'), read(OUT/'consumer.json')
    git_commands=[]
    validate_extraction(provider,git_commands)
    validate_extraction(consumer,git_commands)
    plans={name:read(PRIOR/(name+'_plan.json')) for name in ('parent','fix')}
    path=OUT/'chain.c'
    with path.open('x', encoding='utf-8') as stream:
        stream.write(create_c(provider,consumer,plans))
    commands,targets=[],{}
    with tempfile.TemporaryDirectory(prefix='hci-provider-chain-') as temporary:
        for target,compiler,launcher,endian in (
            ('x86_64','gcc',[],'little'),('s390x','s390x-linux-gnu-gcc',['qemu-s390x'],'big')):
            binary=Path(temporary)/target
            argv=[compiler,'-std=gnu11','-static','-O0','-Wall','-Wextra','-Werror',str(path),'-o',str(binary)]
            process=subprocess.run(argv,capture_output=True,text=True)
            commands.append(dict(argv=argv,returncode=process.returncode,stdout=process.stdout,stderr=process.stderr))
            assert process.returncode==0, process.stderr
            argv=launcher+[str(binary)]
            process=subprocess.run(argv,capture_output=True,text=True)
            commands.append(dict(argv=argv,returncode=process.returncode,stdout=process.stdout,stderr=process.stderr))
            assert process.returncode==0, process.stderr
            rows=[json.loads(line) for line in process.stdout.splitlines()]
            summary=verify_rows(rows,endian)
            targets[target]=dict(rows=rows,summary=summary,executable_sha256=sha(binary),independent_oracle='source host values + raw bytes + actual Linux reader verified')
    record=dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Known-source projected callbacks and assignments; simulated response/status/sent context, no device or kernel execution.',
        values=VALUES,git_commands=git_commands,commands=commands,targets=targets,
        runner_sha256=sha(Path(__file__)),source_sha256=sha(path),
        input_hashes={str(file.relative_to(HERE.parent)):sha(file) for file in [OUT/'source.json',OUT/'consumer.json',PRIOR/'parent_plan.json',PRIOR/'fix_plan.json']})
    save(OUT/'results.json',record)
    print('known provider/reader projections verified:',{target:data['summary'] for target,data in targets.items()})


if __name__=='__main__':
    main()
