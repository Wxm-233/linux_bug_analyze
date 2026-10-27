.global _start, armed, same_write, changed_write, restored_write, neighbor_write, finished
.text
_start:
    ldr x0, =0x40100000
    mov w1, #0x1234
    str w1, [x0]
armed:
    nop
same_write:
    str w1, [x0]
    mov w1, #0x5678
changed_write:
    str w1, [x0]
    mov w1, #0x1234
restored_write:
    str w1, [x0]
neighbor_write:
    str w1, [x0, #4]
finished:
    b finished
