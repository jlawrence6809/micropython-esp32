#pragma once
#include <stdbool.h>
#include <stddef.h>

/* One independent bounded buffer per physical transport. Caller supplies
 * capacity+1 bytes. Oversized lines are discarded until LF, never truncated
 * into valid requests. No credential/input echo. */
typedef struct {
    char *data;
    size_t capacity, used;
    bool overflow;
} serial_frame;
void serial_frame_init(serial_frame *f, char *buffer, size_t capacity);
bool serial_frame_feed(serial_frame *f, unsigned char ch);
void serial_frame_reset(serial_frame *f);
