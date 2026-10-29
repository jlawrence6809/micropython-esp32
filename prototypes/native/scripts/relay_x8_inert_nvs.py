#!/usr/bin/env python3
"""Strict original-board failed-startup NVS review, not a general NVS decoder.
Accept ONLY blank bytes, or fresh bench/clock namespaces + bench uint32 schema1.
Reject strings/blobs, arm/profile/Wi-Fi/unknown keys, erased history and bad CRCs.
No raw values or unknown keys exported. Layout/CRC follows IDF5.5.1 NVS parser.
"""
import hashlib
import struct
import zlib


def require(ok, message):
    if not ok:raise ValueError(message)


def inspect(raw):
    raw=bytes(raw)
    require(len(raw)==0x6000,'Wrong NVS length')
    records=[];used_pages=0
    for start in range(0,len(raw),4096):
        p=raw[start:start+4096]
        if p==b'\xff'*4096:continue
        used_pages+=1
        require(struct.unpack_from('<I',p,0)[0] in (0xfffffffe,0xfffffffc) and p[8]==0xfe,'Unexpected NVS page state/version')
        require(struct.unpack_from('<I',p,28)[0]==zlib.crc32(p[4:28],0xffffffff),'NVS page CRC mismatch')
        require(p[63]&0xf0==0xf0,'NVS reserved bitmap bits changed')
        for i in range(126):
            state=(p[32+i//4] >> (2*(i%4))) & 3
            entry=p[64+32*i:96+32*i]
            if state==3:
                require(entry==b'\xff'*32,'Nonblank unallocated NVS entry');continue
            require(state==2,'NVS erased/invalid history refused')
            require(entry[2]==1 and entry[3]==0xff,'Variable/chunked NVS value refused')
            require(struct.unpack_from('<I',entry,4)[0]==zlib.crc32(entry[:4]+entry[8:],0xffffffff),'NVS entry CRC mismatch')
            ns,typ=entry[0],entry[1];key=entry[8:24]
            require(b'\0' in key,'Invalid NVS key')
            key,padding=key.split(b'\0',1);require(not any(padding),'Unexpected NVS key padding')
            if ns==0:
                require(typ==1 and key in (b'bench',b'clock') and entry[25:]==b'\xff'*7,'Unexpected NVS namespace')
                value=entry[24];require(1<=value<255,'Invalid namespace index')
            else:
                require(typ==4 and key==b'schema' and entry[28:]==b'\xff'*4,'Unexpected NVS setting')
                value=struct.unpack_from('<I',entry,24)[0];require(value==1,'Unexpected schema version')
            records.append((ns,typ,key,value))
    if records:
        require(used_pages==1 and len(records)==3,'Not a fresh schema-only NVS')
        namespaces={r[3]:r[2] for r in records if r[0]==0}
        require(len(namespaces)==2 and set(namespaces.values())=={b'bench',b'clock'},'Namespace set mismatch')
        settings=[r for r in records if r[0]!=0]
        require(len(settings)==1 and namespaces.get(settings[0][0])==b'bench','Schema namespace mismatch')
        kind='schema_only'
    else:
        require(used_pages==0,'Nonblank empty NVS refused');kind='blank'
    return dict(kind=kind,bytes=len(raw),md5=hashlib.md5(raw).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),
                activation_profile_credentials_absent=True,records=len(records))
