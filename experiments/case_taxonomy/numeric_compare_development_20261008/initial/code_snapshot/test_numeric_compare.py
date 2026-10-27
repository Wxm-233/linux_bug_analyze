import hashlib
import unittest
from numeric_compare import Source,inspect_function


def probe(body,header='',field='__le32 n;',params='struct pkt *p'):
    text=header+'\nstruct pkt { '+field+' };\nstatic int probe('+params+') {\n'+body+'\n}\n'
    raw=text.encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    return inspect_function(Source('probe.c','synthetic','synthetic/probe.c',blob,raw),'probe')


def statuses(result):
    return [r['status'] for r in result['field_atoms']]


class NumericCompareTests(unittest.TestCase):
    def test_host_and_reversed(self):
        for expr in ('v != p->n','p->n == v','p->n >= v','v < p->n'):
            with self.subTest(expr=expr):self.assertEqual(statuses(probe('u32 v=7; if ('+expr+') return 1; return 0;')),['candidate'])

    def test_matching_decode(self):
        for expr in ('v != le32_to_cpu(p->n)','le32_to_cpu(p->n) > v'):
            self.assertEqual(statuses(probe('u32 v=7; if ('+expr+') return 1; return 0;')),['normal'])

    def test_local_encoded_type_does_not_mean_host(self):
        self.assertEqual(statuses(probe('u32 v=cpu_to_le32(7); if (p->n == v) return 1; return 0;')),['normal'])
        self.assertEqual(statuses(probe('u32 v=cpu_to_le32(7); if (p->n < v) return 1; return 0;')),['insufficient'])

    def test_zero_equalities_and_order(self):
        for expr in ('p->n==0','0!=p->n','!p->n','p->n'):
            self.assertEqual(statuses(probe('if ('+expr+') return 1; return 0;')),['normal'])
        self.assertEqual(statuses(probe('if (p->n > 0) return 1; return 0;')),['insufficient'])

    def test_update_shapes(self):
        body='u32 count, v; count=8; v=sizeof(u64)*8+3; while(count) { count >>= 1; v -= 1; } if (v != p->n) return 1; return 0;'
        value=probe(body)['field_atoms'][0]
        self.assertEqual(value['status'],'candidate')
        self.assertEqual(len(value['left']['visible_writes']),2)
        self.assertFalse(value['left']['runtime_value_proven'])

    def test_zero_atom_inside_nested_logic(self):
        r=probe('u32 v=1; if ((p->n != v) || ((!p->n) && (le32_to_cpu(p->n) == v))) return 1; return 0;')
        self.assertEqual(statuses(r),['candidate','normal','normal'])

    def test_unknown_value_sources(self):
        for body,params in [('if(p->n!=v)return 1; return 0;','struct pkt *p, u32 v'),
                            ('u32 v=external(); if(p->n!=v)return 1; return 0;','struct pkt *p'),
                            ('u32 v; if(1) v=7; if(p->n!=v)return 1; return 0;','struct pkt *p')]:
            self.assertEqual(statuses(probe(body,params=params)),['insufficient'])

    def test_width_signed_and_conversion_direction(self):
        for body in ['u16 v=7; if(p->n!=v)return 1;', 's32 v=7; if(p->n!=v)return 1;',
                     'u32 v=7; if(le16_to_cpu(p->n)!=v)return 1;',
                     'u32 v=7; if(be32_to_cpu(p->n)!=v)return 1;']:
            self.assertEqual(statuses(probe(body)),['insufficient'])

    def test_escape_shadow_mixed_write(self):
        for body in ['u32 v=7; unknown(&v); if(p->n!=v)return 1;',
                     'u32 v=7; {u32 v=8;} if(p->n!=v)return 1;',
                     'u32 v=7; v=cpu_to_le32(8); if(p->n!=v)return 1;']:
            self.assertEqual(statuses(probe(body)),['insufficient'])

    def test_masks(self):
        for expression,want in [('p->n & cpu_to_le32(7)','normal'),('p->n & 7','candidate'),
                                 ('p->n & cpu_to_be32(7)','insufficient'),('p->n & cpu_to_le16(7)','insufficient')]:
            self.assertEqual(statuses(probe('if ('+expression+') return 1;')), [want])

    def test_array_repeat_macro_and_directive(self):
        self.assertEqual(statuses(probe('if(p->n==7)return 1;',field='__le32 n[2];')),['insufficient'])
        self.assertEqual(statuses(probe('if(p->n==p->n)return 1;')),['insufficient'])
        self.assertEqual(statuses(probe('if(le32_to_cpu(p->n)==7)return 1;',header='#define le32_to_cpu(x) (x)')),['insufficient'])
        r=probe('#ifdef X\n if(p->n==7)return 1;\n#endif\n')
        self.assertEqual(r['execution_status'],'insufficient')

    def test_sizeof(self):
        self.assertEqual(statuses(probe('if(sizeof(p->n)) return 1;')),['not_value_read'])

    def test_raw_copy_is_encoded_not_host(self):
        self.assertEqual(statuses(probe('u32 v=p->n; if(p->n==v)return 1;')),['normal'])

    def test_mixed_revision_decl(self):
        text='struct pkt {__le32 n;}; static int probe(struct pkt *p){if(p->n==7)return 1;}'
        raw=text.encode();s=Source('x.c','one','x.c','unknown',raw)
        d=Source('x.c','two','x.c','unknown',raw)
        self.assertEqual(statuses(inspect_function(s,'probe',[d])),['insufficient'])

    def test_helper_and_sizeof_type_bindings(self):
        r=probe('if(le32_to_cpu(p->n)==7)return 1;',params='struct pkt *p, u32 (*le32_to_cpu)(u32)')
        self.assertEqual(statuses(r),['insufficient'])
        self.assertEqual(statuses(probe('if(p->n==sizeof(u32))return 1;',header='#define u32 u64')),['insufficient'])
        self.assertEqual(statuses(probe('typedef unsigned char u32; if(p->n==sizeof(u32))return 1;')),['insufficient'])


if __name__=='__main__': unittest.main()
