/* Native HAL: used only by the opted-in controller backend or the explicitly
   enabled disconnected-spare selftest. Default runtime remains memory-only. */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "board_io.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"
#include "target_board.h"
#if defined(CONFIG_IDF_TARGET_ESP32) && defined(CONFIG_BENCH_IO_SELFTEST)
#error "Physical spare selftest wiring is reviewed for ESP32-S3 only"
#endif

static bool tested, passed, physical_ran, test_pins_released;
static unsigned test_count;
static long long missing_sensor_us;

bool io_pin_allowed(int pin)
{
    static const int allowed[]=GARDEN_ALLOWED_PINS;
    for (unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);i++) if (pin==allowed[i]) return true;
    return false;
}
int relay_gpio_level(bool command,bool inverted) { return command != inverted; }
esp_err_t relay_gpio_open(relay_gpio *r,int pin,bool inverted,bool boot_value)
{
    if (!r || !io_pin_allowed(pin)) return ESP_ERR_INVALID_ARG;
    if (r->opened) return ESP_ERR_INVALID_STATE;
    esp_err_t err=gpio_reset_pin(pin);
    if (err!=ESP_OK) return err;
    /* Retain cleanup ownership even when a later initialization call fails. */
    *r=(relay_gpio){.pin=pin,.inverted=inverted,.opened=true,.command=boot_value};
    err=gpio_set_pull_mode(pin,GPIO_FLOATING);
    if (err!=ESP_OK) return err;
    /* Preload intended boot level before enabling output. This cannot guarantee
       safe voltage during ROM/reset/brownout; external bias/relay tests required. */
    err=gpio_set_level(pin,relay_gpio_level(boot_value,inverted));
    if (err!=ESP_OK) return err;
    err=gpio_set_direction(pin,GPIO_MODE_INPUT_OUTPUT);
    if (err!=ESP_OK) return err;
    *r=(relay_gpio){.pin=pin,.inverted=inverted,.opened=true,.command=boot_value};
    return ESP_OK;
}
esp_err_t relay_gpio_set(relay_gpio *r,bool command)
{
    if (!r || !r->opened) return ESP_ERR_INVALID_STATE;
    esp_err_t err=gpio_set_level(r->pin,relay_gpio_level(command,r->inverted));
    if (err==ESP_OK) r->command=command;
    return err;
}
esp_err_t relay_gpio_configure(relay_gpio *r,bool inverted,bool command)
{
    if (!r || !r->opened) return ESP_ERR_INVALID_STATE;
    /* Deliberate live polarity edit: retain logical command, change electrical
       level immediately. Publish new polarity only after successful write. */
    esp_err_t err=gpio_set_level(r->pin,relay_gpio_level(command,inverted));
    if (err==ESP_OK) {r->inverted=inverted;r->command=command;}
    return err;
}
esp_err_t relay_gpio_close(relay_gpio *r)
{
    if (!r) return ESP_ERR_INVALID_ARG;
    if (!r->opened) return ESP_OK;
    esp_err_t err=gpio_set_direction(r->pin,GPIO_MODE_INPUT);
    if (err==ESP_OK) err=gpio_set_pull_mode(r->pin,GPIO_FLOATING);
    if (err==ESP_OK) r->opened=false;
    return err;
}
void switch_debounce_init(switch_debounce *d,bool initial,uint32_t now,uint32_t interval)
{
    *d=(switch_debounce){.stable=initial,.candidate=initial,.candidate_since=now,.interval_ms=interval};
}
bool switch_debounce_update(switch_debounce *d,bool pressed,uint32_t now)
{
    if (pressed!=d->candidate) {d->candidate=pressed;d->candidate_since=now;}
    if (d->candidate!=d->stable && (uint32_t)(now-d->candidate_since)>=d->interval_ms)
        d->stable=d->candidate;
    return d->stable;
}
esp_err_t switch_gpio_open(switch_gpio *s,int pin,uint32_t now)
{
    if (!s || !io_pin_allowed(pin)) return ESP_ERR_INVALID_ARG;
    if (s->opened) return ESP_ERR_INVALID_STATE;
    gpio_config_t config={.pin_bit_mask=1ULL<<pin,.mode=GPIO_MODE_INPUT,
        .pull_up_en=GPIO_PULLUP_ENABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,.intr_type=GPIO_INTR_DISABLE};
    s->pin=pin;s->opened=true;
    esp_err_t err=gpio_config(&config);
    if (err!=ESP_OK) return err;
    /* Establish a stable baseline before outputs are enabled. A few microseconds
       is insufficient for cable capacitance with a weak internal pull-up. */
    vTaskDelay(pdMS_TO_TICKS(5)+1);
    uint32_t started=(uint32_t)(esp_timer_get_time()/1000);
    switch_debounce_init(&s->debounce,gpio_get_level(pin)==0,started,40);
    for (;;) {
        now=(uint32_t)(esp_timer_get_time()/1000);
        bool pressed=gpio_get_level(pin)==0;
        switch_debounce_update(&s->debounce,pressed,now);
        if ((uint32_t)(now-s->debounce.candidate_since)>=40) {
            s->debounce.stable=s->debounce.candidate;return ESP_OK;
        }
        if ((uint32_t)(now-started)>=200) return ESP_ERR_TIMEOUT;
        vTaskDelay(pdMS_TO_TICKS(5)+1);
    }
}
bool switch_gpio_sample(switch_gpio *s,uint32_t now)
{
    return s && s->opened ? switch_debounce_update(&s->debounce,gpio_get_level(s->pin)==0,now) : false;
}
esp_err_t switch_gpio_close(switch_gpio *s)
{
    if (!s) return ESP_ERR_INVALID_ARG;
    if (!s->opened) return ESP_OK;
    esp_err_t err=gpio_set_direction(s->pin,GPIO_MODE_INPUT);
    if (err==ESP_OK) err=gpio_set_pull_mode(s->pin,GPIO_FLOATING);
    if (err==ESP_OK) s->opened=false;
    return err;
}
uint8_t aht21_crc(const uint8_t *data,unsigned length)
{
    uint8_t crc=0xff;
    for (unsigned i=0;i<length;i++) {
        crc^=data[i];
        for (unsigned bit=0;bit<8;bit++) crc=(crc&0x80)?(uint8_t)((crc<<1)^0x31):(uint8_t)(crc<<1);
    }
    return crc;
}
esp_err_t aht21_decode(const uint8_t frame[7],double *temperature,double *humidity)
{
    *temperature=NAN;*humidity=NAN;
    if (frame[0]&0x80) return ESP_ERR_NOT_FINISHED;
    if (!(frame[0]&0x08)) return ESP_ERR_INVALID_STATE;
    if (aht21_crc(frame,6)!=frame[6]) return ESP_ERR_INVALID_CRC;
    uint32_t h=((uint32_t)frame[1]<<12)|((uint32_t)frame[2]<<4)|(frame[3]>>4);
    uint32_t t=((uint32_t)(frame[3]&0x0f)<<16)|((uint32_t)frame[4]<<8)|frame[5];
    *humidity=(double)h*100.0/1048576.0;
    *temperature=(double)t*200.0/1048576.0-50.0;
    return ESP_OK;
}
esp_err_t aht21_close(aht21_sensor *s)
{
    if (!s) return ESP_ERR_INVALID_ARG;
    if (s->device) {
        esp_err_t err=i2c_master_bus_rm_device(s->device);
        if (err!=ESP_OK) return err;
        s->device=NULL;
    }
    if (s->bus) {
        esp_err_t err=i2c_del_master_bus(s->bus);
        if (err!=ESP_OK) return err;
        s->bus=NULL;
    }
    s->pending=false;s->started_at=0;return ESP_OK;
}
esp_err_t aht21_open(aht21_sensor *s,int scl,int sda)
{
    if (!s || !io_pin_allowed(scl) || !io_pin_allowed(sda) || scl==sda) return ESP_ERR_INVALID_ARG;
    if (s->bus || s->device) return ESP_ERR_INVALID_STATE;
    i2c_master_bus_config_t bus={.i2c_port=I2C_NUM_0,.sda_io_num=sda,.scl_io_num=scl,
        .clk_source=I2C_CLK_SRC_DEFAULT,.glitch_ignore_cnt=7,.flags.enable_internal_pullup=true};
    esp_err_t err=i2c_new_master_bus(&bus,&s->bus);
    if (err!=ESP_OK) return err;
    err=i2c_master_probe(s->bus,0x38,20);
    if (err!=ESP_OK) {aht21_close(s);return err;}
    i2c_device_config_t device={.dev_addr_length=I2C_ADDR_BIT_LEN_7,.device_address=0x38,.scl_speed_hz=100000};
    err=i2c_master_bus_add_device(s->bus,&device,&s->device);
    if (err!=ESP_OK) {aht21_close(s);return err;}
    uint8_t status;
    err=i2c_master_receive(s->device,&status,1,20);
    if (err!=ESP_OK) {aht21_close(s);return err;}
    if (!(status&0x08)) {
        const uint8_t init[]={0xbe,0x08,0x00};
        err=i2c_master_transmit(s->device,init,sizeof(init),20);
        if (err==ESP_OK) {
            vTaskDelay(pdMS_TO_TICKS(10));err=i2c_master_receive(s->device,&status,1,20);
        }
        if (err!=ESP_OK || !(status&0x08)) {aht21_close(s);return err==ESP_OK?ESP_ERR_INVALID_STATE:err;}
    }
    return ESP_OK;
}
esp_err_t aht21_start(aht21_sensor *s,uint32_t now)
{
    if (!s || !s->device || s->pending) return ESP_ERR_INVALID_STATE;
    const uint8_t command[]={0xac,0x33,0x00};
    esp_err_t err=i2c_master_transmit(s->device,command,sizeof(command),20);
    if (err==ESP_OK) {s->pending=true;s->started_at=now;}
    return err;
}
esp_err_t aht21_poll(aht21_sensor *s,uint32_t now,double *temperature,double *humidity)
{
    *temperature=NAN;*humidity=NAN;
    if (!s || !s->device || !s->pending) return ESP_ERR_INVALID_STATE;
    uint32_t elapsed=now-s->started_at;
    if (elapsed>200) {s->pending=false;return ESP_ERR_TIMEOUT;}
    if (elapsed<80) return ESP_ERR_NOT_FINISHED;
    uint8_t frame[7];esp_err_t err=i2c_master_receive(s->device,frame,sizeof(frame),20);
    if (err==ESP_OK) err=aht21_decode(frame,temperature,humidity);
    if (err!=ESP_ERR_NOT_FINISHED) s->pending=false;
    return err;
}
static void check(const char *name,bool ok)
{
    test_count++;passed&=ok;printf("IO_TEST %s %s\n",name,ok?"PASS":"FAIL");
}
bool board_io_selftests(void)
{
    passed=true;tested=true;
    check("active-high-off",relay_gpio_level(false,false)==0);
    check("active-high-on",relay_gpio_level(true,false)==1);
    check("active-low-off",relay_gpio_level(false,true)==1);
    check("active-low-on",relay_gpio_level(true,true)==0);
#if defined(CONFIG_IDF_TARGET_ESP32)
    check("reject-console-flash-input-only-pins",!io_pin_allowed(1)&&!io_pin_allowed(3)&&!io_pin_allowed(6)&&!io_pin_allowed(34));
#else
    check("reject-console-flash-pins",!io_pin_allowed(43)&&!io_pin_allowed(44)&&!io_pin_allowed(26));
#endif
    switch_debounce d;
    switch_debounce_init(&d,false,0,40);
    bool ok=!switch_debounce_update(&d,true,10)&&!switch_debounce_update(&d,false,20)&&
        !switch_debounce_update(&d,true,25)&&!switch_debounce_update(&d,true,64)&&
        switch_debounce_update(&d,true,65)&&switch_debounce_update(&d,true,90)&&
        switch_debounce_update(&d,false,100)&&!switch_debounce_update(&d,false,140);
    check("debounce-bounce-hold-release",ok);
    switch_debounce_init(&d,false,UINT32_MAX-20,40);
    check("debounce-wrap",!switch_debounce_update(&d,true,UINT32_MAX-10)&&switch_debounce_update(&d,true,30));
    switch_debounce_init(&d,true,0,40);check("boot-no-invented-edge",d.stable&&d.candidate);
    const uint8_t crc_vector[]={0xbe,0xef};
    check("crc8-reference-vector",aht21_crc(crc_vector,2)==0x92);
    uint8_t frame[]={0x08,0x80,0x00,0x06,0x00,0x00,0};frame[6]=aht21_crc(frame,6);
    double t,h;
    check("aht21-known-frame",aht21_decode(frame,&t,&h)==ESP_OK&&fabs(t-25)<0.00001&&fabs(h-50)<0.00001);
    frame[6]^=1;check("aht21-crc-reject",aht21_decode(frame,&t,&h)==ESP_ERR_INVALID_CRC&&isnan(t)&&isnan(h));
    frame[0]=0x88;frame[6]=aht21_crc(frame,6);
    check("aht21-busy",aht21_decode(frame,&t,&h)==ESP_ERR_NOT_FINISHED&&isnan(t));
    frame[0]=0;frame[6]=aht21_crc(frame,6);
    check("aht21-uncalibrated",aht21_decode(frame,&t,&h)==ESP_ERR_INVALID_STATE&&isnan(t));
#ifdef CONFIG_BENCH_IO_SELFTEST
    /* ONLY on the explicitly authorized disconnected spare. Pin 4 is a free
       header pin, pin 5 uses internal pull resistors. Never on live controllers. */
    physical_ran=true;
    for (int inv=0;inv<2;inv++) {
        bool gpio_ok=true;
        for (int boot=0;boot<2 && gpio_ok;boot++) {
            relay_gpio r={0};
            gpio_ok=relay_gpio_open(&r,4,inv,boot)==ESP_OK;
            vTaskDelay(pdMS_TO_TICKS(2)+1);
            gpio_ok=gpio_ok&&gpio_get_level(4)==relay_gpio_level(boot,inv);
            for (int command=0;command<2 && gpio_ok;command++) {
                gpio_ok=relay_gpio_set(&r,command)==ESP_OK;
                vTaskDelay(pdMS_TO_TICKS(2)+1);
                gpio_ok=gpio_ok&&gpio_get_level(4)==relay_gpio_level(command,inv);
            }
            gpio_ok=(relay_gpio_set(&r,false)==ESP_OK)&&gpio_ok;
            gpio_ok=(relay_gpio_close(&r)==ESP_OK)&&gpio_ok;
            gpio_io_config_t released={0};
            gpio_ok=(gpio_get_io_config(4,&released)==ESP_OK)&&gpio_ok;
            gpio_ok=gpio_ok&&!released.oe&&released.ie&&!released.pu&&!released.pd;
        }
        check(inv?"gpio4-active-low-readback":"gpio4-active-high-readback",gpio_ok);
    }
    switch_gpio s={0};uint32_t now=(uint32_t)(esp_timer_get_time()/1000);
    bool input_ok=switch_gpio_open(&s,5,now)==ESP_OK;
    vTaskDelay(pdMS_TO_TICKS(5)+1);
    input_ok=input_ok&&!switch_gpio_sample(&s,(uint32_t)(esp_timer_get_time()/1000));
    if (input_ok) {
        gpio_set_pull_mode(5,GPIO_PULLDOWN_ONLY);vTaskDelay(pdMS_TO_TICKS(5)+1);
        input_ok=!switch_gpio_sample(&s,(uint32_t)(esp_timer_get_time()/1000));
        vTaskDelay(pdMS_TO_TICKS(50));
        input_ok=input_ok&&switch_gpio_sample(&s,(uint32_t)(esp_timer_get_time()/1000));
    }
    input_ok=(switch_gpio_close(&s)==ESP_OK)&&input_ok;
    gpio_io_config_t released={0};
    input_ok=(gpio_get_io_config(5,&released)==ESP_OK)&&input_ok;
    input_ok=input_ok&&!released.oe&&released.ie&&!released.pu&&!released.pd;
    check("gpio5-active-low-debounced-input",input_ok);
    test_pins_released=input_ok;
    gpio_io_config_t output_released={0};
    test_pins_released=test_pins_released&&gpio_get_io_config(4,&output_released)==ESP_OK&&
        !output_released.oe&&output_released.ie&&!output_released.pu&&!output_released.pd;
    aht21_sensor sensor={0};int64_t before=esp_timer_get_time();
    esp_err_t err=aht21_open(&sensor,1,2);missing_sensor_us=esp_timer_get_time()-before;
    esp_err_t closed=aht21_close(&sensor);
    check("missing-aht21-bounded",closed==ESP_OK&&(err==ESP_ERR_NOT_FOUND||err==ESP_ERR_TIMEOUT)&&missing_sensor_us<250000);
#endif
    printf("IO_SELFTEST %s cases=%u physical=%d\n",passed?"PASS":"FAIL",test_count,physical_ran);
    return passed;
}
cJSON *board_io_plan(cJSON *relays,cJSON *sensors)
{
    /* Pure pin/resource validation: never configures hardware or persists data. */
    if (!cJSON_IsArray(relays) || cJSON_GetArraySize(relays)>16 || !cJSON_IsObject(sensors)) return NULL;
    uint64_t used=0;cJSON *r;
    cJSON_ArrayForEach(r,relays) {
        cJSON *pin=cJSON_GetObjectItemCaseSensitive(r,"pin");
        if (!cJSON_IsNumber(pin) || pin->valuedouble!=pin->valueint || !io_pin_allowed(pin->valueint) ||
            !cJSON_IsBool(cJSON_GetObjectItemCaseSensitive(r,"isInverted")) ||
            !cJSON_IsBool(cJSON_GetObjectItemCaseSensitive(r,"defaultValue"))) return NULL;
        uint64_t bit=1ULL<<pin->valueint;
        if (used&bit) return NULL;
        used|=bit;
    }
    const char *keys[]={"i2c_scl","i2c_sda","ds18b20","photo_sensor","light_switch","reset_switch"};
    int pins[6];unsigned count=0;
    cJSON_ArrayForEach(r,sensors) count++;
    if (count!=6) return NULL;
    for (unsigned i=0;i<6;i++) {
        cJSON *v=cJSON_GetObjectItemCaseSensitive(sensors,keys[i]);
        if (!cJSON_IsNumber(v) || v->valuedouble!=v->valueint) return NULL;
        pins[i]=v->valueint;
        if (pins[i]==-1) continue;
        if (!io_pin_allowed(pins[i]) || (used&(1ULL<<pins[i]))) return NULL;
        used|=1ULL<<pins[i];
    }
    if ((pins[0]==-1)!=(pins[1]==-1)) return NULL;
    /* These optional sensor drivers are not implemented yet. */
    if (pins[2]!=-1 || pins[3]!=-1) return NULL;
    cJSON *o=cJSON_CreateObject(),*levels=cJSON_CreateArray();
    cJSON_AddBoolToObject(o,"success",true);cJSON_AddBoolToObject(o,"hardware_applied",false);
    cJSON_AddBoolToObject(o,"application_start_levels_only",true);
    cJSON_AddNumberToObject(o,"switch_debounce_ms",40);
    cJSON_AddBoolToObject(o,"switch_active_low",true);
    cJSON_AddBoolToObject(o,"aht21_configured",pins[0]!=-1);
    cJSON_ArrayForEach(r,relays) {
        cJSON *item=cJSON_CreateObject();
        cJSON_AddNumberToObject(item,"pin",cJSON_GetObjectItemCaseSensitive(r,"pin")->valueint);
        bool inverted=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"isInverted"));
        bool value=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"defaultValue"));
        cJSON_AddNumberToObject(item,"boot_level",relay_gpio_level(value,inverted));
        cJSON_AddItemToArray(levels,item);
    }
    cJSON_AddItemToObject(o,"relay_boot_levels",levels);return o;
}
cJSON *board_io_status(void)
{
    cJSON *o=cJSON_CreateObject();
    cJSON_AddBoolToObject(o,"tested",tested);cJSON_AddBoolToObject(o,"passed",passed);
    cJSON_AddNumberToObject(o,"cases",test_count);cJSON_AddBoolToObject(o,"physical_selftest_ran",physical_ran);
    /* Runtime mode is supplied by the API wrapper, not guessed by this HAL. */
    if (physical_ran) cJSON_AddBoolToObject(o,"test_pins_released",test_pins_released);
    else cJSON_AddNullToObject(o,"test_pins_released");
    cJSON_AddNumberToObject(o,"missing_sensor_probe_us",(double)missing_sensor_us);
    return o;
}
