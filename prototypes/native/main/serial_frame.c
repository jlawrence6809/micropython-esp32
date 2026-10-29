#include "serial_frame.h"

void serial_frame_init(serial_frame *f, char *buffer, size_t capacity)
{
    *f=(serial_frame){.data=buffer,.capacity=capacity};
    buffer[0]=0;
}
bool serial_frame_feed(serial_frame *f, unsigned char ch)
{
    if (ch=='\r') return false;
    if (ch=='\n') { f->data[f->used]=0; return true; }
    if (f->used<f->capacity) f->data[f->used++]=(char)ch;
    else f->overflow=true;
    return false;
}
void serial_frame_reset(serial_frame *f)
{
    /* Volatile stores keep credential clearing observable even under LTO. */
    volatile char *p=f->data;
    for (size_t i=0;i<=f->used;i++) p[i]=0;
    f->used=0; f->overflow=false;
}
