/* Default build is memory-only. Controller GPIO requires separate build + USB opt-in. */
#include <stdio.h>
#include <stdbool.h>
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_ota_ops.h"
#include "runtime.h"
#include "ota.h"
#include "ota_fence.h"
#include "board_io.h"
#include "io_backend.h"
#include "runtime_lease.h"
#include "device_profile.h"
#if defined(CONFIG_GARDEN_CONTROLLER_IO) && (defined(CONFIG_BENCH_WATCHDOG_STALL) || defined(CONFIG_BENCH_IO_SELFTEST) || defined(CONFIG_BENCH_OTA_FAIL_PENDING_BOOT))
#error "Controller firmware cannot contain bench diagnostics"
#endif
#if (defined(CONFIG_BENCH_WATCHDOG_STALL) + defined(CONFIG_BENCH_IO_SELFTEST) + defined(CONFIG_BENCH_OTA_FAIL_PENDING_BOOT)) > 1
#error "Select one bench diagnostic per build"
#endif

void app_main(void)
{
    const struct { const char *name,*source; double temperature; int expected; } tests[]={
        {"on","return get_temperature() < 18",15,1},
        {"off","return get_temperature() < 18",25,0},
        {"hold","return nil",25,-1},
        {"syntax","return (",25,-2},
        {"invalid-result","return 123",25,-2},
        {"runaway","while true do end",25,-2},
        {"allocation","local x={} for i=1,10000 do x[i]={i,i,i,i} end return true",25,-2},
        {"no-os","return os.execute('anything')",25,-2},
        {"no-bytecode","return load('return true')()",25,-2},
        {"time-helper","return time(14,2,3)==50523",25,1},
        {"time-bounds","return time(24,0)",25,-2},
        {"invalid-clock","return get_time()==nil and get_last_time()==nil",25,1},
        {"null-sensors","return get_humidity()==nil and get_light_level()==nil",25,1},
        {"last-readings","return get_last_temperature()==25 and not get_last_switch_state()",25,1},
    };
    bool passed=true;
    printf("BENCH_BEGIN reset_reason=%d gpio_outputs=disabled\n",esp_reset_reason());
    for (size_t i=0;i<sizeof(tests)/sizeof(tests[0]);i++) {
        char error[160]="";size_t peak=0;
        int64_t started=esp_timer_get_time();
        int result=evaluate(tests[i].source,tests[i].temperature,error,sizeof(error),&peak);
        bool ok=result==tests[i].expected;passed&=ok;
        printf("TEST %s %s result=%d us=%lld lua_peak=%u error=%s\n",tests[i].name,
               ok?"PASS":"FAIL",result,(long long)(esp_timer_get_time()-started),(unsigned)peak,error);
    }
    passed &= board_io_selftests();
    passed &= io_backend_selftests();
    passed &= runtime_lease_selftests();
    passed &= profile_edit_selftests();
    passed &= ota_fence_selftests();
    printf("BENCH_%s heap=%lu min_heap=%lu\n",passed?"PASS":"FAIL",
           (unsigned long)esp_get_free_heap_size(),(unsigned long)esp_get_minimum_free_heap_size());
    ota_boot_check(passed);
    runtime_start();
    ota_health_start();
}
