.section .text
.global _start
_start:
 call main
 mov %eax,%ebx
 mov $1,%eax
 int $0x80
.global call6
call6:
 push %ebp
 push %edi
 push %esi
 push %ebx
 mov 20(%esp),%eax
 mov 24(%esp),%ebx
 mov 28(%esp),%ecx
 mov 32(%esp),%edx
 mov 36(%esp),%esi
 mov 40(%esp),%edi
 mov 44(%esp),%ebp
 int $0x80
 pop %ebx
 pop %esi
 pop %edi
 pop %ebp
 ret
.section .note.GNU-stack,"",@progbits
