_Static_assert(IOMMU_READ == 1 && IOMMU_WRITE == 2, "update input contract encoding");
_Static_assert(DMA_PTE_READ == 1 && DMA_PTE_WRITE == 2, "update output contract encoding");
int main(void) {
    for (int first=0; first<2; first++) {
        for (int requested=1; requested<=3; requested++) {
            uint64_t attr=encode(first,requested);
            printf("{\"first\":%d,\"requested\":%d,\"encoded\":%llu}\n",
                   first,requested,(unsigned long long)(attr & (DMA_PTE_READ|DMA_PTE_WRITE)));
        }
    }
}
