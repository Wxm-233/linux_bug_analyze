"""Relocation-aware finite verification of CPU export objects in linked ELF.

Pointer width is 64 bits. Only the relocation encodings seen in the pinned
ELF64 x86/s390 objects are accepted. Literal merging is checked by content at
the actual linked target, never by assuming an input section base survived.
"""
import hashlib

from elf64 import ELF64, need

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

class Graph:
    def __init__(self,obj,image):
        self.obj,self.image=obj,image
        need(obj.type==1 and image.type==2 and obj.machine==image.machine and obj.order==image.order,'ELF_context_mismatch')
        self.bases={}; self.data_rows={}; self.function_rows={}
        group=obj.unique('topology_attr_group',1); linked=image.unique('topology_attr_group',1)
        need(group['size']==linked['size'],'group_layout_size_mismatch')
        self.group,self.linked_group=group,linked
        self.bind_section(group,linked['value'])
        fields={}
        for reloc in obj.relocs_in(group):
            need(self.width(reloc)==8,'group_field_not_64_bit')
            field_offset=reloc['offset']-group['value']
            target=obj.object_target(reloc)
            pointer=image.pointer(linked['value']+field_offset)
            names=[s['name'] for s in target]
            if names in [['default_attrs'],['bin_attrs']]:
                symbol=target[0]
                candidates=[s for s in image.named(symbol['name'],1) if s['value']==pointer]
                need(len(candidates)==1 and candidates[0]['size']==symbol['size'],'group_pointer_not_selected_array:'+symbol['name'])
                fields[symbol['name']]={'offset':field_offset,'pointer':pointer,'object_symbol':symbol}
                self.bind_section(symbol,pointer)
            else:
                expected=self.literal(reloc)
                need(expected=='topology' and image.cstring(pointer)==expected,'group_name_binding_failed')
                fields['name']={'offset':field_offset,'pointer':pointer,'string':expected}
        need(set(fields)=={'name','default_attrs','bin_attrs'},'group_fields_incomplete_or_ambiguous')
        self.fields=fields

    def bind_section(self,symbol,linked_address):
        section=symbol['section']; base=linked_address-symbol['value']
        need(section not in self.bases or self.bases[section]==base,'input_data_section_mapping_inconsistent')
        self.bases[section]=base

    def width(self,reloc):
        types={62:{1:8,2:4,4:4,10:4,11:4},22:{4:4,5:4,19:4,20:4,22:8}}
        width=types.get(self.obj.machine,{}).get(reloc['type'])
        need(width is not None,'unsupported_relocation:'+str(reloc['type']))
        return width

    def bias(self,reloc):
        if self.obj.machine==62 and reloc['type'] in [2,4]:
            return 4
        if self.obj.machine==22 and reloc['type'] in [19,20]:
            return -2
        return 0

    def literal(self,reloc):
        symbol=reloc['symbol']
        need(0<symbol['section']<len(self.obj.sections),'literal_has_no_object_section')
        section=self.obj.sections[symbol['section']]
        need(section['flags']&0x20 and section['flags']&0x10,'not_a_mergeable_string_literal')
        offset=symbol['value']+reloc['addend']+self.bias(reloc)
        return self.obj.cstr_bytes(self.obj.section_bytes(section),offset,256)

    def linked_symbol(self,symbol):
        if symbol['section'] in self.bases:
            address=self.bases[symbol['section']]+symbol['value']
            rows=[s for s in self.image.named(symbol['name']) if s['value']==address]
        else:
            rows=self.image.named(symbol['name'])
        need(len(rows)==1,'linked_symbol_not_unique:'+symbol['name'])
        return rows[0]

    def resolve(self,reloc,location,encoded):
        width=self.width(reloc); typ=reloc['type']; symbol=reloc['symbol']; addend=reloc['addend']
        literal=None
        if 0<symbol['section']<len(self.obj.sections):
            section=self.obj.sections[symbol['section']]
            if section['flags']&0x20 and section['flags']&0x10:
                literal=self.literal(reloc)
        if literal is not None:
            signed=int.from_bytes(encoded,self.image.order,signed=True)
            if self.obj.machine==62 and typ in [2,4]:
                address=location+signed+4
            elif self.obj.machine==22 and typ in [19,20]:
                address=location+signed*2-2
            elif self.obj.machine==22 and typ==5:
                address=location+signed
            elif self.obj.machine==62 and typ==11:
                address=signed&((1<<64)-1)
            else:
                address=int.from_bytes(encoded,self.image.order)
            need(self.image.cstring(address)==literal,'linked_literal_content_mismatch')
            return {'kind':'string','value':literal,'linked_target':address,'relocation_type':typ}
        if symbol['type']==3:
            # Section-relative targets are bound through actual named objects
            # or functions, not an unverified whole output section mapping.
            targets=self.obj.object_target(reloc,self.bias(reloc))
            need(len(targets)==1,'section_target_not_unique_named_object')
            target=targets[0]; linked=self.linked_symbol(target)
            value=linked['value']+(symbol['value']+addend-target['value'])
            target_name=target['name']; target_kind='function' if target['type']==2 else 'object'
        else:
            linked=self.linked_symbol(symbol)
            value=linked['value']+addend; target_name=symbol['name']
            target_kind='function' if linked['type']==2 else 'object'
        if self.obj.machine==62 and typ in [2,4]:
            value-=location
        elif self.obj.machine==22 and typ in [19,20]:
            delta=value-location; need(delta%2==0,'s390_halfword_relocation_not_aligned'); value=delta//2
        elif self.obj.machine==22 and typ==5:
            value-=location
        wanted=(value&((1<<(8*width))-1)).to_bytes(width,self.image.order)
        need(encoded==wanted,'linked_relocation_target_mismatch:'+target_name)
        return {'kind':target_kind,'symbol':target_name,'linked_symbol_value':linked['value'],
                'addend':addend,'relocation_type':typ}

    def compare(self,symbol,linked_address):
        original=self.obj.symbol_bytes(symbol)
        actual=self.image.va_bytes(linked_address,symbol['size'])
        unrelocated=bytearray(original); normalized=bytearray(actual); relocs=[]
        occupied=set()
        for reloc in self.obj.relocs_in(symbol):
            offset=reloc['offset']-symbol['value']; width=self.width(reloc)
            need(0<=offset and offset+width<=len(original),'relocation_outside_symbol')
            interval=set(range(offset,offset+width)); need(not occupied&interval,'overlapping_relocations'); occupied|=interval
            resolved=self.resolve(reloc,linked_address+offset,actual[offset:offset+width])
            resolved['offset_in_symbol']=offset; relocs.append(resolved)
            unrelocated[offset:offset+width]=b'\0'*width; normalized[offset:offset+width]=b'\0'*width
        need(unrelocated==normalized,'nonrelocated_bytes_differ:'+symbol['name'])
        return {'name':symbol['name'],'object_section':self.obj.sections[symbol['section']]['name'],
                'object_value':symbol['value'],'linked_address':linked_address,'bytes':symbol['size'],
                'relocations_verified':relocs,'all_nonrelocated_bytes_match':True,
                'object_bytes_sha256':digest(original),'linked_bytes_sha256':digest(actual)}

    def function(self,name):
        if name in self.function_rows:
            return self.function_rows[name]
        symbol=self.obj.unique(name,2); linked=self.image.unique(name,2)
        need(symbol['size']==linked['size'],'function_size_differs:'+name)
        row=self.compare(symbol,linked['value']); self.function_rows[name]=row
        return row

    def data(self,symbol,address):
        self.bind_section(symbol,address)
        row=self.compare(symbol,address); self.data_rows[symbol['name']]=row
        return row

    def analyze(self,expected_arrays):
        self.data(self.group,self.linked_group['value'])
        arrays={}
        for name in ['default_attrs','bin_attrs']:
            field=self.fields[name]; symbol=field['object_symbol']; pointer=field['pointer']
            need(symbol['size']%8==0,'array_size_not_pointer_multiple')
            expected=expected_arrays[name]
            need(symbol['size']==(len(expected)+1)*8,'array_length_mismatch')
            array_row=self.data(symbol,pointer); members=[]
            for index,member in enumerate(expected):
                address=self.image.pointer(pointer+index*8); obj=self.obj.unique(member,1)
                linked=self.linked_symbol(obj)
                need(address==linked['value'],'array_points_to_wrong_member:'+member)
                row=self.data(obj,address)
                literals=[r for r in row['relocations_verified'] if r['kind']=='string']
                expected_name=member.split('dev_attr_',1)[1] if member.startswith('dev_attr_') else member.split('bin_attr_',1)[1]
                need(len(literals)==1 and literals[0]['value']==expected_name,'attribute_name_mismatch:'+member)
                functions=[r for r in row['relocations_verified'] if r['kind']=='function']
                handler=expected_name+('_show' if member.startswith('dev_attr_') else '_read')
                need(len(functions)==1 and functions[0]['symbol']==handler,'attribute_callback_mismatch:'+member)
                callback=self.function(handler)
                members.append({'member':member,'address':address,'attribute_name':expected_name,
                                'handler':handler,'handler_address':callback['linked_address']})
            need(self.image.pointer(pointer+len(expected)*8)==0,'array_not_null_terminated')
            arrays[name]={'address':pointer,'members':members,'full_array_verified':True,'trailing_null':True}
        # This callback is the concrete link to the sysfs registration path.
        publish=self.function('topology_add_dev')
        targets={r.get('symbol') for r in publish['relocations_verified']}
        need({'get_cpu_device','topology_attr_group','sysfs_create_group'}<=targets,'registration_callback_not_bound')
        return {'status':'supported','ELF_machine':self.obj.machine,'byte_order':self.obj.order,
                'linked_address_domain':'static ELF link addresses, not observed runtime addresses',
                'group_address':self.linked_group['value'],'group_fields':{k:{a:b for a,b in v.items() if a!='object_symbol'} for k,v in self.fields.items()},
                'arrays':arrays,'data_objects':list(self.data_rows.values()),'functions':list(self.function_rows.values()),
                'registration_callback_bound':True,'native_textual_origin_from_binary_alone_proved':False,
                'runtime_execution_or_stability_proved':False}

def analyze(obj,image,arrays):
    return Graph(obj,image).analyze(arrays)
