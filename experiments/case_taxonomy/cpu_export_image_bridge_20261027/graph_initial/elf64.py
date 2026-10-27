"""Small bounded ELF64 reader for the two pinned kernel build architectures."""
from pathlib import Path
import struct

def need(value,reason):
    if not value:
        raise ValueError(reason)

class ELF64:
    def __init__(self,path):
        self.path=Path(path); self.raw=self.path.read_bytes()
        need(self.raw[:5]==b'\x7fELF\x02','not_ELF64')
        need(self.raw[5] in [1,2],'unknown_endian')
        self.order='little' if self.raw[5]==1 else 'big'
        self.endian='<' if self.order=='little' else '>'
        hdr=struct.unpack_from(self.endian+'HHIQQQIHHHHHH',self.raw,16)
        self.type,self.machine=hdr[0:2]
        need(self.type in [1,2,3] and self.machine in [22,62],'outside_pinned_ELF_domain')
        offset,entsize,count,nameindex=hdr[5],hdr[10],hdr[11],hdr[12]
        need(entsize==64 and 0<count<10000 and nameindex<count,'unsupported_section_table')
        self.sections=[]
        for index in range(count):
            vals=struct.unpack_from(self.endian+'IIQQQQIIQQ',self.raw,offset+index*entsize)
            row=dict(zip(['name_offset','type','flags','address','offset','size','link','info','alignment','entry_size'],vals))
            row['index']=index
            need(row['type']==8 or row['offset']+row['size']<=len(self.raw),'section_outside_file')
            self.sections.append(row)
        names=self.section_bytes(self.sections[nameindex])
        for row in self.sections:
            row['name']=self.cstr_bytes(names,row['name_offset'])
        symtabs=[s for s in self.sections if s['type']==2]
        need(len(symtabs)==1,'missing_or_multiple_full_symbol_tables')
        symtab=symtabs[0]; self.symtab_index=symtab['index']
        need(symtab['entry_size']==24 and symtab['size']%24==0,'unsupported_symbols')
        strings=self.section_bytes(self.sections[symtab['link']])
        self.symbols=[]; self.by_name={}
        for index in range(symtab['size']//24):
            name,info,other,section,value,size=struct.unpack_from(self.endian+'IBBHQQ',self.raw,symtab['offset']+index*24)
            row={'index':index,'name':self.cstr_bytes(strings,name),'type':info&15,'binding':info>>4,'visibility':other,
                 'section':section,'value':value,'size':size}
            self.symbols.append(row); self.by_name.setdefault(row['name'],[]).append(row)
        self.relocations=[]
        for section in self.sections:
            if section['type']!=4:
                continue
            need(section['entry_size']==24 and section['size']%24==0 and section['link']==self.symtab_index,'unsupported_RELA')
            for offset in range(0,section['size'],24):
                pos,info,addend=struct.unpack_from(self.endian+'QQq',self.raw,section['offset']+offset)
                self.relocations.append({'section':section['info'],'offset':pos,'type':info&0xffffffff,
                                         'symbol':self.symbols[info>>32],'addend':addend})

    @staticmethod
    def cstr_bytes(raw,offset,limit=None):
        need(0<=offset<len(raw),'string_offset_outside_file')
        end=raw.find(b'\0',offset,len(raw) if limit is None else min(len(raw),offset+limit))
        need(end!=-1,'unterminated_string')
        return raw[offset:end].decode('ascii')

    def section_bytes(self,section):
        need(section['type']!=8,'no_bytes_for_NOBITS')
        return self.raw[section['offset']:section['offset']+section['size']]

    def named(self,name,kind=None):
        return [s for s in self.by_name.get(name,[]) if s['section']!=0 and (kind is None or s['type']==kind)]

    def unique(self,name,kind=None):
        rows=self.named(name,kind)
        need(len(rows)==1,'symbol_not_unique:'+name)
        return rows[0]

    def symbol_bytes(self,symbol):
        section=self.sections[symbol['section']]
        offset=symbol['value']-(0 if self.type==1 else section['address'])
        need(0<=offset and offset+symbol['size']<=section['size'],'symbol_outside_section')
        return self.section_bytes(section)[offset:offset+symbol['size']]

    def va_bytes(self,address,size):
        rows=[s for s in self.sections if s['flags']&2 and s['type']!=8 and s['address']<=address and address+size<=s['address']+s['size']]
        need(len(rows)==1,'virtual_address_not_unique_file_backed:'+hex(address))
        row=rows[0]; offset=row['offset']+address-row['address']
        return self.raw[offset:offset+size]

    def pointer(self,address):
        return int.from_bytes(self.va_bytes(address,8),self.order)

    def cstring(self,address,limit=128):
        raw=bytearray()
        for index in range(limit):
            byte=self.va_bytes(address+index,1)
            if byte==b'\0':
                return raw.decode('ascii')
            raw.extend(byte)
        raise ValueError('bounded_string_not_terminated')

    def relocs_in(self,symbol):
        return [r for r in self.relocations if r['section']==symbol['section'] and symbol['value']<=r['offset']<symbol['value']+symbol['size']]

    def object_target(self,relocation,bias=0):
        symbol=relocation['symbol']; point=symbol['value']+relocation['addend']+bias
        return [s for s in self.symbols if s['section']==symbol['section'] and s['type'] in [1,2]
                and s['value']<=point<s['value']+s['size']]
