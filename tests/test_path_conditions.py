import unittest

from linux_bug_analyze.path_conditions import analyze, occurrences, params, strip_code


def calls(text, name):
    return [c for c in analyze(text) if c.name == name]


class PathConditionTests(unittest.TestCase):
    def test_early_exit_adds_reversed_condition(self):
        text = """
pte_t f(struct mm_struct *mm, pte_t *ptep, pte_t pte)
{
	if (!pte_present(pte)) {
		foo(pte);
		return pte;
	}
	if (!pte_napot(pte)) {
		bar();
		return pte;
	}
	baz(pte);
}
"""
        (napot,) = calls(text, 'pte_napot')
        self.assertEqual(napot.conds, (('! pte_present ( pte )', False),))
        self.assertEqual(napot.cond_prefix, '!')
        (foo,) = calls(text, 'foo')
        self.assertEqual(foo.conds, (('! pte_present ( pte )', True),))
        (baz,) = calls(text, 'baz')
        self.assertEqual(baz.conds, (('! pte_present ( pte )', False), ('! pte_napot ( pte )', False)))
        self.assertEqual(baz.line, 12)

    def test_else_if_chain(self):
        text = """
void g(pte_t entry)
{
	if (none(entry)) {
		a();
	} else if (is_migration(entry)) {
		b();
	} else
		c(entry);
}
"""
        (c,) = calls(text, 'c')
        self.assertEqual(c.conds, (('none ( entry )', False), ('is_migration ( entry )', False)))
        (b,) = calls(text, 'b')
        self.assertEqual(b.conds, (('none ( entry )', False), ('is_migration ( entry )', True)))

    def test_same_condition_prefix(self):
        text = "pte_t h(pte_t x)\n{\n\tif (!pte_present(x) || !pte_cont(x))\n\t\treturn x;\n\tk(x);\n}\n"
        (cont,) = calls(text, 'pte_cont')
        self.assertEqual(cont.cond_prefix, '! pte_present ( x ) || !')
        self.assertEqual(cont.conds, ())
        (k,) = calls(text, 'k')
        self.assertEqual(k.conds, (('! pte_present ( x ) || ! pte_cont ( x )', False),))

    def test_loop_macro_continue_and_unbraced_if(self):
        text = """
void l(void)
{
	for_each_napot_order(order) {
		if (!ok(order))
			continue;
		use(order);
	}
	after();
}
"""
        (use,) = calls(text, 'use')
        self.assertEqual(use.conds, (('! ok ( order )', False),))
        (after,) = calls(text, 'after')
        self.assertEqual(after.conds, ())   # the continue only leaves the loop body

    def test_comments_strings_preprocessor_switch_do(self):
        text = """
int m(int v)
{
	/* if (fake(v)) return 0; */
	// gone(v);
#ifdef CONFIG_X
	hidden(v);
#endif
	printk("if (x) %d", v);
	switch (v) {
	case 1:
		one();
		break;
	default:
		other();
	}
	do {
		step();
	} while (more(v));
	if (v)
		yes();
	else
		no();
}
"""
        names = [c.name for c in analyze(text)]
        self.assertNotIn('fake', names)
        self.assertNotIn('gone', names)
        for n in ('hidden', 'printk', 'one', 'other', 'step', 'more', 'yes', 'no'):  # both config branches kept
            self.assertIn(n, names)
        (no,) = calls(text, 'no')
        self.assertEqual(no.conds, (('v', False),))
        self.assertEqual(strip_code('a\n#define X(v) \\\n\tf(v)\nb'), 'a\n\n\nb')

    def test_args_and_params(self):
        text = "void set_huge_pte_at(struct mm_struct *mm, unsigned long addr, pte_t *ptep,\n" \
               "\t\t     pte_t pte, unsigned long sz)\n{\n\tq(mm, f(a, b), (c, d), sz);\n}\n"
        self.assertEqual(params(text), ['mm', 'addr', 'ptep', 'pte', 'sz'])
        (q,) = calls(text, 'q')
        self.assertEqual(q.args, ['mm', 'f ( a , b )', '( c , d )', 'sz'])

    def test_statement_expression_and_initializer(self):
        text = "void n(void)\n{\n\tstruct s v = { .a = g(1) };\n\tint w = ({ int t = h(); t; });\n\tif (w)\n\t\tz();\n}\n"
        names = [c.name for c in analyze(text)]
        self.assertEqual(names[:2], ['g', 'h'])
        (z,) = calls(text, 'z')
        self.assertEqual(z.conds, (('w', True),))


    def test_occurrences_with_conditions(self):
        text = """
void e(struct pt_regs *regs, long nr)
{
	nr = syscall_enter_from_user_mode(regs, nr);
	if (nr >= 0 && nr < NR_syscalls)
		call(regs, nr);
	else if (nr != -1)
		regs->a0 = -ENOSYS;
}
"""
        (o,) = occurrences(text, {'ENOSYS'})
        self.assertEqual(o.line, 8)
        self.assertEqual(o.conds, (('nr >= 0 && nr < NR_syscalls', False), ('nr != - 1', True)))
        self.assertEqual(len(occurrences(text, {'regs'})), 3)   # body only; the header is not searched


if __name__ == '__main__':
    unittest.main()
