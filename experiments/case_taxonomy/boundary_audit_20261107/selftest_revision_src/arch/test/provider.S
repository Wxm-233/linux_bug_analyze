.text
.globl asm_api
.type asm_api,@function
asm_api:
 mov $1, %eax
 ret
.size asm_api,.-asm_api
