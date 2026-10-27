
#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <assert.h>
struct virtio_device;
struct config {void (*reset)(struct virtio_device*);void (*synchronize_cbs)(struct virtio_device*);};
struct virtio_device {struct config *config;};
struct pci_dev {int irq;};
struct virtio_pci_modern_device {int unused;};
struct virtio_pci_device {struct virtio_device vdev;struct virtio_pci_modern_device mdev;bool intx_enabled;int msix_vectors;struct pci_dev *pci_dev;};
static int delay,reads,irq_count,rcus,breaks,cleanups;
static struct virtio_pci_device *to_vp_device(struct virtio_device*d){return (struct virtio_pci_device*)d;}
static void synchronize_irq(int i){irq_count++;printf("SYNC_IRQ %d\n",i);}
static int pci_irq_vector(struct pci_dev*p,int i){(void)p;return 100+i;}
static void synchronize_rcu(void){rcus++;puts("SYNC_RCU");}
static void __attribute__((unused)) virtio_break_device(struct virtio_device*d){(void)d;breaks++;puts("BREAK");}
static void vp_modern_set_status(struct virtio_pci_modern_device*d,int s){(void)d;assert(s==0);puts("STATUS_WRITE_ZERO");}
static int vp_modern_get_status(struct virtio_pci_modern_device*d){(void)d;int s=reads++<delay;printf("STATUS_READ %d\n",s);return s;}
static void msleep(int n){assert(n==1);puts("SLEEP");}
static void vp_modern_avq_cleanup(struct virtio_device*d){(void)d;cleanups++;puts("AVQ_CLEANUP");}
void vp_synchronize_vectors(struct virtio_device *vdev)
{
	struct virtio_pci_device *vp_dev = to_vp_device(vdev);
	int i;

	if (vp_dev->intx_enabled)
		synchronize_irq(vp_dev->pci_dev->irq);

	for (i = 0; i < vp_dev->msix_vectors; ++i)
		synchronize_irq(pci_irq_vector(vp_dev->pci_dev, i));
}
static inline
void virtio_synchronize_cbs(struct virtio_device *dev)
{
	if (dev->config->synchronize_cbs) {
		dev->config->synchronize_cbs(dev);
	} else {
		/*
		 * A best effort fallback to synchronize with
		 * interrupts, preemption and softirq disabled
		 * regions. See comment above synchronize_rcu().
		 */
		synchronize_rcu();
	}
}
static void vp_reset(struct virtio_device *vdev)
{
	struct virtio_pci_device *vp_dev = to_vp_device(vdev);
	struct virtio_pci_modern_device *mdev = &vp_dev->mdev;

	/* 0 status means a reset. */
	vp_modern_set_status(mdev, 0);
	/* After writing 0 to device_status, the driver MUST wait for a read of
	 * device_status to return 0 before reinitializing the device.
	 * This will flush out the status write, and flush in device writes,
	 * including MSI-X interrupts, if any.
	 */
	while (vp_modern_get_status(mdev))
		msleep(1);

	vp_modern_avq_cleanup(vdev);

	/* Flush pending VQ/configuration callbacks. */
	vp_synchronize_vectors(vdev);
}
void virtio_reset_device(struct virtio_device *dev)
{
#ifdef CONFIG_VIRTIO_HARDEN_NOTIFICATION
	/*
	 * The below virtio_synchronize_cbs() guarantees that any
	 * interrupt for this line arriving after
	 * virtio_synchronize_vqs() has completed is guaranteed to see
	 * vq->broken as true.
	 */
	virtio_break_device(dev);
	virtio_synchronize_cbs(dev);
#endif

	dev->config->reset(dev);
}
int main(int argc,char**argv){assert(argc==5);int cb=atoi(argv[1]),intx=atoi(argv[2]),vectors=atoi(argv[3]);delay=atoi(argv[4]);struct config c={.reset=vp_reset,.synchronize_cbs=cb?vp_synchronize_vectors:NULL};struct pci_dev p={.irq=17};struct virtio_pci_device d={.vdev={&c},.intx_enabled=intx,.msix_vectors=vectors,.pci_dev=&p};virtio_reset_device(&d.vdev);int hard=0;
#ifdef CONFIG_VIRTIO_HARDEN_NOTIFICATION
hard=1;
#endif
assert(breaks==hard&&rcus==hard*!cb&&irq_count==(intx+vectors)*(1+hard*cb)&&reads==delay+1&&cleanups==1);puts("RESET_RETURN");}
