from c_ranges import declarations, changed_lines, scrub
from common import write

src = '''/* int fake(void) { } */
#define OUTER(x) \\
 INNER(x)
static int real(int a)
{
 return a;
}
struct shape { int member; };
static const struct shape ops[] = {
 { .member = 2 },
};
typedef unsigned long count_t;
'''
EXPECTED = {('macro','OUTER',2,3), ('function','real',4,7), ('struct','shape',8,8),
            ('object','ops',9,11), ('typedef','count_t',12,12)}
got, errors = declarations(src)
assert {(r['kind'],r['name'],r['start'],r['end']) for r in got} == EXPECTED, got
assert not errors
patch = '''diff --git a/a.c b/a.c
--- a/a.c
+++ b/a.c
@@ -3,1 +3,1 @@ unrelated_function(void)
- return 0;
+ return 1;
'''
p = changed_lines(patch)[0]
assert p['old_lines'] == [3] and p['new_lines'] == [3]
assert not [r for r in got if r['kind']=='function' and r['start'] <= 3 <= r['end']]
assert declarations('int added(void) { return 1; }')[0][0]['name'] == 'added'
assert declarations('int removed(void) { return 0; }')[0][0]['name'] == 'removed'
assert not declarations('/* comment only */')[0]
assert declarations('DEFINE_UNKNOWN(foo) { x; }')[1][0]['reason'] == 'macro_generated_function'
assert declarations('static int same(void) { return 0; }')[0][0]['name'] == 'same'
assert not scrub('// hi\n /* bye */').strip()
assert scrub('"literal-only changed line"',keep_literals=True).strip()
assert declarations('unsigned long actual __ro_after_init;')[0][0]['name'] == 'actual'
assert declarations('unsigned long actual __attribute__((used)) = 0;')[0][0]['name'] == 'actual'
write('selftest_match_result.json', {'passed': True, 'expected_declarations': sorted(EXPECTED),
      'checks': ['added', 'deleted', 'misleading_hunk_context', 'multiline_macro',
                 'object_initializer', 'type', 'comments', 'static_name', 'unknown_macro']})
print('match selftest passed')
