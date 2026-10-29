/* Temporary, per-image single-AP experiment. Original config never leaves RAM.
 * No NVS writes. Network health heartbeat is withheld until restore succeeds,
 * so restore errors abort a still-pending candidate and permit OTA rollback.
 */
#include "sdkconfig.h"
#include "wifi_ap_trial.h"
#include <stdatomic.h>
#include <string.h>
#ifdef CONFIG_GARDEN_WIFI_SINGLE_AP_TRIAL
static atomic_bool pending=true, prepared=false;
static wifi_config_t original;
static uint32_t deadline;
static int hex(char c) {
    if(c>='0' && c<='9') return c-'0';
    if(c>='a' && c<='f') return c-'a'+10;
    if(c>='A' && c<='F') return c-'A'+10;
    return -1;
}
bool wifi_ap_trial_enabled(void) {return true;}
bool wifi_ap_trial_pending(void) {return atomic_load(&pending);}
esp_err_t wifi_ap_trial_prepare(wifi_config_t *config,uint32_t now_ms)
{
    if(!config || atomic_load(&prepared)) return ESP_ERR_INVALID_STATE;
    const char *s=CONFIG_GARDEN_WIFI_TRIAL_BSSID;
    uint8_t bssid[6];
    if(strlen(s)!=17) return ESP_ERR_INVALID_ARG;
    for(unsigned i=0;i<6;i++) {
        int hi=hex(s[i*3]),lo=hex(s[i*3+1]);
        if(hi<0 || lo<0 || (i<5 && s[i*3+2]!=':')) return ESP_ERR_INVALID_ARG;
        bssid[i]=(uint8_t)((hi<<4)|lo);
    }
    uint8_t any=0;for(unsigned i=0;i<6;i++)any|=bssid[i];
    if(!any || (bssid[0]&1)) return ESP_ERR_INVALID_ARG;
    memcpy(&original,config,sizeof(original));
    memcpy(config->sta.bssid,bssid,6);config->sta.bssid_set=true;
    deadline=now_ms+20000u;atomic_store(&prepared,true);return ESP_OK;
}
esp_err_t wifi_ap_trial_poll(uint32_t now_ms)
{
    if(!atomic_load(&pending) || !atomic_load(&prepared) || (int32_t)(now_ms-deadline)<0) return ESP_OK;
    esp_err_t err=esp_wifi_stop();if(err!=ESP_OK)return err;
    err=esp_wifi_set_config(WIFI_IF_STA,&original);if(err!=ESP_OK)return err;
    err=esp_wifi_start();if(err!=ESP_OK)return err;
    memset(&original,0,sizeof(original));atomic_store(&pending,false);return ESP_OK;
}
#else
bool wifi_ap_trial_enabled(void) {return false;}
bool wifi_ap_trial_pending(void) {return false;}
esp_err_t wifi_ap_trial_prepare(wifi_config_t *config,uint32_t now_ms) {(void)config;(void)now_ms;return ESP_OK;}
esp_err_t wifi_ap_trial_poll(uint32_t now_ms) {(void)now_ms;return ESP_OK;}
#endif
