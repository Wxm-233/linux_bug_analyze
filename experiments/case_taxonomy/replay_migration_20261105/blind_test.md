## A018

### 真实补丁T

```diff
commit 9151dde40356880bb445f719f5ebbb1319054d5f
Subject: LoongArch: module: Use got/plt section indices for relocations


diff --git a/arch/loongarch/include/asm/module.h b/arch/loongarch/include/asm/module.h
index b29b19a46f42..60dc62a1146e 100644
--- a/arch/loongarch/include/asm/module.h
+++ b/arch/loongarch/include/asm/module.h
@@ -11,7 +11,7 @@
 #define RELA_STACK_DEPTH 16
 
 struct mod_section {
-	Elf_Shdr *shdr;
+	int shndx;
 	int num_entries;
 	int max_entries;
 };
@@ -37,8 +37,8 @@ struct plt_idx_entry {
 	Elf_Addr symbol_addr;
 };
 
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val);
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val);
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
 
 static inline struct got_entry emit_got_entry(Elf_Addr val)
 {
@@ -62,10 +62,10 @@ static inline struct plt_idx_entry emit_plt_idx_entry(unsigned long val)
 	return (struct plt_idx_entry) { val };
 }
 
-static inline int get_plt_idx(unsigned long val, const struct mod_section *sec)
+static inline int get_plt_idx(unsigned long val, Elf_Shdr *sechdrs, const struct mod_section *sec)
 {
 	int i;
-	struct plt_idx_entry *plt_idx = (struct plt_idx_entry *)sec->shdr->sh_addr;
+	struct plt_idx_entry *plt_idx = (struct plt_idx_entry *)sechdrs[sec->shndx].sh_addr;
 
 	for (i = 0; i < sec->num_entries; i++) {
 		if (plt_idx[i].symbol_addr == val)
@@ -76,11 +76,12 @@ static inline int get_plt_idx(unsigned long val, const struct mod_section *sec)
 }
 
 static inline struct plt_entry *get_plt_entry(unsigned long val,
-				      const struct mod_section *sec_plt,
-				      const struct mod_section *sec_plt_idx)
+					      Elf_Shdr *sechdrs,
+					      const struct mod_section *sec_plt,
+					      const struct mod_section *sec_plt_idx)
 {
-	int plt_idx = get_plt_idx(val, sec_plt_idx);
-	struct plt_entry *plt = (struct plt_entry *)sec_plt->shdr->sh_addr;
+	int plt_idx = get_plt_idx(val, sechdrs, sec_plt_idx);
+	struct plt_entry *plt = (struct plt_entry *)sechdrs[sec_plt->shndx].sh_addr;
 
 	if (plt_idx < 0)
 		return NULL;
@@ -89,10 +90,11 @@ static inline struct plt_entry *get_plt_entry(unsigned long val,
 }
 
 static inline struct got_entry *get_got_entry(Elf_Addr val,
+					      Elf_Shdr *sechdrs,
 					      const struct mod_section *sec)
 {
-	struct got_entry *got = (struct got_entry *)sec->shdr->sh_addr;
 	int i;
+	struct got_entry *got = (struct got_entry *)sechdrs[sec->shndx].sh_addr;
 
 	for (i = 0; i < sec->num_entries; i++)
 		if (got[i].symbol_addr == val)
diff --git a/arch/loongarch/kernel/module-sections.c b/arch/loongarch/kernel/module-sections.c
index d296a70b758f..13d9a427325a 100644
--- a/arch/loongarch/kernel/module-sections.c
+++ b/arch/loongarch/kernel/module-sections.c
@@ -7,17 +7,17 @@
 #include <linux/kernel.h>
 #include <linux/module.h>
 
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	struct mod_section *got_sec = &mod->arch.got;
 	int i = got_sec->num_entries;
-	struct got_entry *got = get_got_entry(val, got_sec);
+	struct got_entry *got = get_got_entry(val, sechdrs, got_sec);
 
 	if (got)
 		return (Elf_Addr)got;
 
 	/* There is no GOT entry for val yet, create a new one. */
-	got = (struct got_entry *)got_sec->shdr->sh_addr;
+	got = (struct got_entry *)sechdrs[got_sec->shndx].sh_addr;
 	got[i] = emit_got_entry(val);
 
 	got_sec->num_entries++;
@@ -33,12 +33,12 @@ Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val)
 	return (Elf_Addr)&got[i];
 }
 
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	int nr;
 	struct mod_section *plt_sec = &mod->arch.plt;
 	struct mod_section *plt_idx_sec = &mod->arch.plt_idx;
-	struct plt_entry *plt = get_plt_entry(val, plt_sec, plt_idx_sec);
+	struct plt_entry *plt = get_plt_entry(val, sechdrs, plt_sec, plt_idx_sec);
 	struct plt_idx_entry *plt_idx;
 
 	if (plt)
@@ -47,9 +47,9 @@ Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val)
 	nr = plt_sec->num_entries;
 
 	/* There is no duplicate entry, create a new one */
-	plt = (struct plt_entry *)plt_sec->shdr->sh_addr;
+	plt = (struct plt_entry *)sechdrs[plt_sec->shndx].sh_addr;
 	plt[nr] = emit_plt_entry(val);
-	plt_idx = (struct plt_idx_entry *)plt_idx_sec->shdr->sh_addr;
+	plt_idx = (struct plt_idx_entry *)sechdrs[plt_idx_sec->shndx].sh_addr;
 	plt_idx[nr] = emit_plt_idx_entry(val);
 
 	plt_sec->num_entries++;
@@ -103,28 +103,29 @@ int module_frob_arch_sections(Elf_Ehdr *ehdr, Elf_Shdr *sechdrs,
 			      char *secstrings, struct module *mod)
 {
 	unsigned int i, num_plts = 0, num_gots = 0;
+	Elf_Shdr *got_sec, *plt_sec, *plt_idx_sec;
 
 	/*
 	 * Find the empty .plt sections.
 	 */
 	for (i = 0; i < ehdr->e_shnum; i++) {
 		if (!strcmp(secstrings + sechdrs[i].sh_name, ".got"))
-			mod->arch.got.shdr = sechdrs + i;
+			mod->arch.got.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt"))
-			mod->arch.plt.shdr = sechdrs + i;
+			mod->arch.plt.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt.idx"))
-			mod->arch.plt_idx.shdr = sechdrs + i;
+			mod->arch.plt_idx.shndx = i;
 	}
 
-	if (!mod->arch.got.shdr) {
+	if (!mod->arch.got.shndx) {
 		pr_err("%s: module GOT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt.shdr) {
+	if (!mod->arch.plt.shndx) {
 		pr_err("%s: module PLT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt_idx.shdr) {
+	if (!mod->arch.plt_idx.shndx) {
 		pr_err("%s: module PLT.IDX section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
@@ -145,24 +146,27 @@ int module_frob_arch_sections(Elf_Ehdr *ehdr, Elf_Shdr *sechdrs,
 		count_max_entries(relas, num_rela, &num_plts, &num_gots);
 	}
 
-	mod->arch.got.shdr->sh_type = SHT_NOBITS;
-	mod->arch.got.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.got.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.got.shdr->sh_size = (num_gots + 1) * sizeof(struct got_entry);
+	got_sec = sechdrs + mod->arch.got.shndx;
+	got_sec->sh_type = SHT_NOBITS;
+	got_sec->sh_flags = SHF_ALLOC;
+	got_sec->sh_addralign = L1_CACHE_BYTES;
+	got_sec->sh_size = (num_gots + 1) * sizeof(struct got_entry);
 	mod->arch.got.num_entries = 0;
 	mod->arch.got.max_entries = num_gots;
 
-	mod->arch.plt.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt.shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
-	mod->arch.plt.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
+	plt_sec = sechdrs + mod->arch.plt.shndx;
+	plt_sec->sh_type = SHT_NOBITS;
+	plt_sec->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
+	plt_sec->sh_addralign = L1_CACHE_BYTES;
+	plt_sec->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
 	mod->arch.plt.num_entries = 0;
 	mod->arch.plt.max_entries = num_plts;
 
-	mod->arch.plt_idx.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt_idx.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.plt_idx.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt_idx.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
+	plt_idx_sec = sechdrs + mod->arch.plt_idx.shndx;
+	plt_idx_sec->sh_type = SHT_NOBITS;
+	plt_idx_sec->sh_flags = SHF_ALLOC;
+	plt_idx_sec->sh_addralign = L1_CACHE_BYTES;
+	plt_idx_sec->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
 	mod->arch.plt_idx.num_entries = 0;
 	mod->arch.plt_idx.max_entries = num_plts;
 
diff --git a/arch/loongarch/kernel/module.c b/arch/loongarch/kernel/module.c
index 825fcf77f9e7..899dc677cec3 100644
--- a/arch/loongarch/kernel/module.c
+++ b/arch/loongarch/kernel/module.c
@@ -99,16 +99,17 @@ static int apply_r_larch_sop_push_dup(struct module *mod, u32 *location, Elf_Add
 	return 0;
 }
 
-static int apply_r_larch_sop_push_plt_pcrel(struct module *mod, u32 *location, Elf_Addr v,
+static int apply_r_larch_sop_push_plt_pcrel(struct module *mod,
+			Elf_Shdr *sechdrs, u32 *location, Elf_Addr v,
 			s64 *rela_stack, size_t *rela_stack_top, unsigned int type)
 {
 	ptrdiff_t offset = (void *)v - (void *)location;
 
 	if (offset >= SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
 	if (offset < -SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
 	return apply_r_larch_sop_push_pcrel(mod, location, v, rela_stack, rela_stack_top, type);
 }
@@ -272,17 +273,18 @@ static int apply_r_larch_add_sub(struct module *mod, u32 *location, Elf_Addr v,
 	}
 }
 
-static int apply_r_larch_b26(struct module *mod, u32 *location, Elf_Addr v,
+static int apply_r_larch_b26(struct module *mod,
+			Elf_Shdr *sechdrs, u32 *location, Elf_Addr v,
 			s64 *rela_stack, size_t *rela_stack_top, unsigned int type)
 {
 	ptrdiff_t offset = (void *)v - (void *)location;
 	union loongarch_instruction *insn = (union loongarch_instruction *)location;
 
 	if (offset >= SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
 	if (offset < -SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
 	offset = (void *)v - (void *)location;
 
@@ -339,10 +341,11 @@ static int apply_r_larch_pcala(struct module *mod, u32 *location, Elf_Addr v,
 	return 0;
 }
 
-static int apply_r_larch_got_pc(struct module *mod, u32 *location, Elf_Addr v,
+static int apply_r_larch_got_pc(struct module *mod,
+			Elf_Shdr *sechdrs, u32 *location, Elf_Addr v,
 			s64 *rela_stack, size_t *rela_stack_top, unsigned int type)
 {
-	Elf_Addr got = module_emit_got_entry(mod, v);
+	Elf_Addr got = module_emit_got_entry(mod, sechdrs, v);
 
 	if (!got)
 		return -EINVAL;
@@ -387,13 +390,10 @@ static reloc_rela_handler reloc_rela_handlers[] = {
 	[R_LARCH_SOP_PUSH_PCREL]			     = apply_r_larch_sop_push_pcrel,
 	[R_LARCH_SOP_PUSH_ABSOLUTE]			     = apply_r_larch_sop_push_absolute,
 	[R_LARCH_SOP_PUSH_DUP]				     = apply_r_larch_sop_push_dup,
-	[R_LARCH_SOP_PUSH_PLT_PCREL]			     = apply_r_larch_sop_push_plt_pcrel,
 	[R_LARCH_SOP_SUB ... R_LARCH_SOP_IF_ELSE] 	     = apply_r_larch_sop,
 	[R_LARCH_SOP_POP_32_S_10_5 ... R_LARCH_SOP_POP_32_U] = apply_r_larch_sop_imm_field,
 	[R_LARCH_ADD32 ... R_LARCH_SUB64]		     = apply_r_larch_add_sub,
-	[R_LARCH_B26]					     = apply_r_larch_b26,
 	[R_LARCH_PCALA_HI20...R_LARCH_PCALA64_HI12]	     = apply_r_larch_pcala,
-	[R_LARCH_GOT_PC_HI20...R_LARCH_GOT_PC_LO12]	     = apply_r_larch_got_pc,
 };
 
 int apply_relocate_add(Elf_Shdr *sechdrs, const char *strtab,
@@ -444,7 +444,22 @@ int apply_relocate_add(Elf_Shdr *sechdrs, const char *strtab,
 		       sym->st_value, rel[i].r_addend, (u64)location);
 
 		v = sym->st_value + rel[i].r_addend;
-		err = handler(mod, location, v, rela_stack, &rela_stack_top, type);
+		switch (type) {
+		case R_LARCH_B26:
+			err = apply_r_larch_b26(mod, sechdrs, location,
+						     v, rela_stack, &rela_stack_top, type);
+			break;
+		case R_LARCH_GOT_PC_HI20...R_LARCH_GOT_PC_LO12:
+			err = apply_r_larch_got_pc(mod, sechdrs, location,
+						     v, rela_stack, &rela_stack_top, type);
+			break;
+		case R_LARCH_SOP_PUSH_PLT_PCREL:
+			err = apply_r_larch_sop_push_plt_pcrel(mod, sechdrs, location,
+						     v, rela_stack, &rela_stack_top, type);
+			break;
+		default:
+			err = handler(mod, location, v, rela_stack, &rela_stack_top, type);
+		}
 		if (err)
 			return err;
 	}
```

### X

```diff
diff --git a/arch/loongarch/include/asm/module.h b/arch/loongarch/include/asm/module.h
--- a/arch/loongarch/include/asm/module.h
+++ b/arch/loongarch/include/asm/module.h
@@
 struct mod_section {
-	Elf_Shdr *shdr;
+	int shndx;
 	int num_entries;
 	int max_entries;
 };
@@
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val);
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val);
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
@@
-static inline int get_plt_idx(unsigned long val, const struct mod_section *sec)
+static inline int get_plt_idx(unsigned long val, Elf_Shdr *sechdrs,
+			      const struct mod_section *sec)
 {
 	int i;
-	struct plt_idx_entry *plt_idx = (struct plt_idx_entry *)sec->shdr->sh_addr;
+	struct plt_idx_entry *plt_idx =
+		(struct plt_idx_entry *)sechdrs[sec->shndx].sh_addr;
@@
-static inline struct plt_entry *get_plt_entry(unsigned long val,
+static inline struct plt_entry *get_plt_entry(unsigned long val,
+				      Elf_Shdr *sechdrs,
 				      const struct mod_section *sec_plt,
 				      const struct mod_section *sec_plt_idx)
 {
-	int plt_idx = get_plt_idx(val, sec_plt_idx);
-	struct plt_entry *plt = (struct plt_entry *)sec_plt->shdr->sh_addr;
+	int plt_idx = get_plt_idx(val, sechdrs, sec_plt_idx);
+	struct plt_entry *plt = (struct plt_entry *)sechdrs[sec_plt->shndx].sh_addr;
@@
-static inline struct got_entry *get_got_entry(Elf_Addr val,
+static inline struct got_entry *get_got_entry(Elf_Addr val,
+					      Elf_Shdr *sechdrs,
 					      const struct mod_section *sec)
 {
-	struct got_entry *got = (struct got_entry *)sec->shdr->sh_addr;
+	struct got_entry *got = (struct got_entry *)sechdrs[sec->shndx].sh_addr;
 	int i;
diff --git a/arch/loongarch/kernel/module-sections.c b/arch/loongarch/kernel/module-sections.c
--- a/arch/loongarch/kernel/module-sections.c
+++ b/arch/loongarch/kernel/module-sections.c
@@
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	struct mod_section *got_sec = &mod->arch.got;
 	int i = got_sec->num_entries;
-	struct got_entry *got = get_got_entry(val, got_sec);
+	struct got_entry *got = get_got_entry(val, sechdrs, got_sec);
 
 	if (got)
 		return (Elf_Addr)got;
 
 	/* There is no GOT entry for val yet, create a new one. */
-	got = (struct got_entry *)got_sec->shdr->sh_addr;
+	got = (struct got_entry *)sechdrs[got_sec->shndx].sh_addr;
 	got[i] = emit_got_entry(val);
@@
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	int nr;
 	struct mod_section *plt_sec = &mod->arch.plt;
 	struct mod_section *plt_idx_sec = &mod->arch.plt_idx;
-	struct plt_entry *plt = get_plt_entry(val, plt_sec, plt_idx_sec);
+	struct plt_entry *plt = get_plt_entry(val, sechdrs, plt_sec, plt_idx_sec);
 	struct plt_idx_entry *plt_idx;
@@
-	plt = (struct plt_entry *)plt_sec->shdr->sh_addr;
+	plt = (struct plt_entry *)sechdrs[plt_sec->shndx].sh_addr;
 	plt[nr] = emit_plt_entry(val);
-	plt_idx = (struct plt_idx_entry *)plt_idx_sec->shdr->sh_addr;
+	plt_idx = (struct plt_idx_entry *)sechdrs[plt_idx_sec->shndx].sh_addr;
 	plt_idx[nr] = emit_plt_idx_entry(val);
@@
 	unsigned int i, num_plts = 0, num_gots = 0;
+	Elf_Shdr *shdr;
 
@@
 		if (!strcmp(secstrings + sechdrs[i].sh_name, ".got"))
-			mod->arch.got.shdr = sechdrs + i;
+			mod->arch.got.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt"))
-			mod->arch.plt.shdr = sechdrs + i;
+			mod->arch.plt.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt.idx"))
-			mod->arch.plt_idx.shdr = sechdrs + i;
+			mod->arch.plt_idx.shndx = i;
 	}
 
-	if (!mod->arch.got.shdr) {
+	if (!mod->arch.got.shndx) {
 		pr_err("%s: module GOT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt.shdr) {
+	if (!mod->arch.plt.shndx) {
 		pr_err("%s: module PLT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt_idx.shdr) {
+	if (!mod->arch.plt_idx.shndx) {
 		pr_err("%s: module PLT.IDX section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
@@
-	mod->arch.got.shdr->sh_type = SHT_NOBITS;
-	mod->arch.got.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.got.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.got.shdr->sh_size = (num_gots + 1) * sizeof(struct got_entry);
+	shdr = sechdrs + mod->arch.got.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_gots + 1) * sizeof(struct got_entry);
 	mod->arch.got.num_entries = 0;
 	mod->arch.got.max_entries = num_gots;
 
-	mod->arch.plt.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt.shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
-	mod->arch.plt.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
+	shdr = sechdrs + mod->arch.plt.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
 	mod->arch.plt.num_entries = 0;
 	mod->arch.plt.max_entries = num_plts;
 
-	mod->arch.plt_idx.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt_idx.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.plt_idx.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt_idx.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
+	shdr = sechdrs + mod->arch.plt_idx.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
 	mod->arch.plt_idx.num_entries = 0;
 	mod->arch.plt_idx.max_entries = num_plts;
diff --git a/arch/loongarch/kernel/module.c b/arch/loongarch/kernel/module.c
--- a/arch/loongarch/kernel/module.c
+++ b/arch/loongarch/kernel/module.c
@@
+/* sechdrs is passed to handlers via this file-local variable-free wrapper. */
 static int apply_r_larch_sop_push_plt_pcrel(struct module *mod, u32 *location, Elf_Addr v,
-			s64 *rela_stack, size_t *rela_stack_top, unsigned int type)
+			s64 *rela_stack, size_t *rela_stack_top, unsigned int type,
+			Elf_Shdr *sechdrs)
 {
 	ptrdiff_t offset = (void *)v - (void *)location;
 
 	if (offset >= SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
 	if (offset < -SZ_128M)
-		v = module_emit_plt_entry(mod, v);
+		v = module_emit_plt_entry(mod, sechdrs, v);
 
-	return apply_r_larch_sop_push_pcrel(mod, location, v, rela_stack, rela_stack_top, type);
+	return apply_r_larch_sop_push_pcrel(mod, location, v, rela_stack, rela_stack_top, type);
 }
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/module.h b/arch/loongarch/include/asm/module.h
--- a/arch/loongarch/include/asm/module.h
+++ b/arch/loongarch/include/asm/module.h
@@ -11,7 +11,7 @@
 #define RELA_STACK_DEPTH 16
 
 struct mod_section {
-	Elf_Shdr *shdr;
+	int shndx;
 	int num_entries;
 	int max_entries;
 };
@@ -35,8 +35,9 @@ struct plt_idx_entry {
 	Elf_Addr symbol_addr;
 };
 
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val);
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val);
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val);
 
 static inline struct got_entry emit_got_entry(Elf_Addr val)
 {
@@ -63,11 +64,13 @@ static inline struct plt_idx_entry emit_plt_idx_entry(unsigned long val)
 	return (struct plt_idx_entry) { val };
 }
 
-static inline int get_plt_idx(unsigned long val, const struct mod_section *sec)
+static inline int get_plt_idx(unsigned long val, Elf_Shdr *sechdrs,
+			      const struct mod_section *sec)
 {
 	int i;
-	struct plt_idx_entry *plt_idx = (struct plt_idx_entry *)sec->shdr->sh_addr;
+	struct plt_idx_entry *plt_idx =
+		(struct plt_idx_entry *)sechdrs[sec->shndx].sh_addr;
 
 	for (i = 0; i < sec->num_entries; i++) {
 		if (plt_idx[i].symbol_addr == val)
@@ -77,12 +80,13 @@ static inline int get_plt_idx(unsigned long val, const struct mod_section *sec)
 	return -1;
 }
 
-static inline struct plt_entry *get_plt_entry(unsigned long val,
+static inline struct plt_entry *get_plt_entry(unsigned long val, Elf_Shdr *sechdrs,
 				      const struct mod_section *sec_plt,
 				      const struct mod_section *sec_plt_idx)
 {
-	int plt_idx = get_plt_idx(val, sec_plt_idx);
-	struct plt_entry *plt = (struct plt_entry *)sec_plt->shdr->sh_addr;
+	int plt_idx = get_plt_idx(val, sechdrs, sec_plt_idx);
+	struct plt_entry *plt =
+		(struct plt_entry *)sechdrs[sec_plt->shndx].sh_addr;
 
 	if (plt_idx < 0)
 		return NULL;
@@ -90,10 +94,10 @@ static inline struct plt_entry *get_plt_entry(unsigned long val,
 	return plt + plt_idx;
 }
 
-static inline struct got_entry *get_got_entry(Elf_Addr val,
+static inline struct got_entry *get_got_entry(Elf_Addr val, Elf_Shdr *sechdrs,
 					      const struct mod_section *sec)
 {
-	struct got_entry *got = (struct got_entry *)sec->shdr->sh_addr;
+	struct got_entry *got = (struct got_entry *)sechdrs[sec->shndx].sh_addr;
 	int i;
 
 	for (i = 0; i < sec->num_entries; i++)
diff --git a/arch/loongarch/kernel/module-sections.c b/arch/loongarch/kernel/module-sections.c
--- a/arch/loongarch/kernel/module-sections.c
+++ b/arch/loongarch/kernel/module-sections.c
@@ -6,11 +6,11 @@
 #include <linux/kernel.h>
 #include <linux/module.h>
 
-Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_got_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	struct mod_section *got_sec = &mod->arch.got;
 	int i = got_sec->num_entries;
-	struct got_entry *got = get_got_entry(val, got_sec);
+	struct got_entry *got = get_got_entry(val, sechdrs, got_sec);
 
 	if (got)
 		return (Elf_Addr)got;
 
 	/* There is no GOT entry for val yet, create a new one. */
-	got = (struct got_entry *)got_sec->shdr->sh_addr;
+	got = (struct got_entry *)sechdrs[got_sec->shndx].sh_addr;
 	got[i] = emit_got_entry(val);
 
 	got_sec->num_entries++;
@@ -32,13 +32,13 @@ Elf_Addr module_emit_got_entry(struct module *mod, Elf_Addr val)
 	return (Elf_Addr)&got[i];
 }
 
-Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val)
+Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Shdr *sechdrs, Elf_Addr val)
 {
 	int nr;
 	struct mod_section *plt_sec = &mod->arch.plt;
 	struct mod_section *plt_idx_sec = &mod->arch.plt_idx;
-	struct plt_entry *plt = get_plt_entry(val, plt_sec, plt_idx_sec);
+	struct plt_entry *plt = get_plt_entry(val, sechdrs, plt_sec, plt_idx_sec);
 	struct plt_idx_entry *plt_idx;
 
 	if (plt)
@@ -47,9 +47,9 @@ Elf_Addr module_emit_plt_entry(struct module *mod, Elf_Addr val)
 	nr = plt_sec->num_entries;
 
 	/* There is no duplicate entry, create a new one */
-	plt = (struct plt_entry *)plt_sec->shdr->sh_addr;
+	plt = (struct plt_entry *)sechdrs[plt_sec->shndx].sh_addr;
 	plt[nr] = emit_plt_entry(val);
-	plt_idx = (struct plt_idx_entry *)plt_idx_sec->shdr->sh_addr;
+	plt_idx = (struct plt_idx_entry *)sechdrs[plt_idx_sec->shndx].sh_addr;
 	plt_idx[nr] = emit_plt_idx_entry(val);
 
 	plt_sec->num_entries++;
@@ -102,24 +102,25 @@ int module_frob_arch_sections(Elf_Ehdr *ehdr, Elf_Shdr *sechdrs,
 			      char *secstrings, struct module *mod)
 {
 	unsigned int i, num_plts = 0, num_gots = 0;
+	Elf_Shdr *shdr;
 
 	/*
 	 * Find the empty .plt sections.
 	 */
 	for (i = 0; i < ehdr->e_shnum; i++) {
 		if (!strcmp(secstrings + sechdrs[i].sh_name, ".got"))
-			mod->arch.got.shdr = sechdrs + i;
+			mod->arch.got.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt"))
-			mod->arch.plt.shdr = sechdrs + i;
+			mod->arch.plt.shndx = i;
 		else if (!strcmp(secstrings + sechdrs[i].sh_name, ".plt.idx"))
-			mod->arch.plt_idx.shdr = sechdrs + i;
+			mod->arch.plt_idx.shndx = i;
 	}
 
-	if (!mod->arch.got.shdr) {
+	if (!mod->arch.got.shndx) {
 		pr_err("%s: module GOT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt.shdr) {
+	if (!mod->arch.plt.shndx) {
 		pr_err("%s: module PLT section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
-	if (!mod->arch.plt_idx.shdr) {
+	if (!mod->arch.plt_idx.shndx) {
 		pr_err("%s: module PLT.IDX section(s) missing\n", mod->name);
 		return -ENOEXEC;
 	}
@@ -140,26 +141,29 @@ int module_frob_arch_sections(Elf_Ehdr *ehdr, Elf_Shdr *sechdrs,
 		count_max_entries(relas, num_rela, &num_plts, &num_gots);
 	}
 
-	mod->arch.got.shdr->sh_type = SHT_NOBITS;
-	mod->arch.got.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.got.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.got.shdr->sh_size = (num_gots + 1) * sizeof(struct got_entry);
+	shdr = sechdrs + mod->arch.got.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_gots + 1) * sizeof(struct got_entry);
 	mod->arch.got.num_entries = 0;
 	mod->arch.got.max_entries = num_gots;
 
-	mod->arch.plt.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt.shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
-	mod->arch.plt.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
+	shdr = sechdrs + mod->arch.plt.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_plts + 1) * sizeof(struct plt_entry);
 	mod->arch.plt.num_entries = 0;
 	mod->arch.plt.max_entries = num_plts;
 
-	mod->arch.plt_idx.shdr->sh_type = SHT_NOBITS;
-	mod->arch.plt_idx.shdr->sh_flags = SHF_ALLOC;
-	mod->arch.plt_idx.shdr->sh_addralign = L1_CACHE_BYTES;
-	mod->arch.plt_idx.shdr->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
+	shdr = sechdrs + mod->arch.plt_idx.shndx;
+	shdr->sh_type = SHT_NOBITS;
+	shdr->sh_flags = SHF_ALLOC;
+	shdr->sh_addralign = L1_CACHE_BYTES;
+	shdr->sh_size = (num_plts + 1) * sizeof(struct plt_idx_entry);
 	mod->arch.plt_idx.num_entries = 0;
 	mod->arch.plt_idx.max_entries = num_plts;
 
 	return 0;
 }
```

## A024

### 真实补丁T

```diff
commit 93eb1215ed794a18ba8753e0654f069d58838966
Subject: LoongArch: module: set section addresses to 0x0


diff --git a/arch/loongarch/include/asm/module.lds.h b/arch/loongarch/include/asm/module.lds.h
index 438f09d4ccf4..88554f92e010 100644
--- a/arch/loongarch/include/asm/module.lds.h
+++ b/arch/loongarch/include/asm/module.lds.h
@@ -2,8 +2,8 @@
 /* Copyright (C) 2020-2022 Loongson Technology Corporation Limited */
 SECTIONS {
 	. = ALIGN(4);
-	.got : { BYTE(0) }
-	.plt : { BYTE(0) }
-	.plt.idx : { BYTE(0) }
-	.ftrace_trampoline : { BYTE(0) }
+	.got 0 : { BYTE(0) }
+	.plt 0 : { BYTE(0) }
+	.plt.idx 0 : { BYTE(0) }
+	.ftrace_trampoline 0 : { BYTE(0) }
 }
```

### X

```diff
diff --git a/arch/loongarch/include/asm/module.lds.h b/arch/loongarch/include/asm/module.lds.h
--- a/arch/loongarch/include/asm/module.lds.h
+++ b/arch/loongarch/include/asm/module.lds.h
@@ -2,8 +2,8 @@
 /* Copyright (C) 2020-2022 Loongson Technology Corporation Limited */
 SECTIONS {
 	. = ALIGN(4);
-	.got : { BYTE(0) }
-	.plt : { BYTE(0) }
-	.plt.idx : { BYTE(0) }
-	.ftrace_trampoline : { BYTE(0) }
+	.got 0 : { BYTE(0) }
+	.plt 0 : { BYTE(0) }
+	.plt.idx 0 : { BYTE(0) }
+	.ftrace_trampoline 0 : { BYTE(0) }
 }
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/module.lds.h b/arch/loongarch/include/asm/module.lds.h
--- a/arch/loongarch/include/asm/module.lds.h
+++ b/arch/loongarch/include/asm/module.lds.h
@@ -2,8 +2,8 @@
 /* Copyright (C) 2020-2022 Loongson Technology Corporation Limited */
 SECTIONS {
 	. = ALIGN(4);
-	.got : { BYTE(0) }
-	.plt : { BYTE(0) }
-	.plt.idx : { BYTE(0) }
-	.ftrace_trampoline : { BYTE(0) }
+	.got 0 : { BYTE(0) }
+	.plt 0 : { BYTE(0) }
+	.plt.idx 0 : { BYTE(0) }
+	.ftrace_trampoline 0 : { BYTE(0) }
 }
```

## A025

### 真实补丁T

```diff
commit 69e3a6aa6be21de6aaf38130fad97ecde34a193c
Subject: LoongArch: Add checksum optimization for 64-bit system


diff --git a/arch/loongarch/include/asm/checksum.h b/arch/loongarch/include/asm/checksum.h
new file mode 100644
index 000000000000..cabbf6af44c4
--- /dev/null
+++ b/arch/loongarch/include/asm/checksum.h
@@ -0,0 +1,66 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+/*
+ * Copyright (C) 2016 ARM Ltd.
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ */
+#ifndef __ASM_CHECKSUM_H
+#define __ASM_CHECKSUM_H
+
+#include <linux/bitops.h>
+#include <linux/in6.h>
+
+#define _HAVE_ARCH_IPV6_CSUM
+__sum16 csum_ipv6_magic(const struct in6_addr *saddr,
+			const struct in6_addr *daddr,
+			__u32 len, __u8 proto, __wsum sum);
+
+/*
+ * turns a 32-bit partial checksum (e.g. from csum_partial) into a
+ * 1's complement 16-bit checksum.
+ */
+static inline __sum16 csum_fold(__wsum sum)
+{
+	u32 tmp = (__force u32)sum;
+
+	/*
+	 * swap the two 16-bit halves of sum
+	 * if there is a carry from adding the two 16-bit halves,
+	 * it will carry from the lower half into the upper half,
+	 * giving us the correct sum in the upper half.
+	 */
+	return (__force __sum16)(~(tmp + rol32(tmp, 16)) >> 16);
+}
+#define csum_fold csum_fold
+
+/*
+ * This is a version of ip_compute_csum() optimized for IP headers,
+ * which always checksum on 4 octet boundaries.  ihl is the number
+ * of 32-bit words and is always >= 5.
+ */
+static inline __sum16 ip_fast_csum(const void *iph, unsigned int ihl)
+{
+	u64 sum;
+	__uint128_t tmp;
+	int n = ihl; /* we want it signed */
+
+	tmp = *(const __uint128_t *)iph;
+	iph += 16;
+	n -= 4;
+	tmp += ((tmp >> 64) | (tmp << 64));
+	sum = tmp >> 64;
+	do {
+		sum += *(const u32 *)iph;
+		iph += 4;
+	} while (--n > 0);
+
+	sum += ror64(sum, 32);
+	return csum_fold((__force __wsum)(sum >> 32));
+}
+#define ip_fast_csum ip_fast_csum
+
+extern unsigned int do_csum(const unsigned char *buff, int len);
+#define do_csum do_csum
+
+#include <asm-generic/checksum.h>
+
+#endif	/* __ASM_CHECKSUM_H */
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
index 40bde632900f..271ed45f51bb 100644
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -4,4 +4,4 @@
 #
 
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
-	   clear_user.o copy_user.o dump_tlb.o unaligned.o
+	   clear_user.o copy_user.o csum.o dump_tlb.o unaligned.o
diff --git a/arch/loongarch/lib/csum.c b/arch/loongarch/lib/csum.c
new file mode 100644
index 000000000000..a5e84b403c3b
--- /dev/null
+++ b/arch/loongarch/lib/csum.c
@@ -0,0 +1,141 @@
+// SPDX-License-Identifier: GPL-2.0-only
+// Copyright (C) 2019-2020 Arm Ltd.
+
+#include <linux/compiler.h>
+#include <linux/kasan-checks.h>
+#include <linux/kernel.h>
+
+#include <net/checksum.h>
+
+static u64 accumulate(u64 sum, u64 data)
+{
+	sum += data;
+	if (sum < data)
+		sum += 1;
+	return sum;
+}
+
+/*
+ * We over-read the buffer and this makes KASAN unhappy. Instead, disable
+ * instrumentation and call kasan explicitly.
+ */
+unsigned int __no_sanitize_address do_csum(const unsigned char *buff, int len)
+{
+	unsigned int offset, shift, sum;
+	const u64 *ptr;
+	u64 data, sum64 = 0;
+
+	if (unlikely(len == 0))
+		return 0;
+
+	offset = (unsigned long)buff & 7;
+	/*
+	 * This is to all intents and purposes safe, since rounding down cannot
+	 * result in a different page or cache line being accessed, and @buff
+	 * should absolutely not be pointing to anything read-sensitive. We do,
+	 * however, have to be careful not to piss off KASAN, which means using
+	 * unchecked reads to accommodate the head and tail, for which we'll
+	 * compensate with an explicit check up-front.
+	 */
+	kasan_check_read(buff, len);
+	ptr = (u64 *)(buff - offset);
+	len = len + offset - 8;
+
+	/*
+	 * Head: zero out any excess leading bytes. Shifting back by the same
+	 * amount should be at least as fast as any other way of handling the
+	 * odd/even alignment, and means we can ignore it until the very end.
+	 */
+	shift = offset * 8;
+	data = *ptr++;
+	data = (data >> shift) << shift;
+
+	/*
+	 * Body: straightforward aligned loads from here on (the paired loads
+	 * underlying the quadword type still only need dword alignment). The
+	 * main loop strictly excludes the tail, so the second loop will always
+	 * run at least once.
+	 */
+	while (unlikely(len > 64)) {
+		__uint128_t tmp1, tmp2, tmp3, tmp4;
+
+		tmp1 = *(__uint128_t *)ptr;
+		tmp2 = *(__uint128_t *)(ptr + 2);
+		tmp3 = *(__uint128_t *)(ptr + 4);
+		tmp4 = *(__uint128_t *)(ptr + 6);
+
+		len -= 64;
+		ptr += 8;
+
+		/* This is the "don't dump the carry flag into a GPR" idiom */
+		tmp1 += (tmp1 >> 64) | (tmp1 << 64);
+		tmp2 += (tmp2 >> 64) | (tmp2 << 64);
+		tmp3 += (tmp3 >> 64) | (tmp3 << 64);
+		tmp4 += (tmp4 >> 64) | (tmp4 << 64);
+		tmp1 = ((tmp1 >> 64) << 64) | (tmp2 >> 64);
+		tmp1 += (tmp1 >> 64) | (tmp1 << 64);
+		tmp3 = ((tmp3 >> 64) << 64) | (tmp4 >> 64);
+		tmp3 += (tmp3 >> 64) | (tmp3 << 64);
+		tmp1 = ((tmp1 >> 64) << 64) | (tmp3 >> 64);
+		tmp1 += (tmp1 >> 64) | (tmp1 << 64);
+		tmp1 = ((tmp1 >> 64) << 64) | sum64;
+		tmp1 += (tmp1 >> 64) | (tmp1 << 64);
+		sum64 = tmp1 >> 64;
+	}
+	while (len > 8) {
+		__uint128_t tmp;
+
+		sum64 = accumulate(sum64, data);
+		tmp = *(__uint128_t *)ptr;
+
+		len -= 16;
+		ptr += 2;
+
+		data = tmp >> 64;
+		sum64 = accumulate(sum64, tmp);
+	}
+	if (len > 0) {
+		sum64 = accumulate(sum64, data);
+		data = *ptr;
+		len -= 8;
+	}
+	/*
+	 * Tail: zero any over-read bytes similarly to the head, again
+	 * preserving odd/even alignment.
+	 */
+	shift = len * -8;
+	data = (data << shift) >> shift;
+	sum64 = accumulate(sum64, data);
+
+	/* Finally, folding */
+	sum64 += (sum64 >> 32) | (sum64 << 32);
+	sum = sum64 >> 32;
+	sum += (sum >> 16) | (sum << 16);
+	if (offset & 1)
+		return (u16)swab32(sum);
+
+	return sum >> 16;
+}
+
+__sum16 csum_ipv6_magic(const struct in6_addr *saddr,
+			const struct in6_addr *daddr,
+			__u32 len, __u8 proto, __wsum csum)
+{
+	__uint128_t src, dst;
+	u64 sum = (__force u64)csum;
+
+	src = *(const __uint128_t *)saddr->s6_addr;
+	dst = *(const __uint128_t *)daddr->s6_addr;
+
+	sum += (__force u32)htonl(len);
+	sum += (u32)proto << 24;
+	src += (src >> 64) | (src << 64);
+	dst += (dst >> 64) | (dst << 64);
+
+	sum = accumulate(sum, src >> 64);
+	sum = accumulate(sum, dst >> 64);
+
+	sum += ((sum >> 32) | (sum << 32));
+	return csum_fold((__force __wsum)(sum >> 32));
+}
+EXPORT_SYMBOL(csum_ipv6_magic);
```

### X

```diff
diff --git a/arch/loongarch/include/asm/checksum.h b/arch/loongarch/include/asm/checksum.h
new file mode 100644
index 000000000000..2d5c1a3b7e10
--- /dev/null
+++ b/arch/loongarch/include/asm/checksum.h
@@ -0,0 +1,12 @@
+/* SPDX-License-Identifier: GPL-2.0 */
+#ifndef __ASM_LOONGARCH_CHECKSUM_H
+#define __ASM_LOONGARCH_CHECKSUM_H
+
+#include <linux/types.h>
+
+extern unsigned int do_csum(const unsigned char *buff, int len);
+#define do_csum do_csum
+
+#include <asm-generic/checksum.h>
+
+#endif	/* __ASM_LOONGARCH_CHECKSUM_H */
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -4,4 +4,4 @@
 #
 
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
-	   clear_user.o copy_user.o dump_tlb.o unaligned.o
+	   clear_user.o copy_user.o dump_tlb.o unaligned.o csum.o
diff --git a/arch/loongarch/lib/csum.c b/arch/loongarch/lib/csum.c
new file mode 100644
index 000000000000..5c1e9a4d2b73
--- /dev/null
+++ b/arch/loongarch/lib/csum.c
@@ -0,0 +1,80 @@
+// SPDX-License-Identifier: GPL-2.0
+/*
+ * Optimised do_csum() for LoongArch, based on the arm64 version.
+ */
+#include <linux/compiler.h>
+#include <linux/kasan-checks.h>
+#include <linux/kernel.h>
+
+#include <net/checksum.h>
+
+/* End-around-carry 64-bit add */
+static inline u64 accumulate(u64 sum, u64 data)
+{
+	sum += data;
+	return sum + (sum < data);
+}
+
+unsigned int do_csum(const unsigned char *buff, int len)
+{
+	unsigned int offset, shift, sum;
+	const u64 *ptr;
+	u64 data, sum64 = 0;
+
+	offset = (unsigned long)buff & 7;
+	/*
+	 * Rounding down cannot cross a page or cache line, so the aligned
+	 * head/tail reads are safe. Use unchecked reads for them and check
+	 * the real range up-front for KASAN.
+	 */
+	kasan_check_read(buff, len);
+	ptr = (u64 *)(buff - offset);
+	len = len + offset - 8;
+
+	/* Head: zero out leading bytes before the buffer */
+	shift = offset * 8;
+	data = READ_ONCE_NOCHECK(*ptr++);
+	data = (data >> shift) << shift;
+
+	/* Body: aligned 64-bit loads, tail excluded */
+	while (len > 32) {
+		u64 d1 = READ_ONCE_NOCHECK(ptr[0]);
+		u64 d2 = READ_ONCE_NOCHECK(ptr[1]);
+		u64 d3 = READ_ONCE_NOCHECK(ptr[2]);
+		u64 d4 = READ_ONCE_NOCHECK(ptr[3]);
+
+		len -= 32;
+		ptr += 4;
+
+		sum64 = accumulate(sum64, data);
+		sum64 = accumulate(sum64, d1);
+		sum64 = accumulate(sum64, d2);
+		sum64 = accumulate(sum64, d3);
+		data = d4;
+	}
+	while (len > 0) {
+		sum64 = accumulate(sum64, data);
+		data = READ_ONCE_NOCHECK(*ptr++);
+		len -= 8;
+	}
+
+	/* Tail: zero over-read bytes (len is in -7..0 here) */
+	shift = len * -8;
+	data = (data << shift) >> shift;
+	sum64 = accumulate(sum64, data);
+
+	/* Fold to 16 bits */
+	sum64 += (sum64 >> 32) | (sum64 << 32);
+	sum = sum64 >> 32;
+	sum += (sum >> 16) | (sum << 16);
+	if (offset & 1)
+		return (u16)swab32(sum);
+
+	return sum >> 16;
+}
```

### Y

```diff
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -4,4 +4,4 @@
 #
 
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
-	   clear_user.o copy_user.o dump_tlb.o unaligned.o
+	   clear_user.o copy_user.o dump_tlb.o unaligned.o
```

## A026

### 真实补丁T

```diff
commit 8b5ee2c66d5c4c1312fd193d4138e6963160ba43
Subject: LoongArch: Add support for function error injection


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 3e5d6acbf240..629a6dac33e1 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -100,6 +100,7 @@ config LOONGARCH
 	select HAVE_FAST_GUP
 	select HAVE_FTRACE_MCOUNT_RECORD
 	select HAVE_FUNCTION_ARG_ACCESS_API
+	select HAVE_FUNCTION_ERROR_INJECTION
 	select HAVE_FUNCTION_GRAPH_TRACER
 	select HAVE_FUNCTION_TRACER
 	select HAVE_GENERIC_VDSO
diff --git a/arch/loongarch/include/asm/ptrace.h b/arch/loongarch/include/asm/ptrace.h
index d761db943335..35f0958163ac 100644
--- a/arch/loongarch/include/asm/ptrace.h
+++ b/arch/loongarch/include/asm/ptrace.h
@@ -154,6 +154,11 @@ static inline long regs_return_value(struct pt_regs *regs)
 	return regs->regs[4];
 }
 
+static inline void regs_set_return_value(struct pt_regs *regs, unsigned long val)
+{
+	regs->regs[4] = val;
+}
+
 #define instruction_pointer(regs) ((regs)->csr_era)
 #define profile_pc(regs) instruction_pointer(regs)
 
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
index 271ed45f51bb..d60d4e096cfa 100644
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -5,3 +5,5 @@
 
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
 	   clear_user.o copy_user.o csum.o dump_tlb.o unaligned.o
+
+obj-$(CONFIG_FUNCTION_ERROR_INJECTION) += error-inject.o
diff --git a/arch/loongarch/lib/error-inject.c b/arch/loongarch/lib/error-inject.c
new file mode 100644
index 000000000000..afc9e1c7c973
--- /dev/null
+++ b/arch/loongarch/lib/error-inject.c
@@ -0,0 +1,10 @@
+// SPDX-License-Identifier: GPL-2.0
+
+#include <linux/error-injection.h>
+#include <linux/kprobes.h>
+
+void override_function_with_return(struct pt_regs *regs)
+{
+	instruction_pointer_set(regs, regs->regs[1]);
+}
+NOKPROBE_SYMBOL(override_function_with_return);
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -118,6 +118,7 @@ config LOONGARCH
 	select HAVE_FTRACE_MCOUNT_RECORD
 	select HAVE_FUNCTION_ARG_ACCESS_API
+	select HAVE_FUNCTION_ERROR_INJECTION
 	select HAVE_FUNCTION_GRAPH_TRACER
 	select HAVE_FUNCTION_TRACER
 	select HAVE_GENERIC_VDSO
diff --git a/arch/loongarch/include/asm/ptrace.h b/arch/loongarch/include/asm/ptrace.h
--- a/arch/loongarch/include/asm/ptrace.h
+++ b/arch/loongarch/include/asm/ptrace.h
@@ -155,6 +155,11 @@ static inline long regs_return_value(struct pt_regs *regs)
 	return regs->regs[4];
 }
 
+static inline void regs_set_return_value(struct pt_regs *regs, unsigned long val)
+{
+	regs->regs[4] = val;
+}
+
 #define instruction_pointer(regs) ((regs)->csr_era)
 #define profile_pc(regs) instruction_pointer(regs)
 
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -6,3 +6,5 @@
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
 	   clear_user.o copy_user.o csum.o dump_tlb.o unaligned.o
+
+obj-$(CONFIG_FUNCTION_ERROR_INJECTION) += error-inject.o
diff --git a/arch/loongarch/lib/error-inject.c b/arch/loongarch/lib/error-inject.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/lib/error-inject.c
@@ -0,0 +1,19 @@
+// SPDX-License-Identifier: GPL-2.0
+
+#include <linux/error-injection.h>
+#include <linux/kprobes.h>
+
+void override_function_with_return(struct pt_regs *regs)
+{
+	/*
+	 * 'regs' represents the state on entry of a predefined function in
+	 * the kernel/module and which is captured on a kprobe.
+	 *
+	 * When kprobe returns back from exception it will override the end
+	 * of probed function and directly return to the predefined
+	 * function's caller.
+	 */
+	instruction_pointer_set(regs, regs->regs[1]);
+}
+NOKPROBE_SYMBOL(override_function_with_return);
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -99,6 +99,7 @@ config LOONGARCH
 	select HAVE_FAST_GUP
 	select HAVE_FTRACE_MCOUNT_RECORD
 	select HAVE_FUNCTION_ARG_ACCESS_API
+	select HAVE_FUNCTION_ERROR_INJECTION
 	select HAVE_FUNCTION_GRAPH_TRACER
 	select HAVE_FUNCTION_TRACER
 	select HAVE_GENERIC_VDSO
diff --git a/arch/loongarch/include/asm/ptrace.h b/arch/loongarch/include/asm/ptrace.h
--- a/arch/loongarch/include/asm/ptrace.h
+++ b/arch/loongarch/include/asm/ptrace.h
@@ -143,6 +143,11 @@ static inline long regs_return_value(struct pt_regs *regs)
 	return regs->regs[4];
 }
 
+static inline void regs_set_return_value(struct pt_regs *regs, unsigned long val)
+{
+	regs->regs[4] = val;
+}
+
 #define instruction_pointer(regs) ((regs)->csr_era)
 #define profile_pc(regs) instruction_pointer(regs)
 
diff --git a/arch/loongarch/lib/Makefile b/arch/loongarch/lib/Makefile
--- a/arch/loongarch/lib/Makefile
+++ b/arch/loongarch/lib/Makefile
@@ -5,3 +5,5 @@
 
 lib-y	+= delay.o memset.o memcpy.o memmove.o \
 	   clear_user.o copy_user.o csum.o dump_tlb.o unaligned.o
+
+obj-$(CONFIG_FUNCTION_ERROR_INJECTION)	+= error-inject.o
diff --git a/arch/loongarch/lib/error-inject.c b/arch/loongarch/lib/error-inject.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/lib/error-inject.c
@@ -0,0 +1,18 @@
+// SPDX-License-Identifier: GPL-2.0
+
+#include <linux/error-injection.h>
+#include <linux/kprobes.h>
+#include <linux/ptrace.h>
+
+void override_function_with_return(struct pt_regs *regs)
+{
+	/*
+	 * 'regs' is the state on entry of the probed function, captured
+	 * by a kprobe. On return from the exception, execution resumes
+	 * at the caller (the link register $ra), skipping the function body.
+	 */
+	instruction_pointer_set(regs, regs->regs[1]);
+}
+NOKPROBE_SYMBOL(override_function_with_return);
```

## A028

### 真实补丁T

```diff
commit 7b0a096436c2dac6de77d132e751a8a3328798d5
Subject: LoongArch: Replace kretprobe with rethook


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 64cdc6802295..b787f8fcbac7 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -127,6 +127,7 @@ config LOONGARCH
 	select HAVE_PERF_REGS
 	select HAVE_PERF_USER_STACK_DUMP
 	select HAVE_REGS_AND_STACK_ACCESS_API
+	select HAVE_RETHOOK
 	select HAVE_RSEQ
 	select HAVE_SAMPLE_FTRACE_DIRECT
 	select HAVE_SAMPLE_FTRACE_DIRECT_MULTI
diff --git a/arch/loongarch/include/asm/kprobes.h b/arch/loongarch/include/asm/kprobes.h
index 798020ae02c6..7b9fc3ed71c3 100644
--- a/arch/loongarch/include/asm/kprobes.h
+++ b/arch/loongarch/include/asm/kprobes.h
@@ -49,9 +49,6 @@ bool kprobe_fault_handler(struct pt_regs *regs, int trapnr);
 bool kprobe_breakpoint_handler(struct pt_regs *regs);
 bool kprobe_singlestep_handler(struct pt_regs *regs);
 
-void __kretprobe_trampoline(void);
-void *trampoline_probe_handler(struct pt_regs *regs);
-
 #else /* !CONFIG_KPROBES */
 
 static inline bool kprobe_breakpoint_handler(struct pt_regs *regs) { return false; }
diff --git a/arch/loongarch/kernel/Makefile b/arch/loongarch/kernel/Makefile
index 64ea76f60e2c..1061c36f5ad5 100644
--- a/arch/loongarch/kernel/Makefile
+++ b/arch/loongarch/kernel/Makefile
@@ -28,6 +28,8 @@ ifdef CONFIG_FUNCTION_TRACER
   CFLAGS_REMOVE_inst.o = $(CC_FLAGS_FTRACE)
   CFLAGS_REMOVE_time.o = $(CC_FLAGS_FTRACE)
   CFLAGS_REMOVE_perf_event.o = $(CC_FLAGS_FTRACE)
+  CFLAGS_REMOVE_rethook.o = $(CC_FLAGS_FTRACE)
+  CFLAGS_REMOVE_rethook_trampoline.o = $(CC_FLAGS_FTRACE)
 endif
 
 obj-$(CONFIG_MODULES)		+= module.o module-sections.o
@@ -52,7 +54,8 @@ obj-$(CONFIG_UNWINDER_PROLOGUE) += unwind_prologue.o
 obj-$(CONFIG_PERF_EVENTS)	+= perf_event.o perf_regs.o
 obj-$(CONFIG_HAVE_HW_BREAKPOINT)	+= hw_breakpoint.o
 
-obj-$(CONFIG_KPROBES)		+= kprobes.o kprobes_trampoline.o
+obj-$(CONFIG_KPROBES)		+= kprobes.o
+obj-$(CONFIG_RETHOOK)		+= rethook.o rethook_trampoline.o
 
 obj-$(CONFIG_JUMP_LABEL)	+= jump_label.o
 
diff --git a/arch/loongarch/kernel/kprobes.c b/arch/loongarch/kernel/kprobes.c
index 56c8c4b09a42..83467232ca3c 100644
--- a/arch/loongarch/kernel/kprobes.c
+++ b/arch/loongarch/kernel/kprobes.c
@@ -378,27 +378,6 @@ int __init arch_init_kprobes(void)
 	return 0;
 }
 
-/* ASM function that handles the kretprobes must not be probed */
-NOKPROBE_SYMBOL(__kretprobe_trampoline);
-
-/* Called from __kretprobe_trampoline */
-void __used *trampoline_probe_handler(struct pt_regs *regs)
-{
-	return (void *)kretprobe_trampoline_handler(regs, NULL);
-}
-NOKPROBE_SYMBOL(trampoline_probe_handler);
-
-void arch_prepare_kretprobe(struct kretprobe_instance *ri,
-			    struct pt_regs *regs)
-{
-	ri->ret_addr = (kprobe_opcode_t *)regs->regs[1];
-	ri->fp = NULL;
-
-	/* Replace the return addr with trampoline addr */
-	regs->regs[1] = (unsigned long)&__kretprobe_trampoline;
-}
-NOKPROBE_SYMBOL(arch_prepare_kretprobe);
-
 int arch_trampoline_kprobe(struct kprobe *p)
 {
 	return 0;
diff --git a/arch/loongarch/kernel/rethook.c b/arch/loongarch/kernel/rethook.c
new file mode 100644
index 000000000000..db1c5f5024fd
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.c
@@ -0,0 +1,28 @@
+// SPDX-License-Identifier: GPL-2.0
+/*
+ * Generic return hook for LoongArch.
+ */
+
+#include <linux/kprobes.h>
+#include <linux/rethook.h>
+#include "rethook.h"
+
+/* This is called from arch_rethook_trampoline() */
+unsigned long __used arch_rethook_trampoline_callback(struct pt_regs *regs)
+{
+	return rethook_trampoline_handler(regs, 0);
+}
+NOKPROBE_SYMBOL(arch_rethook_trampoline_callback);
+
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount)
+{
+	rhn->frame = 0;
+	rhn->ret_addr = regs->regs[1];
+
+	/* replace return addr with trampoline */
+	regs->regs[1] = (unsigned long)arch_rethook_trampoline;
+}
+NOKPROBE_SYMBOL(arch_rethook_prepare);
+
+/* ASM function that handles the rethook must not be probed itself */
+NOKPROBE_SYMBOL(arch_rethook_trampoline);
diff --git a/arch/loongarch/kernel/rethook.h b/arch/loongarch/kernel/rethook.h
new file mode 100644
index 000000000000..3f1c1edf0d0b
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.h
@@ -0,0 +1,8 @@
+/* SPDX-License-Identifier: GPL-2.0 */
+#ifndef __LOONGARCH_RETHOOK_H
+#define __LOONGARCH_RETHOOK_H
+
+unsigned long arch_rethook_trampoline_callback(struct pt_regs *regs);
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount);
+
+#endif
diff --git a/arch/loongarch/kernel/kprobes_trampoline.S b/arch/loongarch/kernel/rethook_trampoline.S
similarity index 93%
rename from arch/loongarch/kernel/kprobes_trampoline.S
rename to arch/loongarch/kernel/rethook_trampoline.S
index af94b0d213fa..bd5772c96338 100644
--- a/arch/loongarch/kernel/kprobes_trampoline.S
+++ b/arch/loongarch/kernel/rethook_trampoline.S
@@ -75,7 +75,7 @@
 	csrxchg t0, t1, LOONGARCH_CSR_CRMD
 	.endm
 
-SYM_CODE_START(__kretprobe_trampoline)
+SYM_CODE_START(arch_rethook_trampoline)
 	addi.d	sp, sp, -PT_SIZE
 	save_all_base_regs
 
@@ -84,7 +84,7 @@ SYM_CODE_START(__kretprobe_trampoline)
 
 	move a0, sp /* pt_regs */
 
-	bl trampoline_probe_handler
+	bl arch_rethook_trampoline_callback
 
 	/* use the result as the return-address */
 	move ra, a0
@@ -93,4 +93,4 @@ SYM_CODE_START(__kretprobe_trampoline)
 	addi.d	sp, sp, PT_SIZE
 
 	jr ra
-SYM_CODE_END(__kretprobe_trampoline)
+SYM_CODE_END(arch_rethook_trampoline)
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -137,6 +137,7 @@ config LOONGARCH
 	select HAVE_KPROBES
 	select HAVE_KPROBES_ON_FTRACE
 	select HAVE_KRETPROBES
+	select HAVE_RETHOOK
 	select HAVE_MOD_ARCH_SPECIFIC
 	select HAVE_NMI
 	select HAVE_PCI
diff --git a/arch/loongarch/include/asm/kprobes.h b/arch/loongarch/include/asm/kprobes.h
--- a/arch/loongarch/include/asm/kprobes.h
+++ b/arch/loongarch/include/asm/kprobes.h
@@ -48,9 +48,6 @@ bool kprobe_fault_handler(struct pt_regs *regs, int trapnr);
 bool kprobe_breakpoint_handler(struct pt_regs *regs);
 bool kprobe_singlestep_handler(struct pt_regs *regs);
 
-void __kretprobe_trampoline(void);
-void *trampoline_probe_handler(struct pt_regs *regs);
-
 #else /* !CONFIG_KPROBES */
 
 static inline bool kprobe_breakpoint_handler(struct pt_regs *regs) { return false; }
diff --git a/arch/loongarch/kernel/kprobes.c b/arch/loongarch/kernel/kprobes.c
--- a/arch/loongarch/kernel/kprobes.c
+++ b/arch/loongarch/kernel/kprobes.c
@@ -349,26 +349,6 @@ int __init arch_init_kprobes(void)
 	return 0;
 }
 
-/* ASM function that handles the kretprobes must not be probed */
-NOKPROBE_SYMBOL(__kretprobe_trampoline);
-
-/* Called from __kretprobe_trampoline */
-void __used *trampoline_probe_handler(struct pt_regs *regs)
-{
-	return (void *)kretprobe_trampoline_handler(regs, NULL);
-}
-NOKPROBE_SYMBOL(trampoline_probe_handler);
-
-void arch_prepare_kretprobe(struct kretprobe_instance *ri,
-			    struct pt_regs *regs)
-{
-	ri->ret_addr = (kprobe_opcode_t *)regs->regs[1];
-	ri->fp = NULL;
-
-	/* Replace the return addr with trampoline addr */
-	regs->regs[1] = (unsigned long)&__kretprobe_trampoline;
-}
-NOKPROBE_SYMBOL(arch_prepare_kretprobe);
-
 int arch_trampoline_kprobe(struct kprobe *p)
 {
 	return 0;
diff --git a/arch/loongarch/kernel/rethook.c b/arch/loongarch/kernel/rethook.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.c
@@ -0,0 +1,27 @@
+// SPDX-License-Identifier: GPL-2.0-only
+/*
+ * Generic return hook for LoongArch.
+ */
+
+#include <linux/kprobes.h>
+#include <linux/rethook.h>
+#include "rethook.h"
+
+/* This is called from arch_rethook_trampoline() */
+unsigned long __used arch_rethook_trampoline_callback(struct pt_regs *regs)
+{
+	return rethook_trampoline_handler(regs, 0);
+}
+NOKPROBE_SYMBOL(arch_rethook_trampoline_callback);
+
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount)
+{
+	rhn->frame = 0;
+	rhn->ret_addr = regs->regs[1];
+
+	/* replace return addr with trampoline */
+	regs->regs[1] = (unsigned long)arch_rethook_trampoline;
+}
+NOKPROBE_SYMBOL(arch_rethook_prepare);
+
+/* ASM function that handles the rethook must not be probed itself */
+NOKPROBE_SYMBOL(arch_rethook_trampoline);
diff --git a/arch/loongarch/kernel/rethook.h b/arch/loongarch/kernel/rethook.h
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.h
@@ -0,0 +1,8 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+#ifndef __LOONGARCH_RETHOOK_H
+#define __LOONGARCH_RETHOOK_H
+
+unsigned long arch_rethook_trampoline_callback(struct pt_regs *regs);
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount);
+
+#endif
diff --git a/arch/loongarch/kernel/kprobes_trampoline.S b/arch/loongarch/kernel/rethook_trampoline.S
rename from arch/loongarch/kernel/kprobes_trampoline.S
rename to arch/loongarch/kernel/rethook_trampoline.S
--- a/arch/loongarch/kernel/kprobes_trampoline.S
+++ b/arch/loongarch/kernel/rethook_trampoline.S
@@ -76,13 +76,13 @@
 	csrxchg t0, t1, LOONGARCH_CSR_CRMD
 	.endm
 
-SYM_CODE_START(__kretprobe_trampoline)
+SYM_CODE_START(arch_rethook_trampoline)
 	addi.d	sp, sp, -PT_SIZE
 	save_all_base_regs
 
 	addi.d	t0, sp, PT_SIZE
 	LONG_S	t0, sp, PT_R3
 
 	move a0, sp /* pt_regs */
 
-	bl trampoline_probe_handler
+	bl arch_rethook_trampoline_callback
 
 	/* use the result as the return-address */
 	move ra, a0
@@ -92,4 +92,4 @@
 	addi.d	sp, sp, PT_SIZE
 
 	jr ra
-SYM_CODE_END(__kretprobe_trampoline)
+SYM_CODE_END(arch_rethook_trampoline)
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -123,6 +123,7 @@ config LOONGARCH
 	select HAVE_KPROBES
 	select HAVE_KPROBES_ON_FTRACE
 	select HAVE_KRETPROBES
+	select HAVE_RETHOOK
 	select HAVE_MOD_ARCH_SPECIFIC
 	select HAVE_NMI
 	select HAVE_PCI
diff --git a/arch/loongarch/include/asm/kprobes.h b/arch/loongarch/include/asm/kprobes.h
--- a/arch/loongarch/include/asm/kprobes.h
+++ b/arch/loongarch/include/asm/kprobes.h
@@ -49,9 +49,6 @@ bool kprobe_fault_handler(struct pt_regs *regs, int trapnr);
 bool kprobe_breakpoint_handler(struct pt_regs *regs);
 bool kprobe_singlestep_handler(struct pt_regs *regs);
 
-void __kretprobe_trampoline(void);
-void *trampoline_probe_handler(struct pt_regs *regs);
-
 #else /* !CONFIG_KPROBES */
 
 static inline bool kprobe_breakpoint_handler(struct pt_regs *regs) { return false; }
diff --git a/arch/loongarch/kernel/kprobes.c b/arch/loongarch/kernel/kprobes.c
--- a/arch/loongarch/kernel/kprobes.c
+++ b/arch/loongarch/kernel/kprobes.c
@@ -358,27 +358,6 @@ int __init arch_init_kprobes(void)
 	return 0;
 }
 
-/* ASM function that handles the kretprobes must not be probed */
-NOKPROBE_SYMBOL(__kretprobe_trampoline);
-
-/* Called from __kretprobe_trampoline */
-void __used *trampoline_probe_handler(struct pt_regs *regs)
-{
-	return (void *)kretprobe_trampoline_handler(regs, NULL);
-}
-NOKPROBE_SYMBOL(trampoline_probe_handler);
-
-void arch_prepare_kretprobe(struct kretprobe_instance *ri,
-			    struct pt_regs *regs)
-{
-	ri->ret_addr = (kprobe_opcode_t *)regs->regs[1];
-	ri->fp = NULL;
-
-	/* Replace the return addr with trampoline addr */
-	regs->regs[1] = (unsigned long)&__kretprobe_trampoline;
-}
-NOKPROBE_SYMBOL(arch_prepare_kretprobe);
-
 int arch_trampoline_kprobe(struct kprobe *p)
 {
 	return 0;
diff --git a/arch/loongarch/kernel/rethook.c b/arch/loongarch/kernel/rethook.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.c
@@ -0,0 +1,28 @@
+// SPDX-License-Identifier: GPL-2.0-only
+/*
+ * Generic return hook for LoongArch.
+ */
+
+#include <linux/kprobes.h>
+#include <linux/rethook.h>
+#include "rethook.h"
+
+/* This is called from arch_rethook_trampoline() */
+unsigned long __used arch_rethook_trampoline_callback(struct pt_regs *regs)
+{
+	return rethook_trampoline_handler(regs, 0);
+}
+NOKPROBE_SYMBOL(arch_rethook_trampoline_callback);
+
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount)
+{
+	rhn->frame = 0;
+	rhn->ret_addr = regs->regs[1];
+
+	/* replace return addr with trampoline */
+	regs->regs[1] = (unsigned long)arch_rethook_trampoline;
+}
+NOKPROBE_SYMBOL(arch_rethook_prepare);
+
+/* ASM function that handles the rethook must not be probed itself */
+NOKPROBE_SYMBOL(arch_rethook_trampoline);
diff --git a/arch/loongarch/kernel/rethook.h b/arch/loongarch/kernel/rethook.h
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/rethook.h
@@ -0,0 +1,8 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+#ifndef __LOONGARCH_RETHOOK_H
+#define __LOONGARCH_RETHOOK_H
+
+unsigned long arch_rethook_trampoline_callback(struct pt_regs *regs);
+void arch_rethook_prepare(struct rethook_node *rhn, struct pt_regs *regs, bool mcount);
+
+#endif
diff --git a/arch/loongarch/kernel/kprobes_trampoline.S b/arch/loongarch/kernel/rethook_trampoline.S
similarity index 93%
rename from arch/loongarch/kernel/kprobes_trampoline.S
rename to arch/loongarch/kernel/rethook_trampoline.S
--- a/arch/loongarch/kernel/kprobes_trampoline.S
+++ b/arch/loongarch/kernel/rethook_trampoline.S
@@ -75,13 +75,13 @@
 	csrxchg t0, t1, LOONGARCH_CSR_CRMD
 	.endm
 
-SYM_CODE_START(__kretprobe_trampoline)
+SYM_CODE_START(arch_rethook_trampoline)
 	addi.d	sp, sp, -PT_SIZE
 	save_all_base_regs
 
 	addi.d	t0, sp, PT_SIZE
 	LONG_S	t0, sp, PT_R3
 
 	move a0, sp /* pt_regs */
 
-	bl trampoline_probe_handler
+	bl arch_rethook_trampoline_callback
 
 	/* use the result as the return-address */
 	move ra, a0
@@ -90,4 +90,4 @@ SYM_CODE_START(__kretprobe_trampoline)
 	addi.d	sp, sp, PT_SIZE
 
 	jr ra
-SYM_CODE_END(__kretprobe_trampoline)
+SYM_CODE_END(arch_rethook_trampoline)
```

## A029

### 真实补丁T

```diff
commit f02644e32c9e4bd1a9b286dc0b84f9cbe294f4e2
Subject: LoongArch: Add jump-label implementation


diff --git a/Documentation/features/core/jump-labels/arch-support.txt b/Documentation/features/core/jump-labels/arch-support.txt
index 2328eada3a49..94d9dece580f 100644
--- a/Documentation/features/core/jump-labels/arch-support.txt
+++ b/Documentation/features/core/jump-labels/arch-support.txt
@@ -13,7 +13,7 @@
     |        csky: |  ok  |
     |     hexagon: | TODO |
     |        ia64: | TODO |
-    |   loongarch: | TODO |
+    |   loongarch: |  ok  |
     |        m68k: | TODO |
     |  microblaze: | TODO |
     |        mips: |  ok  |
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 8c7b67eca838..64cdc6802295 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -87,6 +87,8 @@ config LOONGARCH
 	select GPIOLIB
 	select HAS_IOPORT
 	select HAVE_ARCH_AUDITSYSCALL
+	select HAVE_ARCH_JUMP_LABEL
+	select HAVE_ARCH_JUMP_LABEL_RELATIVE
 	select HAVE_ARCH_MMAP_RND_BITS if MMU
 	select HAVE_ARCH_SECCOMP_FILTER
 	select HAVE_ARCH_TRACEHOOK
diff --git a/arch/loongarch/include/asm/jump_label.h b/arch/loongarch/include/asm/jump_label.h
new file mode 100644
index 000000000000..3cea299a5ef5
--- /dev/null
+++ b/arch/loongarch/include/asm/jump_label.h
@@ -0,0 +1,50 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/include/asm/jump_label.h
+ */
+#ifndef __ASM_JUMP_LABEL_H
+#define __ASM_JUMP_LABEL_H
+
+#ifndef __ASSEMBLY__
+
+#include <linux/types.h>
+
+#define JUMP_LABEL_NOP_SIZE	4
+
+#define JUMP_TABLE_ENTRY				\
+	 ".pushsection	__jump_table, \"aw\"	\n\t"	\
+	 ".align	3			\n\t"	\
+	 ".long		1b - ., %l[l_yes] - .	\n\t"	\
+	 ".quad		%0 - .			\n\t"	\
+	 ".popsection				\n\t"
+
+static __always_inline bool arch_static_branch(struct static_key * const key, const bool branch)
+{
+	asm_volatile_goto(
+		"1:	nop			\n\t"
+		JUMP_TABLE_ENTRY
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+static __always_inline bool arch_static_branch_jump(struct static_key * const key, const bool branch)
+{
+	asm_volatile_goto(
+		"1:	b	%l[l_yes]	\n\t"
+		JUMP_TABLE_ENTRY
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+#endif  /* __ASSEMBLY__ */
+#endif	/* __ASM_JUMP_LABEL_H */
diff --git a/arch/loongarch/kernel/Makefile b/arch/loongarch/kernel/Makefile
index 9a72d91cd104..64ea76f60e2c 100644
--- a/arch/loongarch/kernel/Makefile
+++ b/arch/loongarch/kernel/Makefile
@@ -54,4 +54,6 @@ obj-$(CONFIG_HAVE_HW_BREAKPOINT)	+= hw_breakpoint.o
 
 obj-$(CONFIG_KPROBES)		+= kprobes.o kprobes_trampoline.o
 
+obj-$(CONFIG_JUMP_LABEL)	+= jump_label.o
+
 CPPFLAGS_vmlinux.lds		:= $(KBUILD_CFLAGS)
diff --git a/arch/loongarch/kernel/jump_label.c b/arch/loongarch/kernel/jump_label.c
new file mode 100644
index 000000000000..31891214b767
--- /dev/null
+++ b/arch/loongarch/kernel/jump_label.c
@@ -0,0 +1,22 @@
+// SPDX-License-Identifier: GPL-2.0-only
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/kernel/jump_label.c
+ */
+#include <linux/kernel.h>
+#include <linux/jump_label.h>
+#include <asm/inst.h>
+
+void arch_jump_label_transform(struct jump_entry *entry, enum jump_label_type type)
+{
+	u32 insn;
+	void *addr = (void *)jump_entry_code(entry);
+
+	if (type == JUMP_LABEL_JMP)
+		insn = larch_insn_gen_b(jump_entry_code(entry), jump_entry_target(entry));
+	else
+		insn = larch_insn_gen_nop();
+
+	larch_insn_patch_text(addr, insn);
+}
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -87,6 +87,8 @@ config LOONGARCH
 	select HAS_IOPORT
 	select HAVE_ARCH_AUDITSYSCALL
+	select HAVE_ARCH_JUMP_LABEL
+	select HAVE_ARCH_JUMP_LABEL_RELATIVE
 	select HAVE_ARCH_MMAP_RND_BITS if MMU
 	select HAVE_ARCH_SECCOMP_FILTER
 	select HAVE_ARCH_TRACEHOOK
diff --git a/arch/loongarch/include/asm/jump_label.h b/arch/loongarch/include/asm/jump_label.h
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/include/asm/jump_label.h
@@ -0,0 +1,50 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/include/asm/jump_label.h
+ */
+#ifndef __ASM_JUMP_LABEL_H
+#define __ASM_JUMP_LABEL_H
+
+#ifndef __ASSEMBLY__
+
+#include <linux/types.h>
+
+#define JUMP_LABEL_NOP_SIZE	4
+
+#define JUMP_TABLE_ENTRY				\
+	 ".pushsection	__jump_table, \"aw\"	\n\t"	\
+	 ".align	3			\n\t"	\
+	 ".long		1b - ., %l[l_yes] - .	\n\t"	\
+	 ".quad		%0 - .			\n\t"	\
+	 ".popsection				\n\t"
+
+static __always_inline bool arch_static_branch(struct static_key *key, bool branch)
+{
+	asm goto(
+		"1:	nop			\n\t"
+		JUMP_TABLE_ENTRY
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+static __always_inline bool arch_static_branch_jump(struct static_key *key, bool branch)
+{
+	asm goto(
+		"1:	b	%l[l_yes]	\n\t"
+		JUMP_TABLE_ENTRY
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+#endif /* __ASSEMBLY__ */
+#endif /* __ASM_JUMP_LABEL_H */
diff --git a/arch/loongarch/kernel/jump_label.c b/arch/loongarch/kernel/jump_label.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/jump_label.c
@@ -0,0 +1,26 @@
+// SPDX-License-Identifier: GPL-2.0-only
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/kernel/jump_label.c
+ */
+#include <linux/kernel.h>
+#include <linux/jump_label.h>
+#include <asm/inst.h>
+
+void arch_jump_label_transform(struct jump_entry *entry, enum jump_label_type type)
+{
+	u32 insn;
+	void *addr = (void *)jump_entry_code(entry);
+
+	if (type == JUMP_LABEL_JMP)
+		insn = larch_insn_gen_b(jump_entry_code(entry), jump_entry_target(entry));
+	else
+		insn = larch_insn_gen_nop();
+
+	larch_insn_patch_text(addr, insn);
+}
diff --git a/arch/loongarch/kernel/Makefile b/arch/loongarch/kernel/Makefile
--- a/arch/loongarch/kernel/Makefile
+++ b/arch/loongarch/kernel/Makefile
@@ -58,4 +58,6 @@ obj-$(CONFIG_HAVE_HW_BREAKPOINT)	+= hw_breakpoint.o
 
 obj-$(CONFIG_KPROBES)		+= kprobes.o kprobes_trampoline.o
 
+obj-$(CONFIG_JUMP_LABEL)	+= jump_label.o
+
 CPPFLAGS_vmlinux.lds		:= $(KBUILD_CFLAGS)
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -96,6 +96,8 @@ config LOONGARCH
 	select GPIOLIB
 	select HAS_IOPORT
 	select HAVE_ARCH_AUDITSYSCALL
+	select HAVE_ARCH_JUMP_LABEL
+	select HAVE_ARCH_JUMP_LABEL_RELATIVE
 	select HAVE_ARCH_MMAP_RND_BITS if MMU
 	select HAVE_ARCH_SECCOMP_FILTER
 	select HAVE_ARCH_TRACEHOOK
diff --git a/arch/loongarch/include/asm/jump_label.h b/arch/loongarch/include/asm/jump_label.h
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/include/asm/jump_label.h
@@ -0,0 +1,50 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/include/asm/jump_label.h
+ */
+#ifndef __ASM_JUMP_LABEL_H
+#define __ASM_JUMP_LABEL_H
+
+#ifndef __ASSEMBLY__
+
+#include <linux/types.h>
+
+#define JUMP_LABEL_NOP_SIZE	4
+
+#define JUMP_TABLE_ENTRY(key, label)			\
+	".pushsection	__jump_table, \"aw\"	\n\t"	\
+	".align		3			\n\t"	\
+	".long		1b - ., " label " - .	\n\t"	\
+	".dword		" key " - .		\n\t"	\
+	".popsection				\n\t"
+
+static __always_inline bool arch_static_branch(struct static_key * const key, const bool branch)
+{
+	asm goto(
+		"1:	nop			\n\t"
+		JUMP_TABLE_ENTRY("%0", "%l[l_yes]")
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+static __always_inline bool arch_static_branch_jump(struct static_key * const key, const bool branch)
+{
+	asm goto(
+		"1:	b	%l[l_yes]	\n\t"
+		JUMP_TABLE_ENTRY("%0", "%l[l_yes]")
+		:  :  "i"(&((char *)key)[branch]) :  : l_yes);
+
+	return false;
+
+l_yes:
+	return true;
+}
+
+#endif /* __ASSEMBLY__ */
+#endif /* __ASM_JUMP_LABEL_H */
diff --git a/arch/loongarch/kernel/jump_label.c b/arch/loongarch/kernel/jump_label.c
new file mode 100644
--- /dev/null
+++ b/arch/loongarch/kernel/jump_label.c
@@ -0,0 +1,25 @@
+// SPDX-License-Identifier: GPL-2.0-only
+/*
+ * Copyright (C) 2023 Loongson Technology Corporation Limited
+ *
+ * Based on arch/arm64/kernel/jump_label.c
+ */
+#include <linux/kernel.h>
+#include <linux/jump_label.h>
+#include <asm/inst.h>
+
+void arch_jump_label_transform(struct jump_entry *entry, enum jump_label_type type)
+{
+	u32 *addr = (u32 *)jump_entry_code(entry);
+	union loongarch_instruction insn;
+
+	if (type == JUMP_LABEL_JMP) {
+		long offset = jump_entry_target(entry) - jump_entry_code(entry);
+
+		insn.reg0i26_format.opcode = b_op;
+		insn.reg0i26_format.immediate_l = (offset >> 2) & 0xffff;
+		insn.reg0i26_format.immediate_h = (offset >> 18) & 0x3ff;
+	} else {
+		insn.word = INSN_NOP;
+	}
+
+	larch_insn_patch_text(addr, insn.word);
+}
diff --git a/arch/loongarch/kernel/Makefile b/arch/loongarch/kernel/Makefile
--- a/arch/loongarch/kernel/Makefile
+++ b/arch/loongarch/kernel/Makefile
@@ -57,6 +57,8 @@ obj-$(CONFIG_UNWINDER_PROLOGUE) += unwind_prologue.o
 obj-$(CONFIG_PERF_EVENTS)	+= perf_event.o perf_regs.o
 obj-$(CONFIG_HAVE_HW_BREAKPOINT)	+= hw_breakpoint.o
 
+obj-$(CONFIG_JUMP_LABEL)	+= jump_label.o
+
 obj-$(CONFIG_KPROBES)		+= kprobes.o kprobes_trampoline.o
 
 CPPFLAGS_vmlinux.lds		:= $(KBUILD_CFLAGS)
```

## A039

### 真实补丁T

```diff
commit 80c7889de7a8246e44a9632a2b7d15b41ab3fe41
Subject: LoongArch: Support PREEMPT_DYNAMIC with static keys


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index e14396a2ddcb..86fdc8c55608 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -135,6 +135,7 @@ config LOONGARCH
 	select HAVE_PERF_EVENTS
 	select HAVE_PERF_REGS
 	select HAVE_PERF_USER_STACK_DUMP
+	select HAVE_PREEMPT_DYNAMIC_KEY
 	select HAVE_REGS_AND_STACK_ACCESS_API
 	select HAVE_RETHOOK
 	select HAVE_RSEQ
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -134,6 +134,7 @@ config LOONGARCH
 	select HAVE_PERF_EVENTS
 	select HAVE_PERF_REGS
 	select HAVE_PERF_USER_STACK_DUMP
+	select HAVE_PREEMPT_DYNAMIC_KEY
 	select HAVE_REGS_AND_STACK_ACCESS_API
 	select HAVE_RETHOOK
 	select HAVE_RSEQ
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -141,6 +141,7 @@ config LOONGARCH
 	select HAVE_PERF_EVENTS
 	select HAVE_PERF_REGS
 	select HAVE_PERF_USER_STACK_DUMP
+	select HAVE_PREEMPT_DYNAMIC_KEY
 	select HAVE_REGS_AND_STACK_ACCESS_API
 	select HAVE_RETHOOK
 	select HAVE_RSEQ
```

## A059

### 真实补丁T

```diff
commit e8dd556c74325f29597665c2c557a8ea699a0686
Subject: LoongArch: Enable generic CPU vulnerabilites support


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 34531dc8a61f..b9d3c98efe18 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -82,6 +82,7 @@ config LOONGARCH
 	select GENERIC_CMOS_UPDATE
 	select GENERIC_CPU_AUTOPROBE
 	select GENERIC_CPU_DEVICES
+	select GENERIC_CPU_VULNERABILITIES
 	select GENERIC_ENTRY
 	select GENERIC_GETTIMEOFDAY
 	select GENERIC_IOREMAP if !ARCH_IOREMAP
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -80,6 +80,7 @@ config LOONGARCH
 	select GENERIC_CMOS_UPDATE
 	select GENERIC_CPU_AUTOPROBE
 	select GENERIC_CPU_DEVICES
+	select GENERIC_CPU_VULNERABILITIES
 	select GENERIC_ENTRY
 	select GENERIC_GETTIMEOFDAY
 	select GENERIC_IOREMAP if !ARCH_IOREMAP
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -87,6 +87,7 @@ config LOONGARCH
 	select GENERIC_CMOS_UPDATE
 	select GENERIC_CPU_AUTOPROBE
 	select GENERIC_CPU_DEVICES
+	select GENERIC_CPU_VULNERABILITIES
 	select GENERIC_ENTRY
 	select GENERIC_GETTIMEOFDAY
 	select GENERIC_IOREMAP if !ARCH_IOREMAP
```

## A060

### 真实补丁T

```diff
commit f93f67d06b1023313ef1662eac490e29c025c030
Subject: LoongArch: Improve hardware page table walker


diff --git a/arch/loongarch/include/asm/atomic.h b/arch/loongarch/include/asm/atomic.h
index 99af8b3160a8..c86f0ab922ec 100644
--- a/arch/loongarch/include/asm/atomic.h
+++ b/arch/loongarch/include/asm/atomic.h
@@ -15,6 +15,7 @@
 #define __LL		"ll.w	"
 #define __SC		"sc.w	"
 #define __AMADD		"amadd.w	"
+#define __AMOR		"amor.w		"
 #define __AMAND_DB	"amand_db.w	"
 #define __AMOR_DB	"amor_db.w	"
 #define __AMXOR_DB	"amxor_db.w	"
@@ -22,6 +23,7 @@
 #define __LL		"ll.d	"
 #define __SC		"sc.d	"
 #define __AMADD		"amadd.d	"
+#define __AMOR		"amor.d		"
 #define __AMAND_DB	"amand_db.d	"
 #define __AMOR_DB	"amor_db.d	"
 #define __AMXOR_DB	"amxor_db.d	"
diff --git a/arch/loongarch/include/asm/mmu_context.h b/arch/loongarch/include/asm/mmu_context.h
index 9f97c3453b9c..304363bd3935 100644
--- a/arch/loongarch/include/asm/mmu_context.h
+++ b/arch/loongarch/include/asm/mmu_context.h
@@ -49,12 +49,12 @@ static inline void enter_lazy_tlb(struct mm_struct *mm, struct task_struct *tsk)
 
 /* Normal, classic get_new_mmu_context */
 static inline void
-get_new_mmu_context(struct mm_struct *mm, unsigned long cpu)
+get_new_mmu_context(struct mm_struct *mm, unsigned long cpu, bool *need_flush)
 {
 	u64 asid = asid_cache(cpu);
 
 	if (!((++asid) & cpu_asid_mask(&cpu_data[cpu])))
-		local_flush_tlb_user();	/* start new asid cycle */
+		*need_flush = true;	/* start new asid cycle */
 
 	cpu_context(cpu, mm) = asid_cache(cpu) = asid;
 }
@@ -74,21 +74,34 @@ init_new_context(struct task_struct *tsk, struct mm_struct *mm)
 	return 0;
 }
 
+static inline void atomic_update_pgd_asid(unsigned long asid, unsigned long pgdl)
+{
+	__asm__ __volatile__(
+	"csrwr %[pgdl_val], %[pgdl_reg] \n\t"
+	"csrwr %[asid_val], %[asid_reg] \n\t"
+	: [asid_val] "+r" (asid), [pgdl_val] "+r" (pgdl)
+	: [asid_reg] "i" (LOONGARCH_CSR_ASID), [pgdl_reg] "i" (LOONGARCH_CSR_PGDL)
+	: "memory"
+	);
+}
+
 static inline void switch_mm_irqs_off(struct mm_struct *prev, struct mm_struct *next,
 				      struct task_struct *tsk)
 {
+	bool need_flush = false;
 	unsigned int cpu = smp_processor_id();
 
 	/* Check if our ASID is of an older version and thus invalid */
 	if (!asid_valid(next, cpu))
-		get_new_mmu_context(next, cpu);
-
-	write_csr_asid(cpu_asid(cpu, next));
+		get_new_mmu_context(next, cpu, &need_flush);
 
 	if (next != &init_mm)
-		csr_write64((unsigned long)next->pgd, LOONGARCH_CSR_PGDL);
+		atomic_update_pgd_asid(cpu_asid(cpu, next), (unsigned long)next->pgd);
 	else
-		csr_write64((unsigned long)invalid_pg_dir, LOONGARCH_CSR_PGDL);
+		atomic_update_pgd_asid(cpu_asid(cpu, next), (unsigned long)invalid_pg_dir);
+
+	if (need_flush)
+		local_flush_tlb_user(); /* Flush tlb after update ASID */
 
 	/*
 	 * Mark current->active_mm as not "active" anymore.
@@ -135,9 +148,15 @@ drop_mmu_context(struct mm_struct *mm, unsigned int cpu)
 	asid = read_csr_asid() & cpu_asid_mask(&current_cpu_data);
 
 	if (asid == cpu_asid(cpu, mm)) {
+		bool need_flush = false;
+
 		if (!current->mm || (current->mm == mm)) {
-			get_new_mmu_context(mm, cpu);
+			get_new_mmu_context(mm, cpu, &need_flush);
+
 			write_csr_asid(cpu_asid(cpu, mm));
+			if (need_flush)
+				local_flush_tlb_user(); /* Flush tlb after update ASID */
+
 			goto out;
 		}
 	}
diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
index 85431f20a14d..9965f52ef65b 100644
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -331,29 +331,23 @@ static inline void set_pte(pte_t *ptep, pte_t pteval)
 		 * Make sure the buddy is global too (if it's !none,
 		 * it better already be global)
 		 */
+		if (pte_none(ptep_get(buddy))) {
 #ifdef CONFIG_SMP
-		/*
-		 * For SMP, multiple CPUs can race, so we need to do
-		 * this atomically.
-		 */
-		unsigned long page_global = _PAGE_GLOBAL;
-		unsigned long tmp;
-
-		__asm__ __volatile__ (
-		"1:"	__LL	"%[tmp], %[buddy]		\n"
-		"	bnez	%[tmp], 2f			\n"
-		"	 or	%[tmp], %[tmp], %[global]	\n"
-			__SC	"%[tmp], %[buddy]		\n"
-		"	beqz	%[tmp], 1b			\n"
-		"	nop					\n"
-		"2:						\n"
-		__WEAK_LLSC_MB
-		: [buddy] "+m" (buddy->pte), [tmp] "=&r" (tmp)
-		: [global] "r" (page_global));
+			/*
+			 * For SMP, multiple CPUs can race, so we need
+			 * to do this atomically.
+			 */
+			__asm__ __volatile__(
+			__AMOR "$zero, %[global], %[buddy] \n"
+			: [buddy] "+ZB" (buddy->pte)
+			: [global] "r" (_PAGE_GLOBAL)
+			: "memory");
+
+			DBAR(0b11000); /* o_wrw = 0b11000 */
 #else /* !CONFIG_SMP */
-		if (pte_none(ptep_get(buddy)))
 			WRITE_ONCE(*buddy, __pte(pte_val(ptep_get(buddy)) | _PAGE_GLOBAL));
 #endif /* CONFIG_SMP */
+		}
 	}
 }
 
diff --git a/arch/loongarch/mm/fault.c b/arch/loongarch/mm/fault.c
index 97b40defde06..deefd9617d00 100644
--- a/arch/loongarch/mm/fault.c
+++ b/arch/loongarch/mm/fault.c
@@ -31,11 +31,52 @@
 
 int show_unhandled_signals = 1;
 
+static int __kprobes spurious_fault(unsigned long write, unsigned long address)
+{
+	pgd_t *pgd;
+	p4d_t *p4d;
+	pud_t *pud;
+	pmd_t *pmd;
+	pte_t *pte;
+
+	if (!(address & __UA_LIMIT))
+		return 0;
+
+	pgd = pgd_offset_k(address);
+	if (!pgd_present(pgdp_get(pgd)))
+		return 0;
+
+	p4d = p4d_offset(pgd, address);
+	if (!p4d_present(p4dp_get(p4d)))
+		return 0;
+
+	pud = pud_offset(p4d, address);
+	if (!pud_present(pudp_get(pud)))
+		return 0;
+
+	pmd = pmd_offset(pud, address);
+	if (!pmd_present(pmdp_get(pmd)))
+		return 0;
+
+	if (pmd_leaf(*pmd)) {
+		return write ? pmd_write(pmdp_get(pmd)) : 1;
+	} else {
+		pte = pte_offset_kernel(pmd, address);
+		if (!pte_present(ptep_get(pte)))
+			return 0;
+
+		return write ? pte_write(ptep_get(pte)) : 1;
+	}
+}
+
 static void __kprobes no_context(struct pt_regs *regs,
 			unsigned long write, unsigned long address)
 {
 	const int field = sizeof(unsigned long) * 2;
 
+	if (spurious_fault(write, address))
+		return;
+
 	/* Are we prepared to handle this kernel fault?	 */
 	if (fixup_exception(regs))
 		return;
```

### X

```diff
diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -12,6 +12,7 @@
 #include <linux/compiler.h>
 #include <asm/addrspace.h>
+#include <asm/barrier.h>
 #include <asm/page.h>
 #include <asm/pgtable-bits.h>
 
@@ -203,6 +204,13 @@ static inline pud_t *pud_pgtable(pud_t pud)
 static inline void set_pud(pud_t *pud, pud_t pudval)
 {
 	WRITE_ONCE(*pud, pudval);
+
+	/*
+	 * A valid block mapping must be visible to the page table walker
+	 * before any subsequent access through it.
+	 */
+	if ((pud_val(pudval) & _PAGE_HUGE) && (pud_val(pudval) & _PAGE_PRESENT))
+		__sync();
 }
 
 static inline void pud_clear(pud_t *pudp)
@@ -251,6 +259,13 @@ static inline int pmd_present(pmd_t pmd)
 static inline void set_pmd(pmd_t *pmd, pmd_t pmdval)
 {
 	WRITE_ONCE(*pmd, pmdval);
+
+	/*
+	 * A valid block mapping must be visible to the page table walker
+	 * before any subsequent access through it.
+	 */
+	if ((pmd_val(pmdval) & _PAGE_HUGE) && (pmd_val(pmdval) & _PAGE_PRESENT))
+		__sync();
 }
 
 static inline void pmd_clear(pmd_t *pmdp)
@@ -377,6 +392,15 @@ static inline void set_pte(pte_t *ptep, pte_t pteval)
 		if (pte_none(ptep_get(buddy)))
 			WRITE_ONCE(*buddy, __pte(pte_val(ptep_get(buddy)) | _PAGE_GLOBAL));
 #endif /* CONFIG_SMP */
 	}
+
+	/*
+	 * Only for valid kernel (global) mappings; invalid PTEs are covered
+	 * by TLB maintenance and user mappings by the fault/update_mmu_cache
+	 * path (a spurious fault just re-executes the instruction).
+	 */
+	if ((pte_val(pteval) & (_PAGE_PRESENT | _PAGE_GLOBAL)) ==
+	    (_PAGE_PRESENT | _PAGE_GLOBAL))
+		__sync();
 }
 
 static inline void pte_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -11,6 +11,7 @@
 #define _ASM_PGTABLE_H
 
 #include <linux/compiler.h>
+#include <asm/barrier.h>
 #include <asm/addrspace.h>
 #include <asm/page.h>
 #include <asm/pgtable-bits.h>
@@ -190,6 +191,8 @@ static inline void set_pud(pud_t *pud, pud_t pudval)
 {
 	WRITE_ONCE(*pud, pudval);
+	if (pud_val(pudval) & _PAGE_HUGE)
+		mb();
 }
 
 static inline void pud_clear(pud_t *pudp)
@@ -246,6 +249,8 @@ static inline void set_pmd(pmd_t *pmd, pmd_t pmdval)
 {
 	WRITE_ONCE(*pmd, pmdval);
+	if (pmd_val(pmdval) & _PAGE_HUGE)
+		mb();
 }
 
 static inline void pmd_clear(pmd_t *pmdp)
@@ -386,6 +391,14 @@ static inline void set_pte(pte_t *ptep, pte_t pteval)
 			WRITE_ONCE(*buddy, __pte(pte_val(ptep_get(buddy)) | _PAGE_GLOBAL));
 #endif /* CONFIG_SMP */
 	}
+
+	/*
+	 * Valid kernel mapping: make sure the page table write is visible
+	 * to the page table walker before subsequent accesses through the
+	 * new virtual address. Invalid PTEs are covered by TLB flushing and
+	 * user mappings by update_mmu_cache().
+	 */
+	if ((pte_val(pteval) & (_PAGE_GLOBAL | _PAGE_VALID)) == (_PAGE_GLOBAL | _PAGE_VALID))
+		mb();
 }
 
 static inline void pte_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
```

## A063

### 真实补丁T

```diff
commit 73adbd92f3223dc0c3506822b71c6b259d5d537b
Subject: LoongArch: KVM: Mark hrtimer to expire in hard interrupt context


diff --git a/arch/loongarch/kvm/timer.c b/arch/loongarch/kvm/timer.c
index 74a4b5c272d6..32dc213374be 100644
--- a/arch/loongarch/kvm/timer.c
+++ b/arch/loongarch/kvm/timer.c
@@ -161,10 +161,11 @@ static void _kvm_save_timer(struct kvm_vcpu *vcpu)
 	if (kvm_vcpu_is_blocking(vcpu)) {
 
 		/*
-		 * HRTIMER_MODE_PINNED is suggested since vcpu may run in
-		 * the same physical cpu in next time
+		 * HRTIMER_MODE_PINNED_HARD is suggested since vcpu may run in
+		 * the same physical cpu in next time, and the timer should run
+		 * in hardirq context even in the PREEMPT_RT case.
 		 */
-		hrtimer_start(&vcpu->arch.swtimer, expire, HRTIMER_MODE_ABS_PINNED);
+		hrtimer_start(&vcpu->arch.swtimer, expire, HRTIMER_MODE_ABS_PINNED_HARD);
 	}
 }
 
diff --git a/arch/loongarch/kvm/vcpu.c b/arch/loongarch/kvm/vcpu.c
index 0697b1064251..174734a23d0a 100644
--- a/arch/loongarch/kvm/vcpu.c
+++ b/arch/loongarch/kvm/vcpu.c
@@ -1457,7 +1457,7 @@ int kvm_arch_vcpu_create(struct kvm_vcpu *vcpu)
 	vcpu->arch.vpid = 0;
 	vcpu->arch.flush_gpa = INVALID_GPA;
 
-	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED);
+	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED_HARD);
 	vcpu->arch.swtimer.function = kvm_swtimer_wakeup;
 
 	vcpu->arch.handle_exit = kvm_handle_exit;
```

### X

```diff
diff --git a/arch/loongarch/kvm/timer.c b/arch/loongarch/kvm/timer.c
--- a/arch/loongarch/kvm/timer.c
+++ b/arch/loongarch/kvm/timer.c
@@ -1,1 +1,1 @@
-	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED);
+	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED_HARD);
```

### Y

```diff
diff --git a/arch/loongarch/kvm/vcpu.c b/arch/loongarch/kvm/vcpu.c
--- a/arch/loongarch/kvm/vcpu.c
+++ b/arch/loongarch/kvm/vcpu.c
@@ -1,1 +1,1 @@
-	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED);
+	hrtimer_init(&vcpu->arch.swtimer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED_HARD);
diff --git a/arch/loongarch/kvm/timer.c b/arch/loongarch/kvm/timer.c
--- a/arch/loongarch/kvm/timer.c
+++ b/arch/loongarch/kvm/timer.c
@@ -1,1 +1,1 @@
-	hrtimer_start(&vcpu->arch.swtimer, expire, HRTIMER_MODE_ABS_PINNED);
+	hrtimer_start(&vcpu->arch.swtimer, expire, HRTIMER_MODE_ABS_PINNED_HARD);
```

## A073

### 真实补丁T

```diff
commit c9117434c8f7523f0b77db4c5766f5011cc94677
Subject: LoongArch: Use polling play_dead() when resuming from hibernation


diff --git a/arch/loongarch/kernel/smp.c b/arch/loongarch/kernel/smp.c
index fbf747447f13..4b24589c0b56 100644
--- a/arch/loongarch/kernel/smp.c
+++ b/arch/loongarch/kernel/smp.c
@@ -19,6 +19,7 @@
 #include <linux/smp.h>
 #include <linux/threads.h>
 #include <linux/export.h>
+#include <linux/suspend.h>
 #include <linux/syscore_ops.h>
 #include <linux/time.h>
 #include <linux/tracepoint.h>
@@ -423,7 +424,7 @@ void loongson_cpu_die(unsigned int cpu)
 	mb();
 }
 
-void __noreturn arch_cpu_idle_dead(void)
+static void __noreturn idle_play_dead(void)
 {
 	register uint64_t addr;
 	register void (*init_fn)(void);
@@ -447,6 +448,50 @@ void __noreturn arch_cpu_idle_dead(void)
 	BUG();
 }
 
+#ifdef CONFIG_HIBERNATION
+static void __noreturn poll_play_dead(void)
+{
+	register uint64_t addr;
+	register void (*init_fn)(void);
+
+	idle_task_exit();
+	__this_cpu_write(cpu_state, CPU_DEAD);
+
+	__smp_mb();
+	do {
+		__asm__ __volatile__("nop\n\t");
+		addr = iocsr_read64(LOONGARCH_IOCSR_MBUF0);
+	} while (addr == 0);
+
+	init_fn = (void *)TO_CACHE(addr);
+	iocsr_write32(0xffffffff, LOONGARCH_IOCSR_IPI_CLEAR);
+
+	init_fn();
+	BUG();
+}
+#endif
+
+static void (*play_dead)(void) = idle_play_dead;
+
+void __noreturn arch_cpu_idle_dead(void)
+{
+	play_dead();
+	BUG(); /* play_dead() doesn't return */
+}
+
+#ifdef CONFIG_HIBERNATION
+int hibernate_resume_nonboot_cpu_disable(void)
+{
+	int ret;
+
+	play_dead = poll_play_dead;
+	ret = suspend_disable_secondary_cpus();
+	play_dead = idle_play_dead;
+
+	return ret;
+}
+#endif
+
 #endif
 
 /*
```

### X

```diff
（没有补丁）
```

### Y

```diff
（没有补丁）
```

## A077

### 真实补丁T

```diff
commit c271c86a4c72c771b313fd9c3b06db61ab8ab8bf
Subject: LoongArch: vDSO: Remove --hash-style=sysv


diff --git a/arch/loongarch/vdso/Makefile b/arch/loongarch/vdso/Makefile
index fdde1bcd4e26..cf6c41054396 100644
--- a/arch/loongarch/vdso/Makefile
+++ b/arch/loongarch/vdso/Makefile
@@ -36,8 +36,7 @@ endif
 
 # VDSO linker flags.
 ldflags-y := -Bsymbolic --no-undefined -soname=linux-vdso.so.1 \
-	$(filter -E%,$(KBUILD_CFLAGS)) -nostdlib -shared \
-	--hash-style=sysv --build-id -T
+	$(filter -E%,$(KBUILD_CFLAGS)) -nostdlib -shared --build-id -T
 
 #
 # Shared build commands.
```

### X

```diff
diff --git a/arch/loongarch/vdso/Makefile b/arch/loongarch/vdso/Makefile
--- a/arch/loongarch/vdso/Makefile
+++ b/arch/loongarch/vdso/Makefile
@@ -1,1 +1,1 @@
-ldflags-y := -Bsymbolic --no-undefined -soname=linux-vdso.so.1 --hash-style=sysv \
+ldflags-y := -Bsymbolic --no-undefined -soname=linux-vdso.so.1 \
```

### Y

```diff
（没有补丁）
```

## A082

### 真实补丁T

```diff
commit 2468b0e3d5659dfde77f081f266e1111a981efb8
Subject: LoongArch: Prevent cond_resched() occurring within kernel-fpu


diff --git a/arch/loongarch/kernel/kfpu.c b/arch/loongarch/kernel/kfpu.c
index ec5b28e570c9..4c476904227f 100644
--- a/arch/loongarch/kernel/kfpu.c
+++ b/arch/loongarch/kernel/kfpu.c
@@ -18,11 +18,28 @@ static unsigned int euen_mask = CSR_EUEN_FPEN;
 static DEFINE_PER_CPU(bool, in_kernel_fpu);
 static DEFINE_PER_CPU(unsigned int, euen_current);
 
+static inline void fpregs_lock(void)
+{
+	if (IS_ENABLED(CONFIG_PREEMPT_RT))
+		preempt_disable();
+	else
+		local_bh_disable();
+}
+
+static inline void fpregs_unlock(void)
+{
+	if (IS_ENABLED(CONFIG_PREEMPT_RT))
+		preempt_enable();
+	else
+		local_bh_enable();
+}
+
 void kernel_fpu_begin(void)
 {
 	unsigned int *euen_curr;
 
-	preempt_disable();
+	if (!irqs_disabled())
+		fpregs_lock();
 
 	WARN_ON(this_cpu_read(in_kernel_fpu));
 
@@ -73,7 +90,8 @@ void kernel_fpu_end(void)
 
 	this_cpu_write(in_kernel_fpu, false);
 
-	preempt_enable();
+	if (!irqs_disabled())
+		fpregs_unlock();
 }
 EXPORT_SYMBOL_GPL(kernel_fpu_end);
```

### X

```diff
diff --git a/arch/loongarch/kernel/kfpu.c b/arch/loongarch/kernel/kfpu.c
--- a/arch/loongarch/kernel/kfpu.c
+++ b/arch/loongarch/kernel/kfpu.c
@@ -18,18 +18,37 @@
 static DEFINE_PER_CPU(bool, in_kernel_fpu);
 static DEFINE_PER_CPU(unsigned int, euen_current);
 
+static inline void kfpu_lock(void)
+{
+	if (!irqs_disabled()) {
+		if (!IS_ENABLED(CONFIG_PREEMPT_RT))
+			local_bh_disable();
+		else
+			preempt_disable();
+	} else {
+		preempt_disable();
+	}
+}
+
+static inline void kfpu_unlock(void)
+{
+	if (!irqs_disabled()) {
+		if (!IS_ENABLED(CONFIG_PREEMPT_RT))
+			local_bh_enable();
+		else
+			preempt_enable();
+	} else {
+		preempt_enable();
+	}
+}
+
 void kernel_fpu_begin(void)
 {
 	unsigned int *euen_curr;
 
-	preempt_disable();
+	kfpu_lock();
 
 	WARN_ON(this_cpu_read(in_kernel_fpu));
 
 	this_cpu_write(in_kernel_fpu, true);
 	euen_curr = this_cpu_ptr(&euen_current);
 
 	*euen_curr = csr_xchg32(euen_mask, euen_mask, LOONGARCH_CSR_EUEN);
@@ -75,7 +94,7 @@
 
 	this_cpu_write(in_kernel_fpu, false);
 
-	preempt_enable();
+	kfpu_unlock();
 }
 EXPORT_SYMBOL_GPL(kernel_fpu_end);
```

### Y

```diff
diff --git a/arch/loongarch/kernel/kfpu.c b/arch/loongarch/kernel/kfpu.c
--- a/arch/loongarch/kernel/kfpu.c
+++ b/arch/loongarch/kernel/kfpu.c
@@ -4,6 +4,7 @@
  */
 
 #include <linux/cpu.h>
+#include <linux/bottom_half.h>
 #include <linux/init.h>
 #include <asm/fpu.h>
 #include <asm/smp.h>
@@ -11,18 +12,38 @@
 static unsigned int euen_mask = CSR_EUEN_FPEN;
 
 /*
- * The critical section between kernel_fpu_begin() and kernel_fpu_end()
- * is non-reentrant. It is the caller's responsibility to avoid reentrance.
- * See drivers/gpu/drm/amd/display/amdgpu_dm/dc_fpu.c as an example.
+ * The critical section between kernel_fpu_begin() and kernel_fpu_end()
+ * is non-reentrant. Softirq processing is disabled inside the section
+ * (unless hardirqs are already disabled), so it is usable in task and
+ * softirq context, but nested use is not supported.
  */
 static DEFINE_PER_CPU(bool, in_kernel_fpu);
 static DEFINE_PER_CPU(unsigned int, euen_current);
 
+static inline void kfpu_lock(void)
+{
+	if (irqs_disabled())
+		return;
+
+	if (IS_ENABLED(CONFIG_PREEMPT_RT))
+		preempt_disable();
+	else
+		local_bh_disable();
+}
+
+static inline void kfpu_unlock(void)
+{
+	if (irqs_disabled())
+		return;
+
+	if (IS_ENABLED(CONFIG_PREEMPT_RT))
+		preempt_enable();
+	else
+		local_bh_enable();
+}
+
 void kernel_fpu_begin(void)
 {
 	unsigned int *euen_curr;
 
-	preempt_disable();
+	kfpu_lock();
 
 	WARN_ON(this_cpu_read(in_kernel_fpu));
 
@@ -75,7 +96,7 @@ void kernel_fpu_end(void)
 
 	this_cpu_write(in_kernel_fpu, false);
 
-	preempt_enable();
+	kfpu_unlock();
 }
 EXPORT_SYMBOL_GPL(kernel_fpu_end);
```

## A087

### 真实补丁T

```diff
commit f7794a4d92ade518c813de69a01b27ca6d8d86f3
Subject: LoongArch: Increase COMMAND_LINE_SIZE up to 4096


diff --git a/arch/loongarch/include/uapi/asm/setup.h b/arch/loongarch/include/uapi/asm/setup.h
new file mode 100644
index 000000000000..d46363ce3e02
--- /dev/null
+++ b/arch/loongarch/include/uapi/asm/setup.h
@@ -0,0 +1,8 @@
+/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
+
+#ifndef _UAPI_ASM_LOONGARCH_SETUP_H
+#define _UAPI_ASM_LOONGARCH_SETUP_H
+
+#define COMMAND_LINE_SIZE	4096
+
+#endif /* _UAPI_ASM_LOONGARCH_SETUP_H */
```

### X

```diff
diff --git a/arch/loongarch/include/uapi/asm/setup.h b/arch/loongarch/include/uapi/asm/setup.h
--- a/arch/loongarch/include/uapi/asm/setup.h
+++ b/arch/loongarch/include/uapi/asm/setup.h
@@ -1,7 +1,7 @@
 /* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
 
 #ifndef _UAPI_ASM_LOONGARCH_SETUP_H
 #define _UAPI_ASM_LOONGARCH_SETUP_H
 
-#define COMMAND_LINE_SIZE	512
+#define COMMAND_LINE_SIZE	1024
 
 #endif /* _UAPI_ASM_LOONGARCH_SETUP_H */
```

### Y

```diff
diff --git a/arch/loongarch/include/uapi/asm/setup.h b/arch/loongarch/include/uapi/asm/setup.h
--- a/arch/loongarch/include/uapi/asm/setup.h
+++ b/arch/loongarch/include/uapi/asm/setup.h
@@ -1,8 +1,8 @@
 /* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */

 #ifndef _UAPI_ASM_LOONGARCH_SETUP_H
 #define _UAPI_ASM_LOONGARCH_SETUP_H

-#define COMMAND_LINE_SIZE	512
+#define COMMAND_LINE_SIZE	4096

 #endif /* _UAPI_ASM_LOONGARCH_SETUP_H */
```

## A090

### 真实补丁T

```diff
commit b0f50dc09bf008b2e581d5e6ad570d325725881c
Subject: LoongArch: BPF: Remove duplicated bpf_flush_icache()


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index 61135f8bcdad..bee2e8e340e7 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1718,7 +1718,6 @@ int arch_prepare_bpf_trampoline(struct bpf_tramp_image *im, void *ro_image,
 		goto out;
 	}
 
-	bpf_flush_icache(ro_image, ro_image_end);
 out:
 	kvfree(image);
 	return ret < 0 ? ret : size;
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,7 +1,6 @@
 	tmp = bpf_arch_text_copy(ro_image, image, size);
 	if (IS_ERR(tmp)) {
 		ret = PTR_ERR(tmp);
 		goto out;
 	}
 
-	bpf_flush_icache(ro_image, ro_image_end);
 out:
 	kvfree(image);
 	return ret < 0 ? ret : size;
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,7 +1,6 @@
 	tmp = bpf_arch_text_copy(ro_image, image, size);
 	if (IS_ERR(tmp)) {
 		ret = PTR_ERR(tmp);
 		goto out;
 	}
 
-	bpf_flush_icache(ro_image, ro_image_end);
 out:
 	kvfree(image);
 	return ret < 0 ? ret : size;
```

## A102

### 真实补丁T

```diff
commit e815df29b6a5e59293500085a010d5882374cb3e
Subject: LoongArch: BPF: Add fsession support for trampolines


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index a6c001583083..ec3c25b45882 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1737,6 +1737,29 @@ static int invoke_bpf_prog(struct jit_ctx *ctx, struct bpf_tramp_link *l,
 	return ret;
 }
 
+static int invoke_bpf(struct jit_ctx *ctx, struct bpf_tramp_links *tl,
+		      int args_off, int retval_off, int run_ctx_off,
+		      int func_meta_off, bool save_ret, u64 func_meta, int cookie_off)
+{
+	int i, cur_cookie = (cookie_off - args_off) / 8;
+
+	for (i = 0; i < tl->nr_links; i++) {
+		int err;
+
+		if (bpf_prog_calls_session_cookie(tl->links[i])) {
+			u64 meta = func_meta | ((u64)cur_cookie << BPF_TRAMP_COOKIE_INDEX_SHIFT);
+
+			emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, meta);
+			cur_cookie--;
+		}
+		err = invoke_bpf_prog(ctx, tl->links[i], args_off, retval_off, run_ctx_off, save_ret);
+		if (err)
+			return err;
+	}
+
+	return 0;
+}
+
 void *arch_alloc_bpf_trampoline(unsigned int size)
 {
 	return bpf_prog_pack_alloc(size, jit_fill_hole);
@@ -1788,8 +1811,10 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 					 void *func_addr, u32 flags)
 {
 	int i, ret, save_ret;
+	int cookie_cnt, cookie_off;
 	int stack_size, args_off, stk_args_off, nr_arg_slots = 0;
-	int retval_off, nregs_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	int retval_off, func_meta_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	unsigned long long func_meta;
 	bool is_struct_ops = flags & BPF_TRAMP_F_INDIRECT;
 	void *orig_call = func_addr;
 	struct bpf_tramp_links *fentry = &tlinks[BPF_TRAMP_FENTRY];
@@ -1813,10 +1838,14 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 	 *                   [ ...               ]
 	 * FP - args_off     [ arg reg1          ]
 	 *
-	 * FP - nregs_off    [ arg regs count    ]
+	 * FP - func_meta_off [ regs count, etc ]
 	 *
 	 * FP - ip_off       [ traced func       ] BPF_TRAMP_F_IP_ARG
 	 *
+	 *                   [ stack cookie N    ]
+	 *                   [ ...               ]
+	 * FP - cookie_off   [ stack cookie 1    ]
+	 *
 	 * FP - run_ctx_off  [ bpf_tramp_run_ctx ]
 	 *
 	 * FP - sreg_off     [ callee saved reg  ]
@@ -1859,9 +1888,9 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 	stack_size += nr_arg_slots * 8;
 	args_off = stack_size;
 
-	/* Room of trampoline frame to store args number */
+	/* Room of function metadata, such as regs count */
 	stack_size += 8;
-	nregs_off = stack_size;
+	func_meta_off = stack_size;
 
 	/* Room of trampoline frame to store ip address */
 	if (flags & BPF_TRAMP_F_IP_ARG) {
@@ -1869,6 +1898,12 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 		ip_off = stack_size;
 	}
 
+	cookie_cnt = bpf_fsession_cookie_cnt(tlinks);
+
+	/* Room for session cookies */
+	stack_size += cookie_cnt * 8;
+	cookie_off = stack_size;
+
 	/* Room of trampoline frame to store struct bpf_tramp_run_ctx */
 	stack_size += round_up(sizeof(struct bpf_tramp_run_ctx), 8);
 	run_ctx_off = stack_size;
@@ -1929,10 +1964,20 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 		emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -ip_off, (u64)func_addr);
 
 	/* store arg regs count */
-	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -nregs_off, nr_arg_slots);
+	func_meta = nr_arg_slots;
+	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
 
 	store_args(ctx, nr_arg_slots, args_off);
 
+	if (bpf_fsession_cnt(tlinks)) {
+		/* clear all session cookies' value */
+		for (i = 0; i < cookie_cnt; i++)
+			emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP, -cookie_off + 8 * i);
+
+		/* clear return value to make sure fentry always get 0 */
+		emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP, -retval_off);
+	}
+
 	/* To traced function */
 	/* Ftrace jump skips 2 NOP instructions */
 	if (is_kernel_text((unsigned long)orig_call) ||
@@ -1949,9 +1994,9 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 			return ret;
 	}
 
-	for (i = 0; i < fentry->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fentry->links[i], args_off, retval_off,
-				      run_ctx_off, flags & BPF_TRAMP_F_RET_FENTRY_RET);
+	if (fentry->nr_links) {
+		ret = invoke_bpf(ctx, fentry, args_off, retval_off, run_ctx_off, func_meta_off,
+				 flags & BPF_TRAMP_F_RET_FENTRY_RET, func_meta, cookie_off);
 		if (ret)
 			return ret;
 	}
@@ -1995,8 +2040,14 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 		*branches[i] = larch_insn_gen_bne(LOONGARCH_GPR_T1, LOONGARCH_GPR_ZERO, offset);
 	}
 
-	for (i = 0; i < fexit->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fexit->links[i], args_off, retval_off, run_ctx_off, false);
+	/* Set "is_return" flag for fsession */
+	func_meta |= (1ULL << BPF_TRAMP_IS_RETURN_SHIFT);
+	if (bpf_fsession_cnt(tlinks))
+		emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
+
+	if (fexit->nr_links) {
+		ret = invoke_bpf(ctx, fexit, args_off, retval_off, run_ctx_off,
+				 func_meta_off, false, func_meta, cookie_off);
 		if (ret)
 			goto out;
 	}
@@ -2331,6 +2382,11 @@ bool bpf_jit_supports_arena(void)
 	return true;
 }
 
+bool bpf_jit_supports_fsession(void)
+{
+	return true;
+}
+
 /* Indicate the JIT backend supports mixing bpf2bpf and tailcalls. */
 bool bpf_jit_supports_subprog_tailcalls(void)
 {
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,8 @@
 // SPDX-License-Identifier: GPL-2.0-only
 /*
  * BPF JIT compiler for LoongArch
  *
  * Copyright (C) 2022 Loongson Technology Corporation Limited
  */
 #include <linux/memory.h>
 #include "bpf_jit.h"
+
+struct jit_ctx;
+static int invoke_bpf(struct jit_ctx *ctx, struct bpf_tramp_links *tl,
+		      int args_off, int retval_off, int run_ctx_off,
+		      int func_meta_off, bool save_ret, u64 func_meta,
+		      int cookie_off);
 
 #define LOONGARCH_MAX_REG_ARGS 8
 
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,6 +1,6 @@
 static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_image *im, 					 const struct btf_func_model *m, struct bpf_tramp_links *tlinks, 					 void *func_addr, u32 flags)  {
 	int i, ret, save_ret;
 	int stack_size, args_off, stk_args_off, nr_arg_slots = 0;
-	int retval_off, nregs_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	int retval_off, func_meta_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	int cookie_off, cookie_cnt;
 	bool is_struct_ops = flags & BPF_TRAMP_F_INDIRECT;
 	void *orig_call = func_addr;
 	struct bpf_tramp_links *fentry = &tlinks[BPF_TRAMP_FENTRY];
 	struct bpf_tramp_links *fexit = &tlinks[BPF_TRAMP_FEXIT];
 	struct bpf_tramp_links *fmod_ret = &tlinks[BPF_TRAMP_MODIFY_RETURN];
 	u32 **branches = NULL;
+	u64 func_meta;
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,6 +1,10 @@
-	 * FP - nregs_off    [ arg regs count    ]
+	 * FP - func_meta_off [ regs count, etc  ]
 	 *
 	 * FP - ip_off       [ traced func       ] BPF_TRAMP_F_IP_ARG
 	 *
+	 *                   [ stack cookie N    ]
+	 *                   [ ...               ]
+	 * FP - cookie_off   [ stack cookie 1    ]
+	 *
 	 * FP - run_ctx_off  [ bpf_tramp_run_ctx ]
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,13 +1,18 @@
-	/* Room of trampoline frame to store args number */
+	/* Room of trampoline frame to store function metadata, such as args number */
 	stack_size += 8;
-	nregs_off = stack_size;
+	func_meta_off = stack_size;
 
 	/* Room of trampoline frame to store ip address */
 	if (flags & BPF_TRAMP_F_IP_ARG) {
 		stack_size += 8;
 		ip_off = stack_size;
 	}
 
+	cookie_cnt = bpf_fsession_cookie_cnt(tlinks);
+	/* Room for session cookies */
+	stack_size += cookie_cnt * 8;
+	cookie_off = stack_size;
+
 	/* Room of trampoline frame to store struct bpf_tramp_run_ctx */
 	stack_size += round_up(sizeof(struct bpf_tramp_run_ctx), 8);
 	run_ctx_off = stack_size;
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,9 +1,18 @@
-	/* store arg regs count */
-	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -nregs_off, nr_arg_slots);
+	/* store function metadata: arg regs count */
+	func_meta = nr_arg_slots;
+	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
 
 	store_args(ctx, nr_arg_slots, args_off);
 
+	if (bpf_fsession_cnt(tlinks)) {
+		/* clear all session cookies' value */
+		for (i = 0; i < cookie_cnt; i++)
+			emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP,
+				  -cookie_off + 8 * i);
+		/* clear return value to make sure fentry always gets 0 */
+		emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP, -retval_off);
+	}
+
 	/* To traced function */
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,7 +1,7 @@
-	for (i = 0; i < fentry->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fentry->links[i], args_off, retval_off,
-				      run_ctx_off, flags & BPF_TRAMP_F_RET_FENTRY_RET);
+	if (fentry->nr_links) {
+		ret = invoke_bpf(ctx, fentry, args_off, retval_off, run_ctx_off,
+				 func_meta_off, flags & BPF_TRAMP_F_RET_FENTRY_RET,
+				 func_meta, cookie_off);
 		if (ret)
 			return ret;
 	}
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,6 +1,13 @@
-	for (i = 0; i < fexit->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fexit->links[i], args_off, retval_off, run_ctx_off, false);
+	/* set "is_return" flag for fsession */
+	func_meta |= (1ULL << BPF_TRAMP_IS_RETURN_SHIFT);
+	if (bpf_fsession_cnt(tlinks))
+		emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
+
+	if (fexit->nr_links) {
+		ret = invoke_bpf(ctx, fexit, args_off, retval_off, run_ctx_off,
+				 func_meta_off, false, func_meta, cookie_off);
 		if (ret)
 			goto out;
 	}
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,5 +1,32 @@
 	ret = emit_call(ctx, (const u64)bpf_trampoline_exit(p));
 
 	return ret;
 }
 
+static int invoke_bpf(struct jit_ctx *ctx, struct bpf_tramp_links *tl,
+		      int args_off, int retval_off, int run_ctx_off,
+		      int func_meta_off, bool save_ret, u64 func_meta,
+		      int cookie_off)
+{
+	int i, cur_cookie = (cookie_off - args_off) / 8;
+
+	for (i = 0; i < tl->nr_links; i++) {
+		int err;
+
+		if (bpf_prog_calls_session_cookie(tl->links[i])) {
+			u64 meta = func_meta | ((u64)cur_cookie << BPF_TRAMP_COOKIE_INDEX_SHIFT);
+
+			emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, meta);
+			cur_cookie--;
+		}
+		err = invoke_bpf_prog(ctx, tl->links[i], args_off, retval_off,
+				      run_ctx_off, save_ret);
+		if (err)
+			return err;
+	}
+	return 0;
+}
+
+bool bpf_jit_supports_fsession(void)
+{
+	return true;
+}
+
 static void restore_args(struct jit_ctx *ctx, int nr_reg_args, int args_off)  {
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
-static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_image *im, 					 const struct btf_func_model *m, struct bpf_tramp_links *tlinks, 					 void *func_addr, u32 flags)  {
+static int invoke_bpf(struct jit_ctx *ctx, struct bpf_tramp_links *tl, int args_off, int retval_off,
+		      int run_ctx_off, int func_meta_off, bool save_ret, u64 func_meta,
+		      int cookie_off);
+
+static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_image *im, 					 const struct btf_func_model *m, struct bpf_tramp_links *tlinks, 					 void *func_addr, u32 flags)  {
 	int i, ret, save_ret;
 	int stack_size, args_off, stk_args_off, nr_arg_slots = 0;
-	int retval_off, nregs_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	int retval_off, func_meta_off, ip_off, run_ctx_off, sreg_off, tcc_ptr_off;
+	int cookie_off, cookie_cnt;
+	u64 func_meta;
 	bool is_struct_ops = flags & BPF_TRAMP_F_INDIRECT;
 	void *orig_call = func_addr;
 	struct bpf_tramp_links *fentry = &tlinks[BPF_TRAMP_FENTRY];
@@ -1,7 +1,11 @@
 	 * FP - nregs_off    [ arg regs count    ]
 	 *
 	 * FP - ip_off       [ traced func       ] BPF_TRAMP_F_IP_ARG
 	 *
+	 *                   [ stack cookie N    ]
+	 *                   [ ...               ]
+	 * FP - cookie_off   [ stack cookie 1    ]
+	 *
 	 * FP - run_ctx_off  [ bpf_tramp_run_ctx ]
 	 *
 	 * FP - sreg_off     [ callee saved reg  ]
@@ -1,6 +1,6 @@
-	/* Room of trampoline frame to store args number */
+	/* Room of trampoline frame to store func metadata, such as args number */
 	stack_size += 8;
-	nregs_off = stack_size;
+	func_meta_off = stack_size;
 
 	/* Room of trampoline frame to store ip address */
 	if (flags & BPF_TRAMP_F_IP_ARG) {
 		stack_size += 8;
 		ip_off = stack_size;
 	}
 
+	cookie_cnt = bpf_fsession_cookie_cnt(tlinks);
+	/* Room for session cookies */
+	stack_size += cookie_cnt * 8;
+	cookie_off = stack_size;
+
 	/* Room of trampoline frame to store struct bpf_tramp_run_ctx */
 	stack_size += round_up(sizeof(struct bpf_tramp_run_ctx), 8);
 	run_ctx_off = stack_size;
@@ -1,6 +1,15 @@
-	/* store arg regs count */
-	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -nregs_off, nr_arg_slots);
+	/* store func metadata: arg regs count */
+	func_meta = nr_arg_slots;
+	emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
 
 	store_args(ctx, nr_arg_slots, args_off);
 
+	if (bpf_fsession_cnt(tlinks)) {
+		/* clear all session cookies' value */
+		for (i = 0; i < cookie_cnt; i++)
+			emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP,
+				  -cookie_off + 8 * i);
+		/* clear return value to make sure fentry always get 0 */
+		emit_insn(ctx, std, LOONGARCH_GPR_ZERO, LOONGARCH_GPR_FP, -retval_off);
+	}
+
 	/* To traced function */
 	/* Ftrace jump skips 2 NOP instructions */
@@ -1,8 +1,8 @@
-	for (i = 0; i < fentry->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fentry->links[i], args_off, retval_off,
-				      run_ctx_off, flags & BPF_TRAMP_F_RET_FENTRY_RET);
+	if (fentry->nr_links) {
+		ret = invoke_bpf(ctx, fentry, args_off, retval_off, run_ctx_off, func_meta_off,
+				 flags & BPF_TRAMP_F_RET_FENTRY_RET, func_meta, cookie_off);
 		if (ret)
 			return ret;
 	}
 	if (fmod_ret->nr_links) {
@@ -1,6 +1,12 @@
-	for (i = 0; i < fexit->nr_links; i++) {
-		ret = invoke_bpf_prog(ctx, fexit->links[i], args_off, retval_off, run_ctx_off, false);
+	/* set "is_return" flag for fsession */
+	func_meta |= (1ULL << BPF_TRAMP_IS_RETURN_SHIFT);
+	if (bpf_fsession_cnt(tlinks))
+		emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, func_meta);
+
+	if (fexit->nr_links) {
+		ret = invoke_bpf(ctx, fexit, args_off, retval_off, run_ctx_off, func_meta_off,
+				 false, func_meta, cookie_off);
 		if (ret)
 			goto out;
 	}
@@ -1,3 +1,30 @@
+static int invoke_bpf(struct jit_ctx *ctx, struct bpf_tramp_links *tl, int args_off, int retval_off,
+		      int run_ctx_off, int func_meta_off, bool save_ret, u64 func_meta,
+		      int cookie_off)
+{
+	int i, cur_cookie = (cookie_off - args_off) / 8;
+
+	for (i = 0; i < tl->nr_links; i++) {
+		int err;
+
+		if (bpf_prog_calls_session_cookie(tl->links[i])) {
+			u64 meta = func_meta | ((u64)cur_cookie << BPF_TRAMP_COOKIE_INDEX_SHIFT);
+
+			emit_store_stack_imm64(ctx, LOONGARCH_GPR_T1, -func_meta_off, meta);
+			cur_cookie--;
+		}
+		err = invoke_bpf_prog(ctx, tl->links[i], args_off, retval_off, run_ctx_off,
+				      save_ret);
+		if (err)
+			return err;
+	}
+	return 0;
+}
+
 static void restore_args(struct jit_ctx *ctx, int nr_reg_args, int args_off)  {
 	int i;
 
@@ -1,3 +1,8 @@
+bool bpf_jit_supports_fsession(void)
+{
+	return true;
+}
+
 static void jit_fill_hole(void *area, unsigned int size)  {
 	u32 *ptr;
```

## A103

### 真实补丁T

```diff
commit 68571a63f25e44291af472d079eb4f906dea08e2
Subject: LoongArch: BPF: Inline bpf_get_smp_processor_id() helper


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index 66e8c1d2d5cb..ad7e28375aa9 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -5,6 +5,7 @@
  * Copyright (C) 2022 Loongson Technology Corporation Limited
  */
 #include <linux/memory.h>
+#include <asm/asm-offsets.h>
 #include "bpf_jit.h"
 
 #define LOONGARCH_MAX_REG_ARGS 8
@@ -1168,6 +1169,12 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 			break;
 		}
 
+		/* Implement helper call to bpf_get_smp_processor_id() inline */
+		if (insn->src_reg == 0 && insn->imm == BPF_FUNC_get_smp_processor_id) {
+			emit_insn(ctx, ldwu, regmap[BPF_REG_0], LOONGARCH_GPR_TP, TI_CPU);
+			break;
+		}
+
 		ret = bpf_jit_get_func_addr(ctx->prog, insn, extra_pass,
 					    &func_addr, &func_addr_fixed);
 		if (ret < 0)
@@ -2394,6 +2401,7 @@ bool bpf_jit_inlines_helper_call(s32 imm)
 	switch (imm) {
 	case BPF_FUNC_get_current_task:
 	case BPF_FUNC_get_current_task_btf:
+	case BPF_FUNC_get_smp_processor_id:
 		return true;
 	default:
 		return false;
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,4 @@
 // SPDX-License-Identifier: GPL-2.0-only
 /*
  * BPF JIT compiler for LoongArch
@@ bpf_jit_inlines_helper_call
 bool bpf_jit_inlines_helper_call(s32 imm)  {
 	switch (imm) {
 	case BPF_FUNC_get_current_task:
 	case BPF_FUNC_get_current_task_btf:
+	case BPF_FUNC_get_smp_processor_id:
 		return true;
 	default:
 		return false;
 	}
 }
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,0 +1,0 @@ build_insn()
 	/* function call */
 	case BPF_JMP | BPF_CALL:
+		/* Inline bpf_get_smp_processor_id():
+		 * $tp holds current task_struct, thread_info is at offset 0,
+		 * so R0 = ((struct thread_info *)$tp)->cpu
+		 */
+		if (insn->src_reg == 0 && insn->imm == BPF_FUNC_get_smp_processor_id) {
+			emit_insn(ctx, ldwu, regmap[BPF_REG_0], LOONGARCH_GPR_TP,
+				  offsetof(struct thread_info, cpu));
+			break;
+		}
+
 		mark_call(ctx);
@@ bool bpf_jit_inlines_helper_call(s32 imm)  {
 	switch (imm) {
 	case BPF_FUNC_get_current_task:
 	case BPF_FUNC_get_current_task_btf:
+	case BPF_FUNC_get_smp_processor_id:
 		return true;
 	default:
 		return false;
```

## A104

### 真实补丁T

```diff
commit 7f5c21fcd7ab2150d2b6d8ed2597820167ae0744
Subject: LoongArch: BPF: Inline bpf_get_current_task/_btf() helpers


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index 99294f930914..66e8c1d2d5cb 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1161,6 +1161,13 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 
 	/* function call */
 	case BPF_JMP | BPF_CALL:
+		/* Implement helper call to bpf_get_current_task/_btf() inline */
+		if (insn->src_reg == 0 && (insn->imm == BPF_FUNC_get_current_task ||
+					   insn->imm == BPF_FUNC_get_current_task_btf)) {
+			move_reg(ctx, regmap[BPF_REG_0], LOONGARCH_GPR_TP);
+			break;
+		}
+
 		ret = bpf_jit_get_func_addr(ctx->prog, insn, extra_pass,
 					    &func_addr, &func_addr_fixed);
 		if (ret < 0)
@@ -2381,3 +2388,14 @@ bool bpf_jit_supports_subprog_tailcalls(void)
 {
 	return true;
 }
+
+bool bpf_jit_inlines_helper_call(s32 imm)
+{
+	switch (imm) {
+	case BPF_FUNC_get_current_task:
+	case BPF_FUNC_get_current_task_btf:
+		return true;
+	default:
+		return false;
+	}
+}
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 	/* function call */
 	case BPF_JMP | BPF_CALL:
+		/* Implement helper call to bpf_get_current_task/_btf() inline */
+		if (insn->src_reg == 0 && (insn->imm == BPF_FUNC_get_current_task ||
+					   insn->imm == BPF_FUNC_get_current_task_btf)) {
+			move_reg(ctx, regmap[BPF_REG_0], LOONGARCH_GPR_TP);
+			break;
+		}
+
 		ret = bpf_jit_get_func_addr(ctx->prog, insn, extra_pass,
 					    &func_addr, &func_addr_fixed);
 		if (ret < 0)
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 	/* function call */
 	case BPF_JMP | BPF_CALL:
+		/* Implement helper call to bpf_get_current_task/_btf() inline */
+		if (insn->src_reg == 0 && (insn->imm == BPF_FUNC_get_current_task ||
+					   insn->imm == BPF_FUNC_get_current_task_btf)) {
+			move_reg(ctx, regmap[BPF_REG_0], LOONGARCH_GPR_TP);
+			break;
+		}
+
 		ret = bpf_jit_get_func_addr(ctx->prog, insn, extra_pass,
 					    &func_addr, &func_addr_fixed);
 		if (ret < 0)
 			return ret;
@@ -1,4 +1,16 @@
 toofar:
 	pr_info_once("bpf_jit: opcode %02x, jump too far\n", code);
 	return -E2BIG;
 }
+
+bool bpf_jit_inlines_helper_call(s32 imm)
+{
+	switch (imm) {
+	case BPF_FUNC_get_current_task:
+	case BPF_FUNC_get_current_task_btf:
+		return true;
+	default:
+		return false;
+	}
+}
```

## A109

### 真实补丁T

```diff
commit 2677f97a67fdbc62a82ce1faa67791f54451d36f
Subject: LoongArch: Add DIRECT_MAP_PHYSMEM_END definition


diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
index 223528c04d73..59b37a824bab 100644
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -125,6 +125,13 @@ struct vm_area_struct;
 
 #endif
 
+/* Needed to limit get_free_mem_region() */
+#ifndef CONFIG_SPARSEMEM
+#define DIRECT_MAP_PHYSMEM_END ((1ULL << (cpu_pabits + 1)) - 1)
+#else
+#define DIRECT_MAP_PHYSMEM_END min((1ULL << (cpu_pabits + 1)) - 1, (1ULL << MAX_PHYSMEM_BITS) - 1)
+#endif
+
 #define ptep_get(ptep) READ_ONCE(*(ptep))
 #define pmdp_get(pmdp) READ_ONCE(*(pmdp))
```

### X

```diff
diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -101,6 +101,9 @@ struct vm_area_struct;
 #define KFENCE_AREA_START	(VMEMMAP_END + 1)
 #define KFENCE_AREA_END		(KFENCE_AREA_START + KFENCE_AREA_SIZE - 1)
 
+/* Needed to limit get_free_mem_region() to what the CPU can address */
+#define DIRECT_MAP_PHYSMEM_END	((1ULL << (cpu_pabits + 1)) - 1)
+
 #endif
 
 #define ptep_get(ptep) READ_ONCE(*(ptep))
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/pgtable.h b/arch/loongarch/include/asm/pgtable.h
--- a/arch/loongarch/include/asm/pgtable.h
+++ b/arch/loongarch/include/asm/pgtable.h
@@ -105,6 +105,9 @@ struct vm_area_struct;
 #define KFENCE_AREA_START	(VMEMMAP_END + 1)
 #define KFENCE_AREA_END		(KFENCE_AREA_START + KFENCE_AREA_SIZE - 1)
 
+/* Needed to limit get_free_mem_region() */
+#define DIRECT_MAP_PHYSMEM_END	((1ULL << (cpu_pabits + 1)) - 1)
+
 #endif
 
 #define ptep_get(ptep) READ_ONCE(*(ptep))
```

## L081

### 真实补丁T

```diff
commit 772cbe948fb07389639d4e698a2d3299f8e538b8
Subject: LoongArch: BPF: Fix sign-extension mov instructions


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index d76281efc5b8..cd002f183648 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -480,10 +480,12 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 		case 8:
 			move_reg(ctx, t1, src);
 			emit_insn(ctx, extwb, dst, t1);
+			emit_zext_32(ctx, dst, is32);
 			break;
 		case 16:
 			move_reg(ctx, t1, src);
 			emit_insn(ctx, extwh, dst, t1);
+			emit_zext_32(ctx, dst, is32);
 			break;
 		case 32:
 			emit_insn(ctx, addw, dst, src, LOONGARCH_GPR_ZERO);
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -392,8 +392,28 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 	/* dst = src */
 	case BPF_ALU | BPF_MOV | BPF_X:
 	case BPF_ALU64 | BPF_MOV | BPF_X:
-		move_reg(ctx, dst, src);
-		emit_zext_32(ctx, dst, is32);
+		switch (off) {
+		case 0:
+			move_reg(ctx, dst, src);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 8:
+			move_reg(ctx, t1, src);
+			emit_insn(ctx, extwb, dst, t1);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 16:
+			move_reg(ctx, t1, src);
+			emit_insn(ctx, extwh, dst, t1);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 32:
+			emit_insn(ctx, addiw, dst, src, 0);
+			break;
+		}
 		break;
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -437,8 +437,24 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 	/* dst = src */
 	case BPF_ALU | BPF_MOV | BPF_X:
 	case BPF_ALU64 | BPF_MOV | BPF_X:
-		move_reg(ctx, dst, src);
-		emit_zext_32(ctx, dst, is32);
+		switch (off) {
+		case 0:
+			move_reg(ctx, dst, src);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 8:
+			emit_insn(ctx, extwb, dst, src);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 16:
+			emit_insn(ctx, extwh, dst, src);
+			emit_zext_32(ctx, dst, is32);
+			break;
+		case 32:
+			emit_insn(ctx, addiw, dst, src, 0);
+			break;
+		}
 		break;
 
 	/* dst = imm */
```

## L082

### 真实补丁T

```diff
commit e2f7b3d8b4b300956a77fa1ab084c931ba1c7421
Subject: LoongArch: BPF: Fix unconditional bswap instructions


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index cd002f183648..4fcd6cd6da23 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -774,8 +774,8 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 			break;
 		case 32:
 			emit_insn(ctx, revb2w, dst, dst);
-			/* zero-extend 32 bits into 64 bits */
-			emit_zext_32(ctx, dst, is32);
+			/* clear the upper 32 bits */
+			emit_zext_32(ctx, dst, true);
 			break;
 		case 64:
 			emit_insn(ctx, revbd, dst, dst);
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,4 @@
 	case BPF_ALU | BPF_END | BPF_FROM_BE:
+	case BPF_ALU64 | BPF_END | BPF_FROM_LE:
 		switch (imm) {
 		case 16:
 			emit_insn(ctx, revb2h, dst, dst);
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,4 @@
 	/* dst = htobe(dst) */
 	case BPF_ALU | BPF_END | BPF_FROM_BE:
+	case BPF_ALU64 | BPF_END | BPF_FROM_LE:
 		switch (imm) {
```

## L121

### 真实补丁T

```diff
commit 8b51b11b3d81c1ed48a52f87da9256d737b723a0
Subject: LoongArch: BPF: Sign-extend struct ops return values properly


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index fa1a3234e9a6..cbe53d0b7fb0 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1448,6 +1448,37 @@ void arch_free_bpf_trampoline(void *image, unsigned int size)
 	bpf_prog_pack_free(image, size);
 }
 
+/*
+ * Sign-extend the register if necessary
+ */
+static void sign_extend(struct jit_ctx *ctx, int rd, int rj, u8 size, bool sign)
+{
+	/* ABI requires unsigned char/short to be zero-extended */
+	if (!sign && (size == 1 || size == 2)) {
+		if (rd != rj)
+			move_reg(ctx, rd, rj);
+		return;
+	}
+
+	switch (size) {
+	case 1:
+		emit_insn(ctx, extwb, rd, rj);
+		break;
+	case 2:
+		emit_insn(ctx, extwh, rd, rj);
+		break;
+	case 4:
+		emit_insn(ctx, addiw, rd, rj, 0);
+		break;
+	case 8:
+		if (rd != rj)
+			move_reg(ctx, rd, rj);
+		break;
+	default:
+		pr_warn("bpf_jit: invalid size %d for sign_extend\n", size);
+	}
+}
+
 static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_image *im,
 					 const struct btf_func_model *m, struct bpf_tramp_links *tlinks,
 					 void *func_addr, u32 flags)
@@ -1655,8 +1686,12 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 		restore_args(ctx, m->nr_args, args_off);
 
 	if (save_ret) {
-		emit_insn(ctx, ldd, LOONGARCH_GPR_A0, LOONGARCH_GPR_FP, -retval_off);
 		emit_insn(ctx, ldd, regmap[BPF_REG_0], LOONGARCH_GPR_FP, -(retval_off - 8));
+		if (is_struct_ops)
+			sign_extend(ctx, LOONGARCH_GPR_A0, regmap[BPF_REG_0],
+				    m->ret_size, m->ret_flags & BTF_FMODEL_SIGNED_ARG);
+		else
+			emit_insn(ctx, ldd, LOONGARCH_GPR_A0, LOONGARCH_GPR_FP, -retval_off);
 	}
 
 	emit_insn(ctx, ldd, LOONGARCH_GPR_S1, LOONGARCH_GPR_FP, -sreg_off);
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -2,0 +2,0 @@
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,38 @@
 // SPDX-License-Identifier: GPL-2.0-only
 /*
  * BPF JIT compiler for LoongArch
@@ -40,3 +40,38 @@ static const int regmap[] = {
 	[BPF_REG_AX] = LOONGARCH_GPR_T0,
 };
 
+/*
+ * Sign-extend (or zero-extend) the return value according to the
+ * function model and the LoongArch ABI.
+ */
+static int sign_extend_ret(struct jit_ctx *ctx, u8 rd, u8 rs, u8 sz, bool sign)
+{
+	switch (sz) {
+	case 1:
+		if (sign)
+			emit_insn(ctx, extwb, rd, rs);
+		else
+			emit_insn(ctx, bstrpickd, rd, rs, 7, 0);
+		break;
+	case 2:
+		if (sign)
+			emit_insn(ctx, extwh, rd, rs);
+		else
+			emit_insn(ctx, bstrpickd, rd, rs, 15, 0);
+		break;
+	case 4:
+		emit_insn(ctx, addw, rd, rs, LOONGARCH_GPR_ZERO);
+		break;
+	case 8:
+		if (rd != rs)
+			move_reg(ctx, rd, rs);
+		break;
+	default:
+		pr_err("bpf-jit: invalid size %d for sign_extend_ret\n", sz);
+		return -EINVAL;
+	}
+
+	return 0;
+}
+
 static void prepare_bpf_tail_call_cnt(struct jit_ctx *ctx, int *store_offset)
 
 /* ... */
@@ -1,3 +1,3 @@
 	if (save_ret) {
-		emit_insn(ctx, ldd, LOONGARCH_GPR_A0, LOONGARCH_GPR_FP, -retval_off);
 		emit_insn(ctx, ldd, regmap[BPF_REG_0], LOONGARCH_GPR_FP, -(retval_off - 8));
+		if (is_struct_ops) {
+			ret = sign_extend_ret(ctx, LOONGARCH_GPR_A0, regmap[BPF_REG_0],
+					      m->ret_size, m->ret_flags & BTF_FMODEL_SIGNED_ARG);
+			if (ret)
+				goto out;
+		} else {
+			emit_insn(ctx, ldd, LOONGARCH_GPR_A0, LOONGARCH_GPR_FP, -retval_off);
+		}
 	}
```

## L128

### 真实补丁T

```diff
commit 3f5a238f24d7b75f9efe324d3539ad388f58536e
Subject: LoongArch: BPF: Sign extend kfunc call arguments


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index 8dc58781b8eb..5352d0c30fb2 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -950,6 +950,22 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 			emit_insn(ctx, ldd, REG_TCC, LOONGARCH_GPR_SP, tcc_ptr_off);
 		}
 
+		if (insn->src_reg == BPF_PSEUDO_KFUNC_CALL) {
+			const struct btf_func_model *m;
+			int i;
+
+			m = bpf_jit_find_kfunc_model(ctx->prog, insn);
+			if (!m)
+				return -EINVAL;
+
+			for (i = 0; i < m->nr_args; i++) {
+				u8 reg = regmap[BPF_REG_1 + i];
+				bool sign = m->arg_flags[i] & BTF_FMODEL_SIGNED_ARG;
+
+				emit_abi_ext(ctx, reg, m->arg_size[i], sign);
+			}
+		}
+
 		move_addr(ctx, t1, func_addr);
 		emit_insn(ctx, jirl, LOONGARCH_GPR_RA, t1, 0);
 
diff --git a/arch/loongarch/net/bpf_jit.h b/arch/loongarch/net/bpf_jit.h
index 5697158fd164..75b6330030a9 100644
--- a/arch/loongarch/net/bpf_jit.h
+++ b/arch/loongarch/net/bpf_jit.h
@@ -88,6 +88,32 @@ static inline void emit_sext_32(struct jit_ctx *ctx, enum loongarch_gpr reg, boo
 	emit_insn(ctx, addiw, reg, reg, 0);
 }
 
+/* Emit proper extension according to ABI requirements.
+ * Note that it requires a value of size `size` already resides in register `reg`.
+ */
+static inline void emit_abi_ext(struct jit_ctx *ctx, int reg, u8 size, bool sign)
+{
+	/* ABI requires unsigned char/short to be zero-extended */
+	if (!sign && (size == 1 || size == 2))
+		return;
+
+	switch (size) {
+	case 1:
+		emit_insn(ctx, extwb, reg, reg);
+		break;
+	case 2:
+		emit_insn(ctx, extwh, reg, reg);
+		break;
+	case 4:
+		emit_insn(ctx, addiw, reg, reg, 0);
+		break;
+	case 8:
+		break;
+	default:
+		pr_warn("bpf_jit: invalid size %d for extension\n", size);
+	}
+}
+
 static inline void move_addr(struct jit_ctx *ctx, enum loongarch_gpr rd, u64 addr)
 {
 	u64 imm_11_0, imm_31_12, imm_51_32, imm_63_52;
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -907,6 +907,23 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 		if (ret < 0)
 			return ret;
 
+		if (insn->src_reg == BPF_PSEUDO_KFUNC_CALL) {
+			const struct btf_func_model *fm;
+			int idx;
+
+			fm = bpf_jit_find_kfunc_model(ctx->prog, insn);
+			if (!fm)
+				return -EINVAL;
+
+			for (idx = 0; idx < fm->nr_args; idx++) {
+				u8 reg = regmap[BPF_REG_1 + idx];
+
+				if (fm->arg_size[idx] == sizeof(int))
+					emit_insn(ctx, addiw, reg, reg, 0);
+			}
+		}
+
 		move_addr(ctx, t1, func_addr);
 		emit_insn(ctx, jirl, LOONGARCH_GPR_RA, t1, 0);
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -855,6 +855,22 @@ static int build_insn(const struct bpf_insn *insn, struct jit_ctx *ctx, bool ext
 		if (ret < 0)
 			return ret;
 
+		if (insn->src_reg == BPF_PSEUDO_KFUNC_CALL) {
+			const struct btf_func_model *fm;
+			int idx;
+
+			fm = bpf_jit_find_kfunc_model(ctx->prog, insn);
+			if (!fm)
+				return -EINVAL;
+
+			for (idx = 0; idx < fm->nr_args; idx++) {
+				u8 reg = regmap[BPF_REG_1 + idx];
+
+				if (fm->arg_size[idx] == sizeof(int))
+					emit_insn(ctx, addiw, reg, reg, 0);
+			}
+		}
+
 		move_addr(ctx, t1, func_addr);
 		emit_insn(ctx, jirl, LOONGARCH_GPR_RA, t1, 0);
 		move_reg(ctx, regmap[BPF_REG_0], LOONGARCH_GPR_A0);
```

## L132

### 真实补丁T

```diff
commit b254c629a963f0b9d635902f3f979bddbc65f90f
Subject: LoongArch: BPF: Make arch_protect_bpf_trampoline() return 0


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index e8e0ad34928c..9cb796e16379 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1574,6 +1574,11 @@ void arch_free_bpf_trampoline(void *image, unsigned int size)
 	bpf_prog_pack_free(image, size);
 }
 
+int arch_protect_bpf_trampoline(void *image, unsigned int size)
+{
+	return 0;
+}
+
 /*
  * Sign-extend the register if necessary
  */
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,11 @@
 void arch_free_bpf_trampoline(void *image, unsigned int size)
 {
 	bpf_prog_pack_free(image, size);
 }
+
+void arch_protect_bpf_trampoline(void *image, unsigned int size)
+{
+}
+
+void arch_unprotect_bpf_trampoline(void *image, unsigned int size)
+{
+}
```

### Y

```diff
（没有补丁）
```

## L147

### 真实补丁T

```diff
commit 47e20d4b3da97ef3881d1e55e43545c22424f3fc
Subject: LoongArch: BPF: Fix memory leak in bpf_jit_free()


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index c91d474faba7..29c281bef28e 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -2361,6 +2361,7 @@ void bpf_jit_free(struct bpf_prog *prog)
 		 */
 		if (jit_data) {
 			bpf_jit_binary_pack_finalize(jit_data->ro_header, jit_data->header);
+			kvfree(jit_data->ctx.offset);
 			kfree(jit_data);
 		}
 		hdr = bpf_jit_binary_pack_hdr(prog);
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 		if (jit_data) {
 			bpf_jit_binary_pack_finalize(jit_data->ro_header, jit_data->header);
+			kfree(jit_data->ctx.offset);
 			kfree(jit_data);
 		}
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 		if (jit_data) {
 			bpf_jit_binary_pack_finalize(jit_data->ro_header, jit_data->header);
+			kfree(jit_data->ctx.offset);
 			kfree(jit_data);
 		}
```

## R012

### 真实补丁T

```diff
commit 9d5567ccf96fb2f1eb83d531eee23ead4aa8f2a3
Subject: riscv: fix jal offsets in patched alternatives


diff --git a/arch/riscv/include/asm/insn.h b/arch/riscv/include/asm/insn.h
index 98453535324a..25ef9c0b19e7 100644
--- a/arch/riscv/include/asm/insn.h
+++ b/arch/riscv/include/asm/insn.h
@@ -291,6 +291,33 @@ static __always_inline bool riscv_insn_is_branch(u32 code)
 	(RVC_X(x_, RVC_B_IMM_7_6_OPOFF, RVC_B_IMM_7_6_MASK) << RVC_B_IMM_7_6_OFF) | \
 	(RVC_IMM_SIGN(x_) << RVC_B_IMM_SIGN_OFF); })
 
+/*
+ * Get the immediate from a J-type instruction.
+ *
+ * @insn: instruction to process
+ * Return: immediate
+ */
+static inline s32 riscv_insn_extract_jtype_imm(u32 insn)
+{
+	return RV_EXTRACT_JTYPE_IMM(insn);
+}
+
+/*
+ * Update a J-type instruction with an immediate value.
+ *
+ * @insn: pointer to the jtype instruction
+ * @imm: the immediate to insert into the instruction
+ */
+static inline void riscv_insn_insert_jtype_imm(u32 *insn, s32 imm)
+{
+	/* drop the old IMMs, all jal IMM bits sit at 31:12 */
+	*insn &= ~GENMASK(31, 12);
+	*insn |= (RV_X(imm, RV_J_IMM_10_1_OFF, RV_J_IMM_10_1_MASK) << RV_J_IMM_10_1_OPOFF) |
+		 (RV_X(imm, RV_J_IMM_11_OFF, RV_J_IMM_11_MASK) << RV_J_IMM_11_OPOFF) |
+		 (RV_X(imm, RV_J_IMM_19_12_OFF, RV_J_IMM_19_12_MASK) << RV_J_IMM_19_12_OPOFF) |
+		 (RV_X(imm, RV_J_IMM_SIGN_OFF, 1) << RV_J_IMM_SIGN_OPOFF);
+}
+
 /*
  * Put together one immediate from a U-type and I-type instruction pair.
  *
diff --git a/arch/riscv/kernel/alternative.c b/arch/riscv/kernel/alternative.c
index 6212ea0eed72..3d4f1f32c7f6 100644
--- a/arch/riscv/kernel/alternative.c
+++ b/arch/riscv/kernel/alternative.c
@@ -79,6 +79,21 @@ static void riscv_alternative_fix_auipc_jalr(void *ptr, u32 auipc_insn,
 	patch_text_nosync(ptr, call, sizeof(u32) * 2);
 }
 
+static void riscv_alternative_fix_jal(void *ptr, u32 jal_insn, int patch_offset)
+{
+	s32 imm;
+
+	/* get and adjust new target address */
+	imm = riscv_insn_extract_jtype_imm(jal_insn);
+	imm -= patch_offset;
+
+	/* update instruction */
+	riscv_insn_insert_jtype_imm(&jal_insn, imm);
+
+	/* patch the call place again */
+	patch_text_nosync(ptr, &jal_insn, sizeof(u32));
+}
+
 void riscv_alternative_fix_offsets(void *alt_ptr, unsigned int len,
 				      int patch_offset)
 {
@@ -106,6 +121,18 @@ void riscv_alternative_fix_offsets(void *alt_ptr, unsigned int len,
 			riscv_alternative_fix_auipc_jalr(alt_ptr + i * sizeof(u32),
 							 insn, insn2, patch_offset);
 		}
+
+		if (riscv_insn_is_jal(insn)) {
+			s32 imm = riscv_insn_extract_jtype_imm(insn);
+
+			/* Don't modify jumps inside the alternative block */
+			if ((alt_ptr + i * sizeof(u32) + imm) >= alt_ptr &&
+			    (alt_ptr + i * sizeof(u32) + imm) < (alt_ptr + len))
+				continue;
+
+			riscv_alternative_fix_jal(alt_ptr + i * sizeof(u32),
+						  insn, patch_offset);
+		}
 	}
 }
```

### X

```diff
diff --git a/arch/riscv/kernel/alternative.c b/arch/riscv/kernel/alternative.c
--- a/arch/riscv/kernel/alternative.c
+++ b/arch/riscv/kernel/alternative.c
@@ -65,6 +65,56 @@ static u32 riscv_instruction_at(void *p)
 	return (u32)parcel[0] | (u32)parcel[1] << 16;
 }
 
+#define ALT_JAL_OPCODE		0x6f
+#define ALT_JAL_OPCODE_MASK	0x7f
+
+static bool riscv_alt_insn_is_jal(u32 insn)
+{
+	return (insn & ALT_JAL_OPCODE_MASK) == ALT_JAL_OPCODE;
+}
+
+static s32 riscv_alt_jal_extract_imm(u32 insn)
+{
+	u32 imm;
+
+	imm  = ((insn >> 31) & 0x1) << 20;
+	imm |= ((insn >> 21) & 0x3ff) << 1;
+	imm |= ((insn >> 20) & 0x1) << 11;
+	imm |= ((insn >> 12) & 0xff) << 12;
+
+	/* sign extend from bit 20 */
+	return (s32)(imm << 11) >> 11;
+}
+
+static u32 riscv_alt_jal_insert_imm(u32 insn, s32 imm)
+{
+	u32 uimm = (u32)imm;
+
+	/* keep opcode and rd (low 12 bits) */
+	insn &= 0xfff;
+	insn |= ((uimm >> 20) & 0x1) << 31;
+	insn |= ((uimm >> 1) & 0x3ff) << 21;
+	insn |= ((uimm >> 11) & 0x1) << 20;
+	insn |= ((uimm >> 12) & 0xff) << 12;
+
+	return insn;
+}
+
+static void riscv_alternative_fix_jal(void *ptr, u32 jal_insn, int patch_offset)
+{
+	s32 imm;
+
+	/* get and adjust new target address */
+	imm = riscv_alt_jal_extract_imm(jal_insn);
+	imm -= patch_offset;
+
+	/* J-type immediate is 21 bits signed, 2-byte aligned */
+	if (imm < -(1 << 20) || imm >= (1 << 20)) {
+		WARN_ONCE(1, "alternative: jal target out of range\n");
+		return;
+	}
+
+	jal_insn = riscv_alt_jal_insert_imm(jal_insn, imm);
+
+	/* patch the jump place again */
+	patch_text_nosync(ptr, &jal_insn, sizeof(u32));
+}
+
 static void riscv_alternative_fix_auipc_jalr(void *ptr, u32 auipc_insn,
 					     u32 jalr_insn, int patch_offset)
 {
@@ -106,6 +156,17 @@ void riscv_alternative_fix_offsets(void *alt_ptr, unsigned int len,
 
 			riscv_alternative_fix_auipc_jalr(alt_ptr + i * sizeof(u32),
 							 insn, insn2, patch_offset);
+		} else if (riscv_alt_insn_is_jal(insn)) {
+			int rd_reg = RV_EXTRACT_RD_REG(insn);
+
+			/* only calls (link in ra or t0) are fixed up */
+			if (rd_reg != 1 && rd_reg != 5)
+				continue;
+
+			riscv_alternative_fix_jal(alt_ptr + i * sizeof(u32),
+						  insn, patch_offset);
 		}
 	}
 }
```

### Y

```diff
diff --git a/arch/riscv/kernel/alternative.c b/arch/riscv/kernel/alternative.c
--- a/arch/riscv/kernel/alternative.c
+++ b/arch/riscv/kernel/alternative.c
@@ -80,6 +80,43 @@ static void riscv_alternative_fix_auipc_jalr(void *ptr, u32 auipc_insn,
 	patch_text_nosync(ptr, call, sizeof(u32) * 2);
 }
 
+static bool riscv_alt_insn_is_jal(u32 insn)
+{
+	return (insn & 0x7f) == 0x6f;
+}
+
+static s32 riscv_alt_jal_get_imm(u32 insn)
+{
+	u32 imm;
+
+	imm  = ((insn >> 31) & 0x1)   << 20;
+	imm |= ((insn >> 21) & 0x3ff) << 1;
+	imm |= ((insn >> 20) & 0x1)   << 11;
+	imm |= ((insn >> 12) & 0xff)  << 12;
+
+	return sign_extend32(imm, 20);
+}
+
+static u32 riscv_alt_jal_set_imm(u32 insn, s32 offset)
+{
+	u32 imm = (u32)offset;
+
+	insn &= 0xfff;	/* keep rd and opcode */
+	insn |= ((imm >> 20) & 0x1)   << 31;
+	insn |= ((imm >> 1)  & 0x3ff) << 21;
+	insn |= ((imm >> 11) & 0x1)   << 20;
+	insn |= ((imm >> 12) & 0xff)  << 12;
+
+	return insn;
+}
+
+static void riscv_alternative_fix_jal(void *ptr, u32 jal_insn, int patch_offset)
+{
+	s32 imm = riscv_alt_jal_get_imm(jal_insn) - patch_offset;
+	u32 new_insn = riscv_alt_jal_set_imm(jal_insn, imm);
+
+	patch_text_nosync(ptr, &new_insn, sizeof(u32));
+}
+
 void riscv_alternative_fix_offsets(void *alt_ptr, unsigned int len,
 				      int patch_offset)
 {
@@ -88,6 +125,13 @@ void riscv_alternative_fix_offsets(void *alt_ptr, unsigned int len,
 
 	for (i = 0; i < num_insn; i++) {
 		u32 insn = riscv_instruction_at(alt_ptr + i * sizeof(u32));
 
+		/* jal that leaves the block: only fix calls (rd == ra) */
+		if (riscv_alt_insn_is_jal(insn)) {
+			if (RV_EXTRACT_RD_REG(insn) == 1)
+				riscv_alternative_fix_jal(alt_ptr + i * sizeof(u32),
+							  insn, patch_offset);
+			continue;
+		}
+
 		/*
 		 * May be the start of an auipc + jalr pair
 		 * Needs to check that at least one more instruction
```

## R014

### 真实补丁T

```diff
commit 950b879b7f0251317d26bae0687e72592d607532
Subject: riscv: Fixup race condition on PG_dcache_clean in flush_icache_pte


diff --git a/arch/riscv/mm/cacheflush.c b/arch/riscv/mm/cacheflush.c
index 3cc07ed45aeb..fcd6145fbead 100644
--- a/arch/riscv/mm/cacheflush.c
+++ b/arch/riscv/mm/cacheflush.c
@@ -90,8 +90,10 @@ void flush_icache_pte(pte_t pte)
 	if (PageHuge(page))
 		page = compound_head(page);
 
-	if (!test_and_set_bit(PG_dcache_clean, &page->flags))
+	if (!test_bit(PG_dcache_clean, &page->flags)) {
 		flush_icache_all();
+		set_bit(PG_dcache_clean, &page->flags);
+	}
 }
 #endif /* CONFIG_MMU */
```

### X

```diff
（没有补丁）
```

### Y

```diff
diff --git a/arch/riscv/mm/cacheflush.c b/arch/riscv/mm/cacheflush.c
--- a/arch/riscv/mm/cacheflush.c
+++ b/arch/riscv/mm/cacheflush.c
@@ -83,8 +83,10 @@ void flush_icache_pte(pte_t pte)
 {
 	struct page *page = pte_page(pte);
 
-	if (!test_and_set_bit(PG_dcache_clean, &page->flags))
+	if (!test_bit(PG_dcache_clean, &page->flags)) {
 		flush_icache_all();
+		set_bit(PG_dcache_clean, &page->flags);
+	}
 }
 #endif /* CONFIG_MMU */
```

## R046

### 真实补丁T

```diff
commit 88ac3bbcf73853880a9b2a65c67e6854390741cc
Subject: riscv/purgatory: remove PGO flags


diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
index 5730797a6b40..bd2e27f82532 100644
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -35,6 +35,11 @@ CFLAGS_sha256.o := -D__DISABLE_EXPORTS
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
 
+# When profile-guided optimization is enabled, llvm emits two different
+# overlapping text sections, which is not supported by kexec. Remove profile
+# optimization flags.
+KBUILD_CFLAGS := $(filter-out -fprofile-sample-use=% -fprofile-use=%,$(KBUILD_CFLAGS))
+
 # When linking purgatory.ro with -r unresolved symbols are not checked,
 # also link a purgatory.chk binary without -r to check for unresolved symbols.
 PURGATORY_LDFLAGS := -e purgatory_start -z nodefaultlib
```

### X

```diff
diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -37,6 +37,11 @@ CFLAGS_sha256.o := -D__DISABLE_EXPORTS
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
 
+# When profile-guided optimization is enabled, llvm emits two different
+# overlapping text sections, which is not supported by kexec. Remove profile
+# optimization flags.
+KBUILD_CFLAGS := $(filter-out -fprofile-sample-use=% -fprofile-use=%,$(KBUILD_CFLAGS))
+
 # When linking purgatory.ro with -r unresolved symbols are not checked,
 # also link a purgatory.chk binary without -r to check for unresolved symbols.
 PURGATORY_LDFLAGS := -e purgatory_start -z nodefaultlib
```

### Y

```diff
diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -37,6 +37,11 @@ CFLAGS_sha256.o := -D__DISABLE_EXPORTS
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
 
+# When profile-guided optimization is enabled, llvm emits two different
+# overlapping text sections, which is not supported by kexec. Remove profile
+# optimization flags.
+KBUILD_CFLAGS := $(filter-out -fprofile-sample-use=% -fprofile-use=%,$(KBUILD_CFLAGS))
+
 # When linking purgatory.ro with -r unresolved symbols are not checked,
 # also link a purgatory.chk binary without -r to check for unresolved symbols.
 PURGATORY_LDFLAGS := -e purgatory_start -z nodefaultlib
```

## R050

### 真实补丁T

```diff
commit 85fadc0d04119c2fe4a20287767ab904c6d21ba1
Subject: riscv: move memblock_allow_resize() after linear mapping is ready


diff --git a/arch/riscv/mm/init.c b/arch/riscv/mm/init.c
index 3b1e927a06b7..59df29fc635d 100644
--- a/arch/riscv/mm/init.c
+++ b/arch/riscv/mm/init.c
@@ -267,7 +267,6 @@ static void __init setup_bootmem(void)
 	dma_contiguous_reserve(dma32_phys_limit);
 	if (IS_ENABLED(CONFIG_64BIT))
 		hugetlb_cma_reserve(PUD_SHIFT - PAGE_SHIFT);
-	memblock_allow_resize();
 }
 
 #ifdef CONFIG_MMU
@@ -1370,6 +1369,9 @@ void __init paging_init(void)
 {
 	setup_bootmem();
 	setup_vm_final();
+
+	/* Depend on that Linear Mapping is ready */
+	memblock_allow_resize();
 }
 
 void __init misc_mem_init(void)
```

### X

```diff
diff --git a/arch/riscv/mm/init.c b/arch/riscv/mm/init.c
--- a/arch/riscv/mm/init.c
+++ b/arch/riscv/mm/init.c
@@ -246,7 +246,6 @@ static void __init setup_bootmem(void)
 	dma_contiguous_reserve(dma32_phys_limit);
 	if (IS_ENABLED(CONFIG_64BIT))
 		hugetlb_cma_reserve(PUD_SHIFT - PAGE_SHIFT);
-	memblock_allow_resize();
 }
 
 #ifdef CONFIG_MMU
@@ -1304,6 +1303,7 @@ void __init paging_init(void)
 {
 	setup_bootmem();
 	setup_vm_final();
+	memblock_allow_resize();
 }
 
 void __init misc_mem_init(void)
```

### Y

```diff
diff --git a/arch/riscv/mm/init.c b/arch/riscv/mm/init.c
--- a/arch/riscv/mm/init.c
+++ b/arch/riscv/mm/init.c
@@ -246,7 +246,6 @@ static void __init setup_bootmem(void)
 	dma_contiguous_reserve(dma32_phys_limit);
 	if (IS_ENABLED(CONFIG_64BIT))
 		hugetlb_cma_reserve(PUD_SHIFT - PAGE_SHIFT);
-	memblock_allow_resize();
 }
 
 #ifdef CONFIG_MMU
@@ -1319,6 +1318,7 @@ void __init paging_init(void)
 {
 	setup_bootmem();
 	setup_vm_final();
+	memblock_allow_resize();
 }
 
 void __init misc_mem_init(void)
```

## R077

### 真实补丁T

```diff
commit 1d6cd2146c2b58bc91266db1d5d6a5f9632e14c0
Subject: riscv: kdump: fix crashkernel reserving problem on RISC-V


diff --git a/arch/riscv/kernel/setup.c b/arch/riscv/kernel/setup.c
index e600aab116a4..aac853ae4eb7 100644
--- a/arch/riscv/kernel/setup.c
+++ b/arch/riscv/kernel/setup.c
@@ -173,19 +173,6 @@ static void __init init_resources(void)
 	if (ret < 0)
 		goto error;
 
-#ifdef CONFIG_KEXEC_CORE
-	if (crashk_res.start != crashk_res.end) {
-		ret = add_resource(&iomem_resource, &crashk_res);
-		if (ret < 0)
-			goto error;
-	}
-	if (crashk_low_res.start != crashk_low_res.end) {
-		ret = add_resource(&iomem_resource, &crashk_low_res);
-		if (ret < 0)
-			goto error;
-	}
-#endif
-
 #ifdef CONFIG_CRASH_DUMP
 	if (elfcorehdr_size > 0) {
 		elfcorehdr_res.start = elfcorehdr_addr;
```

### X

```diff
diff --git a/arch/riscv/include/asm/crash_core.h b/arch/riscv/include/asm/crash_core.h
new file mode 100644
--- /dev/null
+++ b/arch/riscv/include/asm/crash_core.h
@@ -0,0 +1,12 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+#ifndef _RISCV_CRASH_CORE_H
+#define _RISCV_CRASH_CORE_H
+
+#include <linux/types.h>
+
+extern phys_addr_t dma32_phys_limit;
+
+#define CRASH_ALIGN			PMD_SIZE
+#define CRASH_ADDR_LOW_MAX		dma32_phys_limit
+#define CRASH_ADDR_HIGH_MAX		memblock_end_of_DRAM()
+
+#endif
diff --git a/arch/riscv/Kconfig b/arch/riscv/Kconfig
--- a/arch/riscv/Kconfig
+++ b/arch/riscv/Kconfig
@@ -xxx,6 +xxx,9 @@ config ARCH_SUPPORTS_KEXEC_PURGATORY
 config ARCH_SUPPORTS_CRASH_DUMP
 	def_bool y
 
+config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
+	def_bool CRASH_CORE
+
 config COMPAT
 	bool "Kernel support for 32-bit U-mode"
 	default 64BIT
diff --git a/arch/riscv/mm/init.c b/arch/riscv/mm/init.c
--- a/arch/riscv/mm/init.c
+++ b/arch/riscv/mm/init.c
@@ -67,7 +67,7 @@ uintptr_t _dtb_early_pa __initdata;
 
-static phys_addr_t dma32_phys_limit __initdata;
+phys_addr_t dma32_phys_limit __initdata;
 
 static void __init zone_sizes_init(void)
 
@@ -1,151 +1,26 @@
-static int __init reserve_crashkernel_low(unsigned long long low_size)  {
-	unsigned long long low_base;
-
-	low_base = memblock_phys_alloc_range(low_size, PMD_SIZE, 0, dma32_phys_limit);
-	if (!low_base) {
-		pr_err("cannot allocate crashkernel low memory (size:0x%llx).\n", low_size);
-		return -ENOMEM;
-	}
-
-	pr_info("crashkernel low memory reserved: 0x%016llx - 0x%016llx (%lld MB)\n",
-		low_base, low_base + low_size, low_size >> 20);
-
-	crashk_low_res.start = low_base;
-	crashk_low_res.end = low_base + low_size - 1;
-
-	return 0;
-}
-
-static void __init reserve_crashkernel(void)  {
-	unsigned long long crash_base = 0;
-	unsigned long long crash_size = 0;
-	unsigned long long crash_low_size = 0;
-	unsigned long search_start = memblock_start_of_DRAM();
-	unsigned long search_end = (unsigned long)dma32_phys_limit;
+static void __init arch_reserve_crashkernel(void)  {
+	unsigned long long low_size = 0;
+	unsigned long long crash_base, crash_size;
 	char *cmdline = boot_command_line;
-	bool fixed_base = false;
 	bool high = false;
-
-	int ret = 0;
+	int ret;
 
 	if (!IS_ENABLED(CONFIG_KEXEC_CORE))
 		return;
@@ -156,111 +31,17 @@
 		pr_info("crashkernel: ignoring reservation request\n");
 		return;
 	}
 
 	ret = parse_crashkernel(cmdline, memblock_phys_mem_size(),
-				&crash_size, &crash_base);
-	if (ret == -ENOENT) {
-		/* Fallback to crashkernel=X,[high,low] */
-		ret = parse_crashkernel_high(cmdline, 0, &crash_size, &crash_base);
-		if (ret || !crash_size)
-			return;
-
-		/*
-		 * crashkernel=Y,low is valid only when crashkernel=X,high
-		 * is passed.
-		 */
-		ret = parse_crashkernel_low(cmdline, 0, &crash_low_size, &crash_base);
-		if (ret == -ENOENT)
-			crash_low_size = DEFAULT_CRASH_KERNEL_LOW_SIZE;
-		else if (ret)
-			return;
-
-		search_start = (unsigned long)dma32_phys_limit;
-		search_end = memblock_end_of_DRAM();
-		high = true;
-	} else if (ret || !crash_size) {
-		/* Invalid argument value specified */
+				&crash_size, &crash_base,
+				&low_size, &high);
+	if (ret)
 		return;
-	}
-
-	crash_size = PAGE_ALIGN(crash_size);
-
-	if (crash_base) {
-		fixed_base = true;
-		search_start = crash_base;
-		search_end = crash_base + crash_size;
-	}
-
-	/*
-	 * Current riscv boot protocol requires 2MB alignment for
-	 * RV64 and 4MB alignment for RV32 (hugepage size)
-	 *
-	 * Try to alloc from 32bit addressible physical memory so that
-	 * swiotlb can work on the crash kernel.
-	 */
-	crash_base = memblock_phys_alloc_range(crash_size, PMD_SIZE,
-					       search_start, search_end);
-	if (crash_base == 0) {
-		/*
-		 * For crashkernel=size[KMG]@offset[KMG], print out failure
-		 * message if can't reserve the specified region.
-		 */
-		if (fixed_base) {
-			pr_warn("crashkernel: allocating failed with given size@offset\n");
-			return;
-		}
-
-		if (high) {
-			/*
-			 * For crashkernel=size[KMG],high, if the first attempt was
-			 * for high memory, fall back to low memory.
-			 */
-			search_start = memblock_start_of_DRAM();
-			search_end = (unsigned long)dma32_phys_limit;
-		} else {
-			/*
-			 * For crashkernel=size[KMG], if the first attempt was for
-			 * low memory, fall back to high memory, the minimum required
-			 * low memory will be reserved later.
-			 */
-			search_start = (unsigned long)dma32_phys_limit;
-			search_end = memblock_end_of_DRAM();
-			crash_low_size = DEFAULT_CRASH_KERNEL_LOW_SIZE;
-		}
-
-		crash_base = memblock_phys_alloc_range(crash_size, PMD_SIZE,
-						       search_start, search_end);
-		if (crash_base == 0) {
-			pr_warn("crashkernel: couldn't allocate %lldKB\n",
-				crash_size >> 10);
-			return;
-		}
-	}
-
-	if ((crash_base >= dma32_phys_limit) && crash_low_size &&
-	     reserve_crashkernel_low(crash_low_size)) {
-		memblock_phys_free(crash_base, crash_size);
-		return;
-	}
-
-	pr_info("crashkernel: reserved 0x%016llx - 0x%016llx (%lld MB)\n",
-		crash_base, crash_base + crash_size, crash_size >> 20);
-
-	crashk_res.start = crash_base;
-	crashk_res.end = crash_base + crash_size - 1;
+
+	reserve_crashkernel_generic(cmdline, crash_size, crash_base,
+				    low_size, high);
 }
 
 void __init misc_mem_init(void)  {
@@ -268,7 +49,7 @@
 	arch_numa_init();
 	sparse_init();
 	zone_sizes_init();
-	reserve_crashkernel();
+	arch_reserve_crashkernel();
 	memblock_dump_all();
 }
```

### Y

```diff
diff --git a/arch/riscv/Kconfig b/arch/riscv/Kconfig
--- a/arch/riscv/Kconfig
+++ b/arch/riscv/Kconfig
@@ -xxx,6 +xxx,9 @@ config ARCH_SUPPORTS_KEXEC_PURGATORY
 config ARCH_SUPPORTS_CRASH_DUMP
 	def_bool y
 
+config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
+	def_bool CRASH_CORE
+
 config COMPAT
 	bool "Kernel support for 32-bit U-mode"
 	default 64BIT
diff --git a/arch/riscv/include/asm/crash_core.h b/arch/riscv/include/asm/crash_core.h
new file mode 100644
--- /dev/null
+++ b/arch/riscv/include/asm/crash_core.h
@@ -0,0 +1,12 @@
+/* SPDX-License-Identifier: GPL-2.0-only */
+#ifndef _RISCV_CRASH_CORE_H
+#define _RISCV_CRASH_CORE_H
+
+#include <linux/types.h>
+
+#define CRASH_ALIGN			PMD_SIZE
+
+extern phys_addr_t dma32_phys_limit;
+#define CRASH_ADDR_LOW_MAX		dma32_phys_limit
+#define CRASH_ADDR_HIGH_MAX		memblock_end_of_DRAM()
+#endif
diff --git a/arch/riscv/mm/init.c b/arch/riscv/mm/init.c
--- a/arch/riscv/mm/init.c
+++ b/arch/riscv/mm/init.c
@@ -66,7 +66,7 @@ extern char _start[];
 void *_dtb_early_va __initdata;
 uintptr_t _dtb_early_pa __initdata;
 
-static phys_addr_t dma32_phys_limit __initdata;
+phys_addr_t dma32_phys_limit __initdata;
 
 static void __init zone_sizes_init(void)
 
@@ -1,160 +1,32 @@
-static int __init reserve_crashkernel_low(unsigned long long low_size)  {
-	unsigned long long low_base;
-
-	low_base = memblock_phys_alloc_range(low_size, PMD_SIZE, 0, dma32_phys_limit);
-	if (!low_base) {
-		pr_err("cannot allocate crashkernel low memory (size:0x%llx).\n", low_size);
-		return -ENOMEM;
-	}
-
-	pr_info("crashkernel low memory reserved: 0x%016llx - 0x%016llx (%lld MB)\n",
-		low_base, low_base + low_size, low_size >> 20);
-
-	crashk_low_res.start = low_base;
-	crashk_low_res.end = low_base + low_size - 1;
-
-	return 0;
-}
-
-static void __init reserve_crashkernel(void)  {
-	unsigned long long crash_base = 0;
-	unsigned long long crash_size = 0;
-	unsigned long long crash_low_size = 0;
-	unsigned long search_start = memblock_start_of_DRAM();
-	unsigned long search_end = (unsigned long)dma32_phys_limit;
+static void __init arch_reserve_crashkernel(void)  {
+	unsigned long long low_size = 0;
+	unsigned long long crash_base, crash_size;
 	char *cmdline = boot_command_line;
-	bool fixed_base = false;
 	bool high = false;
-
-	int ret = 0;
+	int ret;
 
 	if (!IS_ENABLED(CONFIG_KEXEC_CORE))
 		return;
@@ -165,125 +37,15 @@
 		return;
 	}
 
 	ret = parse_crashkernel(cmdline, memblock_phys_mem_size(),
-				&crash_size, &crash_base);
-	if (ret == -ENOENT) {
-		/* Fallback to crashkernel=X,[high,low] */
-		ret = parse_crashkernel_high(cmdline, 0, &crash_size, &crash_base);
-		if (ret || !crash_size)
-			return;
-
-		/*
-		 * crashkernel=Y,low is valid only when crashkernel=X,high
-		 * is passed.
-		 */
-		ret = parse_crashkernel_low(cmdline, 0, &crash_low_size, &crash_base);
-		if (ret == -ENOENT)
-			crash_low_size = DEFAULT_CRASH_KERNEL_LOW_SIZE;
-		else if (ret)
-			return;
-
-		search_start = (unsigned long)dma32_phys_limit;
-		search_end = memblock_end_of_DRAM();
-		high = true;
-	} else if (ret || !crash_size) {
-		/* Invalid argument value specified */
+				&crash_size, &crash_base,
+				&low_size, &high);
+	if (ret)
 		return;
-	}
-
-	crash_size = PAGE_ALIGN(crash_size);
-
-	if (crash_base) {
-		fixed_base = true;
-		search_start = crash_base;
-		search_end = crash_base + crash_size;
-	}
-
-	/*
-	 * Current riscv boot protocol requires 2MB alignment for
-	 * RV64 and 4MB alignment for RV32 (hugepage size)
-	 *
-	 * Try to alloc from 32bit addressible physical memory so that
-	 * swiotlb can work on the crash kernel.
-	 */
-	crash_base = memblock_phys_alloc_range(crash_size, PMD_SIZE,
-					       search_start, search_end);
-	if (crash_base == 0) {
-		/*
-		 * For crashkernel=size[KMG]@offset[KMG], print out failure
-		 * message if can't reserve the specified region.
-		 */
-		if (fixed_base) {
-			pr_warn("crashkernel: allocating failed with given size@offset\n");
-			return;
-		}
-
-		if (high) {
-			/*
-			 * For crashkernel=size[KMG],high, if the first attempt was
-			 * for high memory, fall back to low memory.
-			 */
-			search_start = memblock_start_of_DRAM();
-			search_end = (unsigned long)dma32_phys_limit;
-		} else {
-			/*
-			 * For crashkernel=size[KMG], if the first attempt was for
-			 * low memory, fall back to high memory, the minimum required
-			 * low memory will be reserved later.
-			 */
-			search_start = (unsigned long)dma32_phys_limit;
-			search_end = memblock_end_of_DRAM();
-			crash_low_size = DEFAULT_CRASH_KERNEL_LOW_SIZE;
-		}
-
-		crash_base = memblock_phys_alloc_range(crash_size, PMD_SIZE,
-						       search_start, search_end);
-		if (crash_base == 0) {
-			pr_warn("crashkernel: couldn't allocate %lldKB\n",
-				crash_size >> 10);
-			return;
-		}
-	}
-
-	if ((crash_base >= dma32_phys_limit) && crash_low_size &&
-	     reserve_crashkernel_low(crash_low_size)) {
-		memblock_phys_free(crash_base, crash_size);
-		return;
-	}
-
-	pr_info("crashkernel: reserved 0x%016llx - 0x%016llx (%lld MB)\n",
-		crash_base, crash_base + crash_size, crash_size >> 20);
-
-	crashk_res.start = crash_base;
-	crashk_res.end = crash_base + crash_size - 1;
+
+	reserve_crashkernel_generic(cmdline, crash_size, crash_base,
+				    low_size, high);
 }
 
 void __init misc_mem_init(void)  {
@@ -291,7 +53,7 @@
 	arch_numa_init();
 	sparse_init();
 	zone_sizes_init();
-	reserve_crashkernel();
+	arch_reserve_crashkernel();
 	memblock_dump_all();
 }
```

## V007

### 真实补丁T

```diff
commit ec87a82ca8740891bce9e93e79ea2cd6c2d70ac8
Subject: KVM: riscv: Fix Spectre-v1 in AIA CSR access


diff --git a/arch/riscv/kvm/aia.c b/arch/riscv/kvm/aia.c
index cac3c2b51d72..38de97d2f5b8 100644
--- a/arch/riscv/kvm/aia.c
+++ b/arch/riscv/kvm/aia.c
@@ -13,6 +13,7 @@
 #include <linux/irqchip/riscv-imsic.h>
 #include <linux/irqdomain.h>
 #include <linux/kvm_host.h>
+#include <linux/nospec.h>
 #include <linux/percpu.h>
 #include <linux/spinlock.h>
 #include <asm/cpufeature.h>
@@ -182,10 +183,13 @@ int kvm_riscv_vcpu_aia_get_csr(struct kvm_vcpu *vcpu,
 			       unsigned long *out_val)
 {
 	struct kvm_vcpu_aia_csr *csr = &vcpu->arch.aia_context.guest_csr;
+	unsigned long regs_max = sizeof(struct kvm_riscv_aia_csr) / sizeof(unsigned long);
 
-	if (reg_num >= sizeof(struct kvm_riscv_aia_csr) / sizeof(unsigned long))
+	if (reg_num >= regs_max)
 		return -ENOENT;
 
+	reg_num = array_index_nospec(reg_num, regs_max);
+
 	*out_val = 0;
 	if (kvm_riscv_aia_available())
 		*out_val = ((unsigned long *)csr)[reg_num];
@@ -198,10 +202,13 @@ int kvm_riscv_vcpu_aia_set_csr(struct kvm_vcpu *vcpu,
 			       unsigned long val)
 {
 	struct kvm_vcpu_aia_csr *csr = &vcpu->arch.aia_context.guest_csr;
+	unsigned long regs_max = sizeof(struct kvm_riscv_aia_csr) / sizeof(unsigned long);
 
-	if (reg_num >= sizeof(struct kvm_riscv_aia_csr) / sizeof(unsigned long))
+	if (reg_num >= regs_max)
 		return -ENOENT;
 
+	reg_num = array_index_nospec(reg_num, regs_max);
+
 	if (kvm_riscv_aia_available()) {
 		((unsigned long *)csr)[reg_num] = val;
```

### X

```diff
（没有补丁）
```

### Y

```diff
（没有补丁）
```

## V011

### 真实补丁T

```diff
commit cc98f006c63c8e9f825ca5f89388fe5ace6a5c74
Subject: KVM: riscv: Use an rwlock for mmu_lock


diff --git a/arch/riscv/include/asm/kvm_host.h b/arch/riscv/include/asm/kvm_host.h
index 75b0a951c1bc..60017ceec9d2 100644
--- a/arch/riscv/include/asm/kvm_host.h
+++ b/arch/riscv/include/asm/kvm_host.h
@@ -48,6 +48,8 @@
 
 #define __KVM_HAVE_ARCH_FLUSH_REMOTE_TLBS_RANGE
 
+#define KVM_HAVE_MMU_RWLOCK
+
 #define KVM_DIRTY_LOG_MANUAL_CAPS	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | \
 					 KVM_DIRTY_LOG_INITIALLY_SET)
 
diff --git a/arch/riscv/kvm/gstage.c b/arch/riscv/kvm/gstage.c
index e020b334ae6f..d4ce5e76989c 100644
--- a/arch/riscv/kvm/gstage.c
+++ b/arch/riscv/kvm/gstage.c
@@ -414,7 +414,7 @@ bool kvm_riscv_gstage_unmap_range(struct kvm_gstage *gstage,
 		 * to prevent starvation and lockup detector warnings.
 		 */
 		if (!(gstage->flags & KVM_GSTAGE_FLAGS_LOCAL) && may_block && addr < end)
-			cond_resched_lock(&gstage->kvm->mmu_lock);
+			cond_resched_rwlock_write(&gstage->kvm->mmu_lock);
 	}
 
 	return flush;
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index da944cb68404..514f06a1f688 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -27,9 +27,9 @@ static void mmu_wp_memory_region(struct kvm *kvm, int slot)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_wp_range(&gstage, start, end);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_memslot(kvm, memslot);
 }
@@ -67,9 +67,9 @@ int kvm_riscv_mmu_ioremap(struct kvm *kvm, gpa_t gpa, phys_addr_t hpa,
 		if (ret)
 			goto out;
 
-		spin_lock(&kvm->mmu_lock);
+		write_lock(&kvm->mmu_lock);
 		ret = kvm_riscv_gstage_set_pte(&gstage, &pcache, &map);
-		spin_unlock(&kvm->mmu_lock);
+		write_unlock(&kvm->mmu_lock);
 		if (ret)
 			goto out;
 
@@ -88,9 +88,9 @@ void kvm_riscv_mmu_iounmap(struct kvm *kvm, gpa_t gpa, unsigned long size)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
@@ -143,9 +143,9 @@ void kvm_arch_flush_shadow_memslot(struct kvm *kvm,
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
 					    size >> PAGE_SHIFT);
@@ -523,7 +523,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 	if (logging && !is_write)
 		writable = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 
 	if (mmu_invalidate_retry(kvm, mmu_seq))
 		goto out_unlock;
@@ -546,7 +546,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 
 out_unlock:
 	kvm_release_faultin_page(kvm, page, ret && ret != -EEXIST, writable);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	return ret;
 }
 
@@ -576,7 +576,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 	void *pgd = NULL;
 	bool flush = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	if (kvm->arch.pgd) {
 		kvm_riscv_gstage_init(&gstage, kvm);
 		flush = kvm_riscv_gstage_unmap_range(&gstage, 0UL,
@@ -586,7 +586,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 		kvm->arch.pgd_phys = 0;
 		kvm->arch.pgd_levels = 0;
 	}
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs(kvm);
```

### X

```diff
diff --git a/arch/riscv/include/asm/kvm_host.h b/arch/riscv/include/asm/kvm_host.h
--- a/arch/riscv/include/asm/kvm_host.h
+++ b/arch/riscv/include/asm/kvm_host.h
@@ -42,6 +42,8 @@
 
 #define __KVM_HAVE_ARCH_FLUSH_REMOTE_TLBS_RANGE
 
+#define KVM_HAVE_MMU_RWLOCK
+
 #define KVM_DIRTY_LOG_MANUAL_CAPS	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | \
 					 KVM_DIRTY_LOG_INITIALLY_SET)
 
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -27,9 +27,9 @@ static void mmu_wp_memory_region(struct kvm *kvm, int slot)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_wp_range(&gstage, start, end);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_memslot(kvm, memslot);
 }
@@ -69,9 +69,9 @@ int kvm_riscv_mmu_ioremap(struct kvm *kvm, gpa_t gpa, phys_addr_t hpa,
 		if (ret)
 			goto out;
 
-		spin_lock(&kvm->mmu_lock);
+		write_lock(&kvm->mmu_lock);
 		ret = kvm_riscv_gstage_set_pte(&gstage, &pcache, &map);
-		spin_unlock(&kvm->mmu_lock);
+		write_unlock(&kvm->mmu_lock);
 		if (ret)
 			goto out;
 
@@ -89,9 +89,9 @@ void kvm_riscv_mmu_iounmap(struct kvm *kvm, gpa_t gpa, unsigned long size)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
@@ -145,9 +145,9 @@ void kvm_arch_flush_shadow_memslot(struct kvm *kvm,
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
 					    size >> PAGE_SHIFT);
@@ -490,7 +490,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 	if (logging && !is_write)
 		writable = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 
 	if (mmu_invalidate_retry(kvm, mmu_seq))
 		goto out_unlock;
@@ -513,7 +513,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 
 out_unlock:
 	kvm_release_faultin_page(kvm, page, ret && ret != -EEXIST, writable);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	return ret;
 }
 
@@ -544,7 +544,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 	void *pgd = NULL;
 	bool flush = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	if (kvm->arch.pgd) {
 		kvm_riscv_gstage_init(&gstage, kvm);
 		flush = kvm_riscv_gstage_unmap_range(&gstage, 0UL,
@@ -554,7 +554,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 		kvm->arch.pgd_phys = 0;
 		kvm->arch.pgd_levels = 0;
 	}
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs(kvm);
```

### Y

```diff
diff --git a/arch/riscv/include/asm/kvm_host.h b/arch/riscv/include/asm/kvm_host.h
--- a/arch/riscv/include/asm/kvm_host.h
+++ b/arch/riscv/include/asm/kvm_host.h
@@ -43,6 +43,8 @@
 #define KVM_DIRTY_LOG_MANUAL_CAPS	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | \
 					 KVM_DIRTY_LOG_INITIALLY_SET)
 
+#define KVM_HAVE_MMU_RWLOCK
+
 struct kvm_vm_stat {
 	struct kvm_vm_stat_generic generic;
 };
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -26,9 +26,9 @@ static void mmu_wp_memory_region(struct kvm *kvm, int slot)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_wp_range(&gstage, start, end);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_memslot(kvm, memslot);
 }
@@ -69,9 +69,9 @@ int kvm_riscv_mmu_ioremap(struct kvm *kvm, gpa_t gpa, phys_addr_t hpa,
 		if (ret)
 			goto out;
 
-		spin_lock(&kvm->mmu_lock);
+		write_lock(&kvm->mmu_lock);
 		ret = kvm_riscv_gstage_set_pte(&gstage, &pcache, &map);
-		spin_unlock(&kvm->mmu_lock);
+		write_unlock(&kvm->mmu_lock);
 		if (ret)
 			goto out;
 
@@ -91,9 +91,9 @@ void kvm_riscv_mmu_iounmap(struct kvm *kvm, gpa_t gpa, unsigned long size)
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
@@ -144,9 +144,9 @@ void kvm_arch_flush_shadow_memslot(struct kvm *kvm,
 
 	kvm_riscv_gstage_init(&gstage, kvm);
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	flush = kvm_riscv_gstage_unmap_range(&gstage, gpa, size, false);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	if (flush)
 		kvm_flush_remote_tlbs_range(kvm, gpa >> PAGE_SHIFT,
 					    size >> PAGE_SHIFT);
@@ -388,7 +388,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 	if (logging && !is_write)
 		writable = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 
 	if (mmu_invalidate_retry(kvm, mmu_seq))
 		goto out_unlock;
@@ -412,7 +412,7 @@ int kvm_riscv_mmu_map(struct kvm_vcpu *vcpu, struct kvm_memory_slot *memslot,
 
 out_unlock:
 	kvm_release_faultin_page(kvm, page, ret && ret != -EEXIST, writable);
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 	return ret;
 }
 
@@ -445,7 +445,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 	void *pgd = NULL;
 	bool flush = false;
 
-	spin_lock(&kvm->mmu_lock);
+	write_lock(&kvm->mmu_lock);
 	if (kvm->arch.pgd) {
 		kvm_riscv_gstage_init(&gstage, kvm);
 		flush = kvm_riscv_gstage_unmap_range(&gstage, 0UL,
@@ -455,7 +455,7 @@ void kvm_riscv_mmu_free_pgd(struct kvm *kvm)
 		kvm->arch.pgd_phys = 0;
 		kvm->arch.pgd_levels = 0;
 	}
-	spin_unlock(&kvm->mmu_lock);
+	write_unlock(&kvm->mmu_lock);
 
 	if (flush)
 		kvm_flush_remote_tlbs(kvm);
```
