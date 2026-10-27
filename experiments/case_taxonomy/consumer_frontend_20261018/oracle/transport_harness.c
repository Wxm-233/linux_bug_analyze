#include <stdio.h>
int empty_relation_pass(int,int,int,int,int,int,int,int);
int singleton_relation_pass(int,int,int,int,int,int,int,int);
int choose_then_test_relation(int,int,int,int,int,int,int,int);
int record_before_revision(int,int,int,int,int,int,int,int);
int omit_focus_and_relate(int,int,int,int,int,int,int,int);
int selected_payload_gate(int,int,int,int,int,int,int,int);
int main(void) {
  int k,a,b,c,d,e,f,g,h,answer;
  while (scanf("%d %d %d %d %d %d %d %d %d",&k,&a,&b,&c,&d,&e,&f,&g,&h)==9) {
    switch(k) {
    case 0: answer=empty_relation_pass(a,b,c,d,e,f,g,h); break;
    case 1: answer=singleton_relation_pass(a,b,c,d,e,f,g,h); break;
    case 2: answer=choose_then_test_relation(a,b,c,d,e,f,g,h); break;
    case 3: answer=record_before_revision(a,b,c,d,e,f,g,h); break;
    case 4: answer=omit_focus_and_relate(a,b,c,d,e,f,g,h); break;
    case 5: answer=selected_payload_gate(a,b,c,d,e,f,g,h); break;
    default:return 2;
    }
    printf("%d\n",answer);
  }
  return 0;
}
