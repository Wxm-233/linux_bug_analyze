
.text
.macro read_ctr reg
 adrp \reg, ctr_fixture
 ldr \reg, [\reg, :lo12:ctr_fixture]
.endm
.macro trace_op op, addr
 adrp x9, trace
 add x9, x9, :lo12:trace
 adrp x10, ntrace
 ldr x11, [x10, :lo12:ntrace]
 add x9, x9, x11, lsl #4
 mov x12, #\op
 str x12, [x9]
 str \addr, [x9, #8]
 add x11, x11, #1
 str x11, [x10, :lo12:ntrace]
.endm
/* Maintenance itself is replaced with a log. Branch/arithmetic stay AArch64. */
.macro dc op, addr
 .ifc \op, cvac
 trace_op 1, \addr
 .else
 .ifc \op, ivac
 trace_op 2, \addr
 .else
 .ifc \op, civac
 trace_op 3, \addr
 .else
 .error "unregistered cache op"
 .endif
 .endif
 .endif
.endm
.macro dsb domain
 trace_op 4, xzr
.endm
.macro _cond_uaccess_extable label, fixup
.endm
	.macro	dcache_line_size, reg, tmp
	read_ctr	\tmp
	ubfm		\tmp, \tmp, #16, #19	// cache line size encoding
	mov		\reg, #4		// bytes per word
	lsl		\reg, \reg, \tmp	// actual cache line size
	.endm

	.macro __dcache_op_workaround_clean_cache, op, addr
.if WORKAROUND == 0
	dc	\op, \addr
.else
	dc	civac, \addr
.endif
	.endm
	.macro dcache_by_myline_op op, domain, start, end, linesz, tmp, fixup
	sub	\tmp, \linesz, #1
	bic	\start, \start, \tmp
.Ldcache_op\@:
	.ifc	\op, cvau
	__dcache_op_workaround_clean_cache \op, \start
	.else
	.ifc	\op, cvac
	__dcache_op_workaround_clean_cache \op, \start
	.else
	.ifc	\op, cvap
	sys	3, c7, c12, 1, \start	// dc cvap
	.else
	.ifc	\op, cvadp
	sys	3, c7, c13, 1, \start	// dc cvadp
	.else
	dc	\op, \start
	.endif
	.endif
	.endif
	.endif
	add	\start, \start, \linesz
	cmp	\start, \end
	b.lo	.Ldcache_op\@
	dsb	\domain

	_cond_uaccess_extable .Ldcache_op\@, \fixup
	.endm
	.macro dcache_by_line_op op, domain, start, end, tmp1, tmp2, fixup
	dcache_line_size \tmp1, \tmp2
	dcache_by_myline_op \op, \domain, \start, \end, \tmp1, \tmp2, \fixup
	.endm
.global __pi_dcache_inval_poc
.type __pi_dcache_inval_poc, %function
__pi_dcache_inval_poc:

	dcache_line_size x2, x3
	sub	x3, x2, #1
	tst	x1, x3				// end cache line aligned?
	bic	x1, x1, x3
	b.eq	1f
	dc	civac, x1			// clean & invalidate D / U line
1:	tst	x0, x3				// start cache line aligned?
	bic	x0, x0, x3
	b.eq	2f
	dc	civac, x0			// clean & invalidate D / U line
	b	3f
2:	dc	ivac, x0			// invalidate D / U line
3:	add	x0, x0, x2
	cmp	x0, x1
	b.lo	2b
	dsb	sy
	ret


.global __pi_dcache_clean_poc
.type __pi_dcache_clean_poc, %function
__pi_dcache_clean_poc:

	dcache_by_line_op cvac, sy, x0, x1, x2, x3
	ret


.global dcache_inval_poc
.set dcache_inval_poc, __pi_dcache_inval_poc
.global dcache_clean_poc
.set dcache_clean_poc, __pi_dcache_clean_poc
.section .note.GNU-stack,"",%progbits
