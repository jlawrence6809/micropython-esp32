#!/usr/bin/env python3
"""Host C tests, no network/USB. Isolated frame buffers and overflow recovery."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
source=r'''
#include <assert.h>
#include <string.h>
#include "serial_frame.h"
int main(void) {
    char a[9],b[9]; serial_frame uart,usb;
    serial_frame_init(&uart,a,8);serial_frame_init(&usb,b,8);
    assert(!serial_frame_feed(&uart,'u'));
    assert(!serial_frame_feed(&usb,'s'));
    assert(!serial_frame_feed(&uart,'1'));
    assert(!serial_frame_feed(&usb,'2'));
    assert(!serial_frame_feed(&usb,'\r'));
    assert(serial_frame_feed(&usb,'\n'));
    assert(!strcmp(b,"s2"));assert(uart.used==2);
    serial_frame_reset(&usb);assert(!b[0]&&!b[1]&&!b[2]);
    assert(serial_frame_feed(&uart,'\n'));assert(!strcmp(a,"u1"));
    serial_frame_reset(&uart);
    for(int i=0;i<8;i++) assert(!serial_frame_feed(&uart,'x'));
    assert(serial_frame_feed(&uart,'\n'));assert(!uart.overflow&&strlen(a)==8);
    serial_frame_reset(&uart);
    for(int i=0;i<1000;i++) assert(!serial_frame_feed(&uart,'p'));
    assert(uart.overflow&&uart.used==8);
    assert(!serial_frame_feed(&usb,'z'));assert(serial_frame_feed(&usb,'\n'));
    assert(!strcmp(b,"z")&&!usb.overflow);
    assert(serial_frame_feed(&uart,'\n'));assert(uart.overflow);
    serial_frame_reset(&uart);
    for(int i=0;i<9;i++) assert(!a[i]);
    assert(!uart.overflow&&!uart.used);
    assert(serial_frame_feed(&uart,'\n'));assert(!strcmp(a,""));
    assert(!serial_frame_feed(&uart,'o'));assert(!serial_frame_feed(&uart,'k'));
    assert(serial_frame_feed(&uart,'\n'));assert(!strcmp(a,"ok"));
    serial_frame_reset(&uart);assert(!strcmp(a,""));
    return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    d=Path(d);(d/'test.c').write_text(source)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(root/'main'),str(d/'test.c'),str(root/'main/serial_frame.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
print('PASS: independent interleaved channels, CRLF, exact bound, overflow discard, recovery and credential-buffer clearing')
