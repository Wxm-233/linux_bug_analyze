/* Test doubles only. STE writes are observations, not device transactions. */
#include <stdio.h>
#include <stdbool.h>
#include <errno.h>
#include <stdlib.h>
enum { ARM_SMMU_DOMAIN_S1, ARM_SMMU_DOMAIN_S2, ARM_SMMU_DOMAIN_BYPASS };
enum { ABORT_STATE, BYPASS_STATE, TRANSLATED_STATE };
#define IOMMU_NO_PASID 0
struct arm_smmu_domain;
struct iommu_domain { struct arm_smmu_domain *owner; };
struct arm_smmu_device { struct { int iopf; } evtq; };
struct arm_smmu_domain {
    struct arm_smmu_device *smmu;
    int stage, devices_lock, devices, init_mutex, cd;
};
struct arm_smmu_master {
    struct arm_smmu_domain *domain;
    struct arm_smmu_device *smmu;
    bool ats_enabled;
    int domain_head;
    struct { void *cdtab; } cd_table;
};
struct iommu_fwspec { int unused; };
struct device {
    struct arm_smmu_master *master;
    struct { bool require_direct; } *iommu;
};
struct arm_smmu_ste { int state; };
static bool disable_bypass;
static int arm_smmu_asid_lock;
static int fail_alloc, fail_write, fail_sva;
static int trace[16], ntrace;
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags)=0; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); } while (0)
#define mutex_lock(lock) ((void)(lock))
#define mutex_unlock(lock) ((void)(lock))
#define list_del(node) ((void)(node))
#define list_add(node, head) do { (void)(node); (void)(head); } while (0)
#define dev_err(...) ((void)0)
#define WARN_ON(x) (x)
#define kfree(x) ((void)(x))
static struct arm_smmu_master *dev_iommu_priv_get(struct device *d) { return d->master; }
static struct iommu_fwspec *dev_iommu_fwspec_get(struct device *d) {
    static struct iommu_fwspec f; (void)d; return &f;
}
static struct arm_smmu_domain *to_smmu_domain(struct iommu_domain *d) { return d->owner; }
static bool arm_smmu_master_sva_enabled(struct arm_smmu_master *m) { (void)m; return fail_sva; }
static void arm_smmu_disable_ats(struct arm_smmu_master *m) { m->ats_enabled=false; }
static void arm_smmu_enable_ats(struct arm_smmu_master *m) { (void)m; }
static bool arm_smmu_ats_supported(struct arm_smmu_master *m) { (void)m; return false; }
static void arm_smmu_make_abort_ste(struct arm_smmu_ste *s) { s->state=ABORT_STATE; }
static void arm_smmu_make_bypass_ste(struct arm_smmu_ste *s) { s->state=BYPASS_STATE; }
static void arm_smmu_make_s2_domain_ste(struct arm_smmu_ste *s, struct arm_smmu_master *m, struct arm_smmu_domain *d) {
    (void)m; (void)d; s->state=TRANSLATED_STATE;
}
static void arm_smmu_make_cdtable_ste(struct arm_smmu_ste *s, struct arm_smmu_master *m) {
    (void)m; s->state=TRANSLATED_STATE;
}
static void arm_smmu_install_ste_for_dev(struct arm_smmu_master *m, struct arm_smmu_ste *s) {
    (void)m; if (ntrace>=16) abort(); trace[ntrace++]=s->state;
}
static int arm_smmu_write_ctx_desc(struct arm_smmu_master *m, int pasid, void *cd) {
    (void)m; (void)pasid; return cd && fail_write ? -ENOMEM : 0;
}
static int arm_smmu_alloc_cd_tables(struct arm_smmu_master *m) {
    static int table; if (fail_alloc) return -ENOMEM; m->cd_table.cdtab=&table; return 0;
}
static int arm_smmu_domain_finalise(struct iommu_domain *d) { (void)d; return 0; }
static void iopf_queue_remove_device(int q, struct device *d) { (void)q; (void)d; }
static void arm_smmu_disable_pasid(struct arm_smmu_master *m) { (void)m; }
static void arm_smmu_remove_master(struct arm_smmu_master *m) { (void)m; }
static void arm_smmu_free_cd_tables(struct arm_smmu_master *m) { (void)m; }

/* EXTRACTED_FUNCTIONS */

int main(void) {
    /* 0 isolated->S2; 1 identity->DMA-with-direct; 2/3 S1 allocation/CD failure;
       4 SVA preflight rejection; 5/6 release without/with required direct. */
    for (int scenario=0; scenario<7; scenario++) for (int disable=0; disable<2; disable++) {
        struct arm_smmu_device hw={0};
        struct arm_smmu_domain old={.smmu=&hw, .stage=ARM_SMMU_DOMAIN_S2};
        struct arm_smmu_domain next={.smmu=&hw,
            .stage=(scenario==2 || scenario==3) ? ARM_SMMU_DOMAIN_S1 : ARM_SMMU_DOMAIN_S2};
        struct iommu_domain domain={.owner=&next};
        struct arm_smmu_master master={.domain=&old, .smmu=&hw};
        struct device dev={.master=&master};
        typeof(*dev.iommu) props={.require_direct=scenario==1 || scenario==6};
        dev.iommu=&props;
        if (scenario==1) old.stage=ARM_SMMU_DOMAIN_BYPASS;
        disable_bypass=disable; fail_alloc=scenario==2; fail_write=scenario==3; fail_sva=scenario==4;
        /* ABORT_STATE here means inaccessible, including an empty translated domain.
           It does not claim the real blocking fallback uses an ABORT STE encoding. */
        ntrace=1; trace[0]=scenario==1 ? BYPASS_STATE : (scenario>=5 ? TRANSLATED_STATE : ABORT_STATE);
        int rc=0;
        if (scenario>=5) arm_smmu_release_device(&dev);
        else rc=arm_smmu_attach_dev(&domain, &dev);
        printf("{\"scenario\":%d,\"disable_bypass\":%d,\"rc\":%d,\"trace\":[",scenario,disable,rc);
        for (int j=0;j<ntrace;j++) printf("%s%d",j?",":"",trace[j]);
        printf("]}\n");
    }
}
