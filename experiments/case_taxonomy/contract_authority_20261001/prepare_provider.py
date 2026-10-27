"""Extract an already-read HCI response provider for a bounded projection."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from outbound_scalar_single_revision import functions
from endian_consumer_single_revision import mask_comments_and_literals, closing_delimiter

REVISION = 'cef456cd354ef485f12d57000c455e83e416a2b6'
FILE = 'net/bluetooth/hci_event.c'
FUNCTION = 'hci_cc_le_read_max_data_len'
STRUCT = 'hci_rp_le_read_max_data_len'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer', action='store_true')
    args = parser.parse_args()
    function_name = 'hci_cc_le_write_def_data_len' if args.consumer else FUNCTION
    struct_name = 'hci_cp_le_write_def_data_len' if args.consumer else STRUCT
    directory = HERE/'provider_projection'
    directory.mkdir(exist_ok=True)
    output = directory/('consumer.json' if args.consumer else 'source.json')
    if output.exists():
        raise RuntimeError('preserve prior provider extraction')
    files, commands = {}, []
    for path in (FILE, 'include/net/bluetooth/hci.h'):
        argv = ['git', '-C', '/root/repos/linux', 'show', REVISION+':'+path]
        text = subprocess.check_output(argv, text=True)
        blob_cmd = ['git', '-C', '/root/repos/linux', 'rev-parse', REVISION+':'+path]
        blob = subprocess.check_output(blob_cmd, text=True).strip()
        files[path] = dict(text=text, sha256=sha(text), git_blob=blob)
        commands.extend([argv, blob_cmd])
    source = files[FILE]['text']
    matched = [fn for fn in functions(mask_comments_and_literals(source)) if fn.name == function_name]
    assert len(matched) == 1
    fn = matched[0]
    # Retain the complete signature from the beginning of its source line.
    start = source.rfind('\n', 0, fn.start)+1
    function = dict(file=FILE, line=source.count('\n', 0, start)+1,
                    quote=source[start:fn.closing+1], sha256=files[FILE]['sha256'])
    header = files['include/net/bluetooth/hci.h']['text']
    needle = 'struct '+struct_name+' {'
    start = header.index(needle)
    opening = header.index('{', start)
    closing = closing_delimiter(mask_comments_and_literals(header), opening, '{', '}')
    assert closing is not None
    end = header.index(';', closing)+1
    structure = dict(file='include/net/bluetooth/hci.h', line=header.count('\n',0,start)+1,
        quote=header[start:end], sha256=files['include/net/bluetooth/hci.h']['sha256'])
    record = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(), revision=REVISION,
        scope='Known-source function extraction; no new sample, kernel or device execution.',
        commands=commands, files={name:{k:v for k,v in file.items() if k!='text'} for name,file in files.items()},
        function=function, structure=structure)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(function['quote'])
    print(structure['quote'])


if __name__ == '__main__':
    main()
