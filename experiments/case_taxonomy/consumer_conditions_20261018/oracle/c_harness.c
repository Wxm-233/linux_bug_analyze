#include <stdio.h>
int select_relation_0(int,int,int,int,int,int,int);
int select_relation_1(int,int,int,int,int,int,int);
int select_relation_2(int,int,int,int,int,int,int);
int select_relation_3(int,int,int,int,int,int,int);
int bind_actor_group(int,int,int,int,int,int,int);
int revise_other_relations(int,int,int,int,int,int,int);
int inspect_before_revision(int,int,int,int,int,int,int);
int main(void) {
  int k,t,a,b,c,x,y,z,status;
  while (scanf("%d %d %d %d %d %d %d %d", &k,&t,&a,&b,&c,&x,&y,&z) == 8) {
    switch (k) {
    case 0: status = select_relation_0(t,a,b,c,x,y,z); break;
    case 1: status = select_relation_1(t,a,b,c,x,y,z); break;
    case 2: status = select_relation_2(t,a,b,c,x,y,z); break;
    case 3: status = select_relation_3(t,a,b,c,x,y,z); break;
    case 4: status = bind_actor_group(t,a,b,c,x,y,z); break;
    case 5: status = revise_other_relations(t,a,b,c,x,y,z); break;
    case 6: status = inspect_before_revision(t,a,b,c,x,y,z); break;
    default: return 2;
    }
    printf("%d\n", status);
  }
  return 0;
}
