if(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/vendor/lua.h")
    message(FATAL_ERROR "Run scripts/fetch-lua.sh first")
endif()
# Only the interpreter and auxiliary API. No filesystem, OS, package, debug,
# coroutine, or standard library modules are linked/exposed.
set(lua_sources lapi.c lcode.c lctype.c ldebug.c ldo.c ldump.c lfunc.c lgc.c
    llex.c lmem.c lobject.c lopcodes.c lparser.c lstate.c lstring.c ltable.c
    ltm.c lundump.c lvm.c lzio.c lauxlib.c)
list(TRANSFORM lua_sources PREPEND "vendor/")
idf_component_register(SRCS ${lua_sources} INCLUDE_DIRS vendor)
