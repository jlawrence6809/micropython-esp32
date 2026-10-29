/* Public consistency token, NOT authentication. No hardware/config operations. */
#include <stdio.h>
#include <string.h>
#include "ota_fence.h"
#include "mbedtls/sha256.h"
static bool hex_string(const char *s,size_t size)
{
    if (!s || strlen(s)!=size) return false;
    for (size_t i=0;i<size;i++) if (!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f'))) return false;
    return true;
}
bool ota_fence_hash(const char *device,const char *boot,const char *layout,const char *revision,const char *elf,bool active,bool armed,char out[65])
{
    if (!hex_string(device,12) || !hex_string(boot,16) || !hex_string(layout,64) || !hex_string(revision,64) || !hex_string(elf,64)) return false;
    char data[384];
    int n=snprintf(data,sizeof(data),"garden-ota-fence-v1/%s/%s/%s/%s/%s/%u/%u",device,boot,layout,revision,elf,(unsigned)active,(unsigned)armed);
    if (n<0 || (size_t)n>=sizeof(data)) return false;
    unsigned char digest[32];mbedtls_sha256_context ctx;mbedtls_sha256_init(&ctx);
    int rc=mbedtls_sha256_starts(&ctx,0);
    if (!rc) rc=mbedtls_sha256_update(&ctx,(const unsigned char *)data,n);
    if (!rc) rc=mbedtls_sha256_finish(&ctx,digest);
    mbedtls_sha256_free(&ctx);
    if (rc) return false;
    for (unsigned i=0;i<32;i++) snprintf(out+i*2,3,"%02x",digest[i]);
    return true;
}
bool ota_fence_accept(bool controller,const char *expected,const char *current)
{
    if (!hex_string(current,64)) return false;
    return expected?hex_string(expected,64) && !strcmp(expected,current):!controller;
}
bool ota_fence_selftests(void)
{
    char device[13]="123456abcdef",boot[17]="1234567890abcdef",layout[65],revision[65],elf[65],a[65]="",b[65]="";
    memset(layout,'1',64);layout[64]=0;memset(revision,'2',64);revision[64]=0;memset(elf,'3',64);elf[64]=0;
    bool ok=ota_fence_hash(device,boot,layout,revision,elf,false,false,a);
    char *fields[]={device,boot,layout,revision,elf};
    for (unsigned i=0;i<5;i++) {
        char old=fields[i][0];fields[i][0]='f';
        ok=ok && ota_fence_hash(device,boot,layout,revision,elf,false,false,b) && strcmp(a,b);
        fields[i][0]=old;
    }
    ok=ok && ota_fence_hash(device,boot,layout,revision,elf,true,false,b) && strcmp(a,b);
    ok=ok && ota_fence_hash(device,boot,layout,revision,elf,false,true,b) && strcmp(a,b);
    ok=ok && ota_fence_hash(device,boot,layout,revision,elf,false,false,b) && !strcmp(a,b);
    ok=ok && !ota_fence_hash(NULL,boot,layout,revision,elf,false,false,b);
    device[0]='X';ok=ok && !ota_fence_hash(device,boot,layout,revision,elf,false,false,b);
    ok=ok && ota_fence_accept(false,NULL,a) && !ota_fence_accept(true,NULL,a);
    ok=ok && ota_fence_accept(true,a,a) && ota_fence_accept(false,a,a);
    b[0]=a[0]=='f'?'0':'f';ok=ok && !ota_fence_accept(true,b,a) && !ota_fence_accept(false,b,a);
    ok=ok && !ota_fence_accept(true,"short",a) && !ota_fence_accept(false,NULL,NULL);
    printf("OTA_FENCE_%s\n",ok?"PASS":"FAIL");return ok;
}
