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

    def test_long_header_and_brace_in_comment_above(self):
        src = ("/*\n * Handle {get,set,swap}_context operations\n */\n"
               "SYSCALL_DEFINE3(swapcontext, struct ucontext __user *, old_ctx,\n"
               "\t\tstruct ucontext __user *, new_ctx,\n\t\tlong, ctx_size)\n{\n\treturn 0;\n}\n"
               "void set_huge_pte_at(struct mm_struct *mm,\n\t\t     unsigned long addr,\n"
               "\t\t     pte_t *ptep,\n\t\t     pte_t pte,\n\t\t     unsigned long sz)\n{\n}\n")
        self.assertEqual([h for _, _, h in named_spans(src)], ["SYSCALL_DEFINE3", "set_huge_pte_at"])
        self.assertEqual([h for _, _, h in named_spans(src, window=4)], ["SYSCALL_DEFINE3"])

    def test_line_comment_and_blank_line_before_brace(self):
        src = ("//#if 0\nstatic int usb_get_report(struct usb_device *dev,\n\t\tstruct usb_host_interface *inter,\n"
               "\t\tunsigned char id, void *buf, int size)\n{\n\treturn 0;\n}\n"
               "static int set_gic_ap0r(struct kvm_vcpu *vcpu,\n\t\t\tu64 val)\n\n{\n\treturn 0;\n}\n")
        self.assertEqual([h for _, _, h in named_spans(src)], ["usb_get_report", "set_gic_ap0r"])

    def test_comment_line_inside_parameter_list(self):
        src = ("int x;\n\nstatic void inputfifo_send_data(\n    /* static inline void inputfifo_send_data( */\n"
               "    unsigned int a,\n    unsigned int b)\n{\n}\n")
        self.assertEqual([h for _, _, h in named_spans(src)], ["inputfifo_send_data"])


if __name__ == "__main__":
    unittest.main()
