import unittest

from linux_bug_analyze.sibling_pairs import function_spans_strict, header_name, named_spans


class HeaderNameTest(unittest.TestCase):
    def test_plain_and_qualified_headers(self):
        self.assertEqual(header_name("static int __init uml_initrd_setup(char *line, int *add)\n"), "uml_initrd_setup")
        self.assertEqual(header_name("void __noreturn die(const char *str, struct pt_regs *regs, long err)"), "die")
        self.assertEqual(header_name("SYSCALL_DEFINE3(s390_pci_mmio_write, unsigned long, mmio_addr, const void __user *, b, size_t, l)"),
                         "SYSCALL_DEFINE3")

    def test_attribute_before_and_after_name(self):
        self.assertEqual(header_name('void __attribute__ ((__section__ (".__syscall_stub"))) stub_clone_handler(void)'),
                         "stub_clone_handler")
        self.assertEqual(header_name("int foo(int a) __attribute__((weak))"), "foo")

    def test_control_statement_and_non_headers(self):
        self.assertIsNone(header_name("\tswitch (insn->code)"))
        self.assertIsNone(header_name("static const struct pci_device_id ids[] = "))
        self.assertIsNone(header_name("struct foo"))

    def test_only_last_statement_fragment(self):
        self.assertEqual(header_name("DEFINE_SHOW_ATTRIBUTE(x); static int bar(void)"), "bar")
        self.assertIsNone(header_name("EXPORT_SYMBOL_GPL(x); struct y"))


SRC = """#ifdef CONFIG_A
static void f(void)
{
#else
static void f(int x)
{
#endif
\tswitch (x) {
\tcase 1:
\t\tbreak;
\t}
}

int g(void)
{
\treturn 0;
}
"""


class SpansTest(unittest.TestCase):
    def test_unbalanced_ifdef_gives_no_switch_name(self):
        names = [h for _, _, h in named_spans(SRC)]
        self.assertNotIn("switch", names)
        self.assertIn("g", names)

    def test_plain_spans(self):
        spans = function_spans_strict("int g(void)\n{\n\treturn 0;\n}\n")
        self.assertEqual(spans, [(2, 4, "g")])


if __name__ == "__main__":
    unittest.main()
