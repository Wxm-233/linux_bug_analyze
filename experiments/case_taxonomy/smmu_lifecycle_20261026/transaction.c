
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <assert.h>
typedef unsigned ioasid_t;
struct device {int id;};
struct iommu_domain;
struct domain_ops {int (*set_dev_pasid)(struct iommu_domain*,struct device*,ioasid_t);};
struct iommu_domain {struct domain_ops *ops;};
struct group_device {struct device *dev;};
struct iommu_group {int mutex; void *pasid_array;struct group_device devices[3];};
struct iommu_ops {void (*remove_dev_pasid)(struct device*,ioasid_t);};
static struct iommu_group g;
static int fail=-1,no_group,insert_error,active[3],calls,removes;
#define GFP_KERNEL 0
#define for_each_group_device(group,device) for(device=(group)->devices;device<(group)->devices+3;device++)
#define WARN_ON(x) assert(!(x))
static void event(const char *name,int id){printf("%s %d %d %d\n",name,id,g.pasid_array!=NULL,g.mutex);}
static void mutex_lock(int *p){assert(!*p);*p=1;}
static void mutex_unlock(int *p){assert(*p);*p=0;}
static struct iommu_group *iommu_group_get(struct device*d){(void)d;return no_group?NULL:&g;}
static void iommu_group_put(struct iommu_group*p){assert(p==&g);}
static void *xa_cmpxchg(void **p,ioasid_t id,void *old,void *v,int flags){(void)id;(void)old;(void)flags;if(insert_error)return(void*)-12L;void*r=*p;if(!r)*p=v;event("publish",-1);return r;}
static int xa_err(void*p){return p==(void*)-12L?-12:0;}
static void *xa_erase(void **p,ioasid_t id){(void)id;void*r=*p;event("erase",-1);*p=NULL;return r;}
static int set(struct iommu_domain*d,struct device*v,ioasid_t id){(void)id;assert(g.mutex&&g.pasid_array==d);calls++;event("set",v->id);if(v->id==fail)return-EIO;active[v->id]=1;return 0;}
static void remove_one(struct device*v,ioasid_t id){(void)id;assert(g.mutex&&g.pasid_array);removes++;event("remove",v->id);active[v->id]=0;}
static struct iommu_ops ops={remove_one};
static const struct iommu_ops *dev_iommu_ops(struct device*d){(void)d;return &ops;}
static int __iommu_set_group_pasid(struct iommu_domain *domain,
				   struct iommu_group *group, ioasid_t pasid)
{
	struct group_device *device;
	int ret = 0;

	for_each_group_device(group, device) {
		ret = domain->ops->set_dev_pasid(domain, device->dev, pasid);
		if (ret)
			break;
	}

	return ret;
}
static void __iommu_remove_group_pasid(struct iommu_group *group,
				       ioasid_t pasid)
{
	struct group_device *device;
	const struct iommu_ops *ops;

	for_each_group_device(group, device) {
		ops = dev_iommu_ops(device->dev);
		ops->remove_dev_pasid(device->dev, pasid);
	}
}
int iommu_attach_device_pasid(struct iommu_domain *domain,
			      struct device *dev, ioasid_t pasid)
{
	struct iommu_group *group;
	void *curr;
	int ret;

	if (!domain->ops->set_dev_pasid)
		return -EOPNOTSUPP;

	group = iommu_group_get(dev);
	if (!group)
		return -ENODEV;

	mutex_lock(&group->mutex);
	curr = xa_cmpxchg(&group->pasid_array, pasid, NULL, domain, GFP_KERNEL);
	if (curr) {
		ret = xa_err(curr) ? : -EBUSY;
		goto out_unlock;
	}

	ret = __iommu_set_group_pasid(domain, group, pasid);
	if (ret) {
		__iommu_remove_group_pasid(group, pasid);
		xa_erase(&group->pasid_array, pasid);
	}
out_unlock:
	mutex_unlock(&group->mutex);
	iommu_group_put(group);

	return ret;
}
void iommu_detach_device_pasid(struct iommu_domain *domain, struct device *dev,
			       ioasid_t pasid)
{
	struct iommu_group *group = iommu_group_get(dev);

	mutex_lock(&group->mutex);
	__iommu_remove_group_pasid(group, pasid);
	WARN_ON(xa_erase(&group->pasid_array, pasid) != domain);
	mutex_unlock(&group->mutex);

	iommu_group_put(group);
}
int main(int argc,char**argv){assert(argc==2);int mode=atoi(argv[1]);struct device ds[3]={{0},{1},{2}};struct domain_ops dop={set};struct iommu_domain domain={&dop},other={&dop};for(int i=0;i<3;i++)g.devices[i].dev=&ds[i];
if(mode>=1&&mode<=3)fail=mode-1;
if(mode==4)g.pasid_array=&other;
if(mode==5)insert_error=1;
if(mode==6)no_group=1;
if(mode==7)dop.set_dev_pasid=NULL;
int ret=iommu_attach_device_pasid(&domain,&ds[0],7);
if(mode==8){assert(!ret);iommu_detach_device_pasid(&domain,&ds[0],7);}
assert(!g.mutex);
if(mode>=1&&mode<=3){assert(ret==-EIO&&calls==mode&&removes==3&&!g.pasid_array);}
if(mode==0)assert(!ret&&calls==3&&removes==0&&g.pasid_array==&domain);
if(mode==4)assert(ret==-EBUSY&&!calls&&!removes&&g.pasid_array==&other);
if(mode==5)assert(ret==-ENOMEM&&!calls&&!removes&&!g.pasid_array);
if(mode==6)assert(ret==-ENODEV&&!calls&&!removes);
if(mode==7)assert(ret==-EOPNOTSUPP&&!calls&&!removes);
if(mode==8)assert(!ret&&calls==3&&removes==3&&!g.pasid_array);
printf("result %d %d %d %d %d\n",ret,calls,removes,g.pasid_array!=NULL,active[0]+active[1]+active[2]);return 0;}
