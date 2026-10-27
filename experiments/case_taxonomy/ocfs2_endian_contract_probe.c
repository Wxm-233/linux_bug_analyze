/* Post-read, reduced historical expression probe for c9dff86e.
 * This is not an ocfs2 kernel build or an automatic detection result.
 * The source fields are __le* in 390ac56c:fs/ocfs2/ocfs2_fs.h:672-693.
 */
#include <endian.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>

enum {
    OCFS2_SUPER_BLOCK_FL = 0x00000020,
    OCFS2_LOCAL_ALLOC_FL = 0x00000040,
    OCFS2_CHAIN_FL = 0x00000400,
    OCFS2_DEALLOC_FL = 0x00000800,
    OCFS2_INLINE_DATA_FL = 0x0001,
};

struct disk_dinode_subset {
    uint32_t i_flags;
    uint16_t i_mode;
    uint64_t i_size;
    uint32_t i_clusters;
    uint16_t i_dyn_features;
};

static int old_has_extents(const struct disk_dinode_subset *di)
{
    if (di->i_flags & (OCFS2_SUPER_BLOCK_FL | OCFS2_LOCAL_ALLOC_FL |
                       OCFS2_CHAIN_FL | OCFS2_DEALLOC_FL))
        return 0;
    if (S_ISLNK(di->i_mode) && di->i_size && di->i_clusters == 0)
        return 0;
    if (di->i_dyn_features & OCFS2_INLINE_DATA_FL)
        return 0;
    return 1;
}

static int fixed_has_extents(const struct disk_dinode_subset *di)
{
    if (le32toh(di->i_flags) & (OCFS2_SUPER_BLOCK_FL | OCFS2_LOCAL_ALLOC_FL |
                             OCFS2_CHAIN_FL | OCFS2_DEALLOC_FL))
        return 0;
    if (S_ISLNK(le16toh(di->i_mode)) && le64toh(di->i_size) &&
        le32toh(di->i_clusters) == 0)
        return 0;
    if (le16toh(di->i_dyn_features) & OCFS2_INLINE_DATA_FL)
        return 0;
    return 1;
}

static int check(const char *label, struct disk_dinode_subset di, int wanted)
{
    int old = old_has_extents(&di);
    int fixed = fixed_has_extents(&di);
    printf("%s old=%d fixed=%d wanted=%d\n", label, old, fixed, wanted);
    return fixed != wanted;
}

int main(void)
{
    int failures = 0;
    struct disk_dinode_subset di = {0};

    di.i_flags = htole32(OCFS2_SUPER_BLOCK_FL);
    failures += check("special_flag", di, 0);

    di = (struct disk_dinode_subset){0};
    di.i_mode = htole16(S_IFLNK | 0600);
    di.i_size = htole64(12);
    failures += check("fast_symlink", di, 0);

    di = (struct disk_dinode_subset){0};
    di.i_dyn_features = htole16(OCFS2_INLINE_DATA_FL);
    failures += check("inline_data", di, 0);

    di = (struct disk_dinode_subset){0};
    di.i_mode = htole16(S_IFREG | 0644);
    di.i_clusters = htole32(1);
    failures += check("ordinary_extent", di, 1);

    return failures ? 1 : 0;
}
