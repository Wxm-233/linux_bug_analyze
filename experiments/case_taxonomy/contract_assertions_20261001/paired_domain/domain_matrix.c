/* Generated bounded integer/byte projection. No kernel translation unit.
 * memcpy models host scalar representation without alignment/aliasing claims.
 * Declared domains are checked by a separately implemented Python oracle. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <assert.h>
_Static_assert(sizeof(uint16_t)==2 && sizeof(uint32_t)==4 && sizeof(uint64_t)==8,
               "supported integer widths");
enum domain { HOST, LE, BE };
static const char *names[] = {"host", "le", "be"};
static void write_value(unsigned width, enum domain d, uint64_t value, unsigned char *p) {
    const unsigned n=width/8;
    assert(width==16 || width==32 || width==64);
    if (d==HOST) {
        if (width==16) { uint16_t v=(uint16_t)value; memcpy(p,&v,2); }
        else if (width==32) { uint32_t v=(uint32_t)value; memcpy(p,&v,4); }
        else { uint64_t v=value; memcpy(p,&v,8); }
        return;
    }
    for (unsigned i=0;i<n;++i) {
        unsigned shift=(d==LE?i:n-1-i)*8;
        p[i]=(unsigned char)(value>>shift);
    }
}
static uint64_t read_value(unsigned width, enum domain d, const unsigned char *p) {
    const unsigned n=width/8;
    assert(width==16 || width==32 || width==64);
    if (d==HOST) {
        if (width==16) { uint16_t v; memcpy(&v,p,2); return v; }
        if (width==32) { uint32_t v; memcpy(&v,p,4); return v; }
        uint64_t v; memcpy(&v,p,8); return v;
    }
    uint64_t value=0;
    for (unsigned i=0;i<n;++i) {
        unsigned shift=(d==LE?i:n-1-i)*8;
        value |= (uint64_t)p[i]<<shift;
    }
    return value;
}
static void emit(const char *tag, unsigned width, enum domain declared_write,
                 enum domain declared_read, enum domain actual_write,
                 enum domain actual_read, uint64_t value) {
    unsigned char payload[8]={0};
    write_value(width,actual_write,value,payload);
    uint64_t actual=read_value(width,actual_read,payload);
    printf("%s,%u,%s,%s,%" PRIu64 ",%" PRIu64 ",",tag,width,
           names[declared_write],names[declared_read],value,actual);
    for (unsigned i=0;i<width/8;++i) printf("%02x",(unsigned)payload[i]);
    putchar('\n');
}
int main(void) {
    uint16_t marker=0x0102; unsigned char b[2]; memcpy(b,&marker,2);
    const char *actual_host;
    if (b[0]==2 && b[1]==1) actual_host="little";
    else if(b[0]==1 && b[1]==2) actual_host="big";
    else return 2;
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    assert(strcmp(actual_host,"little")==0);
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(actual_host,"big")==0);
#else
    return 3;
#endif
    printf("META,%s,%zu,%zu,%zu\n",actual_host,sizeof(uint16_t),sizeof(uint32_t),sizeof(uint64_t));
    struct sample { unsigned width; uint64_t value; };
    const struct sample samples[] = {
        {16, UINT64_C(258)},
        {16, UINT64_C(41121)},
        {16, UINT64_C(0)},
        {32, UINT64_C(16909060)},
        {32, UINT64_C(2694947491)},
        {32, UINT64_C(0)},
        {64, UINT64_C(72623859790382856)},
        {64, UINT64_C(11574711341044573863)},
        {64, UINT64_C(0)},
    };
    for(size_t i=0;i<sizeof(samples)/sizeof(samples[0]);++i)
        for(enum domain w=HOST;w<=BE;++w)
            for(enum domain r=HOST;r<=BE;++r)
                emit("ROW",samples[i].width,w,r,w,r,samples[i].value);
    /* Deliberate common-mode bug: declared BE/BE but both implementations LE.
     * Numeric roundtrip still succeeds; independent byte/decode oracles reject. */
    emit("MUT",32,BE,BE,LE,LE,UINT64_C(16909060));
    return 0;
}
