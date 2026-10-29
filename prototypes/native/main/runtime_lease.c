#include <limits.h>
#include <stdio.h>
#include "runtime_lease.h"

void runtime_lease_init(runtime_lease *lease,const unsigned counts[RUNTIME_TASKS],uint32_t now)
{
    for (unsigned i=0;i<RUNTIME_TASKS;i++) {lease->observed[i]=counts[i];lease->changed_at[i]=now;}
}
unsigned runtime_lease_poll(runtime_lease *lease,const unsigned counts[RUNTIME_TASKS],uint32_t now)
{
    unsigned expired=0;
    for (unsigned i=0;i<RUNTIME_TASKS;i++) {
        if (counts[i]!=lease->observed[i]) {lease->observed[i]=counts[i];lease->changed_at[i]=now;}
        if ((uint32_t)(now-lease->changed_at[i])>=RUNTIME_LEASE_MS) expired|=1u<<i;
    }
    return expired;
}
bool runtime_lease_selftests(void)
{
    unsigned counts[RUNTIME_TASKS]={0};runtime_lease lease;
    runtime_lease_init(&lease,counts,0);
    bool ok=runtime_lease_poll(&lease,counts,9999)==0 && runtime_lease_poll(&lease,counts,10000)==15;
    for (unsigned stalled=0;stalled<RUNTIME_TASKS;stalled++) {
        for (unsigned i=0;i<RUNTIME_TASKS;i++) counts[i]=10;
        runtime_lease_init(&lease,counts,100);
        for (unsigned i=0;i<RUNTIME_TASKS;i++) if (i!=stalled) counts[i]++;
        ok=ok&&runtime_lease_poll(&lease,counts,10100)==(1u<<stalled);
        counts[stalled]++;ok=ok&&runtime_lease_poll(&lease,counts,10101)==0;
    }
    for (unsigned i=0;i<RUNTIME_TASKS;i++) counts[i]=UINT_MAX;
    runtime_lease_init(&lease,counts,0);
    for (unsigned i=0;i<RUNTIME_TASKS;i++) counts[i]=0;
    ok=ok&&runtime_lease_poll(&lease,counts,10000)==0; /* counter wrap = progress */
    runtime_lease_init(&lease,counts,UINT32_MAX-500);
    ok=ok&&runtime_lease_poll(&lease,counts,9498)==0 && runtime_lease_poll(&lease,counts,9499)==15;
    printf("RUNTIME_LEASE_TEST %s\n",ok?"PASS":"FAIL");return ok;
}
