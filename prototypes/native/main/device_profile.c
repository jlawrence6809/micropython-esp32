#include <string.h>
#include <ctype.h>
#include <stdint.h>
#include "device_profile.h"
#include "board_io.h"
#include "clock_service.h"

static const char *text(cJSON *o,const char *key)
{
    cJSON *v=cJSON_GetObjectItemCaseSensitive(o,key);return cJSON_IsString(v)?v->valuestring:NULL;
}
bool profile_valid_relays(cJSON *array)
{
    if (!cJSON_IsArray(array) || cJSON_GetArraySize(array)>16) return false;
    uint64_t pins=0;cJSON *r;
    cJSON_ArrayForEach(r,array) {
        const char *label=text(r,"label"),*rule=text(r,"rule");
        cJSON *pin=cJSON_GetObjectItemCaseSensitive(r,"pin");
        if (!cJSON_IsObject(r) || !label || !*label || strlen(label)>48 || !rule || strlen(rule)>2048 ||
            !cJSON_IsNumber(pin) || pin->valuedouble!=pin->valueint || !io_pin_allowed(pin->valueint)) return false;
        uint64_t bit=1ULL<<pin->valueint;if (pins&bit) return false;pins|=bit;
        const char *required[]={"pin","label","rule","value","auto","isInverted","defaultValue","defaultAuto"};
        for (unsigned i=0;i<8;i++) {
            unsigned occurrences=0;cJSON *field;
            cJSON_ArrayForEach(field,r) if (!strcmp(field->string,required[i])) occurrences++;
            if (occurrences!=1) return false;
        }
        const char *keys[]={"value","auto","isInverted","defaultValue","defaultAuto"};
        for (unsigned i=0;i<5;i++) if (!cJSON_IsBool(cJSON_GetObjectItemCaseSensitive(r,keys[i]))) return false;
        cJSON *other;
        cJSON_ArrayForEach(other,array) if (other!=r && text(other,"label") && !strcmp(label,text(other,"label"))) return false;
    }
    return true;
}
static bool valid_name(const char *s)
{
    if (!s || !*s || strlen(s)>63 || s[0]=='-' || s[strlen(s)-1]=='-') return false;
    for (;*s;s++) if (!(*s>='a'&&*s<='z') && !(*s>='0'&&*s<='9') && *s!='-') return false;
    return true;
}
cJSON *profile_normalize(cJSON *o)
{
    if (!cJSON_IsObject(o)) return NULL;
    const char *keys[]={"format_version","hostname","relays","sensor_pins","timezone","clock_source","schedule_policy","sensors_enabled"};
    unsigned count=0;cJSON *v;cJSON_ArrayForEach(v,o) count++;
    if (count!=8) return NULL;
    for (unsigned i=0;i<8;i++) if (!cJSON_HasObjectItem(o,keys[i])) return NULL;
    cJSON *version=cJSON_GetObjectItemCaseSensitive(o,"format_version");
    cJSON *zone=cJSON_GetObjectItemCaseSensitive(o,"timezone"),*relays=cJSON_GetObjectItemCaseSensitive(o,"relays");
    const char *source=text(o,"clock_source"),*policy=text(o,"schedule_policy");
    if (!cJSON_IsNumber(version) || version->valuedouble!=1 || !valid_name(text(o,"hostname")) ||
        !profile_valid_relays(relays) || !source || (strcmp(source,"manual")&&strcmp(source,"network")) ||
        !policy || strcmp(policy,"edge_no_catchup") || !cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(o,"sensors_enabled")) ||
        !(cJSON_IsNull(zone) || (cJSON_IsString(zone)&&zone->valuestring[0]&&clock_service_zone_supported(zone->valuestring)))) return NULL;
    cJSON *plan=board_io_plan(relays,cJSON_GetObjectItemCaseSensitive(o,"sensor_pins"));
    if (!plan) return NULL;
    cJSON_Delete(plan);
    cJSON *out=cJSON_CreateObject();
    for (unsigned i=0;i<8;i++) {
        cJSON *copy=cJSON_Duplicate(cJSON_GetObjectItemCaseSensitive(o,keys[i]),true);
        if (!copy || !cJSON_AddItemToObject(out,keys[i],copy)) {cJSON_Delete(copy);cJSON_Delete(out);return NULL;}
    }
    /* Whitelist relay fields: never persist diagnostics or unrelated secret metadata. */
    cJSON_ArrayForEach(v,cJSON_GetObjectItemCaseSensitive(out,"relays")) {
        cJSON *entry=v->child;
        while (entry) {
            cJSON *next=entry->next;
            const char *allowed[]={"pin","label","rule","value","auto","isInverted","defaultValue","defaultAuto"};
            bool keep=false;for (unsigned i=0;i<8;i++) if (!strcmp(entry->string,allowed[i])) keep=true;
            if (!keep) cJSON_DeleteItemFromObjectCaseSensitive(v,entry->string);
            entry=next;
        }
    }
    return out;
}
cJSON *profile_from_legacy(cJSON *relays,const char *timezone)
{
    cJSON *o=cJSON_CreateObject(),*pins=cJSON_CreateObject();
    cJSON_AddNumberToObject(o,"format_version",1);cJSON_AddStringToObject(o,"hostname","garden-bench");
    cJSON_AddItemToObject(o,"relays",cJSON_Duplicate(relays,true));
    const char *keys[]={"i2c_scl","i2c_sda","ds18b20","photo_sensor","light_switch","reset_switch"};
    for (unsigned i=0;i<6;i++) cJSON_AddNumberToObject(pins,keys[i],-1);
    cJSON_AddItemToObject(o,"sensor_pins",pins);
    if (timezone) cJSON_AddStringToObject(o,"timezone",timezone);else cJSON_AddNullToObject(o,"timezone");
    cJSON_AddStringToObject(o,"clock_source","manual");
    cJSON_AddStringToObject(o,"schedule_policy","edge_no_catchup");cJSON_AddBoolToObject(o,"sensors_enabled",false);
    cJSON *out=profile_normalize(o);cJSON_Delete(o);return out;
}
