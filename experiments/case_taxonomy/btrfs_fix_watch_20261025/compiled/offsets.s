	.arch armv8-a
	.file	"super.c"
	.text
#APP
	.section	".initcall7.init", "a"		
__initcall__kmod_btrfs__900_2691_init_btrfs_fs7:			
.long	init_btrfs_fs - .	
.previous					

#NO_APP
	.align	2
	.p2align 4,,11
	.type	btrfs_test_super, %function
btrfs_test_super:
.LFB6370:
	.cfi_startproc
	ldr	x2, [x0, 872]
	ldr	x0, [x1, 1632]
	ldr	x1, [x2, 1632]
	cmp	x1, x0
	cset	w0, eq
	ret
	.cfi_endproc
.LFE6370:
	.size	btrfs_test_super, .-btrfs_test_super
	.align	2
	.p2align 4,,11
	.type	btrfs_cmp_device_free_bytes, %function
btrfs_cmp_device_free_bytes:
.LFB6380:
	.cfi_startproc
	ldr	x2, [x0, 16]
	ldr	x0, [x1, 16]
	cmp	x2, x0
	cset	w0, cc
	csinv	w0, w0, wzr, ls
	ret
	.cfi_endproc
.LFE6380:
	.size	btrfs_cmp_device_free_bytes, .-btrfs_cmp_device_free_bytes
	.align	2
	.p2align 4,,11
	.type	btrfs_control_open, %function
btrfs_control_open:
.LFB6385:
	.cfi_startproc
	mov	w0, 0
	str	xzr, [x1, 192]
	ret
	.cfi_endproc
.LFE6385:
	.size	btrfs_control_open, .-btrfs_control_open
	.align	2
	.p2align 4,,11
	.type	btrfs_unfreeze, %function
btrfs_unfreeze:
.LFB6388:
	.cfi_startproc
	ldr	x0, [x0, 872]
	mov	x1, 4096
	add	x0, x0, 16
#APP
// 229 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_andnot
	prfm	pstl1strm, [x0]
1:	ldxr	x2, [x0]
	bic	x2, x2, x1
	stxr	w3, x2, [x0]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
	mov	w0, 0
	ret
	.cfi_endproc
.LFE6388:
	.size	btrfs_unfreeze, .-btrfs_unfreeze
	.align	2
	.p2align 4,,11
	.type	btrfs_freeze, %function
btrfs_freeze:
.LFB6387:
	.cfi_startproc
	stp	x29, x30, [sp, -16]!
	.cfi_def_cfa_offset 16
	.cfi_offset 29, -16
	.cfi_offset 30, -8
	mov	x29, sp
	ldr	x1, [x0, 872]
	add	x1, x1, 16
	ldr	x0, [x1, 16]
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x1]
1:	ldxr	x2, [x1]
	orr	x2, x2, 4096
	stxr	w3, x2, [x1]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
	bl	btrfs_attach_transaction_barrier
	cmn	x0, #4096
	bhi	.L13
	ldp	x29, x30, [sp], 16
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	b	btrfs_commit_transaction
	.p2align 2,,3
.L13:
	.cfi_restore_state
	cmn	x0, #2
	csel	w0, w0, wzr, ne
	ldp	x29, x30, [sp], 16
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6387:
	.size	btrfs_freeze, .-btrfs_freeze
	.align	2
	.p2align 4,,11
	.type	btrfs_kill_super, %function
btrfs_kill_super:
.LFB6384:
	.cfi_startproc
	stp	x29, x30, [sp, -32]!
	.cfi_def_cfa_offset 32
	.cfi_offset 29, -32
	.cfi_offset 30, -24
	mov	x29, sp
	str	x19, [sp, 16]
	.cfi_offset 19, -16
	ldr	x19, [x0, 872]
	bl	kill_anon_super
	mov	x0, x19
	ldr	x19, [sp, 16]
	ldp	x29, x30, [sp], 32
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_def_cfa_offset 0
	b	btrfs_free_fs_info
	.cfi_endproc
.LFE6384:
	.size	btrfs_kill_super, .-btrfs_kill_super
	.align	2
	.p2align 4,,11
	.type	btrfs_set_super, %function
btrfs_set_super:
.LFB6371:
	.cfi_startproc
	stp	x29, x30, [sp, -32]!
	.cfi_def_cfa_offset 32
	.cfi_offset 29, -32
	.cfi_offset 30, -24
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -16
	.cfi_offset 20, -8
	mov	x19, x0
	mov	x20, x1
	bl	set_anon_super
	cbnz	w0, .L17
	str	x20, [x19, 872]
.L17:
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 32
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6371:
	.size	btrfs_set_super, .-btrfs_set_super
	.section	.text.unlikely,"ax",@progbits
	.align	2
	.type	btrfs_put_super, %function
btrfs_put_super:
.LFB6358:
	.cfi_startproc
	ldr	x0, [x0, 872]
	b	close_ctree
	.cfi_endproc
.LFE6358:
	.size	btrfs_put_super, .-btrfs_put_super
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align	3
.LC0:
	.string	" \t\n\\"
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_show_devname, %function
btrfs_show_devname:
.LFB6389:
	.cfi_startproc
	stp	x29, x30, [sp, -16]!
	.cfi_def_cfa_offset 16
	.cfi_offset 29, -16
	.cfi_offset 30, -8
	mov	x29, sp
	ldr	x1, [x1, 104]
	ldr	x1, [x1, 872]
	ldr	x4, [x1, 1632]
	ldr	x1, [x4, 152]!
	cmp	x1, x4
	beq	.L22
	mov	x2, 0
	b	.L24
	.p2align 2,,3
.L37:
	ldr	x3, [x2, 120]
	ldr	x5, [x1, 120]
	cmp	x5, x3
	csel	x2, x2, x1, cs
.L23:
	ldr	x1, [x1]
	cmp	x1, x4
	beq	.L36
.L24:
	ldr	x3, [x1, 104]
	tbnz	x3, 2, .L23
	ldr	x3, [x1, 64]
	cbz	x3, .L23
	cbnz	x2, .L37
	mov	x2, x1
	ldr	x1, [x1]
	cmp	x1, x4
	bne	.L24
	.p2align 3,,7
.L36:
	cbz	x2, .L22
	ldr	x1, [x2, 64]
	adrp	x2, .LC0
	add	x2, x2, :lo12:.LC0
	add	x1, x1, 16
	bl	seq_escape
	bl	rcu_read_unlock_strict
	mov	w0, 0
	ldp	x29, x30, [sp], 16
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L22:
	.cfi_restore_state
#APP
// 2498 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/fs/btrfs/super.c" 1
	.pushsection __bug_table,"aw"; .align 2; 14470: .long 14471f - 14470b; .pushsection .rodata.str,"aMS",@progbits,1; 14472: .string "fs/btrfs/super.c"; .popsection; .long 14472b - 14470b; .short 2498; .short (1 << 0)|(((9) << 8)); .popsection; 14471: brk 0x800
// 0 "" 2
#NO_APP
	bl	rcu_read_unlock_strict
	mov	w0, 0
	ldp	x29, x30, [sp], 16
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6389:
	.size	btrfs_show_devname, .-btrfs_show_devname
	.align	2
	.p2align 4,,11
	.type	btrfs_control_ioctl, %function
btrfs_control_ioctl:
.LFB6386:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	w0, 21
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -32
	.cfi_offset 20, -24
	mov	w20, w1
	str	x21, [sp, 32]
	.cfi_offset 21, -16
	mov	x21, x2
	bl	capable
	tbz	x0, 0, .L49
	mov	x0, x21
	mov	x1, 4096
	bl	memdup_user
	mov	x19, x0
	cmn	x0, #4096
	bhi	.L53
	strb	wzr, [x0, 4095]
	mov	w0, 37945
	movk	w0, 0x8048, lsl 16
	cmp	w20, w0
	beq	.L41
	bhi	.L42
	mov	w0, 37892
	movk	w0, 0x5000, lsl 16
	cmp	w20, w0
	beq	.L43
	add	w0, w0, 1
	cmp	w20, w0
	bne	.L52
	add	x0, x19, 8
	bl	btrfs_forget_devices
	sxtw	x20, w0
	b	.L45
	.p2align 2,,3
.L42:
	mov	w0, 37927
	movk	w0, 0x9000, lsl 16
	cmp	w20, w0
	bne	.L52
	adrp	x21, uuid_mutex
	add	x21, x21, :lo12:uuid_mutex
	mov	x0, x21
	bl	mutex_lock
	add	x0, x19, 8
	adrp	x2, .LANCHOR0
	mov	w1, 1
	add	x2, x2, :lo12:.LANCHOR0
	bl	btrfs_scan_one_device
	mov	x20, x0
	cmn	x0, #4096
	bhi	.L54
	ldr	x1, [x20, 48]
	mov	x0, x21
	ldr	x2, [x1, 56]
	ldr	x1, [x1, 96]
	cmp	x2, x1
	cset	w20, ne
	bl	mutex_unlock
	.p2align 3,,7
.L45:
	mov	x0, x19
	bl	kfree
.L38:
	ldr	x21, [sp, 32]
	mov	x0, x20
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 48
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L52:
	.cfi_restore_state
	mov	x20, -25
	b	.L45
	.p2align 2,,3
.L43:
	adrp	x21, uuid_mutex
	add	x21, x21, :lo12:uuid_mutex
	mov	x0, x21
	bl	mutex_lock
	add	x0, x19, 8
	mov	w1, 1
	adrp	x2, .LANCHOR0
	add	x2, x2, :lo12:.LANCHOR0
	bl	btrfs_scan_one_device
	mov	x20, x0
	cmn	x20, #4095
	mov	x0, x21
	csel	x20, x20, xzr, cs
	bl	mutex_unlock
	b	.L45
	.p2align 2,,3
.L41:
	mov	x0, x21
	bl	btrfs_ioctl_get_supported_features
	sxtw	x20, w0
	b	.L45
	.p2align 2,,3
.L53:
	mov	x20, x0
	b	.L38
	.p2align 2,,3
.L49:
	mov	x20, -1
	b	.L38
	.p2align 2,,3
.L54:
	mov	x0, x21
	bl	mutex_unlock
	b	.L45
	.cfi_endproc
.LFE6386:
	.size	btrfs_control_ioctl, .-btrfs_control_ioctl
	.section	.rodata.str1.8
	.align	3
.LC1:
	.string	"\0016Btrfs loaded, crc32c=%s%s\n"
	.section	.init.text,"ax",@progbits
	.align	2
	.type	init_btrfs_fs, %function
init_btrfs_fs:
.LFB6393:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	str	x21, [sp, 32]
	.cfi_offset 19, -32
	.cfi_offset 20, -24
	.cfi_offset 21, -16
	bl	btrfs_props_init
	bl	btrfs_init_sysfs
	mov	w19, w0
	cbnz	w0, .L55
	bl	btrfs_init_compress
	bl	btrfs_init_cachep
	mov	w19, w0
	cbnz	w0, .L57
	bl	extent_io_init
	mov	w19, w0
	cbnz	w0, .L58
	bl	extent_state_cache_init
	mov	w19, w0
	cbnz	w0, .L59
	bl	extent_map_init
	mov	w19, w0
	cbnz	w0, .L60
	bl	ordered_data_init
	mov	w19, w0
	cbnz	w0, .L61
	bl	btrfs_delayed_inode_init
	mov	w19, w0
	cbnz	w0, .L62
	bl	btrfs_auto_defrag_init
	mov	w19, w0
	cbnz	w0, .L63
	bl	btrfs_delayed_ref_init
	mov	w19, w0
	cbnz	w0, .L64
	bl	btrfs_prelim_ref_init
	mov	w19, w0
	cbnz	w0, .L65
	bl	btrfs_end_io_wq_init
	mov	w19, w0
	cbnz	w0, .L66
	adrp	x20, .LANCHOR0
	add	x20, x20, :lo12:.LANCHOR0
	add	x21, x20, 72
	mov	x0, x21
	bl	misc_register
	mov	w19, w0
	cbnz	w0, .L67
	bl	crc32c_impl
	mov	x1, x0
	adrp	x2, .LANCHOR1
	add	x2, x2, :lo12:.LANCHOR1
	adrp	x0, .LC1
	add	x0, x0, :lo12:.LC1
	bl	printk
	add	x0, x20, 152
	bl	register_filesystem
	mov	w19, w0
	cbz	w0, .L55
	mov	x0, x21
	bl	misc_deregister
.L67:
	bl	btrfs_end_io_wq_exit
.L66:
	bl	btrfs_prelim_ref_exit
.L65:
	bl	btrfs_delayed_ref_exit
.L64:
	bl	btrfs_auto_defrag_exit
.L63:
	bl	btrfs_delayed_inode_exit
.L62:
	bl	ordered_data_exit
.L61:
	bl	extent_map_exit
.L60:
	bl	extent_state_cache_exit
.L59:
	bl	extent_io_exit
.L58:
	bl	btrfs_destroy_cachep
.L57:
	bl	btrfs_exit_compress
	bl	btrfs_exit_sysfs
.L55:
	ldr	x21, [sp, 32]
	mov	w0, w19
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 48
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6393:
	.size	init_btrfs_fs, .-init_btrfs_fs
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_statfs, %function
btrfs_statfs:
.LFB6383:
	.cfi_startproc
	stp	x29, x30, [sp, -160]!
	.cfi_def_cfa_offset 160
	.cfi_offset 29, -160
	.cfi_offset 30, -152
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -144
	.cfi_offset 20, -136
	mov	x20, x1
	stp	x21, x22, [sp, 32]
	stp	x23, x24, [sp, 48]
	stp	x27, x28, [sp, 80]
	str	x0, [sp, 128]
	ldr	x0, [x0, 104]
	ldr	x19, [x0, 872]
	.cfi_offset 21, -128
	.cfi_offset 22, -120
	.cfi_offset 23, -112
	.cfi_offset 24, -104
	.cfi_offset 27, -80
	.cfi_offset 28, -72
	add	x23, x19, 1640
	ldr	x1, [x19, 768]
	str	x1, [sp, 112]
	ldr	x1, [x19, 1632]
	str	x1, [sp, 120]
	ldr	x0, [x19, 1640]
	ldr	w1, [x19, 3264]
	str	w1, [sp, 144]
	cmp	x23, x0
	beq	.L99
	mov	w22, 0
	mov	w28, 1
	mov	x27, 0
	stp	x25, x26, [sp, 64]
	.cfi_offset 26, -88
	.cfi_offset 25, -96
	sub	x25, x0, #112
	stp	xzr, xzr, [sp, 96]
	b	.L78
	.p2align 2,,3
.L74:
	ldr	x3, [x25, 88]
	cbnz	w22, .L77
	ldr	x0, [x25, 104]
	tbz	x0, 2, .L77
	tbnz	x0, 0, .L100
	ldr	x0, [x25, 96]
	ldr	x1, [sp, 104]
	add	x0, x1, x0
	sub	x0, x0, x3
	str	x0, [sp, 104]
	.p2align 3,,7
.L77:
	ldr	x2, [x25, 112]
	add	x27, x27, x3
	sub	x25, x2, #112
	cmp	x23, x2
	beq	.L138
.L78:
	ldr	x2, [x25, 104]
	tbz	x2, 0, .L74
	ldp	x21, x2, [x25, 88]
	mov	x0, x25
	ldr	x1, [sp, 96]
	add	x24, x25, 232
	add	x26, x1, x2
	bl	btrfs_account_ro_block_groups_free_space
	add	x21, x0, x21
	sub	x0, x26, x21
	str	x0, [sp, 96]
	adrp	x0, btrfs_raid_array+24
	add	x26, x0, :lo12:btrfs_raid_array+24
	mov	w21, 0
	.p2align 3,,7
.L76:
	add	x3, x25, w21, sxtw 4
	add	x3, x3, 224
	ldr	x3, [x3, 8]
	cmp	x3, x24
	beq	.L75
	ldr	x0, [x26]
	bl	btrfs_bg_type_to_factor
	mov	w28, w0
.L75:
	add	w21, w21, 1
	add	x24, x24, 16
	add	x26, x26, 32
	cmp	w21, 9
	bne	.L76
	b	.L74
	.p2align 2,,3
.L100:
	ldr	x2, [x25, 112]
	add	x27, x27, x3
	mov	w22, 1
	sub	x25, x2, #112
	cmp	x23, x2
	bne	.L78
	.p2align 3,,7
.L138:
	uxtw	x23, w28
	ldrb	w1, [sp, 144]
	ldp	x25, x26, [sp, 64]
	.cfi_restore 26
	.cfi_restore 25
	udiv	x0, x27, x23
	lsr	x0, x0, x1
.L73:
	ldr	x1, [sp, 112]
	ldrb	w2, [sp, 144]
	ldr	x1, [x1, 112]
	udiv	x1, x1, x23
	lsr	x1, x1, x2
	sub	x0, x1, x0
	stp	x1, x0, [x20, 16]
	mov	x2, 0
	add	x0, x19, 272
	mov	w3, 1
#APP
// 305 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
		prfm	pstl1strm, [x0]
1:	ldaxr	w1, [x0]
	eor	w4, w1, w2
	cbnz	w4, 2f
	stxr	w4, w3, [x0]
	cbnz	w4, 1b
	
2:
// 0 "" 2
#NO_APP
	cbnz	w1, .L139
.L79:
	ldr	x1, [x19, 248]
	mov	w2, 0
	ldr	x0, [x20, 24]
	ldrb	w3, [sp, 144]
	lsr	x1, x1, x3
	subs	x0, x0, x1
	csel	x0, x0, xzr, cs
	str	x0, [x20, 24]
	add	x0, x19, 272
#APP
// 99 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/include/asm-generic/qspinlock.h" 1
	stlrb w2, [x0]
// 0 "" 2
#NO_APP
	ldr	x0, [sp, 96]
	udiv	x21, x0, x23
	str	x21, [x20, 32]
	ldr	x11, [x19, 1632]
	ldr	x0, [x11, 64]
	mov	w28, w0
	cbnz	w0, .L81
#APP
// 2138 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/fs/btrfs/super.c" 1
	dmb ish
// 0 "" 2
#NO_APP
	ldr	x0, [x19, 1632]
	ldr	x0, [x0, 64]
	mov	w28, w0
	cbz	w0, .L102
.L81:
	sxtw	x1, w28
	sbfiz	x0, x28, 5, 32
	cmp	xzr, x1, lsr 59
	cset	x21, ne
	bne	.L87
	mov	w1, 3264
	str	x11, [sp, 112]
	bl	__kmalloc
	mov	x27, x0
	cbz	x0, .L87
	mov	x1, 1
	mov	x0, x19
	bl	btrfs_get_alloc_profile
	str	x0, [sp, 96]
	bl	btrfs_bg_flags_to_raid_index
	ldr	x1, [sp, 96]
	mov	w6, w28
	ldr	x11, [sp, 112]
	tbz	x1, 3, .L140
.L88:
	ubfiz	x1, x0, 5, 32
	adrp	x10, btrfs_raid_array
	add	x10, x10, :lo12:btrfs_raid_array
	uxtw	x9, w0
	add	x0, x10, x1
	ldrb	w8, [x0, 1]
	ubfiz	x8, x8, 16, 8
	ldr	x2, [x11, 152]!
	cmp	x11, x2
	beq	.L107
	add	x13, x8, 1048576
	mov	w5, 0
	mov	x4, 0
	.p2align 3,,7
.L92:
	ldr	x0, [x2, 104]
	tbz	x0, 1, .L90
	ldr	x0, [x2, 80]
	mov	x1, x4
	cbz	x0, .L90
	ldr	x0, [x2, 104]
	lsl	x3, x4, 5
	add	x12, x27, x3
	tbnz	x0, 3, .L90
	cmp	w5, w28
	bge	.L137
	ldr	x0, [x2, 128]
	ldr	x1, [x2, 144]
	sub	x0, x0, x1
	and	x0, x0, -65536
	sub	x1, x0, #1048576
	cmp	x0, x13
	bls	.L90
	add	w5, w5, 1
	str	x2, [x27, x3]
	str	x1, [x12, 16]
	sxtw	x4, w5
.L90:
	ldr	x2, [x2]
	cmp	x2, x11
	bne	.L92
	mov	x1, x4
.L137:
	sub	w28, w5, #1
.L89:
	str	w5, [sp, 96]
	str	x1, [sp, 112]
	str	x9, [sp, 136]
	str	w6, [sp, 148]
	str	x8, [sp, 152]
	bl	rcu_read_unlock_strict
	ldr	x1, [sp, 112]
	mov	x0, x27
	mov	x4, 0
	adrp	x3, btrfs_cmp_device_free_bytes
	mov	x2, 32
	add	x3, x3, :lo12:btrfs_cmp_device_free_bytes
	bl	sort
	ldr	w5, [sp, 96]
	ldr	x9, [sp, 136]
	adrp	x0, btrfs_raid_array
	add	x10, x0, :lo12:btrfs_raid_array
	add	x9, x10, x9, lsl 5
	ldrb	w4, [x9, 3]
	cmp	w5, w4
	blt	.L93
	ldr	x8, [sp, 152]
	sxtw	x28, w28
	ldr	w6, [sp, 148]
	sub	w4, w4, #1
	add	x9, x27, 16
	add	x12, x27, 48
	mov	w11, 32
	mov	x10, 16
	b	.L97
	.p2align 2,,3
.L94:
	sub	w5, w5, #1
	sub	x28, x28, #1
	cmp	w4, w5
	beq	.L93
.L97:
	lsl	x0, x28, 5
	cmp	w6, w5
	csel	w6, w6, w5, le
	ldr	x0, [x9, x0]
	cmp	x8, x0
	bhi	.L94
	sxtw	x1, w6
	add	w3, w28, 1
	sub	w3, w3, w6
	madd	x21, x1, x0, x21
	cmp	w3, w28
	bgt	.L94
	sub	w2, w28, w3
	smaddl	x1, w3, w11, x10
	add	x3, x2, w3, sxtw
	add	x1, x27, x1
	add	x3, x12, x3, lsl 5
	.p2align 3,,7
.L96:
	ldr	x2, [x1]
	sub	x2, x2, x0
	str	x2, [x1], 32
	cmp	x1, x3
	bne	.L96
	sub	w5, w5, #1
	sub	x28, x28, #1
	cmp	w4, w5
	bne	.L97
.L93:
	mov	x0, x27
	bl	kfree
	udiv	x21, x21, x23
.L82:
	ldr	x0, [x20, 32]
	add	x21, x21, x0
	ldrb	w0, [sp, 144]
	lsr	x21, x21, x0
	str	x21, [x20, 32]
	cbz	w22, .L141
.L98:
	ldp	x3, x4, [sp, 120]
	mov	x0, 26686
	movk	x0, 0x9123, lsl 16
	str	x0, [x20]
	mov	x1, 255
	mov	w0, 0
	ldr	x2, [x4, 104]
	ldr	x2, [x2, 24]
	str	x2, [x20, 8]
	str	x1, [x20, 64]
	ldr	w1, [x3]
	ldr	w2, [x3, 8]
	eor	w2, w2, w1
	mov	x1, x3
	rev	w2, w2
	str	w2, [x20, 56]
	ldr	w3, [x3, 4]
	ldr	w1, [x1, 12]
	eor	w1, w1, w3
	rev	w1, w1
	str	w1, [x20, 60]
	ldr	x3, [x4, 48]
	sub	x3, x3, #568
	ldr	x3, [x3]
	add	x3, x3, 512
	ldr	w3, [x3, -29]
	eor	w2, w2, w3
	str	w2, [x20, 56]
	ldr	x2, [x4, 48]
	sub	x2, x2, #568
	ldr	x2, [x2]
	add	x2, x2, 512
	ldr	x2, [x2, -33]
	eor	w1, w1, w2
	str	w1, [x20, 60]
.L72:
	ldp	x19, x20, [sp, 16]
	ldp	x21, x22, [sp, 32]
	ldp	x23, x24, [sp, 48]
	ldp	x27, x28, [sp, 80]
	ldp	x29, x30, [sp], 160
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 27
	.cfi_restore 28
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L140:
	.cfi_restore_state
	mov	w6, 2
	tbnz	x1, 4, .L88
	mov	w6, 3
	tbnz	x1, 9, .L88
	mov	x2, 1088
	tst	x1, x2
	mov	w6, 4
	csinc	w6, w6, wzr, ne
	b	.L88
	.p2align 2,,3
.L141:
	ldr	x0, [x19, 264]
	ldrb	w0, [x0, 76]
	tbz	x0, 0, .L98
	ldr	x1, [sp, 104]
	ldr	x0, [x19, 248]
	sub	x27, x1, #4194304
	cmp	x27, x0
	bcs	.L98
	str	xzr, [x20, 32]
	b	.L98
	.p2align 2,,3
.L102:
	mov	x21, 0
	b	.L82
.L99:
	mov	x0, 0
	mov	x23, 1
	mov	w22, 0
	stp	xzr, xzr, [sp, 96]
	b	.L73
.L139:
	bl	queued_spin_lock_slowpath
	b	.L79
.L87:
	mov	w0, -12
	b	.L72
.L107:
	mov	x1, 0
	mov	w28, -1
	mov	w5, 0
	b	.L89
	.cfi_endproc
.LFE6383:
	.size	btrfs_statfs, .-btrfs_statfs
	.section	.exit.text,"ax",@progbits
	.align	2
	.type	exit_btrfs_fs, %function
exit_btrfs_fs:
.LFB6394:
	.cfi_startproc
	stp	x29, x30, [sp, -32]!
	.cfi_def_cfa_offset 32
	.cfi_offset 29, -32
	.cfi_offset 30, -24
	mov	x29, sp
	str	x19, [sp, 16]
	.cfi_offset 19, -16
	bl	btrfs_destroy_cachep
	adrp	x19, .LANCHOR0
	bl	btrfs_delayed_ref_exit
	add	x19, x19, :lo12:.LANCHOR0
	bl	btrfs_auto_defrag_exit
	bl	btrfs_delayed_inode_exit
	bl	btrfs_prelim_ref_exit
	bl	ordered_data_exit
	bl	extent_map_exit
	bl	extent_state_cache_exit
	bl	extent_io_exit
	add	x0, x19, 72
	bl	misc_deregister
	bl	btrfs_end_io_wq_exit
	add	x0, x19, 152
	bl	unregister_filesystem
	bl	btrfs_exit_sysfs
	bl	btrfs_cleanup_fs_uuids
	ldr	x19, [sp, 16]
	ldp	x29, x30, [sp], 32
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_def_cfa_offset 0
	b	btrfs_exit_compress
	.cfi_endproc
.LFE6394:
	.size	exit_btrfs_fs, .-exit_btrfs_fs
	.text
	.align	2
	.p2align 4,,11
	.global	btrfs_sync_fs
	.type	btrfs_sync_fs, %function
btrfs_sync_fs:
.LFB6367:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	str	x21, [sp, 32]
	.cfi_offset 19, -32
	.cfi_offset 20, -24
	.cfi_offset 21, -16
	ldr	x20, [x0, 872]
	ldr	x21, [x20, 32]
	cbz	w1, .L161
	mov	x3, -1
	mov	x1, x3
	mov	x2, 0
	mov	x19, x0
	mov	x0, x20
	bl	btrfs_wait_ordered_roots
	mov	x0, x21
	bl	btrfs_attach_transaction_barrier
	cmn	x0, #4096
	bhi	.L162
.L147:
	ldp	x19, x20, [sp, 16]
	ldr	x21, [sp, 32]
	ldp	x29, x30, [sp], 48
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	b	btrfs_commit_transaction
	.p2align 2,,3
.L161:
	.cfi_restore_state
	ldr	x0, [x20, 792]
	ldr	x0, [x0, 32]
	bl	filemap_flush
.L146:
	mov	w0, 0
.L144:
	ldp	x19, x20, [sp, 16]
	ldr	x21, [sp, 32]
	ldp	x29, x30, [sp], 48
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L162:
	.cfi_restore_state
	cmn	x0, #2
	bne	.L144
	ldr	x0, [x20, 624]
	cbz	x0, .L146
	ldr	w0, [x19, 584]
	cbnz	w0, .L151
	ldr	x0, [x19, 632]
	add	x20, x19, 584
#APP
// 39 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	.if 1 == 1
661:
	mrs x1, tpidr_el1
662:
.pushsection .altinstructions,"a"
 .word 661b - .
 .word 663f - .
 .hword 31
 .byte 662b-661b
 .byte 664f-663f
.popsection
.subsection 1
663:
	mrs x1, tpidr_el2
664:
	.org	. - (664b-663b) + (662b-661b)
	.org	. - (662b-661b) + (664b-663b)
	.previous
.endif

// 0 "" 2
#NO_APP
	mov	w2, 1
	add	x0, x0, x1
#APP
// 126 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	1:	ldxr	w4, [x0]
add	w4, w4, w2
	stxr	w3, w4, [x0]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
.L152:
	ldr	w0, [x19, 584]
	cbnz	w0, .L154
	ldr	x0, [x20, 48]
#APP
// 39 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	.if 1 == 1
661:
	mrs x1, tpidr_el1
662:
.pushsection .altinstructions,"a"
 .word 661b - .
 .word 663f - .
 .hword 31
 .byte 662b-661b
 .byte 664f-663f
.popsection
.subsection 1
663:
	mrs x1, tpidr_el2
664:
	.org	. - (664b-663b) + (662b-661b)
	.org	. - (662b-661b) + (664b-663b)
	.previous
.endif

// 0 "" 2
#NO_APP
	mov	w2, -1
	add	x0, x0, x1
#APP
// 126 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	1:	ldxr	w4, [x0]
add	w4, w4, w2
	stxr	w3, w4, [x0]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
.L155:
	mov	w1, 0
	mov	x0, x21
	bl	btrfs_start_transaction
	cmn	x0, #4096
	bls	.L147
	b	.L144
.L151:
	add	x20, x19, 584
	mov	w1, 1
	mov	x0, x20
	bl	__percpu_down_read
	and	w0, w0, 255
	tbnz	x0, 0, .L152
	mov	w0, 0
	b	.L144
.L154:
#APP
// 112 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/include/linux/percpu-rwsem.h" 1
	dmb ish
// 0 "" 2
#NO_APP
	ldr	x0, [x20, 48]
#APP
// 39 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	.if 1 == 1
661:
	mrs x1, tpidr_el1
662:
.pushsection .altinstructions,"a"
 .word 661b - .
 .word 663f - .
 .hword 31
 .byte 662b-661b
 .byte 664f-663f
.popsection
.subsection 1
663:
	mrs x1, tpidr_el2
664:
	.org	. - (664b-663b) + (662b-661b)
	.org	. - (662b-661b) + (664b-663b)
	.previous
.endif

// 0 "" 2
#NO_APP
	mov	w2, -1
	add	x0, x0, x1
#APP
// 126 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/percpu.h" 1
	1:	ldxr	w4, [x0]
add	w4, w4, w2
	stxr	w3, w4, [x0]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
	add	x0, x19, 640
	bl	rcuwait_wake_up
	b	.L155
	.cfi_endproc
.LFE6367:
	.size	btrfs_sync_fs, .-btrfs_sync_fs
	.section	.rodata.str1.8
	.align	3
.LC2:
	.string	"unknown"
	.align	3
.LC3:
	.string	"No such entry"
	.align	3
.LC4:
	.string	"IO failure"
	.align	3
.LC5:
	.string	"Out of memory"
	.align	3
.LC6:
	.string	"Object already exists"
	.align	3
.LC7:
	.string	"No space left"
	.align	3
.LC8:
	.string	"Readonly filesystem"
	.align	3
.LC9:
	.string	"Operation not supported"
	.align	3
.LC10:
	.string	"Filesystem corrupted"
	.align	3
.LC11:
	.string	"Quota exceeded"
	.text
	.align	2
	.p2align 4,,11
	.global	btrfs_decode_error
	.type	btrfs_decode_error, %function
btrfs_decode_error:
.LFB6353:
	.cfi_startproc
	cmn	w0, #28
	beq	.L168
	cmn	w0, #27
	blt	.L177
	cmn	w0, #5
	beq	.L173
	cmn	w0, #4
	bge	.L167
	cmn	w0, #17
	beq	.L174
	cmn	w0, #12
	adrp	x1, .LC5
	adrp	x0, .LC2
	add	x1, x1, :lo12:.LC5
	add	x0, x0, :lo12:.LC2
	csel	x0, x0, x1, ne
	ret
	.p2align 2,,3
.L177:
	cmn	w0, #95
	beq	.L169
	cmn	w0, #94
	bge	.L166
	cmn	w0, #122
	beq	.L170
	cmn	w0, #117
	adrp	x1, .LC10
	adrp	x0, .LC2
	add	x1, x1, :lo12:.LC10
	add	x0, x0, :lo12:.LC2
	csel	x0, x0, x1, ne
	ret
	.p2align 2,,3
.L174:
	adrp	x0, .LC6
	add	x0, x0, :lo12:.LC6
	ret
	.p2align 2,,3
.L170:
	adrp	x0, .LC11
	add	x0, x0, :lo12:.LC11
	ret
	.p2align 2,,3
.L166:
	cmn	w0, #30
	adrp	x1, .LC8
	adrp	x0, .LC2
	add	x1, x1, :lo12:.LC8
	add	x0, x0, :lo12:.LC2
	csel	x0, x0, x1, ne
	ret
	.p2align 2,,3
.L167:
	cmn	w0, #2
	adrp	x1, .LC3
	adrp	x0, .LC2
	add	x1, x1, :lo12:.LC3
	add	x0, x0, :lo12:.LC2
	csel	x0, x0, x1, ne
	ret
	.p2align 2,,3
.L173:
	adrp	x0, .LC4
	add	x0, x0, :lo12:.LC4
	ret
	.p2align 2,,3
.L168:
	adrp	x0, .LC7
	add	x0, x0, :lo12:.LC7
	ret
	.p2align 2,,3
.L169:
	adrp	x0, .LC9
	add	x0, x0, :lo12:.LC9
	ret
	.cfi_endproc
.LFE6353:
	.size	btrfs_decode_error, .-btrfs_decode_error
	.section	.rodata.str1.8
	.align	3
.LC12:
	.string	"warning"
	.align	3
.LC13:
	.string	"%sBTRFS %s (device %s): %pV\n"
	.align	3
.LC14:
	.string	"%sBTRFS %s: %pV\n"
	.section	.text.unlikely
	.align	2
	.global	btrfs_printk
	.type	btrfs_printk, %function
btrfs_printk:
.LFB6355:
	.cfi_startproc
	stp	x29, x30, [sp, -144]!
	.cfi_def_cfa_offset 144
	.cfi_offset 29, -144
	.cfi_offset 30, -136
	adrp	x9, .LANCHOR0
	add	x9, x9, :lo12:.LANCHOR0
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -128
	.cfi_offset 20, -120
	mov	x20, x0
	adrp	x19, .LC12
	add	x0, x9, 384
	add	x19, x19, :lo12:.LC12
	mov	x8, x1
	add	x10, sp, 96
	mov	w1, -48
	strh	wzr, [sp, 40]
	strb	wzr, [sp, 42]
	str	x10, [sp, 80]
	stp	w1, wzr, [sp, 88]
	stp	x2, x3, [sp, 96]
	add	x2, sp, 144
	stp	x2, x2, [sp, 64]
	stp	x4, x5, [sp, 112]
	stp	x6, x7, [sp, 128]
.L179:
	ldrb	w1, [x8]
	cmp	w1, 1
	bne	.L180
	ldrb	w3, [x8, 1]
	cbz	w3, .L180
	cmp	w3, 55
	bhi	.L181
	cmp	w3, 47
	bls	.L180
	b	.L182
.L181:
	cmp	w3, 99
	bne	.L180
.L182:
	sub	w3, w3, #48
	add	x4, x8, 2
	cmp	w3, 7
	bhi	.L184
	adrp	x1, .LANCHOR1
	add	x1, x1, :lo12:.LANCHOR1
	add	x1, x1, 24
	add	x2, x9, 224
	mov	w0, 40
	ldrh	w5, [x8]
	strh	w5, [sp, 40]
	ldr	x19, [x1, w3, sxtw 3]
	smaddl	x0, w3, w0, x2
	strb	wzr, [sp, 42]
.L184:
	mov	x8, x4
	b	.L179
.L180:
	add	x2, sp, 64
	adrp	x1, .LANCHOR1
	add	x1, x1, :lo12:.LANCHOR1
	stp	x8, x2, [sp, 48]
	add	x1, x1, 88
	bl	___ratelimit
	cbz	w0, .L178
	cbz	x20, .L186
	ldr	x3, [x20, 784]
	add	x4, sp, 48
	mov	x2, x19
	add	x1, sp, 40
	add	x3, x3, 904
	adrp	x0, .LC13
	add	x0, x0, :lo12:.LC13
	bl	printk
	b	.L178
.L186:
	adrp	x0, .LC14
	add	x3, sp, 48
	mov	x2, x19
	add	x1, sp, 40
	add	x0, x0, :lo12:.LC14
	bl	printk
.L178:
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 144
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6355:
	.size	btrfs_printk, .-btrfs_printk
	.section	.rodata.str1.8
	.align	3
.LC15:
	.string	"\0012BTRFS: error (device %s) in %s:%d: errno=%d %s (%pV)\n"
	.align	3
.LC16:
	.string	"\0012BTRFS: error (device %s) in %s:%d: errno=%d %s\n"
	.align	3
.LC17:
	.string	"\0016forced readonly"
	.section	.text.unlikely
	.align	2
	.global	__btrfs_handle_fs_error
	.type	__btrfs_handle_fs_error, %function
__btrfs_handle_fs_error:
.LFB6354:
	.cfi_startproc
	stp	x29, x30, [sp, -112]!
	.cfi_def_cfa_offset 112
	.cfi_offset 29, -112
	.cfi_offset 30, -104
	mov	w8, w3
	mov	w3, w2
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -96
	.cfi_offset 20, -88
	mov	x2, x1
	mov	x19, x0
	stp	x5, x6, [sp, 88]
	str	x7, [sp, 104]
	mov	x7, x4
	ldr	x20, [x0, 784]
	cmn	w8, #30
	bne	.L195
	ldr	x0, [x20, 80]
	tbnz	x0, 0, .L194
.L195:
	mov	w0, w8
	bl	btrfs_decode_error
	add	x1, x20, 904
	mov	x5, x0
	mov	w4, w8
	cbz	x7, .L197
	add	x9, sp, 80
	add	x10, sp, 48
	stp	x7, x10, [sp, 32]
	add	x7, sp, 112
	mov	w8, -24
	add	x6, sp, 32
	adrp	x0, .LC15
	add	x0, x0, :lo12:.LC15
	stp	x7, x7, [sp, 48]
	str	x9, [sp, 64]
	stp	w8, wzr, [sp, 72]
	bl	printk
	b	.L198
.L197:
	adrp	x0, .LC16
	add	x0, x0, :lo12:.LC16
	bl	printk
.L198:
	add	x2, x19, 2584
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x2]
1:	ldxr	x0, [x2]
	orr	x0, x0, 1
	stxr	w1, x0, [x2]
	cbnz	w1, 1b
// 0 "" 2
#NO_APP
	ldr	x0, [x20, 80]
	tbz	x0, 29, .L194
	tbnz	x0, 0, .L194
	mov	x0, x19
	bl	btrfs_discard_stop
	ldr	x1, [x20, 80]
	ldr	x0, [x20, 872]
	orr	x1, x1, 1
	str	x1, [x20, 80]
	add	x0, x0, 2584
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x0]
1:	ldxr	x1, [x0]
	orr	x1, x1, 4
	stxr	w2, x1, [x0]
	cbnz	w2, 1b
// 0 "" 2
#NO_APP
	adrp	x1, .LC17
	mov	x0, x19
	add	x1, x1, :lo12:.LC17
	bl	btrfs_printk
.L194:
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 112
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6354:
	.size	__btrfs_handle_fs_error, .-__btrfs_handle_fs_error
	.section	.rodata.str1.8
	.align	3
.LC18:
	.string	","
	.align	3
.LC19:
	.string	"%pg"
	.align	3
.LC20:
	.string	"generic"
	.align	3
.LC21:
	.string	"\0013super_setup_bdi failed"
	.align	3
.LC22:
	.string	"\0013open_ctree failed"
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_mount_root, %function
btrfs_mount_root:
.LFB6374:
	.cfi_startproc
.L209:
	stp	x29, x30, [sp, -192]!
	.cfi_def_cfa_offset 192
	.cfi_offset 29, -192
	.cfi_offset 30, -184
	mov	x29, sp
	stp	x27, x28, [sp, 80]
	.cfi_offset 27, -112
	.cfi_offset 28, -104
	ands	w28, w1, 1
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -176
	.cfi_offset 20, -168
	mov	x20, -12
	stp	x21, x22, [sp, 32]
	.cfi_offset 21, -160
	.cfi_offset 22, -152
	mov	w22, w1
	mov	w1, 3520
	stp	x23, x24, [sp, 48]
	.cfi_offset 23, -144
	.cfi_offset 24, -136
	mov	x23, x0
	mov	w24, 3
	mov	x0, 3376
	csinc	w24, w24, wzr, eq
	stp	x25, x26, [sp, 64]
	.cfi_offset 25, -128
	.cfi_offset 26, -120
	mov	x26, x2
	mov	x25, x3
	mov	w2, -1
	bl	kvmalloc_node
	cbz	x0, .L207
	adrp	x20, kmalloc_caches
	add	x20, x20, :lo12:kmalloc_caches
	mov	x19, x0
	bl	btrfs_init_fs_info
	mov	w1, 3520
	ldr	x0, [x20, 96]
	bl	kmem_cache_alloc
	mov	x1, x0
	ldr	x0, [x20, 96]
	str	x1, [x19, 768]
	mov	w1, 3520
	bl	kmem_cache_alloc
	str	x0, [x19, 776]
	ldr	x1, [x19, 768]
	cmp	x1, 0
	ccmp	x0, 0, 4, ne
	beq	.L238
	adrp	x27, uuid_mutex
	add	x0, x27, :lo12:uuid_mutex
	str	x0, [sp, 112]
	bl	mutex_lock
	cbz	x25, .L211
	mov	x0, x25
	mov	w1, 3264
	bl	kstrdup
	str	x0, [sp, 120]
	str	x0, [sp, 136]
	cbz	x0, .L212
	adrp	x20, .LANCHOR1
	add	x20, x20, :lo12:.LANCHOR1
	adrp	x21, .LC18
	add	x20, x20, 104
	add	x21, x21, :lo12:.LC18
	.p2align 3,,7
.L214:
	mov	x1, x21
	add	x0, sp, 136
	bl	strsep
	add	x2, sp, 144
	mov	x1, x20
	mov	x3, x0
	cbz	x0, .L257
	ldrb	w3, [x3]
	cbz	w3, .L214
	bl	match_token
	cmp	w0, 9
	bne	.L214
	add	x0, sp, 144
	bl	match_strdup
	str	x0, [sp, 104]
	mov	x2, x23
	mov	w1, w24
	cbz	x0, .L216
	bl	btrfs_scan_one_device
	mov	x27, x0
	ldr	x3, [sp, 104]
	mov	x0, x3
	bl	kfree
	cmn	x27, #4096
	bls	.L214
	ldr	x0, [sp, 120]
	sxtw	x20, w27
	bl	kfree
.L256:
	ldr	x0, [sp, 112]
	bl	mutex_unlock
	mov	x0, x19
	bl	btrfs_free_fs_info
.L207:
	ldp	x21, x22, [sp, 32]
	mov	x0, x20
	ldp	x19, x20, [sp, 16]
	ldp	x23, x24, [sp, 48]
	ldp	x25, x26, [sp, 64]
	ldp	x27, x28, [sp, 80]
	ldp	x29, x30, [sp], 192
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 27
	.cfi_restore 28
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L238:
	.cfi_restore_state
	mov	x20, -12
.L210:
	mov	x0, x19
	bl	btrfs_free_fs_info
	ldp	x21, x22, [sp, 32]
	mov	x0, x20
	ldp	x19, x20, [sp, 16]
	ldp	x23, x24, [sp, 48]
	ldp	x25, x26, [sp, 64]
	ldp	x27, x28, [sp, 80]
	ldp	x29, x30, [sp], 192
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 27
	.cfi_restore 28
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L257:
	.cfi_restore_state
	ldr	x0, [sp, 120]
	bl	kfree
.L211:
	mov	x0, x26
	mov	x2, x23
	mov	w1, w24
	bl	btrfs_scan_one_device
	mov	x20, x0
	cmn	x0, #4096
	bhi	.L256
	ldr	x26, [x0, 48]
	str	x26, [x19, 1632]
	mov	w1, w24
	mov	x2, x23
	mov	x0, x26
	bl	btrfs_open_devices
	sxtw	x20, w0
	ldr	x0, [sp, 112]
	bl	mutex_unlock
	cbnz	w20, .L210
	cbnz	w28, .L222
	ldr	x0, [x26, 72]
	cbz	x0, .L239
.L222:
	ldr	x20, [x26, 112]
	mov	x4, x19
	orr	w3, w22, 268435456
	mov	x0, x23
	adrp	x2, btrfs_set_super
	adrp	x1, btrfs_test_super
	add	x2, x2, :lo12:btrfs_set_super
	add	x1, x1, :lo12:btrfs_test_super
	bl	sget
	mov	x21, x0
	cmn	x0, #4096
	bhi	.L240
	ldr	x0, [x0, 104]
	cbz	x0, .L224
	mov	x0, x26
	bl	btrfs_close_devices
	mov	x0, x19
	bl	btrfs_free_fs_info
	ldr	x0, [x21, 80]
	eor	x0, x0, x22
	tbnz	x0, 0, .L258
	ldr	x20, [x21, 104]
	cbz	x20, .L207
.L233:
	add	x0, x20, 88
	bl	lockref_get
	b	.L207
.L258:
	mov	x20, -16
.L225:
	mov	x0, x21
	bl	deactivate_locked_super
	b	.L207
.L239:
	mov	x20, -13
.L223:
	mov	x0, x26
	bl	btrfs_close_devices
	b	.L210
.L224:
	mov	x1, 32
	mov	x3, x20
	add	x0, x21, 904
	adrp	x2, .LC19
	add	x2, x2, :lo12:.LC19
	bl	snprintf
	ldr	x0, [x21, 872]
	str	x23, [x0, 1952]
	bl	crc32c_impl
	adrp	x1, .LC20
	add	x1, x1, :lo12:.LC20
	bl	strstr
	cbz	x0, .L259
.L227:
	ldp	x5, x4, [x21, 80]
	adrp	x1, .LANCHOR1
	add	x1, x1, :lo12:.LANCHOR1
	adrp	x2, btrfs_dentry_operations
	add	x1, x1, 984
	add	x2, x2, :lo12:btrfs_dentry_operations
	adrp	x6, btrfs_export_ops
	adrp	x3, btrfs_xattr_handlers
	add	x6, x6, :lo12:btrfs_export_ops
	add	x3, x3, :lo12:btrfs_xattr_handlers
	orr	x5, x5, 8388608
	orr	x4, x4, 1
	mov	x8, 26686
	mov	x0, 9223372036854775807
	movk	x8, 0x9123, lsl 16
	mov	w7, 1
	str	x0, [x21, 32]
	mov	x0, x21
	str	x1, [x21, 48]
	stp	x6, x5, [x21, 72]
	stp	x4, x8, [x21, 88]
	str	x3, [x21, 160]
	str	w7, [x21, 880]
	str	x2, [x21, 1000]
	ldr	x19, [x21, 872]
	bl	super_setup_bdi
	mov	w20, w0
	cbz	w0, .L228
	mov	x0, x19
	adrp	x1, .LC21
	sxtw	x20, w20
	add	x1, x1, :lo12:.LC21
	bl	btrfs_printk
	b	.L225
	.p2align 2,,3
.L216:
	ldr	x0, [sp, 120]
	bl	kfree
.L212:
	mov	x20, -12
	b	.L256
.L240:
	mov	x20, x0
	b	.L223
.L259:
	add	x2, x19, 16
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x2]
1:	ldxr	x0, [x2]
	orr	x0, x0, 65536
	stxr	w1, x0, [x2]
	cbnz	w1, 1b
// 0 "" 2
#NO_APP
	b	.L227
.L228:
	mov	x2, x25
	mov	x1, x26
	mov	x0, x21
	bl	open_ctree
	mov	w20, w0
	cbz	w0, .L230
	mov	x0, x19
	adrp	x1, .LC22
	sxtw	x20, w20
	add	x1, x1, :lo12:.LC22
	bl	btrfs_printk
	b	.L225
.L230:
	ldr	x2, [x19, 56]
	mov	x0, x21
	mov	x1, 256
	bl	btrfs_iget
	mov	x20, x0
	cmn	x0, #4096
	bls	.L260
.L232:
	mov	x0, x19
	sxtw	x20, w20
	bl	close_ctree
	b	.L225
.L260:
	bl	d_make_root
	str	x0, [x21, 104]
	mov	x20, x0
	cbnz	x0, .L261
	mov	w20, -12
	b	.L232
.L261:
	ldr	x0, [x21, 80]
	orr	x0, x0, 1073741824
	str	x0, [x21, 80]
	b	.L233
	.cfi_endproc
.LFE6374:
	.size	btrfs_mount_root, .-btrfs_mount_root
	.section	.rodata.str1.8
	.align	3
.LC23:
	.string	"\0016resize thread pool %d -> %d"
	.section	.text.unlikely
	.align	2
	.type	btrfs_resize_thread_pool.part.0, %function
btrfs_resize_thread_pool.part.0:
.LFB6396:
	.cfi_startproc
	stp	x29, x30, [sp, -32]!
	.cfi_def_cfa_offset 32
	.cfi_offset 29, -32
	.cfi_offset 30, -24
	mov	w3, w1
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -16
	.cfi_offset 20, -8
	mov	w19, w1
	mov	x20, x0
	str	w19, [x0, 1512]
	adrp	x1, .LC23
	add	x1, x1, :lo12:.LC23
	bl	btrfs_printk
	ldr	x0, [x20, 1384]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1392]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1464]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1408]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1416]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1440]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1448]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1456]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1488]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 1472]
	mov	w1, w19
	bl	btrfs_workqueue_set_max
	ldr	x0, [x20, 2048]
	mov	w1, w19
	ldp	x19, x20, [sp, 16]
	ldp	x29, x30, [sp], 32
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	b	btrfs_workqueue_set_max
	.cfi_endproc
.LFE6396:
	.size	btrfs_resize_thread_pool.part.0, .-btrfs_resize_thread_pool.part.0
	.align	2
	.global	__btrfs_abort_transaction
	.type	__btrfs_abort_transaction, %function
__btrfs_abort_transaction:
.LFB6356:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -32
	.cfi_offset 20, -24
	mov	w19, w3
	sxth	w3, w3
	stp	x21, x22, [sp, 32]
	.cfi_offset 21, -16
	.cfi_offset 22, -8
	mov	x21, x1
	mov	w22, w2
	ldr	x1, [x0, 32]
	strh	w3, [x0, 64]
	ldr	x20, [x0, 80]
	mov	x3, 0
	str	w19, [x1, 36]
	mov	w2, 1
	add	x0, x20, 688
	mov	w1, 3
	bl	__wake_up
	add	x0, x20, 712
	mov	x3, 0
	mov	w2, 1
	mov	w1, 3
	bl	__wake_up
	mov	w3, w19
	mov	w2, w22
	mov	x1, x21
	mov	x0, x20
	ldp	x19, x20, [sp, 16]
	mov	x4, 0
	ldp	x21, x22, [sp, 32]
	ldp	x29, x30, [sp], 48
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	b	__btrfs_handle_fs_error
	.cfi_endproc
.LFE6356:
	.size	__btrfs_abort_transaction, .-__btrfs_abort_transaction
	.section	.rodata.str1.8
	.align	3
.LC24:
	.string	"<unknown>"
	.align	3
.LC25:
	.string	"\0012BTRFS panic (device %s) in %s:%d: %pV (errno=%d %s)\n"
	.align	3
.LC26:
	.string	"\0012panic in %s:%d: %pV (errno=%d %s)"
	.section	.text.unlikely
	.align	2
	.global	__btrfs_panic
	.type	__btrfs_panic, %function
__btrfs_panic:
.LFB6357:
	.cfi_startproc
	stp	x29, x30, [sp, -96]!
	.cfi_def_cfa_offset 96
	.cfi_offset 29, -96
	.cfi_offset 30, -88
	mov	x29, sp
	str	x4, [sp, 16]
	mov	w4, w2
	stp	x5, x6, [sp, 72]
	mov	x2, x1
	mov	w5, w3
	str	x7, [sp, 88]
	mov	w3, w4
	mov	x7, x0
	cbz	x0, .L269
	ldr	x8, [x0, 784]
	add	x8, x8, 904
	b	.L267
.L269:
	adrp	x8, .LC24
	add	x8, x8, :lo12:.LC24
.L267:
	add	x6, sp, 32
	mov	w1, -24
	add	x4, sp, 64
	str	x6, [sp, 24]
	add	x6, sp, 96
	mov	w0, w5
	stp	x6, x6, [sp, 32]
	str	x4, [sp, 48]
	stp	w1, wzr, [sp, 56]
	bl	btrfs_decode_error
	mov	x6, x0
	add	x4, sp, 16
	cbz	x7, .L268
	ldr	x0, [x7, 616]
	tbz	x0, 21, .L268
	adrp	x0, .LC25
	mov	x1, x8
	add	x0, x0, :lo12:.LC25
	bl	panic
.L268:
	mov	x0, x7
	adrp	x1, .LC26
	add	x1, x1, :lo12:.LC26
	bl	btrfs_printk
	ldp	x29, x30, [sp], 96
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE6357:
	.size	__btrfs_panic, .-__btrfs_panic
	.section	.rodata.str1.8
	.align	3
.LC27:
	.string	"force"
	.align	3
.LC28:
	.string	"use"
	.align	3
.LC29:
	.string	"recovery"
	.align	3
.LC30:
	.string	"usebackuproot"
	.align	3
.LC31:
	.string	"zlib"
	.align	3
.LC32:
	.string	"lzo"
	.align	3
.LC33:
	.string	"zstd"
	.align	3
.LC34:
	.string	"no"
	.align	3
.LC35:
	.string	"\0016zoned: clearing existing space cache"
	.align	3
.LC36:
	.string	"\0016allowing degraded mounts"
	.align	3
.LC37:
	.string	"\0016setting nodatasum"
	.align	3
.LC38:
	.string	"\0016setting datasum, datacow enabled"
	.align	3
.LC39:
	.string	"\0016setting datasum"
	.align	3
.LC40:
	.string	"\0016setting nodatacow, compression disabled"
	.align	3
.LC41:
	.string	"\0016setting nodatacow"
	.align	3
.LC42:
	.string	"\0016setting datacow"
	.align	3
.LC43:
	.string	"COMPRESS_LZO"
	.align	3
.LC44:
	.string	"\0016setting incompat feature flag for %s (0x%llx)"
	.align	3
.LC45:
	.string	"COMPRESS_ZSTD"
	.align	3
.LC46:
	.string	"\0016use no compression"
	.align	3
.LC47:
	.string	"\0016%s %s compression, level %d"
	.align	3
.LC48:
	.string	"\0016enabling ssd optimizations"
	.align	3
.LC49:
	.string	"\0016using spread ssd allocation scheme"
	.align	3
.LC50:
	.string	"\0016not using ssd optimizations"
	.align	3
.LC51:
	.string	"\0016not using spread ssd allocation scheme"
	.align	3
.LC52:
	.string	"\0016turning on barriers"
	.align	3
.LC53:
	.string	"\0016turning off barriers"
	.align	3
.LC54:
	.string	"\0016LBA_CLAMP info=%px super=%px fsid=%pU request=%llu cache=%u disk=%u result=%llu"
	.align	3
.LC55:
	.string	"\0016max_inline at %llu"
	.align	3
.LC56:
	.string	"\0013support for ACL not compiled in!"
	.align	3
.LC57:
	.string	"\0016disabling tree log"
	.align	3
.LC58:
	.string	"\0016enabling tree log"
	.align	3
.LC59:
	.string	"\0014'nologreplay' is deprecated, use 'rescue=nologreplay' instead"
	.align	3
.LC60:
	.string	"\0016disabling log replay at mount time"
	.align	3
.LC61:
	.string	"\0016turning on flush-on-commit"
	.align	3
.LC62:
	.string	"\0016turning off flush-on-commit"
	.align	3
.LC63:
	.string	"\0016metadata ratio %u"
	.align	3
.LC64:
	.string	"sync"
	.align	3
.LC65:
	.string	"\0016turning on sync discard"
	.align	3
.LC66:
	.string	"async"
	.align	3
.LC67:
	.string	"\0016turning on async discard"
	.align	3
.LC68:
	.string	"\0016turning off discard"
	.align	3
.LC69:
	.string	"\0016turning off async discard"
	.align	3
.LC70:
	.string	"\0016enabling disk space caching"
	.align	3
.LC71:
	.string	"\0016enabling free space tree"
	.align	3
.LC72:
	.string	"\0016disabling disk space caching"
	.align	3
.LC73:
	.string	"\0016disabling free space tree"
	.align	3
.LC74:
	.string	"\0014the 'inode_cache' option is deprecated and has no effect since 5.11"
	.align	3
.LC75:
	.string	"\0016force clearing of disk cache"
	.align	3
.LC76:
	.string	"\0016enabling auto defrag"
	.align	3
.LC77:
	.string	"\0016disabling auto defrag"
	.align	3
.LC78:
	.string	"\0014'%s' is deprecated, use 'rescue=usebackuproot' instead"
	.align	3
.LC79:
	.string	"\0016trying to use backup root at mount time"
	.align	3
.LC80:
	.string	"\0013support for check_integrity* not compiled in!"
	.align	3
.LC81:
	.string	"panic"
	.align	3
.LC82:
	.string	"bug"
	.align	3
.LC83:
	.string	"\0016using default commit interval %us"
	.align	3
.LC84:
	.string	"\0014excessive commit interval %d"
	.align	3
.LC85:
	.string	"\0016ignoring bad roots"
	.align	3
.LC86:
	.string	"\0016ignoring data csums"
	.align	3
.LC87:
	.string	"\0016enabling all of the rescue options"
	.align	3
.LC88:
	.string	"\0016unrecognized rescue option '%s'"
	.align	3
.LC89:
	.string	":"
	.align	3
.LC90:
	.string	"\0013unrecognized mount option '%s'"
	.align	3
.LC91:
	.string	"nologreplay"
	.align	3
.LC92:
	.string	"\0013%s must be used with ro mount option"
	.align	3
.LC93:
	.string	"ignorebadroots"
	.align	3
.LC94:
	.string	"ignoredatacsums"
	.align	3
.LC95:
	.string	"\0013cannot disable free space tree"
	.align	3
.LC96:
	.string	"\0016disk space caching is enabled"
	.align	3
.LC97:
	.string	"\0016using free space tree"
	.text
	.align	2
	.p2align 4,,11
	.global	btrfs_parse_options
	.type	btrfs_parse_options, %function
btrfs_parse_options:
.LFB6361:
	.cfi_startproc
	sub	sp, sp, #272
	.cfi_def_cfa_offset 272
	stp	x29, x30, [sp, 16]
	.cfi_offset 29, -256
	.cfi_offset 30, -248
	add	x29, sp, 16
	stp	x19, x20, [sp, 32]
	.cfi_offset 19, -240
	.cfi_offset 20, -232
	mov	x19, x0
	stp	x23, x24, [sp, 64]
	.cfi_offset 23, -208
	.cfi_offset 24, -200
	mov	x23, x2
	str	x1, [sp, 152]
	ldr	x1, [x0, 768]
	ldr	x1, [x1, 180]
	tbz	x1, 0, .L278
	ldr	x0, [x0, 616]
	orr	x0, x0, 33554432
	str	x0, [x19, 616]
.L279:
	ldr	x0, [sp, 152]
	cbz	x0, .L418
	adrp	x24, .LANCHOR1
	add	x24, x24, :lo12:.LANCHOR1
	adrp	x20, .LC18
	add	x20, x20, :lo12:.LC18
	stp	x21, x22, [sp, 48]
	.cfi_offset 22, -216
	.cfi_offset 21, -224
	adrp	x22, .L287
	add	x21, x24, 104
	add	x22, x22, :lo12:.L287
	stp	x25, x26, [sp, 80]
	.cfi_offset 26, -184
	.cfi_offset 25, -192
	stp	x27, x28, [sp, 96]
	.cfi_offset 28, -168
	.cfi_offset 27, -176
.L534:
	mov	w26, 0
	.p2align 3,,7
.L284:
	mov	x1, x20
	add	x0, sp, 152
	bl	strsep
	mov	x25, x0
	cbz	x0, .L538
	ldrb	w1, [x25]
	cbz	w1, .L284
	mov	x1, x21
	add	x2, sp, 176
	bl	match_token
	cmp	w0, 57
	bhi	.L284
	ldrh	w1, [x22,w0,uxtw #1]
	adr	x2, .Lrtx287
	add	x1, x2, w1, sxth #2
	br	x1
.Lrtx287:
	.section	.rodata
	.align	0
	.align	2
.L287:
	.2byte	(.L328 - .Lrtx287) / 4
	.2byte	(.L327 - .Lrtx287) / 4
	.2byte	(.L326 - .Lrtx287) / 4
	.2byte	(.L325 - .Lrtx287) / 4
	.2byte	(.L323 - .Lrtx287) / 4
	.2byte	(.L431 - .Lrtx287) / 4
	.2byte	(.L431 - .Lrtx287) / 4
	.2byte	(.L323 - .Lrtx287) / 4
	.2byte	(.L322 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L321 - .Lrtx287) / 4
	.2byte	(.L320 - .Lrtx287) / 4
	.2byte	(.L319 - .Lrtx287) / 4
	.2byte	(.L318 - .Lrtx287) / 4
	.2byte	(.L317 - .Lrtx287) / 4
	.2byte	(.L316 - .Lrtx287) / 4
	.2byte	(.L315 - .Lrtx287) / 4
	.2byte	(.L314 - .Lrtx287) / 4
	.2byte	(.L313 - .Lrtx287) / 4
	.2byte	(.L312 - .Lrtx287) / 4
	.2byte	(.L311 - .Lrtx287) / 4
	.2byte	(.L310 - .Lrtx287) / 4
	.2byte	(.L308 - .Lrtx287) / 4
	.2byte	(.L309 - .Lrtx287) / 4
	.2byte	(.L308 - .Lrtx287) / 4
	.2byte	(.L293 - .Lrtx287) / 4
	.2byte	(.L307 - .Lrtx287) / 4
	.2byte	(.L306 - .Lrtx287) / 4
	.2byte	(.L305 - .Lrtx287) / 4
	.2byte	(.L303 - .Lrtx287) / 4
	.2byte	(.L304 - .Lrtx287) / 4
	.2byte	(.L303 - .Lrtx287) / 4
	.2byte	(.L302 - .Lrtx287) / 4
	.2byte	(.L301 - .Lrtx287) / 4
	.2byte	(.L300 - .Lrtx287) / 4
	.2byte	(.L299 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L298 - .Lrtx287) / 4
	.2byte	(.L297 - .Lrtx287) / 4
	.2byte	(.L296 - .Lrtx287) / 4
	.2byte	(.L295 - .Lrtx287) / 4
	.2byte	(.L294 - .Lrtx287) / 4
	.2byte	(.L292 - .Lrtx287) / 4
	.2byte	(.L293 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L284 - .Lrtx287) / 4
	.2byte	(.L292 - .Lrtx287) / 4
	.2byte	(.L291 - .Lrtx287) / 4
	.2byte	(.L291 - .Lrtx287) / 4
	.2byte	(.L290 - .Lrtx287) / 4
	.2byte	(.L290 - .Lrtx287) / 4
	.2byte	(.L290 - .Lrtx287) / 4
	.2byte	(.L289 - .Lrtx287) / 4
	.2byte	(.L288 - .Lrtx287) / 4
	.2byte	(.L286 - .Lrtx287) / 4
	.text
	.p2align 2,,3
.L538:
	ldp	x21, x22, [sp, 48]
	.cfi_restore 22
	.cfi_restore 21
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
.L418:
	ldr	x0, [x19, 616]
	tbnz	x23, 0, .L536
	tbnz	x0, 26, .L421
	tbnz	x0, 29, .L539
	tbnz	x0, 30, .L424
.L536:
	ldr	x1, [x19, 768]
	ldr	x1, [x1, 180]
	tbz	x1, 0, .L420
	and	x1, x0, 67100672
	and	x1, x1, -33538049
	cbz	x1, .L427
.L420:
	tbnz	x0, 12, .L540
	tbnz	x0, 25, .L541
.L426:
	mov	w0, 0
	b	.L277
	.p2align 2,,3
.L431:
	.cfi_offset 21, -224
	.cfi_offset 22, -216
	.cfi_offset 25, -192
	.cfi_offset 26, -184
	.cfi_offset 27, -176
	.cfi_offset 28, -168
	mov	w27, 1
.L324:
	ldr	x3, [x19, 616]
	mov	w25, 0
	tbz	x3, 5, .L337
	ldr	x25, [x19, 632]
	and	w25, w25, 15
.L337:
	ldr	w1, [x19, 636]
	sub	w0, w0, #4
	str	w1, [sp, 120]
	and	x28, x3, 2048
	cmp	w0, 1
	bls	.L542
	ldr	x4, [sp, 176]
	adrp	x5, .LC31
	add	x5, x5, :lo12:.LC31
	mov	x2, 4
	mov	x0, x4
	mov	x1, x5
	stp	x4, x3, [sp, 128]
	str	x5, [sp, 144]
	bl	strncmp
	ldp	x4, x3, [sp, 128]
	cbnz	w0, .L340
	ldrb	w2, [x19, 632]
	mov	w0, 1
	mov	w1, 3
	str	w1, [x19, 636]
	add	x1, x4, 4
	bfi	w2, w0, 0, 4
	strb	w2, [x19, 632]
	bl	btrfs_compress_str2level
	str	w0, [x19, 636]
	ldr	x5, [sp, 144]
	ldr	x3, [x19, 616]
	ldr	x0, [x19, 632]
	cbz	w27, .L341
.L581:
	ldr	w2, [x19, 636]
	and	x1, x3, -4
	and	w0, w0, 15
	mov	x4, 2080
	orr	x1, x1, x4
	str	x1, [x19, 616]
.L342:
	cmp	x28, 0
	ccmp	w25, w0, 0, ne
	bne	.L543
	ldr	w0, [sp, 120]
	cmp	w0, w2
	beq	.L534
	adrp	x2, .LC27
	add	x2, x2, :lo12:.LC27
	mov	w26, 0
.L428:
	ldr	w4, [x19, 636]
	mov	x3, x5
	mov	x0, x19
	adrp	x1, .LC47
	add	x1, x1, :lo12:.LC47
	bl	btrfs_printk
	b	.L284
	.p2align 2,,3
.L323:
	mov	w27, 0
	b	.L324
.L303:
	cmp	w0, 29
	beq	.L382
	ldr	x0, [sp, 176]
	ldrb	w1, [x0]
	cmp	w1, 118
	bne	.L532
	ldrb	w2, [x0, 1]
	cmp	w2, 49
	bne	.L384
	ldrb	w2, [x0, 2]
	cbz	w2, .L382
.L384:
	cmp	w1, 118
	bne	.L532
	ldrb	w1, [x0, 1]
	cmp	w1, 50
	bne	.L532
	ldrb	w0, [x0, 2]
	cbnz	w0, .L532
	ldr	x1, [x19, 616]
	and	x0, x1, -4097
	str	x0, [x19, 616]
	tbz	x1, 25, .L544
.L387:
	orr	x0, x0, 33554432
	str	x0, [x19, 616]
	b	.L284
.L308:
	cmp	w0, 22
	beq	.L376
	ldr	x25, [sp, 176]
	adrp	x1, .LC64
	add	x1, x1, :lo12:.LC64
	mov	x0, x25
	bl	strcmp
	cbz	w0, .L376
	adrp	x1, .LC66
	mov	x0, x25
	add	x1, x1, :lo12:.LC66
	bl	strcmp
	cbnz	w0, .L532
	ldr	x1, [x19, 616]
	and	x0, x1, -1025
	str	x0, [x19, 616]
	tbz	x1, 28, .L545
.L379:
	orr	x0, x0, 268435456
	str	x0, [x19, 616]
	b	.L284
.L310:
	ldr	x0, [x19, 616]
	tbnz	x0, 16, .L546
.L391:
	and	x0, x0, -65537
	str	x0, [x19, 616]
	b	.L284
.L294:
	ldr	x0, [sp, 176]
	mov	w1, 3264
	bl	kstrdup
	str	x0, [sp, 120]
	str	x0, [sp, 168]
	cbz	x0, .L517
	adrp	x25, .LC89
	add	x28, x24, 1160
	add	x25, x25, :lo12:.LC89
	.p2align 3,,7
.L399:
	mov	x1, x25
	add	x0, sp, 168
	bl	strsep
	mov	x27, x0
	cbz	x0, .L547
.L415:
	ldrb	w1, [x27]
	cbz	w1, .L399
	add	x2, sp, 224
	mov	x1, x28
	bl	match_token
	cmp	w0, 46
	beq	.L400
	bgt	.L401
	cmp	w0, 44
	beq	.L402
	cmp	w0, 45
	bne	.L399
	ldr	x0, [x19, 616]
	tbz	x0, 26, .L537
.L414:
	orr	x0, x0, 67108864
.L408:
	str	x0, [x19, 616]
.L575:
	mov	x1, x25
	add	x0, sp, 168
	bl	strsep
	mov	x27, x0
	cbnz	x0, .L415
.L547:
.L416:
	ldr	x0, [sp, 120]
	bl	kfree
	b	.L284
.L295:
	ldr	x0, [x19, 616]
	orr	x0, x0, 16384
	str	x0, [x19, 616]
	b	.L284
.L296:
	ldr	x0, [x19, 616]
	tbz	x0, 6, .L548
.L371:
	orr	x0, x0, 64
	str	x0, [x19, 616]
	b	.L284
.L297:
	ldr	x0, [x19, 616]
	tbnz	x0, 6, .L549
.L372:
	and	x0, x0, -65
	str	x0, [x19, 616]
	b	.L284
.L298:
	add	x0, sp, 176
	add	x1, sp, 164
	bl	match_int
	cbnz	w0, .L533
	ldr	w0, [sp, 164]
	cbz	w0, .L532
	str	w0, [x19, 1512]
	b	.L284
.L299:
	ldr	x0, [x19, 616]
.L329:
	tbnz	x0, 8, .L550
.L365:
	and	x0, x0, -257
	str	x0, [x19, 616]
	b	.L284
.L300:
	ldr	x1, [x19, 616]
	tbz	x1, 3, .L551
.L362:
	orr	x0, x1, 8
	str	x0, [x19, 616]
	tbz	x1, 8, .L552
.L363:
	and	x0, x0, -513
	orr	x0, x0, 256
	str	x0, [x19, 616]
	b	.L284
.L301:
	ldr	x1, [x19, 616]
	orr	x0, x1, 512
	str	x0, [x19, 616]
	tbnz	x1, 3, .L553
.L364:
	and	x0, x0, -9
	str	x0, [x19, 616]
	b	.L329
.L321:
	ldr	x25, [sp, 176]
	adrp	x1, .LC81
	add	x1, x1, :lo12:.LC81
	mov	x0, x25
	bl	strcmp
	cbz	w0, .L554
	adrp	x1, .LC82
	mov	x0, x25
	add	x1, x1, :lo12:.LC82
	bl	strcmp
	cbnz	w0, .L532
	ldr	x0, [x19, 616]
	and	x0, x0, -2097153
	str	x0, [x19, 616]
	b	.L284
.L311:
	ldr	x0, [x19, 616]
	tbz	x0, 16, .L555
.L390:
	orr	x0, x0, 65536
	str	x0, [x19, 616]
	b	.L284
.L312:
	ldr	x0, [x19, 616]
	tbz	x0, 0, .L556
.L331:
	orr	x0, x0, 1
	str	x0, [x19, 616]
	b	.L284
.L313:
	ldr	x0, [x19, 616]
	tbnz	x0, 0, .L557
.L332:
	and	x0, x0, -4
	str	x0, [x19, 616]
	b	.L284
.L314:
	ldr	x0, [x19, 616]
	tbz	x0, 1, .L558
.L334:
	mov	x1, -2081
	and	x0, x0, x1
	orr	x0, x0, 3
	str	x0, [x19, 616]
	b	.L284
.L315:
	ldr	x0, [x19, 616]
	tbnz	x0, 1, .L559
.L336:
	and	x0, x0, -3
	str	x0, [x19, 616]
	b	.L284
.L316:
	ldr	x0, [x19, 616]
	tbz	x0, 2, .L560
.L367:
	orr	x0, x0, 4
	str	x0, [x19, 616]
	b	.L284
.L305:
	ldr	x0, [x19, 616]
	orr	x0, x0, 262144
	str	x0, [x19, 616]
	b	.L284
.L302:
	ldr	x0, [x19, 616]
	tbz	x0, 3, .L561
.L361:
	and	x0, x0, -513
	orr	x0, x0, 8
	str	x0, [x19, 616]
	b	.L284
.L304:
	ldr	x0, [x19, 616]
	tbnz	x0, 12, .L562
	tbz	x0, 25, .L284
.L590:
	mov	x0, x19
	adrp	x1, .LC73
	add	x1, x1, :lo12:.LC73
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	and	x0, x0, -33554433
	str	x0, [x19, 616]
	b	.L284
	.p2align 2,,3
.L306:
	ldr	x0, [x19, 616]
	orr	x0, x0, 4194304
	str	x0, [x19, 616]
	b	.L284
.L307:
	add	x0, sp, 176
	add	x1, sp, 164
	bl	match_int
	cbz	w0, .L563
.L533:
	ldp	x21, x22, [sp, 48]
	.cfi_restore 22
	.cfi_restore 21
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
.L368:
	ldr	x1, [x19, 768]
	ldr	x1, [x1, 180]
	tbz	x1, 0, .L277
.L397:
	ldr	x1, [x19, 616]
	and	x1, x1, 67100672
	and	x1, x1, -33538049
	cbz	x1, .L427
.L277:
	ldp	x29, x30, [sp, 16]
	ldp	x19, x20, [sp, 32]
	ldp	x23, x24, [sp, 64]
	add	sp, sp, 272
	.cfi_restore 29
	.cfi_restore 30
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
.L309:
	.cfi_def_cfa_offset 272
	.cfi_offset 19, -240
	.cfi_offset 20, -232
	.cfi_offset 21, -224
	.cfi_offset 22, -216
	.cfi_offset 23, -208
	.cfi_offset 24, -200
	.cfi_offset 25, -192
	.cfi_offset 26, -184
	.cfi_offset 27, -176
	.cfi_offset 28, -168
	.cfi_offset 29, -256
	.cfi_offset 30, -248
	ldr	x1, [x19, 616]
	tbnz	x1, 10, .L564
.L380:
	and	x0, x1, -1025
	str	x0, [x19, 616]
	tbnz	x1, 28, .L565
.L381:
	and	x0, x0, -268435457
	str	x0, [x19, 616]
	b	.L284
.L289:
	ldr	x0, [x19, 616]
	orr	x0, x0, 32768
	str	x0, [x19, 616]
	b	.L284
.L317:
	ldr	x0, [x19, 616]
	tbnz	x0, 2, .L566
.L366:
	and	x0, x0, -5
	str	x0, [x19, 616]
	b	.L284
.L318:
	add	x0, sp, 176
	bl	match_strdup
	mov	x25, x0
	cbnz	x0, .L567
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -12
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
.L319:
	.cfi_restore_state
	ldr	x0, [x19, 616]
	tbnz	x0, 7, .L568
.L375:
	and	x0, x0, -129
	str	x0, [x19, 616]
	b	.L284
.L320:
	ldr	x0, [x19, 616]
	tbz	x0, 7, .L569
.L374:
	orr	x0, x0, 128
	str	x0, [x19, 616]
	b	.L284
.L288:
	ldr	x0, [x19, 616]
	and	x0, x0, -32769
	str	x0, [x19, 616]
	b	.L284
.L325:
	add	x0, sp, 176
	add	x1, sp, 164
	str	wzr, [sp, 164]
	bl	match_int
	cbnz	w0, .L533
	ldr	w2, [sp, 164]
	cbz	w2, .L570
	cmp	w2, 300
	bgt	.L571
	str	w2, [x19, 640]
	b	.L284
.L326:
	ldr	x0, [x19, 616]
	tbz	x0, 13, .L572
.L389:
	orr	x0, x0, 8192
	str	x0, [x19, 616]
	b	.L284
.L327:
	ldr	x1, [x19, 784]
	ldr	x0, [x1, 80]
	and	x0, x0, -65537
	str	x0, [x1, 80]
	b	.L284
	.p2align 2,,3
.L401:
	cmp	w0, 47
	bne	.L573
	ldr	x0, [x19, 616]
	tbz	x0, 30, .L574
	orr	x0, x0, 1073741824
.L589:
	str	x0, [x19, 616]
	b	.L575
	.p2align 2,,3
.L278:
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 27
	.cfi_restore 28
	bl	btrfs_free_space_cache_v1_active
	tbz	x0, 0, .L279
	ldr	x0, [x19, 3320]
	cbnz	x0, .L576
	ldr	x0, [x19, 616]
	orr	x0, x0, 4096
	str	x0, [x19, 616]
	b	.L279
	.p2align 2,,3
.L400:
	.cfi_offset 21, -224
	.cfi_offset 22, -216
	.cfi_offset 25, -192
	.cfi_offset 26, -184
	.cfi_offset 27, -176
	.cfi_offset 28, -168
	ldr	x0, [x19, 616]
	tbz	x0, 29, .L577
	orr	x0, x0, 536870912
.L586:
	str	x0, [x19, 616]
	b	.L575
.L340:
	ldrb	w0, [x4]
	cmp	w0, 108
	bne	.L345
	ldrb	w0, [x4, 1]
	cmp	w0, 122
	bne	.L345
	ldrb	w0, [x4, 2]
	cmp	w0, 111
	bne	.L345
	ldrb	w2, [x19, 632]
	and	x1, x3, -4
	ldr	x26, [x19, 768]
	mov	w0, 2
	bfi	w2, w0, 0, 4
	orr	x4, x1, 32
	str	x4, [x19, 616]
	strb	w2, [x19, 632]
	str	wzr, [x19, 636]
	ldr	x2, [x26, 188]
	and	x4, x2, 8
	tbz	x2, 3, .L346
	cbz	w27, .L347
	mov	x2, 2080
	adrp	x3, .LC32
	orr	x1, x1, x2
	add	x5, x3, :lo12:.LC32
	mov	w2, 0
	str	x1, [x19, 616]
	b	.L342
.L554:
	ldr	x0, [x19, 616]
	orr	x0, x0, 2097152
	str	x0, [x19, 616]
	b	.L284
.L376:
	ldr	x1, [x19, 616]
	and	x0, x1, -268435457
	str	x0, [x19, 616]
	tbz	x1, 10, .L578
.L378:
	orr	x0, x0, 1024
	str	x0, [x19, 616]
	b	.L284
.L382:
	ldr	x1, [x19, 616]
	and	x0, x1, -33554433
	str	x0, [x19, 616]
	tbz	x1, 12, .L579
.L385:
	orr	x0, x0, 4096
	str	x0, [x19, 616]
	b	.L284
.L345:
	adrp	x0, .LC33
	add	x0, x0, :lo12:.LC33
	mov	x1, x0
	mov	x2, 4
	stp	x4, x3, [sp, 128]
	str	x0, [sp, 144]
	mov	x0, x4
	bl	strncmp
	ldp	x4, x3, [sp, 128]
	cbz	w0, .L580
	ldrb	w0, [x4]
	cmp	w0, 110
	bne	.L532
	ldrb	w0, [x4, 1]
	cmp	w0, 111
	bne	.L532
	ldrb	w0, [x19, 632]
	mov	x1, -2081
	add	w26, w26, 1
	and	x3, x3, x1
	and	w0, w0, -16
	str	x3, [x19, 616]
	strb	w0, [x19, 632]
	str	wzr, [x19, 636]
	cmp	w26, 1
	bne	.L433
	mov	x0, x19
	adrp	x1, .LC46
	add	x1, x1, :lo12:.LC46
	bl	btrfs_printk
	b	.L284
	.p2align 2,,3
.L532:
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -22
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
	.p2align 2,,3
.L542:
	.cfi_restore_state
	ldrb	w0, [x19, 632]
	mov	w1, 1
	mov	w2, 3
	str	w2, [x19, 636]
	adrp	x5, .LC31
	add	x5, x5, :lo12:.LC31
	bfi	w0, w1, 0, 4
	strb	w0, [x19, 632]
	ldr	x0, [x19, 632]
	cbnz	w27, .L581
.L341:
	ldr	w2, [x19, 636]
	mov	x1, -2052
	and	w0, w0, 15
	and	x1, x3, x1
	orr	x1, x1, 32
	mov	w26, 0
	str	x1, [x19, 616]
.L343:
	cmp	x28, 0
	ccmp	w25, w0, 0, eq
	bne	.L439
	ldr	w0, [sp, 120]
	cmp	w0, w2
	beq	.L284
.L439:
	adrp	x2, .LC28
	add	x2, x2, :lo12:.LC28
	b	.L428
	.p2align 2,,3
.L573:
	cmp	w0, 48
	beq	.L406
	cmp	w0, 57
	bne	.L399
	mov	x0, x19
	mov	x2, x27
	adrp	x1, .LC88
	add	x1, x1, :lo12:.LC88
	bl	btrfs_printk
	ldr	x0, [sp, 120]
	bl	kfree
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -22
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
	.p2align 2,,3
.L580:
	.cfi_restore_state
	ldrb	w2, [x19, 632]
	mov	w0, 3
	add	x1, x4, 4
	bfi	w2, w0, 0, 4
	strb	w2, [x19, 632]
	bl	btrfs_compress_str2level
	mov	w2, w0
	ldr	x1, [x19, 616]
	str	w2, [x19, 636]
	ldr	x26, [x19, 768]
	and	x4, x1, -4
	orr	x0, x4, 32
	str	x0, [x19, 616]
	ldr	x0, [x26, 188]
	and	x3, x0, 16
	tbz	x0, 4, .L352
	ldr	x0, [x19, 632]
	cbz	w27, .L353
	ldr	x5, [sp, 144]
	mov	x1, 2080
	and	w0, w0, 15
	orr	x4, x4, x1
	str	x4, [x19, 616]
	b	.L342
.L347:
	mov	x1, -2052
	and	x1, x3, x1
	orr	x1, x1, 32
	adrp	x3, .LC32
	mov	w26, 0
	add	x5, x3, :lo12:.LC32
	mov	w2, 0
	str	x1, [x19, 616]
	b	.L343
.L346:
	mov	w2, 1
	add	x0, x19, 760
#APP
// 305 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
		prfm	pstl1strm, [x0]
1:	ldaxr	w1, [x0]
	eor	w3, w1, w4
	cbnz	w3, 2f
	stxr	w3, w2, [x0]
	cbnz	w3, 1b
	
2:
// 0 "" 2
#NO_APP
	cbnz	w1, .L582
.L348:
	ldr	x0, [x26, 188]
	tbz	x0, 3, .L583
.L349:
	add	x1, x19, 760
	mov	w0, 0
#APP
// 99 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/include/asm-generic/qspinlock.h" 1
	stlrb w0, [x1]
// 0 "" 2
#NO_APP
	ldr	x1, [x19, 616]
	adrp	x3, .LC32
	ldr	x0, [x19, 632]
	cbz	w27, .L350
	orr	x1, x1, 2048
	ldr	w2, [x19, 636]
	add	x5, x3, :lo12:.LC32
	and	w0, w0, 15
	str	x1, [x19, 616]
	b	.L342
.L353:
	mov	x3, -2052
	and	x1, x1, x3
	ldr	x5, [sp, 144]
	orr	x1, x1, 32
	and	w0, w0, 15
	mov	w26, 0
	str	x1, [x19, 616]
	b	.L343
.L352:
	mov	w2, 1
	add	x0, x19, 760
#APP
// 305 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
		prfm	pstl1strm, [x0]
1:	ldaxr	w1, [x0]
	eor	w4, w1, w3
	cbnz	w4, 2f
	stxr	w4, w2, [x0]
	cbnz	w4, 1b
	
2:
// 0 "" 2
#NO_APP
	cbnz	w1, .L584
.L354:
	ldr	x0, [x26, 188]
	tbz	x0, 4, .L585
.L355:
	add	x1, x19, 760
	mov	w0, 0
#APP
// 99 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/include/asm-generic/qspinlock.h" 1
	stlrb w0, [x1]
// 0 "" 2
#NO_APP
	ldr	x5, [sp, 144]
	ldr	x1, [x19, 616]
	ldr	x0, [x19, 632]
	cbz	w27, .L356
	orr	x1, x1, 2048
	ldr	w2, [x19, 636]
	and	w0, w0, 15
	str	x1, [x19, 616]
	b	.L342
.L350:
	and	x1, x1, -2049
	ldr	w2, [x19, 636]
	add	x5, x3, :lo12:.LC32
	and	w0, w0, 15
	mov	w26, 0
	str	x1, [x19, 616]
	b	.L343
.L356:
	and	x1, x1, -2049
	ldr	w2, [x19, 636]
	and	w0, w0, 15
	mov	w26, 0
	str	x1, [x19, 616]
	b	.L343
.L584:
	bl	queued_spin_lock_slowpath
	b	.L354
.L582:
	bl	queued_spin_lock_slowpath
	b	.L348
.L433:
	adrp	x3, .LC34
	mov	w2, 0
	add	x5, x3, :lo12:.LC34
	mov	w0, 0
	b	.L343
.L567:
	mov	x1, 0
	bl	memparse
	str	x0, [x19, 648]
	mov	x0, x25
	bl	kfree
	ldr	x5, [x19, 648]
	cbz	x5, .L370
	ldr	w6, [x19, 3260]
	adrp	x1, .LC54
	ldr	x3, [x19, 768]
	uxtw	x0, w6
	cmp	x5, w6, uxtw
	add	x1, x1, :lo12:.LC54
	csel	x0, x0, x5, cs
	str	x0, [sp]
	str	x0, [x19, 648]
	mov	x2, x19
	add	x4, x3, 32
	mov	x0, x19
	ldr	w7, [x3, 144]
	bl	btrfs_printk
.L370:
	ldr	x2, [x19, 648]
	mov	x0, x19
	adrp	x1, .LC55
	add	x1, x1, :lo12:.LC55
	bl	btrfs_printk
	b	.L284
.L517:
	ldr	x0, [x19, 768]
	ldr	x0, [x0, 180]
	tbnz	x0, 0, .L436
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -12
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L277
.L436:
	.cfi_restore_state
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -12
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L397
.L585:
	.cfi_restore_state
	orr	x0, x0, 16
	str	x0, [x26, 188]
	adrp	x2, .LC45
	mov	x0, x19
	add	x2, x2, :lo12:.LC45
	adrp	x1, .LC44
	mov	x3, 16
	add	x1, x1, :lo12:.LC44
	bl	btrfs_printk
	b	.L355
.L583:
	orr	x0, x0, 8
	str	x0, [x26, 188]
	adrp	x2, .LC43
	mov	x0, x19
	add	x2, x2, :lo12:.LC43
	adrp	x1, .LC44
	mov	x3, 8
	add	x1, x1, :lo12:.LC44
	bl	btrfs_printk
	b	.L349
.L427:
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 27
	.cfi_restore 28
	mov	x0, x19
	adrp	x1, .LC95
	add	x1, x1, :lo12:.LC95
	bl	btrfs_printk
	mov	w0, -22
	b	.L277
.L540:
	mov	x0, x19
	adrp	x1, .LC96
	add	x1, x1, :lo12:.LC96
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	tbz	x0, 25, .L426
.L541:
	mov	x0, x19
	adrp	x1, .LC97
	add	x1, x1, :lo12:.LC97
	bl	btrfs_printk
	mov	w0, 0
	b	.L277
.L421:
	mov	x0, x19
	adrp	x2, .LC91
	adrp	x1, .LC92
	add	x2, x2, :lo12:.LC91
	add	x1, x1, :lo12:.LC92
	bl	btrfs_printk
	mov	w0, -22
	b	.L368
.L539:
	mov	x0, x19
	adrp	x2, .LC93
	adrp	x1, .LC92
	add	x2, x2, :lo12:.LC93
	add	x1, x1, :lo12:.LC92
	bl	btrfs_printk
	mov	w0, -22
	b	.L368
.L424:
	mov	x0, x19
	adrp	x2, .LC94
	adrp	x1, .LC92
	add	x2, x2, :lo12:.LC94
	add	x1, x1, :lo12:.LC92
	bl	btrfs_printk
	mov	w0, -22
	b	.L368
.L577:
	.cfi_offset 21, -224
	.cfi_offset 22, -216
	.cfi_offset 25, -192
	.cfi_offset 26, -184
	.cfi_offset 27, -176
	.cfi_offset 28, -168
	mov	x0, x19
	adrp	x1, .LC85
	add	x1, x1, :lo12:.LC85
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 536870912
	b	.L586
.L328:
	mov	x0, x19
	adrp	x1, .LC56
	add	x1, x1, :lo12:.LC56
	bl	btrfs_printk
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -22
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
.L293:
	.cfi_restore_state
	mov	x0, x19
	adrp	x1, .LC59
	add	x1, x1, :lo12:.LC59
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	tbnz	x0, 26, .L373
	mov	x0, x19
	adrp	x1, .LC60
	add	x1, x1, :lo12:.LC60
	bl	btrfs_printk
	ldr	x0, [x19, 616]
.L373:
	orr	x0, x0, 67108864
	str	x0, [x19, 616]
	b	.L284
.L291:
	mov	x0, x19
	adrp	x1, .LC74
	add	x1, x1, :lo12:.LC74
	bl	btrfs_printk
	b	.L284
.L292:
	cmp	w0, 49
	adrp	x2, .LC30
	adrp	x0, .LC29
	add	x2, x2, :lo12:.LC30
	add	x0, x0, :lo12:.LC29
	adrp	x1, .LC78
	csel	x2, x2, x0, ne
	add	x1, x1, :lo12:.LC78
	mov	x0, x19
	bl	btrfs_printk
	mov	x0, x19
	adrp	x1, .LC79
	add	x1, x1, :lo12:.LC79
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 131072
	str	x0, [x19, 616]
	b	.L284
.L290:
	mov	x0, x19
	adrp	x1, .LC80
	add	x1, x1, :lo12:.LC80
	bl	btrfs_printk
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -22
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
.L286:
	.cfi_restore_state
	mov	x2, x25
	mov	x0, x19
	adrp	x1, .LC90
	add	x1, x1, :lo12:.LC90
	bl	btrfs_printk
	ldp	x21, x22, [sp, 48]
	.cfi_remember_state
	.cfi_restore 22
	.cfi_restore 21
	mov	w0, -22
	ldp	x25, x26, [sp, 80]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 96]
	.cfi_restore 28
	.cfi_restore 27
	b	.L368
.L322:
	.cfi_restore_state
	mov	x0, x19
	adrp	x1, .LC36
	add	x1, x1, :lo12:.LC36
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 16
	str	x0, [x19, 616]
	b	.L284
.L402:
	mov	x0, x19
	adrp	x1, .LC79
	add	x1, x1, :lo12:.LC79
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 131072
	str	x0, [x19, 616]
	b	.L575
.L406:
	mov	x0, x19
	adrp	x1, .LC87
	add	x1, x1, :lo12:.LC87
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	tbz	x0, 30, .L587
.L412:
	mov	x1, x0
	orr	x0, x0, 1073741824
	str	x0, [x19, 616]
	tbz	x1, 29, .L588
.L413:
	mov	x1, x0
	orr	x0, x0, 536870912
	str	x0, [x19, 616]
	tbnz	x1, 26, .L414
.L537:
	mov	x0, x19
	adrp	x1, .LC60
	add	x1, x1, :lo12:.LC60
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 67108864
	b	.L408
.L548:
	mov	x0, x19
	adrp	x1, .LC57
	add	x1, x1, :lo12:.LC57
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L371
.L549:
	mov	x0, x19
	adrp	x1, .LC58
	add	x1, x1, :lo12:.LC58
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L372
.L551:
	mov	x0, x19
	adrp	x1, .LC48
	add	x1, x1, :lo12:.LC48
	bl	btrfs_printk
	ldr	x1, [x19, 616]
	b	.L362
.L552:
	mov	x0, x19
	adrp	x1, .LC49
	add	x1, x1, :lo12:.LC49
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L363
.L550:
	mov	x0, x19
	adrp	x1, .LC51
	add	x1, x1, :lo12:.LC51
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L365
.L553:
	mov	x0, x19
	adrp	x1, .LC50
	add	x1, x1, :lo12:.LC50
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L364
.L571:
	mov	x0, x19
	adrp	x1, .LC84
	add	x1, x1, :lo12:.LC84
	bl	btrfs_printk
	ldr	w2, [sp, 164]
	str	w2, [x19, 640]
	b	.L284
.L572:
	mov	x0, x19
	adrp	x1, .LC75
	add	x1, x1, :lo12:.LC75
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L389
.L574:
	mov	x0, x19
	adrp	x1, .LC86
	add	x1, x1, :lo12:.LC86
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	orr	x0, x0, 1073741824
	b	.L589
.L555:
	mov	x0, x19
	adrp	x1, .LC76
	add	x1, x1, :lo12:.LC76
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L390
.L569:
	mov	x0, x19
	adrp	x1, .LC61
	add	x1, x1, :lo12:.LC61
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L374
.L570:
	mov	x0, x19
	mov	w2, 30
	adrp	x1, .LC83
	add	x1, x1, :lo12:.LC83
	bl	btrfs_printk
	mov	w0, 30
	mov	w2, w0
	str	w0, [sp, 164]
	str	w2, [x19, 640]
	b	.L284
.L568:
	mov	x0, x19
	adrp	x1, .LC62
	add	x1, x1, :lo12:.LC62
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L375
.L546:
	mov	x0, x19
	adrp	x1, .LC77
	add	x1, x1, :lo12:.LC77
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L391
.L560:
	mov	x0, x19
	adrp	x1, .LC53
	add	x1, x1, :lo12:.LC53
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L367
.L561:
	mov	x0, x19
	adrp	x1, .LC48
	add	x1, x1, :lo12:.LC48
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L361
.L562:
	mov	x0, x19
	adrp	x1, .LC72
	add	x1, x1, :lo12:.LC72
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	and	x0, x0, -4097
	str	x0, [x19, 616]
	tbz	x0, 25, .L284
	b	.L590
.L563:
	ldr	w2, [sp, 164]
	mov	x0, x19
	str	w2, [x19, 1944]
	adrp	x1, .LC63
	add	x1, x1, :lo12:.LC63
	bl	btrfs_printk
	b	.L284
.L564:
	mov	x0, x19
	adrp	x1, .LC68
	add	x1, x1, :lo12:.LC68
	bl	btrfs_printk
	ldr	x1, [x19, 616]
	b	.L380
.L565:
	mov	x0, x19
	adrp	x1, .LC69
	add	x1, x1, :lo12:.LC69
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L381
.L566:
	mov	x0, x19
	adrp	x1, .LC52
	add	x1, x1, :lo12:.LC52
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L366
.L545:
	mov	x0, x19
	adrp	x1, .LC67
	add	x1, x1, :lo12:.LC67
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L379
.L576:
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 27
	.cfi_restore 28
	mov	x0, x19
	adrp	x1, .LC35
	add	x1, x1, :lo12:.LC35
	bl	btrfs_printk
	ldr	x0, [x19, 768]
	add	x0, x0, 512
	str	xzr, [x0, 43]
	b	.L279
.L579:
	.cfi_offset 21, -224
	.cfi_offset 22, -216
	.cfi_offset 25, -192
	.cfi_offset 26, -184
	.cfi_offset 27, -176
	.cfi_offset 28, -168
	mov	x0, x19
	adrp	x1, .LC70
	add	x1, x1, :lo12:.LC70
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L385
.L578:
	mov	x0, x19
	adrp	x1, .LC65
	add	x1, x1, :lo12:.LC65
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L378
.L543:
	adrp	x2, .LC27
	mov	w26, 0
	add	x2, x2, :lo12:.LC27
	b	.L428
.L544:
	mov	x0, x19
	adrp	x1, .LC71
	add	x1, x1, :lo12:.LC71
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L387
.L556:
	mov	x0, x19
	adrp	x1, .LC37
	add	x1, x1, :lo12:.LC37
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L331
.L557:
	tbz	x0, 1, .L333
	mov	x0, x19
	adrp	x1, .LC38
	add	x1, x1, :lo12:.LC38
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L332
.L558:
	mov	x1, 2080
	and	x0, x0, x1
	cmp	x0, x1
	beq	.L335
	mov	x0, x19
	adrp	x1, .LC40
	add	x1, x1, :lo12:.LC40
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L334
.L559:
	mov	x0, x19
	adrp	x1, .LC42
	add	x1, x1, :lo12:.LC42
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L336
.L335:
	mov	x0, x19
	adrp	x1, .LC41
	add	x1, x1, :lo12:.LC41
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L334
.L333:
	mov	x0, x19
	adrp	x1, .LC39
	add	x1, x1, :lo12:.LC39
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L332
.L587:
	mov	x0, x19
	adrp	x1, .LC86
	add	x1, x1, :lo12:.LC86
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L412
.L588:
	mov	x0, x19
	adrp	x1, .LC85
	add	x1, x1, :lo12:.LC85
	bl	btrfs_printk
	ldr	x0, [x19, 616]
	b	.L413
	.cfi_endproc
.LFE6361:
	.size	btrfs_parse_options, .-btrfs_parse_options
	.section	.rodata.str1.8
	.align	3
.LC98:
	.string	"\0014remount supports changing free space tree only from ro to rw"
	.align	3
.LC99:
	.string	"\0013Remounting read-write after error is not allowed"
	.align	3
.LC100:
	.string	"\0014too many missing devices, writable remount is not allowed"
	.align	3
.LC101:
	.string	"\0014mount required to replay tree-log, cannot remount read-write"
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_remount, %function
btrfs_remount:
.LFB6379:
	.cfi_startproc
	stp	x29, x30, [sp, -176]!
	.cfi_def_cfa_offset 176
	.cfi_offset 29, -176
	.cfi_offset 30, -168
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -160
	.cfi_offset 20, -152
	mov	x20, x1
	mov	x19, x0
	stp	x21, x22, [sp, 32]
	.cfi_offset 21, -144
	.cfi_offset 22, -136
	mov	x22, x2
	stp	x23, x24, [sp, 48]
	stp	x25, x26, [sp, 64]
	stp	x27, x28, [sp, 80]
	.cfi_offset 23, -128
	.cfi_offset 24, -120
	.cfi_offset 25, -112
	.cfi_offset 26, -104
	.cfi_offset 27, -96
	.cfi_offset 28, -88
	ldr	x27, [x0, 872]
	ldr	x28, [x0, 80]
	ldr	x1, [x27, 648]
	str	x1, [sp, 104]
	ldr	x23, [x27, 632]
	ldr	x21, [x27, 616]
	and	w23, w23, 15
	ldr	w25, [x27, 1512]
	ldr	w26, [x27, 1944]
	bl	sync_filesystem
	add	x2, x27, 2584
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x2]
1:	ldxr	x0, [x2]
	orr	x0, x0, 2
	stxr	w1, x0, [x2]
	cbnz	w1, 1b
// 0 "" 2
#NO_APP
	ldrsw	x2, [x20]
	mov	x1, x22
	mov	x0, x27
	and	x24, x21, 65536
	bl	btrfs_parse_options
	mov	w22, w0
	cbz	w0, .L686
	ldr	x1, [x19, 80]
.L592:
	and	w1, w1, 1
	orr	w1, w1, w28
	tbz	x1, 0, .L691
.L622:
	str	x1, [x19, 80]
	ldr	x1, [sp, 104]
	str	x21, [x27, 616]
	ldrb	w0, [x27, 632]
	ldr	w2, [x27, 1512]
	str	x1, [x27, 648]
	bfi	w0, w23, 0, 4
	strb	w0, [x27, 632]
	cmp	w2, w25
	bne	.L692
	str	w26, [x27, 1944]
	ubfx	w19, w21, 12, 1
	mov	x0, x21
	cbnz	x24, .L633
.L625:
	and	x0, x0, 268435456
	tbnz	x21, 28, .L628
.L694:
	cbnz	x0, .L693
.L629:
	mov	x0, x27
	bl	btrfs_free_space_cache_v1_active
	cmp	w19, w0, uxtb
	beq	.L630
	mov	w1, w19
	mov	x0, x27
	bl	btrfs_set_free_space_cache_v1_active
.L630:
	mov	x0, 2
	add	x3, x27, 2584
#APP
// 229 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_andnot
	prfm	pstl1strm, [x3]
1:	ldxr	x1, [x3]
	bic	x1, x1, x0
	stxr	w2, x1, [x3]
	cbnz	w2, 1b
// 0 "" 2
#NO_APP
	ldp	x19, x20, [sp, 16]
	mov	w0, w22
	ldp	x21, x22, [sp, 32]
	ldp	x23, x24, [sp, 48]
	ldp	x25, x26, [sp, 64]
	ldp	x27, x28, [sp, 80]
	ldp	x29, x30, [sp], 176
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 27
	.cfi_restore 28
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L691:
	.cfi_restore_state
	add	x4, x27, 2584
	mov	x0, 4
#APP
// 229 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_andnot
	prfm	pstl1strm, [x4]
1:	ldxr	x2, [x4]
	bic	x2, x2, x0
	stxr	w3, x2, [x4]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
	b	.L622
	.p2align 2,,3
.L628:
	cbnz	x0, .L629
	mov	x0, x27
	bl	btrfs_discard_cleanup
	b	.L629
.L692:
	mov	x0, x27
	mov	w1, w25
	bl	btrfs_resize_thread_pool.part.0
	str	w26, [x27, 1944]
	ldr	x0, [x27, 616]
	ubfx	w19, w0, 12, 1
	cbz	x24, .L625
	tbz	x0, 16, .L626
	.p2align 3,,7
.L633:
	ldr	x1, [x27, 784]
	ldr	x1, [x1, 80]
	tbz	x1, 0, .L625
.L626:
	mov	x0, x27
	bl	btrfs_cleanup_defrag_inodes
	ldr	x0, [x27, 616]
	and	x0, x0, 268435456
	tbnz	x21, 28, .L628
	b	.L694
	.p2align 2,,3
.L686:
	ldr	w0, [x20]
	cbz	x24, .L594
	ldr	x1, [x27, 616]
	and	w0, w0, 1
	str	w0, [sp, 124]
	tbnz	x1, 16, .L695
	ldr	w0, [x27, 1816]
	cbnz	w0, .L632
.L598:
	ldr	w0, [sp, 124]
	cbnz	w0, .L631
.L594:
	ldr	w1, [x27, 1512]
	cmp	w1, w25
	bne	.L696
.L601:
	ldr	x0, [x27, 768]
	ldr	x2, [x27, 616]
	ldr	x0, [x0, 180]
	ubfx	w2, w2, 25, 1
	and	w0, w0, 1
	ldr	x1, [x19, 80]
	cmp	w2, w0
	beq	.L603
	tbz	x1, 0, .L604
	ldr	w0, [x20]
	tbnz	x0, 0, .L604
.L609:
	ldr	x0, [x27, 2584]
	tbnz	x0, 0, .L697
	ldr	x0, [x27, 1632]
	ldr	x0, [x0, 72]
	cbnz	x0, .L698
	mov	w22, -13
	b	.L592
	.p2align 2,,3
.L698:
	mov	x0, x27
	mov	x1, 0
	bl	btrfs_check_rw_degradable
	tbz	x0, 0, .L699
	ldr	x0, [x27, 768]
	ldr	x0, [x0, 96]
	cbnz	x0, .L700
	mov	x0, x27
	bl	btrfs_start_pre_rw_mount
	cbnz	w0, .L635
	ldr	x2, [x19, 80]
	mov	x1, 4
	ldr	x0, [x19, 872]
	and	x2, x2, -2
	str	x2, [x19, 80]
	add	x0, x0, 2584
#APP
// 229 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_andnot
	prfm	pstl1strm, [x0]
1:	ldxr	x2, [x0]
	bic	x2, x2, x1
	stxr	w3, x2, [x0]
	cbnz	w3, 1b
// 0 "" 2
#NO_APP
	add	x2, x27, 16
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x2]
1:	ldxr	x0, [x2]
	orr	x0, x0, 16
	stxr	w1, x0, [x2]
	cbnz	w1, 1b
// 0 "" 2
#NO_APP
.L690:
	ldr	w0, [x20]
.L608:
	orr	w0, w0, 8388608
	str	w0, [x20]
	ldr	x0, [x27, 1496]
	bl	wake_up_process
	ldr	x0, [x27, 616]
	ubfx	w19, w0, 12, 1
	cbz	x24, .L616
	tbz	x0, 16, .L617
	ldr	x1, [x27, 784]
	ldr	x1, [x1, 80]
	tbnz	x1, 0, .L617
	.p2align 3,,7
.L616:
	and	x0, x0, 268435456
	tbz	x21, 28, .L701
	cbz	x0, .L702
.L619:
	mov	x0, x27
	bl	btrfs_free_space_cache_v1_active
	cmp	w19, w0, uxtb
	beq	.L620
	mov	w1, w19
	mov	x0, x27
	bl	btrfs_set_free_space_cache_v1_active
.L620:
	mov	x0, x27
	bl	btrfs_clear_oneshot_options
	mov	x0, 2
	add	x3, x27, 2584
#APP
// 229 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_andnot
	prfm	pstl1strm, [x3]
1:	ldxr	x1, [x3]
	bic	x1, x1, x0
	stxr	w2, x1, [x3]
	cbnz	w2, 1b
// 0 "" 2
#NO_APP
	ldp	x19, x20, [sp, 16]
	mov	w0, w22
	ldp	x21, x22, [sp, 32]
	ldp	x23, x24, [sp, 48]
	ldp	x25, x26, [sp, 64]
	ldp	x27, x28, [sp, 80]
	ldp	x29, x30, [sp], 176
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 27
	.cfi_restore 28
	.cfi_restore 25
	.cfi_restore 26
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L695:
	.cfi_restore_state
	cbz	w0, .L594
	ldr	w0, [x27, 1816]
	cbnz	w0, .L632
.L631:
	ldr	x0, [x27, 784]
	bl	sync_filesystem
	b	.L594
	.p2align 2,,3
.L617:
	mov	x0, x27
	bl	btrfs_cleanup_defrag_inodes
	ldr	x0, [x27, 616]
	b	.L616
	.p2align 2,,3
.L632:
	add	x0, sp, 136
	mov	w1, 0
	bl	init_wait_entry
	add	x0, x27, 688
	str	x0, [sp, 112]
	b	.L600
	.p2align 2,,3
.L703:
	bl	schedule
.L600:
	ldr	x0, [sp, 112]
	add	x1, sp, 136
	mov	w2, 2
	bl	prepare_to_wait_event
	ldr	w0, [x27, 1816]
	cbnz	w0, .L703
	ldr	x0, [sp, 112]
	add	x1, sp, 136
	bl	finish_wait
	b	.L598
.L604:
	mov	x0, x27
	adrp	x1, .LC98
	add	x1, x1, :lo12:.LC98
	bl	btrfs_printk
	ldr	x0, [x27, 768]
	ldr	x0, [x0, 180]
	tbnz	x0, 0, .L704
.L606:
	mov	x0, x27
	bl	btrfs_free_space_cache_v1_active
	tbz	x0, 0, .L689
	ldr	x0, [x27, 616]
	and	x0, x0, -33554433
	orr	x0, x0, 4096
	str	x0, [x27, 616]
.L689:
	ldr	x1, [x19, 80]
	.p2align 3,,7
.L603:
	ldr	w0, [x20]
	and	w2, w1, 1
	and	w3, w0, 1
	cmp	w3, w2
	beq	.L608
	cbz	w3, .L609
	add	x0, x27, 3024
	bl	cancel_work_sync
	add	x0, x27, 3056
	bl	cancel_work_sync
	mov	x0, x27
	bl	btrfs_discard_cleanup
	add	x0, x27, 3000
	str	x0, [sp, 112]
	bl	down
	ldr	x0, [sp, 112]
	bl	up
	ldr	x1, [x19, 80]
	ldr	x0, [x19, 872]
	orr	x1, x1, 1
	str	x1, [x19, 80]
	add	x0, x0, 2584
#APP
// 222 "/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/fix/source/arch/arm64/include/asm/atomic_ll_sc.h" 1
	// atomic64_or
	prfm	pstl1strm, [x0]
1:	ldxr	x1, [x0]
	orr	x1, x1, 4
	stxr	w2, x1, [x0]
	cbnz	w2, 1b
// 0 "" 2
#NO_APP
	mov	x0, x27
	bl	btrfs_delete_unused_bgs
	ldr	x0, [x27, 16]
	tbz	w0, 15, .L610
	adrp	x2, bit_wait
	add	x0, x27, 16
	add	x2, x2, :lo12:bit_wait
	mov	w3, 2
	mov	w1, 15
	bl	out_of_line_wait_on_bit
.L610:
	mov	x0, x27
	bl	btrfs_run_delayed_iputs
	mov	x0, x27
	bl	btrfs_dev_replace_suspend_for_unmount
	mov	x0, x27
	bl	btrfs_scrub_cancel
	mov	x0, x27
	bl	btrfs_pause_balance
	mov	w1, 0
	mov	x0, x27
	bl	btrfs_qgroup_wait_for_completion
	mov	x0, x27
	bl	btrfs_commit_super
	cbz	w0, .L690
.L635:
	ldr	x1, [x19, 80]
	mov	w22, w0
	b	.L592
	.p2align 2,,3
.L701:
	cbz	x0, .L619
	mov	x0, x27
	bl	btrfs_discard_resume
	b	.L619
	.p2align 2,,3
.L693:
	mov	x0, x27
	bl	btrfs_discard_resume
	b	.L629
	.p2align 2,,3
.L702:
	mov	x0, x27
	bl	btrfs_discard_cleanup
	b	.L619
.L700:
	adrp	x1, .LC101
	mov	x0, x27
	add	x1, x1, :lo12:.LC101
	bl	btrfs_printk
.L612:
	ldr	x1, [x19, 80]
	mov	w22, -22
	b	.L592
.L699:
	mov	x0, x27
	adrp	x1, .LC100
	add	x1, x1, :lo12:.LC100
	bl	btrfs_printk
	ldr	x1, [x19, 80]
	mov	w22, -13
	b	.L592
.L697:
	mov	x0, x27
	adrp	x1, .LC99
	add	x1, x1, :lo12:.LC99
	bl	btrfs_printk
	b	.L612
.L696:
	mov	w2, w25
	mov	x0, x27
	bl	btrfs_resize_thread_pool.part.0
	b	.L601
.L704:
	ldr	x0, [x27, 616]
	and	x0, x0, -4097
	orr	x0, x0, 33554432
	str	x0, [x27, 616]
	b	.L606
	.cfi_endproc
.LFE6379:
	.size	btrfs_remount, .-btrfs_remount
	.align	2
	.p2align 4,,11
	.global	btrfs_get_subvol_name_from_objectid
	.type	btrfs_get_subvol_name_from_objectid, %function
btrfs_get_subvol_name_from_objectid:
.LFB6364:
	.cfi_startproc
	stp	x29, x30, [sp, -160]!
	.cfi_def_cfa_offset 160
	.cfi_offset 29, -160
	.cfi_offset 30, -152
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	stp	x21, x22, [sp, 32]
	.cfi_offset 19, -144
	.cfi_offset 20, -136
	.cfi_offset 21, -128
	.cfi_offset 22, -120
	mov	x21, x1
	stp	x23, x24, [sp, 48]
	str	x0, [sp, 112]
	ldr	x0, [x0, 32]
	str	x1, [sp, 96]
	str	x0, [sp, 104]
	.cfi_offset 23, -112
	.cfi_offset 24, -104
	bl	btrfs_alloc_path
	mov	x19, x0
	cbz	x0, .L706
	adrp	x0, kmalloc_caches+96
	mov	w1, 3264
	ldr	x0, [x0, #:lo12:kmalloc_caches+96]
	bl	kmem_cache_alloc
	mov	x22, x0
	cbz	x0, .L706
	add	x20, x0, 4095
	str	x20, [sp, 120]
	strb	wzr, [x0, 4095]
	cmp	x21, 5
	beq	.L707
	stp	x25, x26, [sp, 64]
	.cfi_offset 26, -88
	.cfi_offset 25, -96
	mov	w26, 25
	mov	x25, 101
	stp	x27, x28, [sp, 80]
	.cfi_offset 28, -72
	.cfi_offset 27, -80
.L714:
	mov	x24, -1
	ldp	x3, x0, [sp, 96]
	str	x3, [sp, 136]
	mov	x2, x19
	add	x1, sp, 136
	str	x24, [sp, 145]
	mov	w3, -112
	strb	w3, [sp, 144]
	bl	btrfs_search_backwards
	cmp	w0, 0
	blt	.L733
	bne	.L719
	ldr	w1, [x19, 64]
	mov	x2, 17
	ldr	x0, [x19]
	ldr	x27, [sp, 145]
	smaddl	x1, w1, w26, x25
	str	x27, [sp, 96]
	bl	btrfs_get_32
	uxtw	x23, w0
	ldr	x0, [x19]
	add	x21, x23, 101
	mov	x1, x21
	mov	x2, 16
	bl	btrfs_get_16
	and	x3, x0, 65535
	mvn	x0, x3
	add	x20, x20, x0
	cmp	x20, x22
	bcc	.L720
	ldr	x0, [x19]
	add	x2, x23, 119
	add	x1, x20, 1
	bl	read_extent_buffer
	mov	w0, 47
	strb	w0, [x20]
	mov	x1, x21
	mov	x2, 0
	ldr	x0, [x19]
	bl	btrfs_get_64
	mov	x21, x0
	mov	x0, x19
	bl	btrfs_release_path
	ldr	x0, [sp, 112]
	mov	x1, x27
	mov	w2, 1
	bl	btrfs_get_fs_root
	mov	x23, x0
	cmn	x0, #4096
	bhi	.L710
	mov	w27, 12
	cmp	x21, 256
	bne	.L711
	b	.L712
	.p2align 2,,3
.L713:
	bne	.L721
	ldr	w1, [x19, 64]
	ldr	x0, [x19]
	ldr	x21, [sp, 145]
	smaddl	x1, w1, w26, x25
	bl	btrfs_get_32
	uxtw	x28, w0
	ldr	x0, [x19]
	add	x1, x28, 101
	mov	x2, 8
	bl	btrfs_get_16
	and	x3, x0, 65535
	mvn	x0, x3
	add	x2, x28, 111
	add	x20, x20, x0
	add	x1, x20, 1
	cmp	x20, x22
	bcc	.L722
	ldr	x0, [x19]
	bl	read_extent_buffer
	mov	w1, 47
	strb	w1, [x20]
	mov	x0, x19
	bl	btrfs_release_path
	cmp	x21, 256
	beq	.L712
.L711:
	mov	x2, x19
	add	x1, sp, 136
	mov	x0, x23
	str	x21, [sp, 136]
	strb	w27, [sp, 144]
	str	x24, [sp, 145]
	bl	btrfs_search_backwards
	mov	x2, 17
	cmp	w0, 0
	bge	.L713
	ldp	x25, x26, [sp, 64]
	.cfi_restore 26
	.cfi_restore 25
	sxtw	x20, w0
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	b	.L709
	.p2align 2,,3
.L706:
	mov	x20, -12
	mov	x22, 0
	mov	x23, 0
.L709:
	mov	x0, x23
	bl	btrfs_put_root
	mov	x0, x19
	bl	btrfs_free_path
	mov	x0, x22
	bl	kfree
.L705:
	ldp	x21, x22, [sp, 32]
	mov	x0, x20
	ldp	x19, x20, [sp, 16]
	ldp	x23, x24, [sp, 48]
	ldp	x29, x30, [sp], 160
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L712:
	.cfi_def_cfa_offset 160
	.cfi_offset 19, -144
	.cfi_offset 20, -136
	.cfi_offset 21, -128
	.cfi_offset 22, -120
	.cfi_offset 23, -112
	.cfi_offset 24, -104
	.cfi_offset 25, -96
	.cfi_offset 26, -88
	.cfi_offset 27, -80
	.cfi_offset 28, -72
	.cfi_offset 29, -160
	.cfi_offset 30, -152
	mov	x0, x23
	bl	btrfs_put_root
	ldr	x0, [sp, 96]
	cmp	x0, 5
	bne	.L714
	mov	x0, x19
	bl	btrfs_free_path
	ldr	x0, [sp, 120]
	cmp	x20, x0
	beq	.L734
	add	x2, x22, 4096
	mov	x1, x20
	sub	x2, x2, x20
	mov	x0, x22
	mov	x20, x22
	bl	memmove
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	b	.L705
	.p2align 2,,3
.L721:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	mov	x20, -2
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	b	.L709
	.p2align 2,,3
.L722:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	mov	x20, -36
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	b	.L709
	.p2align 2,,3
.L710:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	sxtw	x20, w0
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	mov	x23, 0
	b	.L709
.L733:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	sxtw	x20, w0
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	mov	x23, 0
	b	.L709
.L719:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_remember_state
	.cfi_restore 26
	.cfi_restore 25
	mov	x20, -2
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	mov	x23, 0
	b	.L709
.L720:
	.cfi_restore_state
	ldp	x25, x26, [sp, 64]
	.cfi_restore 26
	.cfi_restore 25
	mov	x20, -36
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	mov	x23, 0
	b	.L709
.L707:
	mov	x0, x19
	bl	btrfs_free_path
.L718:
	mov	w0, 47
	mov	x20, x22
	strh	w0, [x22]
	b	.L705
.L734:
	.cfi_offset 25, -96
	.cfi_offset 26, -88
	.cfi_offset 27, -80
	.cfi_offset 28, -72
	ldp	x25, x26, [sp, 64]
	.cfi_restore 26
	.cfi_restore 25
	ldp	x27, x28, [sp, 80]
	.cfi_restore 28
	.cfi_restore 27
	b	.L718
	.cfi_endproc
.LFE6364:
	.size	btrfs_get_subvol_name_from_objectid, .-btrfs_get_subvol_name_from_objectid
	.section	.rodata.str1.8
	.align	3
.LC102:
	.string	",rescue="
	.align	3
.LC103:
	.string	",degraded"
	.align	3
.LC104:
	.string	",nodatasum"
	.align	3
.LC105:
	.string	",nodatacow"
	.align	3
.LC106:
	.string	",nobarrier"
	.align	3
.LC107:
	.string	",max_inline=%llu"
	.align	3
.LC108:
	.string	",thread_pool=%u"
	.align	3
.LC109:
	.string	",compress-force=%s"
	.align	3
.LC110:
	.string	",compress=%s"
	.align	3
.LC111:
	.string	":%d"
	.align	3
.LC112:
	.string	",nossd"
	.align	3
.LC113:
	.string	",ssd_spread"
	.align	3
.LC114:
	.string	",ssd"
	.align	3
.LC115:
	.string	",notreelog"
	.align	3
.LC116:
	.string	"%s%s"
	.align	3
.LC117:
	.string	",flushoncommit"
	.align	3
.LC118:
	.string	",discard"
	.align	3
.LC119:
	.string	",discard=async"
	.align	3
.LC120:
	.string	",noacl"
	.align	3
.LC121:
	.string	",space_cache"
	.align	3
.LC122:
	.string	",space_cache=v2"
	.align	3
.LC123:
	.string	",nospace_cache"
	.align	3
.LC124:
	.string	",rescan_uuid_tree"
	.align	3
.LC125:
	.string	",clear_cache"
	.align	3
.LC126:
	.string	",user_subvol_rm_allowed"
	.align	3
.LC127:
	.string	",enospc_debug"
	.align	3
.LC128:
	.string	",autodefrag"
	.align	3
.LC129:
	.string	",skip_balance"
	.align	3
.LC130:
	.string	",metadata_ratio=%u"
	.align	3
.LC131:
	.string	",fatal_errors=panic"
	.align	3
.LC132:
	.string	",commit=%u"
	.align	3
.LC133:
	.string	",ref_verify"
	.align	3
.LC134:
	.string	",subvolid=%llu"
	.align	3
.LC135:
	.string	",subvol="
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_show_options, %function
btrfs_show_options:
.LFB6369:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	.cfi_offset 19, -32
	.cfi_offset 20, -24
	mov	x20, x0
	stp	x21, x22, [sp, 32]
	.cfi_offset 21, -16
	.cfi_offset 22, -8
	mov	x21, x1
	ldr	x1, [x1, 104]
	ldr	x19, [x1, 872]
	ldr	x1, [x19, 616]
	tbnz	x1, 4, .L861
	tbnz	x1, 0, .L862
.L737:
	tbnz	x1, 1, .L863
.L738:
	tbnz	x1, 2, .L864
.L739:
	ldr	x2, [x19, 648]
	cmp	x2, 2048
	beq	.L740
	adrp	x1, .LC107
	mov	x0, x20
	add	x1, x1, :lo12:.LC107
	bl	seq_printf
.L740:
	adrp	x0, __num_online_cpus
	ldr	w2, [x19, 1512]
	mov	x1, 8
	ldr	w0, [x0, #:lo12:__num_online_cpus]
	add	w0, w0, 2
	cmp	x0, x1
	csel	x0, x0, x1, ls
	cmp	x0, w2, uxtw
	beq	.L741
	adrp	x1, .LC108
	mov	x0, x20
	add	x1, x1, :lo12:.LC108
	bl	seq_printf
.L741:
	ldr	x0, [x19, 616]
	tbnz	x0, 5, .L865
	tbnz	x0, 9, .L866
.L746:
	tbnz	x0, 8, .L867
.L747:
	tbnz	x0, 3, .L868
	tbnz	x0, 6, .L869
.L749:
	tbnz	x0, 26, .L750
.L887:
	tbnz	x0, 17, .L870
	tbnz	x0, 29, .L871
	tbnz	x0, 30, .L872
.L759:
	tbnz	x0, 7, .L873
.L762:
	tbnz	x0, 10, .L874
.L763:
	tbnz	x0, 28, .L875
.L764:
	ldr	x0, [x19, 784]
	ldr	x0, [x0, 80]
	tbz	x0, 16, .L876
.L765:
	mov	x0, x19
	bl	btrfs_free_space_cache_v1_active
	tbnz	x0, 0, .L877
.L766:
	ldr	x0, [x19, 768]
	ldr	x0, [x0, 180]
	tbz	x0, 0, .L768
	adrp	x1, .LC122
	mov	x0, x20
	add	x1, x1, :lo12:.LC122
	bl	seq_puts
.L767:
	ldr	x0, [x19, 616]
	tbnz	x0, 22, .L878
	tbnz	x0, 13, .L879
.L770:
	tbnz	x0, 14, .L880
.L771:
	tbnz	x0, 15, .L881
.L772:
	tbnz	x0, 16, .L882
.L773:
	tbnz	x0, 18, .L883
.L774:
	ldr	w2, [x19, 1944]
	cbnz	w2, .L884
.L775:
	ldr	x0, [x19, 616]
	tbnz	x0, 21, .L885
.L776:
	ldr	w2, [x19, 640]
	cmp	w2, 30
	beq	.L777
	adrp	x1, .LC132
	mov	x0, x20
	add	x1, x1, :lo12:.LC132
	bl	seq_printf
.L777:
	ldr	x0, [x19, 616]
	tbnz	x0, 27, .L886
.L778:
	ldr	x2, [x21, 48]
	mov	x0, x20
	adrp	x1, .LC134
	add	x1, x1, :lo12:.LC134
	sub	x2, x2, #568
	ldr	x2, [x2]
	add	x2, x2, 512
	ldr	x2, [x2, -33]
	bl	seq_printf
	ldr	x1, [x21, 48]
	mov	x0, x19
	sub	x1, x1, #568
	ldr	x1, [x1]
	add	x1, x1, 512
	ldr	x1, [x1, -33]
	bl	btrfs_get_subvol_name_from_objectid
	mov	x19, x0
	cmn	x0, #4096
	bhi	.L805
	mov	x0, x20
	adrp	x1, .LC135
	add	x1, x1, :lo12:.LC135
	bl	seq_puts
	mov	x1, x19
	adrp	x2, .LC0
	add	x2, x2, :lo12:.LC0
	mov	x0, x20
	bl	seq_escape
	mov	x0, x19
	bl	kfree
.L805:
	ldp	x19, x20, [sp, 16]
	mov	w0, 0
	ldp	x21, x22, [sp, 32]
	ldp	x29, x30, [sp], 48
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L869:
	.cfi_restore_state
	mov	x0, x20
	adrp	x1, .LC115
	add	x1, x1, :lo12:.LC115
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 26, .L887
.L750:
	adrp	x22, .LC116
	add	x22, x22, :lo12:.LC116
	mov	x0, x20
	mov	x1, x22
	adrp	x3, .LC91
	adrp	x2, .LC102
	add	x3, x3, :lo12:.LC91
	add	x2, x2, :lo12:.LC102
	bl	seq_printf
	ldr	x0, [x19, 616]
	adrp	x2, .LC89
	add	x2, x2, :lo12:.LC89
	tbnz	x0, 17, .L751
	adrp	x2, .LC89
	add	x2, x2, :lo12:.LC89
	tbz	x0, 29, .L857
.L755:
	mov	x0, x20
	mov	x1, x22
	adrp	x3, .LC93
	add	x3, x3, :lo12:.LC93
	bl	seq_printf
	ldr	x0, [x19, 616]
.L891:
	adrp	x2, .LC89
	add	x2, x2, :lo12:.LC89
	tbz	x0, 30, .L759
.L760:
	mov	x0, x20
	mov	x1, x22
	adrp	x3, .LC94
	add	x3, x3, :lo12:.LC94
	bl	seq_printf
	ldr	x0, [x19, 616]
.L890:
	tbz	x0, 7, .L762
	b	.L873
	.p2align 2,,3
.L866:
	mov	x0, x20
	adrp	x1, .LC112
	add	x1, x1, :lo12:.LC112
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 8, .L747
.L867:
	mov	x0, x20
	adrp	x1, .LC113
	add	x1, x1, :lo12:.LC113
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 6, .L749
	b	.L869
	.p2align 2,,3
.L865:
	ldr	x0, [x19, 632]
	and	w0, w0, 15
	bl	btrfs_compress_type2str
	ldr	x1, [x19, 616]
	mov	x2, x0
	tbnz	x1, 11, .L888
	mov	x0, x20
	adrp	x1, .LC110
	add	x1, x1, :lo12:.LC110
	bl	seq_printf
	ldr	w2, [x19, 636]
	cbnz	w2, .L745
.L855:
	ldr	x0, [x19, 616]
.L889:
	tbz	x0, 9, .L746
	b	.L866
	.p2align 2,,3
.L863:
	mov	x0, x20
	adrp	x1, .LC105
	add	x1, x1, :lo12:.LC105
	bl	seq_puts
	ldr	x1, [x19, 616]
	tbz	x1, 2, .L739
.L864:
	mov	x0, x20
	adrp	x1, .LC106
	add	x1, x1, :lo12:.LC106
	bl	seq_puts
	b	.L739
	.p2align 2,,3
.L862:
	mov	x0, x20
	adrp	x1, .LC104
	add	x1, x1, :lo12:.LC104
	bl	seq_puts
	ldr	x1, [x19, 616]
	tbz	x1, 1, .L738
	b	.L863
	.p2align 2,,3
.L861:
	adrp	x1, .LC103
	add	x1, x1, :lo12:.LC103
	bl	seq_puts
	ldr	x1, [x19, 616]
	tbz	x1, 0, .L737
	b	.L862
	.p2align 2,,3
.L870:
	adrp	x2, .LC102
	adrp	x22, .LC116
	add	x2, x2, :lo12:.LC102
	add	x22, x22, :lo12:.LC116
.L751:
	mov	x0, x20
	mov	x1, x22
	adrp	x3, .LC30
	add	x3, x3, :lo12:.LC30
	bl	seq_printf
	ldr	x0, [x19, 616]
	adrp	x2, .LC89
	add	x2, x2, :lo12:.LC89
	tbnz	x0, 29, .L755
.L857:
	adrp	x2, .LC89
	add	x2, x2, :lo12:.LC89
	tbnz	x0, 30, .L760
	tbz	x0, 7, .L762
	b	.L873
	.p2align 2,,3
.L882:
	mov	x0, x20
	adrp	x1, .LC128
	add	x1, x1, :lo12:.LC128
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 18, .L774
.L883:
	mov	x0, x20
	adrp	x1, .LC129
	add	x1, x1, :lo12:.LC129
	bl	seq_puts
	ldr	w2, [x19, 1944]
	cbz	w2, .L775
.L884:
	mov	x0, x20
	adrp	x1, .LC130
	add	x1, x1, :lo12:.LC130
	bl	seq_printf
	ldr	x0, [x19, 616]
	tbz	x0, 21, .L776
.L885:
	mov	x0, x20
	adrp	x1, .LC131
	add	x1, x1, :lo12:.LC131
	bl	seq_puts
	b	.L776
	.p2align 2,,3
.L881:
	mov	x0, x20
	adrp	x1, .LC127
	add	x1, x1, :lo12:.LC127
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 16, .L773
	b	.L882
	.p2align 2,,3
.L880:
	mov	x0, x20
	adrp	x1, .LC126
	add	x1, x1, :lo12:.LC126
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 15, .L772
	b	.L881
	.p2align 2,,3
.L879:
	mov	x0, x20
	adrp	x1, .LC125
	add	x1, x1, :lo12:.LC125
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 14, .L771
	b	.L880
	.p2align 2,,3
.L878:
	mov	x0, x20
	adrp	x1, .LC124
	add	x1, x1, :lo12:.LC124
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 13, .L770
	b	.L879
	.p2align 2,,3
.L874:
	mov	x0, x20
	adrp	x1, .LC118
	add	x1, x1, :lo12:.LC118
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 28, .L764
.L875:
	mov	x0, x20
	adrp	x1, .LC119
	add	x1, x1, :lo12:.LC119
	bl	seq_puts
	ldr	x0, [x19, 784]
	ldr	x0, [x0, 80]
	tbnz	x0, 16, .L765
.L876:
	adrp	x1, .LC120
	add	x1, x1, :lo12:.LC120
	mov	x0, x20
	bl	seq_puts
	mov	x0, x19
	bl	btrfs_free_space_cache_v1_active
	tbz	x0, 0, .L766
.L877:
	mov	x0, x20
	adrp	x1, .LC121
	add	x1, x1, :lo12:.LC121
	bl	seq_puts
	b	.L767
	.p2align 2,,3
.L873:
	mov	x0, x20
	adrp	x1, .LC117
	add	x1, x1, :lo12:.LC117
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 10, .L763
	b	.L874
	.p2align 2,,3
.L868:
	mov	x0, x20
	adrp	x1, .LC114
	add	x1, x1, :lo12:.LC114
	bl	seq_puts
	ldr	x0, [x19, 616]
	tbz	x0, 6, .L749
	b	.L869
	.p2align 2,,3
.L768:
	mov	x0, x20
	adrp	x1, .LC123
	add	x1, x1, :lo12:.LC123
	bl	seq_puts
	b	.L767
	.p2align 2,,3
.L886:
	mov	x0, x20
	adrp	x1, .LC133
	add	x1, x1, :lo12:.LC133
	bl	seq_puts
	b	.L778
	.p2align 2,,3
.L888:
	mov	x0, x20
	adrp	x1, .LC109
	add	x1, x1, :lo12:.LC109
	bl	seq_printf
	ldr	w2, [x19, 636]
	cbz	w2, .L855
.L745:
	mov	x0, x20
	adrp	x1, .LC111
	add	x1, x1, :lo12:.LC111
	bl	seq_printf
	ldr	x0, [x19, 616]
	b	.L889
	.p2align 2,,3
.L872:
	adrp	x22, .LC116
	add	x22, x22, :lo12:.LC116
	mov	x0, x20
	mov	x1, x22
	adrp	x2, .LC102
	adrp	x3, .LC94
	add	x2, x2, :lo12:.LC102
	add	x3, x3, :lo12:.LC94
	bl	seq_printf
	ldr	x0, [x19, 616]
	b	.L890
	.p2align 2,,3
.L871:
	adrp	x22, .LC116
	add	x22, x22, :lo12:.LC116
	mov	x0, x20
	mov	x1, x22
	adrp	x2, .LC102
	adrp	x3, .LC93
	add	x2, x2, :lo12:.LC102
	add	x3, x3, :lo12:.LC93
	bl	seq_printf
	ldr	x0, [x19, 616]
	b	.L891
	.cfi_endproc
.LFE6369:
	.size	btrfs_show_options, .-btrfs_show_options
	.section	.rodata.str1.8
	.align	3
.LC136:
	.string	"default"
	.align	3
.LC137:
	.string	"\0013subvol '%s' does not match subvolid %llu"
	.align	3
.LC138:
	.string	"\0013'%s' is not a valid subvolume"
	.text
	.align	2
	.p2align 4,,11
	.type	btrfs_mount, %function
btrfs_mount:
.LFB6375:
	.cfi_startproc
	stp	x29, x30, [sp, -160]!
	.cfi_def_cfa_offset 160
	.cfi_offset 29, -160
	.cfi_offset 30, -152
	mov	x29, sp
	stp	x19, x20, [sp, 16]
	stp	x21, x22, [sp, 32]
	stp	x23, x24, [sp, 48]
	.cfi_offset 19, -144
	.cfi_offset 20, -136
	.cfi_offset 21, -128
	.cfi_offset 22, -120
	.cfi_offset 23, -112
	.cfi_offset 24, -104
	mov	x23, x3
	str	x25, [sp, 64]
	.cfi_offset 25, -96
	mov	x25, x2
	str	w1, [sp, 92]
	cbz	x3, .L919
	mov	x0, x3
	mov	w1, 3264
	bl	kstrdup
	str	x0, [sp, 96]
	mov	x24, x0
	cbz	x0, .L920
	adrp	x19, .LANCHOR1
	add	x19, x19, :lo12:.LANCHOR1
	adrp	x20, .LC18
	add	x19, x19, 104
	add	x20, x20, :lo12:.LC18
	mov	x22, 0
	mov	x21, 0
	.p2align 3,,7
.L896:
	mov	x1, x20
	add	x0, sp, 96
	bl	strsep
	add	x2, sp, 112
	mov	x1, x19
	mov	x4, x0
	cbz	x0, .L934
.L903:
	ldrb	w3, [x4]
	cbz	w3, .L896
	bl	match_token
	mov	w4, w0
	cmp	w0, 36
	beq	.L897
	add	x1, sp, 104
	add	x0, sp, 112
	cmp	w4, 38
	bne	.L896
	bl	match_u64
	mov	w22, w0
	mov	x1, 5
	cbnz	w0, .L900
	ldr	x22, [sp, 104]
	cbnz	x22, .L896
	mov	x22, x1
	add	x0, sp, 96
	str	x1, [sp, 104]
	mov	x1, x20
	bl	strsep
	add	x2, sp, 112
	mov	x1, x19
	mov	x4, x0
	cbnz	x0, .L903
	.p2align 3,,7
.L934:
	mov	x0, x24
	bl	kfree
.L893:
	ldr	w24, [sp, 92]
	adrp	x19, .LANCHOR0
	add	x19, x19, :lo12:.LANCHOR0
	mov	x3, x23
	mov	x0, x19
	mov	x2, x25
	mov	w1, w24
	bl	vfs_kern_mount
	cmn	x0, #4096
	mov	x20, x0
	ccmn	x0, #16, 0, hi
	beq	.L935
.L906:
	cmn	x20, #4096
	bhi	.L933
.L909:
	cbz	x21, .L936
.L910:
	mov	x0, x20
	mov	x1, x21
	bl	mount_subtree
	mov	x19, x0
	cmn	x0, #4096
	bhi	.L923
	ldr	x0, [x0, 48]
	ldr	x24, [x19, 104]
	sub	x1, x0, #568
	ldr	x2, [x0, 40]
	ldr	x1, [x1]
	ldr	x25, [x24, 872]
	add	x1, x1, 512
	ldr	x1, [x1, -33]
	cmp	x1, x22
	cset	w23, ne
	cmp	x22, 0
	cset	w1, ne
	and	w23, w23, w1
	cmp	x2, 256
	bne	.L916
	mov	x20, 0
	cbnz	w23, .L918
.L915:
	mov	x0, x20
	bl	mntput
	mov	x0, x21
	bl	kfree
.L892:
	ldp	x21, x22, [sp, 32]
	mov	x0, x19
	ldp	x19, x20, [sp, 16]
	ldp	x23, x24, [sp, 48]
	ldr	x25, [sp, 64]
	ldp	x29, x30, [sp], 160
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 25
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L897:
	.cfi_restore_state
	mov	x0, x21
	bl	kfree
	add	x0, sp, 112
	bl	match_strdup
	mov	x21, x0
	cbnz	x0, .L896
	mov	w22, -12
.L900:
	mov	x0, x24
	bl	kfree
.L894:
	mov	x0, x21
	sxtw	x19, w22
	bl	kfree
	ldp	x21, x22, [sp, 32]
	mov	x0, x19
	ldp	x19, x20, [sp, 16]
	ldp	x23, x24, [sp, 48]
	ldr	x25, [sp, 64]
	ldp	x29, x30, [sp], 160
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 25
	.cfi_restore 23
	.cfi_restore 24
	.cfi_restore 21
	.cfi_restore 22
	.cfi_restore 19
	.cfi_restore 20
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L919:
	.cfi_restore_state
	mov	x21, 0
	mov	x22, 0
	b	.L893
	.p2align 2,,3
.L936:
	ldr	x0, [x20, 8]
	ldr	x19, [x0, 872]
	cbnz	x22, .L911
	ldr	x22, [x19, 32]
	bl	btrfs_alloc_path
	mov	x23, x0
	cbz	x0, .L922
	mov	x2, x0
	mov	x1, x22
	ldr	x0, [x19, 768]
	adrp	x4, .LC136
	mov	w6, 0
	add	x4, x4, :lo12:.LC136
	mov	w5, 7
	ldr	x3, [x0, 128]
	mov	x0, 0
	bl	btrfs_lookup_dir_item
	mov	x19, x0
	cmn	x0, #4096
	bhi	.L937
	cbz	x0, .L938
	mov	x2, x0
	add	x1, sp, 112
	ldr	x0, [x23]
	mov	x3, 17
	bl	read_extent_buffer
	mov	x0, x23
	bl	btrfs_free_path
	ldr	x0, [x20, 8]
	ldr	x22, [sp, 112]
.L911:
	mov	x1, x22
	ldr	x0, [x0, 872]
	bl	btrfs_get_subvol_name_from_objectid
	mov	x19, x0
	cmn	x0, #4096
	bhi	.L915
	mov	x21, x0
	b	.L910
.L933:
	mov	x0, x21
	mov	x19, x20
	bl	kfree
	b	.L892
.L923:
	mov	x20, 0
	b	.L915
.L938:
	mov	x0, x23
	bl	btrfs_free_path
	ldr	x0, [x20, 8]
	mov	x22, 5
	b	.L911
.L935:
	mov	x3, x23
	mov	x2, x25
	tbz	x24, 0, .L907
	and	w1, w24, -2
	mov	x0, x19
	bl	vfs_kern_mount
	mov	x20, x0
	b	.L906
.L937:
	mov	x0, x23
	bl	btrfs_free_path
	b	.L915
.L907:
	orr	w1, w24, 1
	mov	x0, x19
	bl	vfs_kern_mount
	mov	x20, x0
	cmn	x0, #4096
	bhi	.L933
	ldr	x0, [x0, 8]
	add	x0, x0, 112
	bl	down_write
	ldr	x0, [x20, 8]
	add	x1, sp, 92
	mov	x2, 0
	bl	btrfs_remount
	sxtw	x19, w0
	ldr	x0, [x20, 8]
	add	x0, x0, 112
	bl	up_write
	tbz	w19, #31, .L909
	b	.L915
.L922:
	mov	x19, -12
	b	.L915
.L920:
	mov	x21, 0
	mov	w22, -12
	b	.L894
.L916:
	adrp	x1, .LC138
	mov	x2, x21
	add	x1, x1, :lo12:.LC138
	mov	x0, x25
	bl	btrfs_printk
	cbz	w23, .L917
.L918:
	adrp	x1, .LC137
	mov	x3, x22
	mov	x0, x25
	mov	x2, x21
	add	x1, x1, :lo12:.LC137
	bl	btrfs_printk
.L917:
	mov	x0, x19
	bl	dput
	mov	x0, x24
	mov	x19, -22
	mov	x20, 0
	bl	deactivate_locked_super
	b	.L915
	.cfi_endproc
.LFE6375:
	.size	btrfs_mount, .-btrfs_mount
	.global	lba_offsets
	.section	.rodata.str1.8
	.align	3
.LC139:
	.string	"btrfs-control"
	.align	3
.LC140:
	.string	"ibadroots"
	.align	3
.LC141:
	.string	"idatacsums"
	.align	3
.LC142:
	.string	"all"
	.align	3
.LC143:
	.string	"acl"
	.align	3
.LC144:
	.string	"noacl"
	.align	3
.LC145:
	.string	"clear_cache"
	.align	3
.LC146:
	.string	"commit=%u"
	.align	3
.LC147:
	.string	"compress"
	.align	3
.LC148:
	.string	"compress=%s"
	.align	3
.LC149:
	.string	"compress-force"
	.align	3
.LC150:
	.string	"compress-force=%s"
	.align	3
.LC151:
	.string	"degraded"
	.align	3
.LC152:
	.string	"device=%s"
	.align	3
.LC153:
	.string	"fatal_errors=%s"
	.align	3
.LC154:
	.string	"flushoncommit"
	.align	3
.LC155:
	.string	"noflushoncommit"
	.align	3
.LC156:
	.string	"inode_cache"
	.align	3
.LC157:
	.string	"noinode_cache"
	.align	3
.LC158:
	.string	"max_inline=%s"
	.align	3
.LC159:
	.string	"barrier"
	.align	3
.LC160:
	.string	"nobarrier"
	.align	3
.LC161:
	.string	"datacow"
	.align	3
.LC162:
	.string	"nodatacow"
	.align	3
.LC163:
	.string	"datasum"
	.align	3
.LC164:
	.string	"nodatasum"
	.align	3
.LC165:
	.string	"autodefrag"
	.align	3
.LC166:
	.string	"noautodefrag"
	.align	3
.LC167:
	.string	"discard"
	.align	3
.LC168:
	.string	"discard=%s"
	.align	3
.LC169:
	.string	"nodiscard"
	.align	3
.LC170:
	.string	"norecovery"
	.align	3
.LC171:
	.string	"metadata_ratio=%u"
	.align	3
.LC172:
	.string	"rescan_uuid_tree"
	.align	3
.LC173:
	.string	"skip_balance"
	.align	3
.LC174:
	.string	"space_cache"
	.align	3
.LC175:
	.string	"nospace_cache"
	.align	3
.LC176:
	.string	"space_cache=%s"
	.align	3
.LC177:
	.string	"ssd"
	.align	3
.LC178:
	.string	"nossd"
	.align	3
.LC179:
	.string	"ssd_spread"
	.align	3
.LC180:
	.string	"nossd_spread"
	.align	3
.LC181:
	.string	"subvol=%s"
	.align	3
.LC182:
	.string	"subvol="
	.align	3
.LC183:
	.string	"subvolid=%s"
	.align	3
.LC184:
	.string	"thread_pool=%u"
	.align	3
.LC185:
	.string	"treelog"
	.align	3
.LC186:
	.string	"notreelog"
	.align	3
.LC187:
	.string	"user_subvol_rm_allowed"
	.align	3
.LC188:
	.string	"rescue=%s"
	.align	3
.LC189:
	.string	"check_int"
	.align	3
.LC190:
	.string	"check_int_data"
	.align	3
.LC191:
	.string	"check_int_print_mask=%u"
	.align	3
.LC192:
	.string	"enospc_debug"
	.align	3
.LC193:
	.string	"noenospc_debug"
	.align	3
.LC194:
	.string	"emergency"
	.align	3
.LC195:
	.string	"alert"
	.align	3
.LC196:
	.string	"critical"
	.align	3
.LC197:
	.string	"error"
	.align	3
.LC198:
	.string	"notice"
	.align	3
.LC199:
	.string	"info"
	.align	3
.LC200:
	.string	"debug"
	.align	3
.LC201:
	.string	"btrfs"
	.data
	.align	3
	.set	.LANCHOR0,. + 0
	.type	btrfs_root_fs_type, %object
	.size	btrfs_root_fs_type, 72
btrfs_root_fs_type:
	.xword	.LC201
	.word	35
	.zero	20
	.xword	btrfs_mount_root
	.xword	btrfs_kill_super
	.xword	0
	.zero	16
	.type	btrfs_misc, %object
	.size	btrfs_misc, 80
btrfs_misc:
	.word	234
	.zero	4
	.xword	.LC139
	.xword	btrfs_ctl_fops
	.zero	56
	.type	btrfs_fs_type, %object
	.size	btrfs_fs_type, 72
btrfs_fs_type:
	.xword	.LC201
	.word	3
	.zero	20
	.xword	btrfs_mount
	.xword	btrfs_kill_super
	.xword	0
	.zero	16
	.type	printk_limits, %object
	.size	printk_limits, 320
printk_limits:
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.word	0
	.word	1250
	.word	100
	.zero	28
	.section	.rodata
	.align	3
	.set	.LANCHOR1,. + 0
	.type	options.0, %object
	.size	options.0, 24
options.0:
	.string	", zoned=no, fsverity=no"
	.type	logtypes, %object
	.size	logtypes, 64
logtypes:
	.xword	.LC194
	.xword	.LC195
	.xword	.LC196
	.xword	.LC197
	.xword	.LC12
	.xword	.LC198
	.xword	.LC199
	.xword	.LC200
	.type	__func__.1, %object
	.size	__func__.1, 13
__func__.1:
	.string	"btrfs_printk"
	.zero	3
	.type	tokens, %object
	.size	tokens, 880
tokens:
	.word	0
	.zero	4
	.xword	.LC143
	.word	1
	.zero	4
	.xword	.LC144
	.word	2
	.zero	4
	.xword	.LC145
	.word	3
	.zero	4
	.xword	.LC146
	.word	4
	.zero	4
	.xword	.LC147
	.word	7
	.zero	4
	.xword	.LC148
	.word	5
	.zero	4
	.xword	.LC149
	.word	6
	.zero	4
	.xword	.LC150
	.word	8
	.zero	4
	.xword	.LC151
	.word	9
	.zero	4
	.xword	.LC152
	.word	10
	.zero	4
	.xword	.LC153
	.word	11
	.zero	4
	.xword	.LC154
	.word	12
	.zero	4
	.xword	.LC155
	.word	50
	.zero	4
	.xword	.LC156
	.word	51
	.zero	4
	.xword	.LC157
	.word	13
	.zero	4
	.xword	.LC158
	.word	14
	.zero	4
	.xword	.LC159
	.word	15
	.zero	4
	.xword	.LC160
	.word	16
	.zero	4
	.xword	.LC161
	.word	17
	.zero	4
	.xword	.LC162
	.word	18
	.zero	4
	.xword	.LC163
	.word	19
	.zero	4
	.xword	.LC164
	.word	20
	.zero	4
	.xword	.LC165
	.word	21
	.zero	4
	.xword	.LC166
	.word	22
	.zero	4
	.xword	.LC167
	.word	24
	.zero	4
	.xword	.LC168
	.word	23
	.zero	4
	.xword	.LC169
	.word	25
	.zero	4
	.xword	.LC170
	.word	26
	.zero	4
	.xword	.LC171
	.word	27
	.zero	4
	.xword	.LC172
	.word	28
	.zero	4
	.xword	.LC173
	.word	29
	.zero	4
	.xword	.LC174
	.word	30
	.zero	4
	.xword	.LC175
	.word	31
	.zero	4
	.xword	.LC176
	.word	32
	.zero	4
	.xword	.LC177
	.word	33
	.zero	4
	.xword	.LC178
	.word	34
	.zero	4
	.xword	.LC179
	.word	35
	.zero	4
	.xword	.LC180
	.word	36
	.zero	4
	.xword	.LC181
	.word	37
	.zero	4
	.xword	.LC182
	.word	38
	.zero	4
	.xword	.LC183
	.word	39
	.zero	4
	.xword	.LC184
	.word	40
	.zero	4
	.xword	.LC185
	.word	41
	.zero	4
	.xword	.LC186
	.word	42
	.zero	4
	.xword	.LC187
	.word	43
	.zero	4
	.xword	.LC188
	.word	45
	.zero	4
	.xword	.LC91
	.word	44
	.zero	4
	.xword	.LC30
	.word	49
	.zero	4
	.xword	.LC29
	.word	52
	.zero	4
	.xword	.LC189
	.word	53
	.zero	4
	.xword	.LC190
	.word	54
	.zero	4
	.xword	.LC191
	.word	55
	.zero	4
	.xword	.LC192
	.word	56
	.zero	4
	.xword	.LC193
	.word	57
	.zero	4
	.xword	0
	.type	btrfs_super_ops, %object
	.size	btrfs_super_ops, 176
btrfs_super_ops:
	.xword	btrfs_alloc_inode
	.xword	btrfs_destroy_inode
	.xword	btrfs_free_inode
	.zero	16
	.xword	btrfs_drop_inode
	.xword	btrfs_evict_inode
	.xword	btrfs_put_super
	.xword	btrfs_sync_fs
	.zero	8
	.xword	btrfs_freeze
	.zero	8
	.xword	btrfs_unfreeze
	.xword	btrfs_statfs
	.xword	btrfs_remount
	.zero	8
	.xword	btrfs_show_options
	.xword	btrfs_show_devname
	.zero	32
	.type	rescue_tokens, %object
	.size	rescue_tokens, 128
rescue_tokens:
	.word	44
	.zero	4
	.xword	.LC30
	.word	45
	.zero	4
	.xword	.LC91
	.word	46
	.zero	4
	.xword	.LC93
	.word	46
	.zero	4
	.xword	.LC140
	.word	47
	.zero	4
	.xword	.LC94
	.word	47
	.zero	4
	.xword	.LC141
	.word	48
	.zero	4
	.xword	.LC142
	.word	57
	.zero	4
	.xword	0
	.type	lba_offsets, %object
	.size	lba_offsets, 32
lba_offsets:
	.xword	768
	.xword	3260
	.xword	648
	.xword	144
	.type	btrfs_ctl_fops, %object
	.size	btrfs_ctl_fops, 256
btrfs_ctl_fops:
	.xword	0
	.xword	noop_llseek
	.zero	64
	.xword	btrfs_control_ioctl
	.xword	0
	.zero	16
	.xword	btrfs_control_open
	.zero	136
	.section	.discard.addressable,"aw"
	.align	3
	.type	__UNIQUE_ID___addressable_init_btrfs_fs901, %object
	.size	__UNIQUE_ID___addressable_init_btrfs_fs901, 8
__UNIQUE_ID___addressable_init_btrfs_fs901:
	.xword	init_btrfs_fs
	.section	.exitcall.exit,"aw"
	.align	3
	.type	__exitcall_exit_btrfs_fs, %object
	.size	__exitcall_exit_btrfs_fs, 8
__exitcall_exit_btrfs_fs:
	.xword	exit_btrfs_fs
	.section	.modinfo,"a"
	.type	__UNIQUE_ID_softdep907, %object
	.size	__UNIQUE_ID_softdep907, 31
__UNIQUE_ID_softdep907:
	.string	"btrfs.softdep=pre: blake2b-256"
	.type	__UNIQUE_ID_softdep906, %object
	.size	__UNIQUE_ID_softdep906, 26
__UNIQUE_ID_softdep906:
	.string	"btrfs.softdep=pre: sha256"
	.type	__UNIQUE_ID_softdep905, %object
	.size	__UNIQUE_ID_softdep905, 28
__UNIQUE_ID_softdep905:
	.string	"btrfs.softdep=pre: xxhash64"
	.type	__UNIQUE_ID_softdep904, %object
	.size	__UNIQUE_ID_softdep904, 26
__UNIQUE_ID_softdep904:
	.string	"btrfs.softdep=pre: crc32c"
	.type	__UNIQUE_ID_license903, %object
	.size	__UNIQUE_ID_license903, 18
__UNIQUE_ID_license903:
	.string	"btrfs.license=GPL"
	.type	__UNIQUE_ID_file902, %object
	.size	__UNIQUE_ID_file902, 26
__UNIQUE_ID_file902:
	.string	"btrfs.file=fs/btrfs/btrfs"
	.type	__UNIQUE_ID_alias899, %object
	.size	__UNIQUE_ID_alias899, 34
__UNIQUE_ID_alias899:
	.string	"btrfs.alias=devname:btrfs-control"
	.type	__UNIQUE_ID_alias898, %object
	.size	__UNIQUE_ID_alias898, 30
__UNIQUE_ID_alias898:
	.string	"btrfs.alias=char-major-10-234"
	.type	__UNIQUE_ID_alias892, %object
	.size	__UNIQUE_ID_alias892, 21
__UNIQUE_ID_alias892:
	.string	"btrfs.alias=fs-btrfs"
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
