/* Pure revision/partial-update helpers. No GPIO, clock mutation or storage. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "device_profile.h"
#include "io_backend.h"
#include "mbedtls/sha256.h"

static const char *str(cJSON *o,const char *key)
{
    cJSON *v=cJSON_GetObjectItemCaseSensitive(o,key);return cJSON_IsString(v)?v->valuestring:NULL;
}
static bool keys(cJSON *o,const char *const *allowed,unsigned n)
{
    if (!cJSON_IsObject(o) || !o->child) return false;
    cJSON *v;cJSON_ArrayForEach(v,o) {
        if (!v->string || cJSON_GetObjectItemCaseSensitive(o,v->string)!=v) return false;
        bool found=false;for (unsigned i=0;i<n;i++) if (!strcmp(v->string,allowed[i])) found=true;
        if (!found) return false;
    }
    return true;
}
static bool copy_field(cJSON *to,const char *key,cJSON *value)
{
    cJSON *copy=cJSON_Duplicate(value,true);if (!copy) return false;
    bool ok=cJSON_HasObjectItem(to,key)?cJSON_ReplaceItemInObjectCaseSensitive(to,key,copy):cJSON_AddItemToObject(to,key,copy);
    if (!ok) cJSON_Delete(copy);
    return ok;
}
static cJSON *ordered(cJSON *o,const char *const *names,unsigned n)
{
    cJSON *out=cJSON_CreateObject();if (!out) return NULL;
    for (unsigned i=0;i<n;i++) if (!copy_field(out,names[i],cJSON_GetObjectItemCaseSensitive(o,names[i]))) {cJSON_Delete(out);return NULL;}
    return out;
}
bool profile_edit_revision(cJSON *profile,uint32_t generation,char hash[65])
{
    cJSON *out=profile_normalize(profile);if (!out) return false;
    const char *const relay_keys[]={"pin","label","rule","auto","isInverted","defaultValue","defaultAuto"};
    const char *const pin_keys[]={"i2c_scl","i2c_sda","ds18b20","photo_sensor","light_switch","reset_switch"};
    cJSON *array=cJSON_CreateArray(),*r;
    if (!array) {cJSON_Delete(out);return false;}
    cJSON_ArrayForEach(r,cJSON_GetObjectItemCaseSensitive(out,"relays")) {
        cJSON *row=ordered(r,relay_keys,7);
        if (!row || !cJSON_AddItemToArray(array,row)) {cJSON_Delete(row);cJSON_Delete(array);cJSON_Delete(out);return false;}
    }
    if (!cJSON_ReplaceItemInObjectCaseSensitive(out,"relays",array)) {cJSON_Delete(array);cJSON_Delete(out);return false;}
    cJSON *pins=ordered(cJSON_GetObjectItemCaseSensitive(out,"sensor_pins"),pin_keys,6);
    if (!pins) {cJSON_Delete(out);return false;}
    if (!cJSON_ReplaceItemInObjectCaseSensitive(out,"sensor_pins",pins)) {cJSON_Delete(pins);cJSON_Delete(out);return false;}
    char *json=cJSON_PrintUnformatted(out);cJSON_Delete(out);if (!json) return false;
    char epoch[9];snprintf(epoch,sizeof(epoch),"%08lx",(unsigned long)generation);
    unsigned char digest[32];mbedtls_sha256_context ctx;mbedtls_sha256_init(&ctx);
    int rc=mbedtls_sha256_starts(&ctx,0);
    if (!rc) rc=mbedtls_sha256_update(&ctx,(unsigned char *)epoch,8);
    if (!rc) rc=mbedtls_sha256_update(&ctx,(unsigned char *)json,strlen(json));
    if (!rc) rc=mbedtls_sha256_finish(&ctx,digest);
    mbedtls_sha256_free(&ctx);free(json);if (rc) return false;
    for (unsigned i=0;i<32;i++) snprintf(hash+2*i,3,"%02x",digest[i]);
    return true;
}
cJSON *profile_edit_merge(cJSON *current,cJSON *changes)
{
    const char *const top[]={"hostname","timezone","clock_source","sensor_pins","relay_update","relay_add","relay_remove"};
    const char *const pins[]={"i2c_scl","i2c_sda","ds18b20","photo_sensor","light_switch","reset_switch"};
    const char *const fields[]={"pin","label","rule","auto","isInverted","defaultValue","defaultAuto"};
    const char *const add_fields[]={"pin","label","rule","isInverted","defaultValue","defaultAuto"};
    const char *const target_fields[]={"pin","label","changes"};
    if (!keys(changes,top,7)) return NULL;
    unsigned operations=cJSON_HasObjectItem(changes,"relay_update")+cJSON_HasObjectItem(changes,"relay_add")+cJSON_HasObjectItem(changes,"relay_remove");
    if (operations>1) return NULL;
    cJSON *next=cJSON_Duplicate(current,true);if (!next) return NULL;
    cJSON *item;cJSON_ArrayForEach(item,changes) {
        if (!strcmp(item->string,"sensor_pins")) {
            if (!keys(item,pins,6)) goto invalid;
            cJSON *field;cJSON_ArrayForEach(field,item)
                if (!copy_field(cJSON_GetObjectItemCaseSensitive(next,"sensor_pins"),field->string,field)) goto invalid;
        } else if (strncmp(item->string,"relay_",6)) {
            if (!copy_field(next,item->string,item)) goto invalid;
        }
    }
    cJSON *array=cJSON_GetObjectItemCaseSensitive(next,"relays");
    cJSON *add=cJSON_GetObjectItemCaseSensitive(changes,"relay_add");
    if (add) {
        if (!keys(add,add_fields,6)) goto invalid;
        cJSON *row=cJSON_Duplicate(add,true);if (!row) goto invalid;
        if (!copy_field(row,"value",cJSON_GetObjectItemCaseSensitive(add,"defaultValue")) ||
            !copy_field(row,"auto",cJSON_GetObjectItemCaseSensitive(add,"defaultAuto")) || !cJSON_AddItemToArray(array,row)) {cJSON_Delete(row);goto invalid;}
    }
    cJSON *target=cJSON_GetObjectItemCaseSensitive(changes,"relay_update");
    bool removing=false;
    if (!target) {target=cJSON_GetObjectItemCaseSensitive(changes,"relay_remove");removing=true;}
    if (target) {
        const char *label=str(target,"label");cJSON *pin=cJSON_GetObjectItemCaseSensitive(target,"pin");
        if (!keys(target,target_fields,removing?2:3) || !label || !cJSON_IsNumber(pin)) goto invalid;
        cJSON *row=NULL,*r;cJSON_ArrayForEach(r,array) if (str(r,"label") && !strcmp(str(r,"label"),label) &&
            cJSON_GetObjectItemCaseSensitive(r,"pin")->valuedouble==pin->valuedouble) {row=r;break;}
        if (!row) goto invalid;
        if (removing) cJSON_Delete(cJSON_DetachItemViaPointer(array,row));
        else {
            cJSON *patch=cJSON_GetObjectItemCaseSensitive(target,"changes");
            if (!keys(patch,fields,7)) goto invalid;
            cJSON *field;cJSON_ArrayForEach(field,patch) if (!copy_field(row,field->string,field)) goto invalid;
        }
    }
    cJSON *result=profile_normalize(next);cJSON_Delete(next);return result;
invalid:
    cJSON_Delete(next);return NULL;
}
bool profile_edit_selftests(void)
{
    /* GPIO18/4 are valid on BOTH supported targets; GPIO1 is ESP32 UART0. */
    cJSON *rows=cJSON_Parse("[{\"pin\":18,\"label\":\"relay\",\"rule\":\"return nil\",\"auto\":false,\"value\":false,\"isInverted\":false,\"defaultValue\":false,\"defaultAuto\":false}]");
    cJSON *base=profile_from_legacy(rows,"UTC");cJSON_Delete(rows);
    if (!base) {printf("PROFILE_EDIT_SELFTEST FAIL invalid baseline\n");return false;}
    char a[65],b[65];bool ok=profile_edit_revision(base,7,a);
    cJSON *value=cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(base,"relays"),0),"value");
    cJSON_SetBoolValue(value,true);
    ok=ok && profile_edit_revision(base,7,b) && !strcmp(a,b);
    ok=ok && profile_edit_revision(base,8,b) && strcmp(a,b);
    cJSON *patch=cJSON_Parse("{\"relay_update\":{\"pin\":18,\"label\":\"relay\",\"changes\":{\"label\":\"renamed\",\"auto\":true}}}");
    cJSON *next=profile_edit_merge(base,patch);cJSON_Delete(patch);
    cJSON *row=cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(next,"relays"),0);
    ok=ok && next && str(row,"label") && !strcmp(str(row,"label"),"renamed") &&
        cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(row,"value")) && cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(row,"auto"));
    char layout_a[65],layout_b[65];
    ok=ok && io_layout_hash(base,layout_a) && io_layout_hash(next,layout_b) && !strcmp(layout_a,layout_b);
    cJSON_Delete(next);
    patch=cJSON_Parse("{\"relay_update\":{\"pin\":18,\"label\":\"relay\",\"changes\":{\"pin\":4}}}");
    next=profile_edit_merge(base,patch);cJSON_Delete(patch);
    ok=ok && next && io_layout_hash(next,layout_b) && strcmp(layout_a,layout_b);
    cJSON_Delete(next);
    const char *invalid[]={"{}","{\"armed\":true}","{\"hostname\":\"ok\",\"hostname\":\"other\"}",
        "{\"relay_update\":{\"pin\":18,\"label\":\"relay\",\"changes\":{\"value\":false}}}",
        "{\"relay_update\":{\"pin\":18,\"label\":\"wrong\",\"changes\":{\"auto\":true}}}",
        "{\"relay_update\":{\"pin\":18,\"label\":\"relay\",\"changes\":{\"auto\":1}}}",
        "{\"sensor_pins\":{\"light_switch\":18}}", "{\"sensor_pins\":{\"i2c_sda\":4}}",
        "{\"sensor_pins\":{\"ds18b20\":4}}",  "{\"relay_remove\":{\"pin\":18,\"label\":\"relay\",\"changes\":{}}}",
        "{\"relay_add\":{},\"relay_remove\":{\"pin\":1,\"label\":\"relay\"}}"};
    for (unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++) {
        patch=cJSON_Parse(invalid[i]);next=profile_edit_merge(base,patch);cJSON_Delete(patch);
        ok=ok && !next;cJSON_Delete(next);
    }
    ok=ok && profile_edit_revision(base,7,b) && !strcmp(a,b);
    cJSON_Delete(base);printf("PROFILE_EDIT_SELFTEST %s\n",ok?"PASS":"FAIL");return ok;
}
