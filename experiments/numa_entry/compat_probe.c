/* Freestanding i386 executable: genuine 32-bit process, no libc dependency. */
typedef unsigned int u32;
extern int call6(int,int,int,int,int,int,int);
static int sc(int n,int a,int b,int c,int d,int e){return call6(n,a,b,c,d,e,0);}
static void text(const char *s){int n=0;while(s[n])n++;sc(4,1,(int)s,n,0,0);}
static void number(int n){char b[24];unsigned int v=n<0?-(unsigned int)n:(unsigned int)n;int k=0;do{b[k++]='0'+v%10;v/=10;}while(v);if(n<0)b[k++]='-';while(k)sc(4,1,(int)&b[--k],1,0,0);}
static void field(const char *s,int n){text(s);number(n);}
static u32 allowed[1024],actual[1024];
int main(void){
 int rc=sc(275,0,(int)allowed,32768,0,4);if(rc){field("environment_blocked=",rc);text("\n");return 77;}
 int node=-1;for(int i=0;i<32768;i++)if(allowed[i/32]&(1U<<(i%32))){node=i;break;}
 if(node<0||node>=32)return 78;
 u32 args[]={0,8192,3,0x22,(u32)-1,0};
 unsigned char *mem=(void*)sc(90,(int)args,0,0,0,0);
 if((u32)mem>=(u32)-4095)return 79;
 if(sc(125,(int)(mem+4096),4096,0,0,0))return 80;
 const int counts[]={65,96,1025,1056};
 for(int i=0;i<4;i++)for(int padded=0;padded<2;padded++)for(int tail=0;tail<2;tail++){
  int bits=counts[i],maxnode=bits+1;
  int bytes=padded?((maxnode+63)/64)*8:((maxnode+31)/32)*4;
  for(int j=0;j<4096;j++)mem[j]=0;
  unsigned char *p=mem+4096-bytes;p[node/8]|=1U<<(node%8);
  if(tail)p[(bits-1)/8]|=1U<<((bits-1)%8);
  int set=sc(276,2,(int)p,maxnode,0,0),mode=-1;
  for(int j=0;j<1024;j++)actual[j]=0;
  int get=sc(275,(int)&mode,(int)actual,32768,0,0),page_node=-1,page_rc=-1;
  if(set==0){
   u32 allocation_args[]={0,4096,3,0x22,(u32)-1,0};
   unsigned char *allocation=(void*)sc(90,(int)allocation_args,0,0,0,0);
   if((u32)allocation>=(u32)-4095)return 82;
   *(volatile unsigned char*)allocation=1;
   page_rc=sc(275,(int)&page_node,0,0,(int)allocation,3);
   sc(91,(int)allocation,4096,0,0,0);
  }
  field("{\"bits\":",bits);field(",\"maxnode\":",maxnode);field(",\"bytes\":",bytes);field(",\"padding64\":",padded);field(",\"tail\":",tail);
  field(",\"set_rc\":",set);field(",\"get_rc\":",get);field(",\"mode\":",mode);field(",\"mask0\":",actual[0]);field(",\"page_query_rc\":",page_rc);field(",\"page_node\":",page_node);text("}\n");
  if(sc(276,0,0,0,0,0))return 81;
 }
 sc(91,(int)mem,8192,0,0,0);return 0;
}
