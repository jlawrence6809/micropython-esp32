#!/usr/bin/env python3
"""Compile the actual power-policy helper twice; no device/network access."""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = (ROOT / 'main/runtime.c').read_text()
start = src.index('static esp_err_t wifi_apply_power_policy(void)')
end = src.index('\nstatic void wifi_json_bssid', start)
helper = src[start:end]
# Fail closed on setter errors, initialize first, policy before any task/start.
init = src.index('ESP_ERROR_CHECK(esp_wifi_init(&init))')
mode = src.index('ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA))', init)
apply = src.index('ESP_ERROR_CHECK(wifi_apply_power_policy())', mode)
assert init < mode < apply < src.index('xTaskCreate(', apply)
assert apply < src.index('ESP_ERROR_CHECK(esp_wifi_start())', apply)
kconfig = (ROOT / 'main/Kconfig.projbuild').read_text()
section = kconfig.split('config GARDEN_WIFI_DISABLE_MODEM_SLEEP', 1)[1].split('endmenu', 1)[0]
assert 'default n' in section
for p in ROOT.glob('sdkconfig*.defaults'):
    assert 'CONFIG_GARDEN_WIFI_DISABLE_MODEM_SLEEP=y' not in p.read_text(), p
harness = '''
#include <assert.h>
typedef int esp_err_t;
enum { ESP_OK=0, WIFI_PS_NONE=0 };
static int calls, returned_error;
static esp_err_t esp_wifi_set_ps(int mode) {
    assert(mode==WIFI_PS_NONE); calls++; return returned_error;
}
''' + helper + '''
int main(void) {
    assert(wifi_apply_power_policy()==ESP_OK);
#ifdef CONFIG_GARDEN_WIFI_DISABLE_MODEM_SLEEP
    assert(calls==1); returned_error=123;
    assert(wifi_apply_power_policy()==123); assert(calls==2);
#else
    assert(calls==0); returned_error=123;
    assert(wifi_apply_power_policy()==ESP_OK); assert(calls==0);
#endif
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='garden-wifi-ps-') as tmp:
    c = pathlib.Path(tmp) / 'test.c'
    exe = pathlib.Path(tmp) / 'test'
    c.write_text(harness)
    for enabled in (False, True):
        flags = ['-DCONFIG_GARDEN_WIFI_DISABLE_MODEM_SLEEP=1'] if enabled else []
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', *flags, str(c), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
print('WIFI_POWER_POLICY_HOST_TEST PASS: default untouched, explicit NONE, error propagation, init/task ordering, no enabled shared defaults')
