#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "esp_timer.h"
#include "lua.h"
#include "lauxlib.h"
#include "runtime.h"

#define MEMORY_LIMIT (64 * 1024)
#define INSTRUCTION_LIMIT 20000
#define HOOK_STEP 100

typedef struct {
    size_t used, peak;
    unsigned instructions;
    int64_t deadline;
    rule_inputs inputs;
} rule_context;

rule_inputs rule_inputs_default(void)
{
    return (rule_inputs){.temperature=23, .last_temperature=23,
        .humidity=NAN,.last_humidity=NAN,.light=NAN,.last_light=NAN,
        .time_seconds=-1,.last_time_seconds=-1};
}
static void *rule_alloc(void *ud, void *ptr, size_t old_size, size_t new_size)
{
    rule_context *ctx=ud;
    if (!ptr) old_size=0;
    if (!new_size) { free(ptr); ctx->used-=old_size; return NULL; }
    size_t remaining=ctx->used-old_size;
    if (new_size>MEMORY_LIMIT-remaining) return NULL;
    void *out=realloc(ptr,new_size);
    if (out) {
        ctx->used=remaining+new_size;
        if (ctx->used>ctx->peak) ctx->peak=ctx->used;
    }
    return out;
}
static rule_context *context(lua_State *L)
{
    void *ud; lua_getallocf(L,&ud); return ud;
}
static void budget_hook(lua_State *L,lua_Debug *ar)
{
    (void)ar;
    rule_context *ctx=context(L);
    ctx->instructions+=HOOK_STEP;
    if (ctx->instructions>=INSTRUCTION_LIMIT || esp_timer_get_time()>ctx->deadline)
        luaL_error(L,"rule execution budget exceeded");
}
static int reading(lua_State *L)
{
    const rule_inputs *in=&context(L)->inputs;
    int which=(int)lua_tointeger(L,lua_upvalueindex(1));
    double value=NAN;
    switch (which) {
        case 0:value=in->temperature;break;
        case 1:value=in->last_temperature;break;
        case 2:value=in->humidity;break;
        case 3:value=in->last_humidity;break;
        case 4:value=in->light;break;
        case 5:value=in->last_light;break;
        case 6:lua_pushboolean(L,in->switch_state);return 1;
        case 7:lua_pushboolean(L,in->last_switch_state);return 1;
        case 8:lua_pushboolean(L,in->reset_switch);return 1;
        case 9:lua_pushboolean(L,in->last_reset_switch);return 1;
        case 10:value=in->time_seconds<0?NAN:in->time_seconds;break;
        case 11:value=in->last_time_seconds<0?NAN:in->last_time_seconds;break;
    }
    if (isfinite(value)) lua_pushnumber(L,value); else lua_pushnil(L);
    return 1;
}
static int make_time(lua_State *L)
{
    lua_Integer h=luaL_checkinteger(L,1),m=luaL_optinteger(L,2,0),s=luaL_optinteger(L,3,0);
    if (h<0 || h>23 || m<0 || m>59 || s<0 || s>59)
        return luaL_error(L,"time requires hour 0..23, minute/second 0..59");
    lua_pushinteger(L,h*3600+m*60+s);return 1;
}
int evaluate_inputs(const char *source,const rule_inputs *inputs,char *error,size_t error_size,size_t *peak)
{
    if (strlen(source)>2048) {
        snprintf(error,error_size,"rule exceeds 2048 bytes");*peak=0;return -2;
    }
    rule_context ctx={.inputs=*inputs};
    lua_State *L=lua_newstate(rule_alloc,&ctx);
    if (!L) { snprintf(error,error_size,"cannot allocate Lua state");*peak=ctx.peak;return -2; }
    const char *names[]={"get_temperature","get_last_temperature","get_humidity","get_last_humidity",
        "get_light_level","get_last_light_level","get_switch_state","get_last_switch_state",
        "get_reset_switch_state","get_last_reset_switch_state","get_time","get_last_time"};
    for (int i=0;i<12;i++) {
        lua_pushinteger(L,i);lua_pushcclosure(L,reading,1);lua_setglobal(L,names[i]);
    }
    lua_pushcfunction(L,make_time);lua_setglobal(L,"time");
    lua_sethook(L,budget_hook,LUA_MASKCOUNT,HOOK_STEP);
    ctx.deadline=esp_timer_get_time()+20000;
    int status=luaL_loadbufferx(L,source,strlen(source),"rule","t");
    if (status==LUA_OK) status=lua_pcall(L,0,1,0);
    int result=-2;
    if (status!=LUA_OK) {
        const char *msg=lua_tostring(L,-1);snprintf(error,error_size,"%s",msg?msg:"Lua error");
    } else if (lua_isnil(L,-1)) result=-1;
    else if (lua_isboolean(L,-1)) result=lua_toboolean(L,-1)?1:0;
    else snprintf(error,error_size,"rule must return boolean or nil");
    lua_close(L);*peak=ctx.peak;return result;
}
int evaluate(const char *source,double temperature,char *error,size_t error_size,size_t *peak)
{
    rule_inputs in=rule_inputs_default();in.temperature=temperature;in.last_temperature=temperature;
    return evaluate_inputs(source,&in,error,error_size,peak);
}
