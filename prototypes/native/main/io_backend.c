#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include "io_backend.h"
#include "target_board.h"
#include "device_profile.h"
#include "mbedtls/sha256.h"

static bool flag(cJSON *o,const char *key) {return cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(o,key));}
static int number(cJSON *o,const char *key) {return cJSON_GetObjectItemCaseSensitive(o,key)->valueint;}
bool io_layout_hash(cJSON *profile,char hash[65])
{
    cJSON *canonical=profile_normalize(profile);
    if (!canonical) return false;
    /* Fixed binary encoding: deterministic across JSON property order, no
       additional allocations or native-endian integers in the hash stream. */
    unsigned char wire[256];size_t used=0;
    cJSON *rows=cJSON_GetObjectItemCaseSensitive(canonical,"relays"),*r;
    wire[used++]=1;wire[used++]=(unsigned char)cJSON_GetArraySize(rows);
    cJSON_ArrayForEach(r,rows) {
        wire[used++]=(unsigned char)number(r,"pin");wire[used++]=flag(r,"isInverted");
        wire[used++]=flag(r,"defaultValue");wire[used++]=flag(r,"defaultAuto");
    }
    const char *keys[]={"i2c_scl","i2c_sda","ds18b20","photo_sensor","light_switch","reset_switch"};
    cJSON *pins=cJSON_GetObjectItemCaseSensitive(canonical,"sensor_pins");
    for (unsigned i=0;i<6;i++) wire[used++]=(unsigned char)(number(pins,keys[i])+1);
    const char *clock[]={"timezone","clock_source","schedule_policy"};
    for (unsigned i=0;i<3;i++) {
        cJSON *item=cJSON_GetObjectItemCaseSensitive(canonical,clock[i]);
        const char *s=cJSON_IsString(item)?item->valuestring:"";size_t length=strlen(s)+1;
        if (used+length>=sizeof(wire)) {cJSON_Delete(canonical);return false;}
        memcpy(wire+used,s,length);used+=length;
    }
    wire[used++]=flag(canonical,"sensors_enabled");
    unsigned char digest[32];bool ok=mbedtls_sha256(wire,used,digest,0)==0;
    if (ok) for (unsigned i=0;i<32;i++) snprintf(hash+2*i,3,"%02x",digest[i]);
    cJSON_Delete(canonical);return ok;
}
bool io_live_settings_compatible(cJSON *current,cJSON *next)
{
    /* Polarity/boot defaults are editable live. Pin ownership, input/clock policy
       and acquisition mode still require isolated resource reconfiguration. The
       full arming hash remains unchanged and is rebound on a successful edit. */
    cJSON *copy=profile_normalize(next),*old=profile_normalize(current);
    if (!copy || !old) {cJSON_Delete(copy);cJSON_Delete(old);return false;}
    cJSON *a=cJSON_GetObjectItemCaseSensitive(old,"relays"),*b=cJSON_GetObjectItemCaseSensitive(copy,"relays");
    bool ok=cJSON_GetArraySize(a)==cJSON_GetArraySize(b);
    const char *fields[]={"isInverted","defaultValue","defaultAuto"};
    for (int i=0;ok && i<cJSON_GetArraySize(a);i++) for (unsigned k=0;k<3;k++) {
        cJSON *from=cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(a,i),fields[k]);
        cJSON *to=cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(b,i),fields[k]);
        cJSON_SetBoolValue(to,cJSON_IsTrue(from));
    }
    char before[65],after[65];
    ok=ok && io_layout_hash(old,before) && io_layout_hash(copy,after) && !strcmp(before,after);
    cJSON_Delete(copy);cJSON_Delete(old);return ok;
}
bool io_live_switch_settings_compatible(cJSON *current,cJSON *next)
{
    cJSON *old=profile_normalize(current),*copy=profile_normalize(next);
    if (!old || !copy) {cJSON_Delete(old);cJSON_Delete(copy);return false;}
    bool ok=true,changed=false;
    const char *keys[]={"light_switch","reset_switch"};
    cJSON *a=cJSON_GetObjectItemCaseSensitive(old,"sensor_pins"),*b=cJSON_GetObjectItemCaseSensitive(copy,"sensor_pins");
    for (unsigned i=0;i<2;i++) {
        int before=number(a,keys[i]),after=number(b,keys[i]);
        if (before!=after) {
            changed=true;
#if defined(CONFIG_IDF_TARGET_ESP32)
            if (after==5 || after==12 || after==15) ok=false; /* Never add a strap bias remotely. */
#endif
        }
        cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(b,keys[i]),before);
    }
    /* No simultaneous polarity/boot-policy change hidden by normal live edits. */
    cJSON *ra=cJSON_GetObjectItemCaseSensitive(old,"relays"),*rb=cJSON_GetObjectItemCaseSensitive(copy,"relays"),*r;
    ok=ok && changed && cJSON_GetArraySize(ra)==cJSON_GetArraySize(rb);
    const char *off[]={"value","auto","defaultValue","defaultAuto"};
    for (int i=0;ok && i<cJSON_GetArraySize(ra);i++) {
        r=cJSON_GetArrayItem(ra,i);cJSON *s=cJSON_GetArrayItem(rb,i);
        for (unsigned j=0;j<4;j++) if (flag(r,off[j]) || flag(s,off[j])) ok=false;
        if (flag(r,"isInverted")!=flag(s,"isInverted")) ok=false;
    }
    ok=ok && io_live_settings_compatible(old,copy);
    cJSON_Delete(old);cJSON_Delete(copy);return ok;
}
/* Input-only transaction: never closes, opens or writes a relay. Caller holds
 * runtime mutex. On open failure restore previous inputs; cleanup failure is
 * explicitly latched so the caller cannot advertise a successful layout. */
esp_err_t io_backend_reconfigure_switches(io_backend *b,cJSON *next,uint32_t now)
{
    if (!b || !b->active || b->cleanup_failed) return ESP_ERR_INVALID_STATE;
    for (unsigned i=0;i<b->count;i++) if (b->commands[i]) return ESP_ERR_INVALID_STATE;
    cJSON *p=profile_normalize(next);if (!p) return ESP_ERR_INVALID_ARG;
    cJSON *pins=cJSON_GetObjectItemCaseSensitive(p,"sensor_pins");
    int old[2]={b->switch_pins[0],b->switch_pins[1]},wanted[2]={number(pins,"light_switch"),number(pins,"reset_switch")};
    cJSON_Delete(p);bool changed[2]={old[0]!=wanted[0],old[1]!=wanted[1]};
    for (unsigned i=0;i<2;i++) if (changed[i] && b->switch_attempted[i]) {
        if (b->ops->switch_close(b->driver,i)!=ESP_OK) {b->cleanup_failed=true;b->failure_pin=old[i];return ESP_FAIL;}
        b->switch_attempted[i]=false;b->switches[i]=false;
    }
    for (unsigned i=0;i<2;i++) if (changed[i]) {
        b->switch_pins[i]=wanted[i];b->switches[i]=false;
        if (wanted[i]<0) continue;
        b->switch_attempted[i]=true;
        if (b->ops->switch_open(b->driver,i,wanted[i],now)!=ESP_OK) {
            b->failure_pin=wanted[i];
            for (unsigned j=0;j<2;j++) if (changed[j] && b->switch_attempted[j]) {
                if (b->ops->switch_close(b->driver,j)!=ESP_OK) b->cleanup_failed=true;
                else b->switch_attempted[j]=false;
            }
            if (b->cleanup_failed) return ESP_FAIL;
            for (unsigned j=0;j<2;j++) if (changed[j]) {
                b->switch_pins[j]=old[j];b->switches[j]=false;
                if (old[j]<0) continue;
                b->switch_attempted[j]=true;
                if (b->ops->switch_open(b->driver,j,old[j],now)!=ESP_OK) {b->cleanup_failed=true;return ESP_FAIL;}
                b->switches[j]=b->ops->switch_sample(b->driver,j,now);
            }
            return ESP_FAIL;
        }
        b->switches[i]=b->ops->switch_sample(b->driver,i,now);
    }
    return ESP_OK;
}
void io_backend_baseline_switches(io_backend *b,rule_inputs *in)
{
    in->switch_state=in->last_switch_state=b->switches[0];
    in->reset_switch=in->last_reset_switch=b->switches[1];
}
bool io_arm_record_matches(const char *record,const char *device_id,const char *layout_hash)
{
    return record && device_id && layout_hash && strlen(record)==77 && strlen(device_id)==12 &&
        strlen(layout_hash)==64 && !strncmp(record,device_id,12) && record[12]=='/' && !strcmp(record+13,layout_hash);
}
esp_err_t io_backend_stop(io_backend *b)
{
    if (!b || !b->ops) return ESP_ERR_INVALID_ARG;
    b->active=false;bool failed=false;
    for (unsigned i=0;i<b->count;i++) if (b->attempted[i]) {
        if (b->ops->relay_close(b->driver,i)==ESP_OK) b->attempted[i]=false;else failed=true;
    }
    for (unsigned i=0;i<2;i++) if (b->switch_attempted[i]) {
        if (b->ops->switch_close(b->driver,i)==ESP_OK) b->switch_attempted[i]=false;else failed=true;
    }
    b->cleanup_failed=failed;return failed?ESP_FAIL:ESP_OK;
}
esp_err_t io_backend_start(io_backend *b,cJSON *profile,const io_operations *ops,void *driver,uint32_t now)
{
    if (!b || !ops || !driver || !ops->relay_open || !ops->relay_set || !ops->relay_close ||
        !ops->switch_open || !ops->switch_sample || !ops->switch_close) return ESP_ERR_INVALID_ARG;
    if (b->active || b->cleanup_failed) return ESP_ERR_INVALID_STATE;
    cJSON *canonical=profile_normalize(profile);
    if (!canonical) return ESP_ERR_INVALID_ARG;
    memset(b,0,sizeof(*b));b->ops=ops;b->driver=driver;b->failure_pin=-1;
    cJSON *pins=cJSON_GetObjectItemCaseSensitive(canonical,"sensor_pins");
    b->switch_pins[0]=number(pins,"light_switch");b->switch_pins[1]=number(pins,"reset_switch");
    cJSON *r;unsigned i=0;
    cJSON_ArrayForEach(r,cJSON_GetObjectItemCaseSensitive(canonical,"relays")) {
        b->pins[i]=number(r,"pin");b->inverted[i]=flag(r,"isInverted");b->commands[i]=flag(r,"defaultValue");i++;
    }
    b->count=i;cJSON_Delete(canonical);esp_err_t err=ESP_OK;
    /* Plan is fully validated before ANY operation. Track attempts, including
       partially failed opens, so rollback cannot forget a touched pin. */
    for (i=0;i<2;i++) if (b->switch_pins[i]>=0) {
        b->switch_attempted[i]=true;
        err=ops->switch_open(driver,i,b->switch_pins[i],now);
        if (err!=ESP_OK) {b->failure_pin=b->switch_pins[i];goto failed;}
        b->switches[i]=ops->switch_sample(driver,i,now);
    }
    for (i=0;i<b->count;i++) {
        b->attempted[i]=true;err=ops->relay_open(driver,i,b->pins[i],b->inverted[i],b->commands[i]);
        if (err!=ESP_OK) {b->failure_pin=b->pins[i];goto failed;}
    }
    b->active=true;return ESP_OK;
failed:
    if (io_backend_stop(b)!=ESP_OK) return ESP_ERR_INVALID_STATE;
    return err;
}
esp_err_t io_backend_write(void *context,int pin,bool command,bool inverted)
{
    io_backend *b=context;
    if (!b || !b->active) return ESP_ERR_INVALID_STATE;
    for (unsigned i=0;i<b->count;i++) if (b->pins[i]==pin) {
        bool change=b->inverted[i]!=inverted;
        if (change && !b->ops->relay_configure) return ESP_ERR_INVALID_STATE;
        esp_err_t err=change?b->ops->relay_configure(b->driver,i,inverted,command):b->ops->relay_set(b->driver,i,command);
        if (err==ESP_OK) {b->commands[i]=command;b->inverted[i]=inverted;}else b->failure_pin=pin;
        return err;
    }
    return ESP_ERR_INVALID_ARG;
}
void io_backend_sample(io_backend *b,uint32_t now)
{
    if (!b->active) return;
    for (unsigned i=0;i<2;i++) if (b->switch_attempted[i]) b->switches[i]=b->ops->switch_sample(b->driver,i,now);
}
void io_backend_baseline(io_backend *b,rule_inputs *in)
{
    in->temperature=NAN;in->humidity=NAN;in->light=NAN;
    in->switch_state=b->switches[0];in->reset_switch=b->switches[1];
    engine_advance_inputs(in); /* No invented input edges or fake sensor readings. */
}
void io_backend_publish(io_backend *b,cJSON *relays)
{
    cJSON *r;cJSON_ArrayForEach(r,relays) for (unsigned i=0;i<b->count;i++) if (number(r,"pin")==b->pins[i])
        cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(r,"value"),b->commands[i]);
}
bool io_backend_apply(io_backend *b,cJSON *relays)
{
    if (!b || !b->active || !profile_valid_relays(relays) || (unsigned)cJSON_GetArraySize(relays)!=b->count) return false;
    unsigned i=0;cJSON *r;
    cJSON_ArrayForEach(r,relays) {
        if (number(r,"pin")!=b->pins[i] || (flag(r,"isInverted")!=b->inverted[i] && !b->ops->relay_configure)) return false;
        i++;
    }
    cJSON_ArrayForEach(r,relays) cJSON_DeleteItemFromObjectCaseSensitive(r,"last_error");
    bool ok=engine_apply_commands(relays,io_backend_write,b)==ESP_OK;
    io_backend_publish(b,relays);
    if (!ok) cJSON_ArrayForEach(r,relays) if (number(r,"pin")==b->failure_pin)
        cJSON_AddStringToObject(r,"last_error","GPIO write failed; published value retains last successful command");
    return ok;
}
#ifdef CONFIG_GARDEN_CONTROLLER_IO
static esp_err_t ro(void *c,unsigned i,int p,bool inv,bool v) {return relay_gpio_open(&((io_gpio_driver *)c)->relays[i],p,inv,v);}
static esp_err_t rs(void *c,unsigned i,bool v) {return relay_gpio_set(&((io_gpio_driver *)c)->relays[i],v);}
static esp_err_t rc(void *c,unsigned i) {return relay_gpio_close(&((io_gpio_driver *)c)->relays[i]);}
static esp_err_t so(void *c,unsigned i,int p,uint32_t n) {return switch_gpio_open(&((io_gpio_driver *)c)->switches[i],p,n);}
static bool ss(void *c,unsigned i,uint32_t n) {return switch_gpio_sample(&((io_gpio_driver *)c)->switches[i],n);}
static esp_err_t sc(void *c,unsigned i) {return switch_gpio_close(&((io_gpio_driver *)c)->switches[i]);}
static esp_err_t rr(void *c,unsigned i,bool inv,bool v) {return relay_gpio_configure(&((io_gpio_driver *)c)->relays[i],inv,v);}
static const io_operations physical={ro,rs,rc,so,ss,sc,rr};
#endif
const io_operations *io_gpio_operations(void)
{
#ifdef CONFIG_GARDEN_CONTROLLER_IO
    return &physical;
#else
    return NULL;
#endif
}

/* Fault-injectable RAM driver: always software-only, even in controller builds. */
typedef struct {
    bool relays[16], switches[2], commands[16], raw[2];int pins[16], sp[2];
    int fail_open,fail_write,fail_close;unsigned calls;switch_debounce debounce[2];
} fake_driver;
static esp_err_t fr_open(void *ctx,unsigned i,int pin,bool inv,bool value)
{
    (void)inv;fake_driver *f=ctx;f->calls++;f->relays[i]=true;f->pins[i]=pin;f->commands[i]=value;
    return pin==f->fail_open?ESP_FAIL:ESP_OK; /* Deliberately partial failure. */
}
static esp_err_t fr_set(void *ctx,unsigned i,bool value)
{
    fake_driver *f=ctx;f->calls++;if (f->pins[i]==f->fail_write) return ESP_FAIL;
    f->commands[i]=value;return ESP_OK;
}
static esp_err_t fr_close(void *ctx,unsigned i)
{
    fake_driver *f=ctx;f->calls++;if (f->pins[i]==f->fail_close) return ESP_FAIL;
    f->relays[i]=false;return ESP_OK;
}
static esp_err_t fs_open(void *ctx,unsigned i,int pin,uint32_t now)
{
    fake_driver *f=ctx;f->calls++;f->switches[i]=true;f->sp[i]=pin;
    switch_debounce_init(&f->debounce[i],f->raw[i],now,40);return pin==f->fail_open?ESP_FAIL:ESP_OK;
}
static bool fs_sample(void *ctx,unsigned i,uint32_t now)
{
    fake_driver *f=ctx;return switch_debounce_update(&f->debounce[i],f->raw[i],now);
}
static esp_err_t fs_close(void *ctx,unsigned i)
{
    fake_driver *f=ctx;f->calls++;if (f->sp[i]==f->fail_close) return ESP_FAIL;
    f->switches[i]=false;return ESP_OK;
}
static esp_err_t fr_configure(void *ctx,unsigned i,bool inv,bool value)
{
    (void)inv;return fr_set(ctx,i,value);
}
static const io_operations fake={fr_open,fr_set,fr_close,fs_open,fs_sample,fs_close,fr_configure};
static bool released(fake_driver *f)
{
    for (unsigned i=0;i<16;i++) if (f->relays[i]) return false;
    return !f->switches[0]&&!f->switches[1];
}
bool io_backend_selftests(void)
{
    cJSON *relays=cJSON_Parse("[{\"pin\":4,\"label\":\"a\",\"rule\":\"return nil\",\"value\":false,\"auto\":false,\"isInverted\":true,\"defaultValue\":true,\"defaultAuto\":false},{\"pin\":6,\"label\":\"b\",\"rule\":\"return nil\",\"value\":false,\"auto\":false,\"isInverted\":false,\"defaultValue\":false,\"defaultAuto\":false}]");
    /* GPIO6 belongs to SPI flash on original ESP32. Tests use RAM callbacks,
       but their profiles must still pass the real target-specific planner. */
    cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(relays,1),"pin"),GARDEN_TEST_SECOND_RELAY_PIN);
    cJSON *p=profile_from_legacy(relays,"UTC");cJSON_Delete(relays);
    if (!p) return false;
    cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(p,"sensor_pins"),"light_switch"),5);
    char h1[65]={0},h2[65]={0};bool ok=io_layout_hash(p,h1);
    cJSON *first=cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(p,"relays"),0);
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(first,"value"),true);
    ok=ok&&io_layout_hash(p,h2)&&!strcmp(h1,h2);
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(first,"defaultValue"),false);
    ok=ok&&io_layout_hash(p,h2)&&strcmp(h1,h2)!=0;
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(first,"defaultValue"),true);
    char record[80];snprintf(record,sizeof(record),"001122334455/%s",h1);
    ok=ok&&io_arm_record_matches(record,"001122334455",h1)&&
        !io_arm_record_matches(record,"001122334456",h1)&&!io_arm_record_matches(record,"001122334455",h2)&&
        !io_arm_record_matches("","001122334455",h1);
    for (unsigned fault=0;fault<5;fault++) {
        fake_driver f={.raw={true,false},.fail_open=(fault==1||fault==4)?4:fault==2?GARDEN_TEST_SECOND_RELAY_PIN:fault==3?5:0,
            .fail_close=fault==4?5:0};io_backend b={0};
        esp_err_t err=io_backend_start(&b,p,&fake,&f,0);
        if (fault==4) {
            ok=ok&&err==ESP_ERR_INVALID_STATE&&!b.active&&b.cleanup_failed&&!released(&f);
            f.fail_close=0;ok=ok&&io_backend_stop(&b)==ESP_OK&&released(&f);continue;
        }
        if (fault) {ok=ok&&err!=ESP_OK&&!b.active&&!b.cleanup_failed&&released(&f);continue;}
        ok=ok&&err==ESP_OK&&b.active&&b.commands[0]&&!b.commands[1];
        rule_inputs in=rule_inputs_default();io_backend_baseline(&b,&in);
        ok=ok&&in.switch_state&&in.last_switch_state&&isnan(in.temperature)&&isnan(in.last_temperature);
        f.raw[0]=false;io_backend_sample(&b,10);ok=ok&&b.switches[0];
        io_backend_sample(&b,50);ok=ok&&!b.switches[0];
        f.fail_write=4;ok=ok&&io_backend_write(&b,4,false,true)!=ESP_OK&&b.commands[0];
        f.fail_write=0;ok=ok&&io_backend_write(&b,4,false,true)==ESP_OK&&!b.commands[0];
        f.fail_write=4;
        ok=ok&&io_backend_write(&b,4,true,false)!=ESP_OK&&b.inverted[0]&&!b.commands[0];
        f.fail_write=0;
        ok=ok&&io_backend_write(&b,4,true,false)==ESP_OK&&!b.inverted[0]&&b.commands[0]&&
            io_backend_write(&b,4,false,true)==ESP_OK&&b.inverted[0]&&!b.commands[0]&&
            io_backend_write(&b,7,true,false)!=ESP_OK;
        cJSON *desired=cJSON_Duplicate(cJSON_GetObjectItemCaseSensitive(p,"relays"),true);
        cJSON *a=cJSON_GetArrayItem(desired,0),*second=cJSON_GetArrayItem(desired,1);
        cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(a,"value"),true);
        cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(second,"value"),true);
        f.fail_write=GARDEN_TEST_SECOND_RELAY_PIN;
        ok=ok&&!io_backend_apply(&b,desired)&&flag(a,"value")&&!flag(second,"value")&&
            cJSON_IsString(cJSON_GetObjectItemCaseSensitive(second,"last_error"));
        f.fail_write=0;cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(second,"value"),true);
        ok=ok&&io_backend_apply(&b,desired)&&flag(second,"value")&&!cJSON_HasObjectItem(second,"last_error");
        unsigned calls=f.calls;cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(second,"pin"),7);
        ok=ok&&!io_backend_apply(&b,desired)&&f.calls==calls;cJSON_Delete(desired);
        f.fail_close=4;ok=ok&&io_backend_stop(&b)!=ESP_OK&&b.cleanup_failed&&
            io_backend_start(&b,p,&fake,&f,0)==ESP_ERR_INVALID_STATE;
        f.fail_close=0;ok=ok&&io_backend_stop(&b)==ESP_OK&&released(&f);
    }
    /* Live polarity and startup defaults are allowed; ownership/policy changes
       remain rejected before any GPIO operation. */
    cJSON *changed=cJSON_Duplicate(p,true);
    cJSON *row=cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(changed,"relays"),0);
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(row,"isInverted"),false);
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(row,"defaultValue"),false);
    cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(row,"defaultAuto"),true);
    ok=ok&&io_live_settings_compatible(p,changed);
    cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(row,"pin"),7);
    ok=ok&&!io_live_settings_compatible(p,changed);cJSON_Delete(changed);
    changed=cJSON_Duplicate(p,true);
    cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(changed,"sensor_pins"),"light_switch"),8);
    ok=ok&&!io_live_settings_compatible(p,changed);cJSON_Delete(changed);
    /* Conflicts must cause ZERO callback activity. */
    cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(p,"sensor_pins"),"light_switch"),4);
    fake_driver f={0};io_backend b={0};
    ok=ok&&io_backend_start(&b,p,&fake,&f,0)!=ESP_OK&&f.calls==0;
    cJSON_Delete(p);printf("BACKEND_SOFTWARE_TEST %s\n",ok?"PASS":"FAIL");return ok;
}
