"""Bounded FDT token/property reader; preserves raw CPU reg bytes and order."""
from pathlib import Path
import struct

def need(value,reason):
    if not value:
        raise ValueError(reason)

def read(path):
    raw=Path(path).read_bytes(); header=struct.unpack_from('>10I',raw,0)
    magic,total,structure,strings,_,version,last,_,string_size,structure_size=header
    need(magic==0xd00dfeed and version>=17 and last<=17 and total<=len(raw),'unsupported_FDT_header')
    need(structure+structure_size<=total and strings+string_size<=total,'FDT_blocks_outside_blob')
    names=raw[strings:strings+string_size]; index=structure; end=structure+structure_size
    stack=[]; nodes=[]; active=[]
    def text(data,offset):
        stop=data.find(b'\0',offset); need(stop>=offset,'unterminated_FDT_string'); return data[offset:stop].decode('ascii'),stop+1
    while index<end:
        token=struct.unpack_from('>I',raw,index)[0]; index+=4
        if token==1:
            name,index=text(raw,index); index=(index+3)&~3
            stack.append(name); path='/'+'/'.join(x for x in stack if x)
            row={'path':path,'properties':{}}; nodes.append(row); active.append(row)
        elif token==2:
            need(bool(stack),'unbalanced_FDT_end_node'); stack.pop(); active.pop()
        elif token==3:
            length,offset=struct.unpack_from('>II',raw,index); index+=8
            name,_=text(names,offset); need(index+length<=end and active,'FDT_property_outside_node')
            need(name not in active[-1]['properties'],'duplicate_FDT_property')
            active[-1]['properties'][name]=raw[index:index+length]; index=(index+length+3)&~3
        elif token==4:
            pass
        elif token==9:
            need(not stack,'FDT_unclosed_node'); return nodes
        else:
            raise ValueError('unknown_FDT_token')
    raise ValueError('FDT_END_missing')

def cpus(path):
    nodes=read(path); parent=next(row for row in nodes if row['path']=='/cpus')
    cells=int.from_bytes(parent['properties']['#address-cells'],'big')
    need(cells in [1,2],'unsupported_CPU_address_cells')
    rows=[]
    for row in nodes:
        p=row['properties']
        if p.get('device_type')!=b'cpu\0':
            continue
        reg=p['reg']; need(len(reg)==cells*4,'unexpected_CPU_reg_length')
        rows.append({'path':row['path'],'reg_hex':reg.hex(),'hardware_id':int.from_bytes(reg,'big'),
                     'status':p.get('status',b'okay\0').rstrip(b'\0').decode(),
                     'enable_method':p.get('enable-method',b'').rstrip(b'\0').decode()})
    need(bool(rows) and len({r['hardware_id'] for r in rows})==len(rows),'CPU_hardware_IDs_empty_or_duplicate')
    return rows

if __name__=='__main__':
    import json,sys
    print(json.dumps(cpus(sys.argv[1]),indent=2))
