#!/usr/bin/env python3
"""Bounded, non-persistent HTTP stress/slow-body tests on the memory-only spare."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import socket
import time
import urllib.error
import urllib.request
from unittest import mock
from ota import Bench, verify_read

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('host')
p.add_argument('--seconds',type=int,default=45)
a=p.parse_args()
if not 5<=a.seconds<=600:
    p.error('Use 5..600 seconds; no unbounded load')

fake=mock.Mock()
fake.get.side_effect=[TimeoutError(),{'ok':True}]
with mock.patch('ota.time.sleep'), mock.patch('builtins.print'):
    assert verify_read(fake,'/api/status')=={'ok':True}
assert fake.get.call_count==2
fake.upload.assert_not_called()
for failure,attempts in ((TimeoutError(),3),(urllib.error.HTTPError('test',503,'test',None,None),1)):
    check=mock.Mock();check.get.side_effect=failure
    with mock.patch('ota.time.sleep'),mock.patch('builtins.print'):
        try:
            verify_read(check,'/api/status')
        except type(failure):
            pass
        else:
            raise AssertionError('Verification suppressed a terminal failure')
    assert check.get.call_count==attempts
    check.upload.assert_not_called()
print('Read-only verification retry unit test PASS (injected errors, bounded attempts, no upload replay)')

b=Bench(a.host)
assert not b.get('/api/io/status')['gpio_compiled']
assert not b.get('/api/watchdog/status')['fault_injection']
start=b.wait(lambda s:s['healthy'] and s['runtime_watchdog_active'])
original=b.get('/api/profile')
def heap():
    return next(r['value'] for r in b.get('/api/status') if r['key']=='free_heap')
before_heap=heap()

cases=[
 ('GET','/api/ota/status',None,200,None),
 ('GET','/api/watchdog/status',None,200,None),
 ('GET','/api/profile/edit',None,200,None),
 ('GET','/api/ota/fence',None,200,True),
 ('POST','/api/validate-rule',b'return true',200,True),
 ('POST','/api/validate-rule',b'while true do end',200,False),
 ('POST','/api/validate-rule',b'local x={} for i=1,10000 do x[i]={i,i,i,i} end return true',200,False),
 ('POST','/api/bench/evaluate',b'{"rule":"return nil","inputs":{}}',200,True),
 ('POST','/api/bench/evaluate',b'{"rule":"return true","inputs":{"switch_state":1}}',400,False),
 ('POST','/api/bench/evaluate',b'['*17+b'0'+b']'*17,400,False),
]
end=time.monotonic()+a.seconds

def worker(offset):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    total=0;errors=[];maximum=0.0
    while time.monotonic()<end:
        method,path,body,expected,success=cases[(total+offset)%len(cases)]
        req=urllib.request.Request(b.base+path,data=body,method=method,
                                   headers={'Content-Type':'application/json','Connection':'close'})
        started=time.monotonic()
        try:
            try:
                with opener.open(req,timeout=8) as response:
                    code,result=response.status,json.load(response)
            except urllib.error.HTTPError as error:
                code,result=error.code,json.load(error)
            assert code==expected, 'status '+str(code)
            if success is not None:
                assert result['success'] is success
            if path=='/api/watchdog/status':
                assert result['monitor_active'] and not result['fault_injection']
        except Exception as error:
            errors.append(type(error).__name__)
        maximum=max(maximum,time.monotonic()-started)
        total+=1
        time.sleep(0.05)
    return total,errors,maximum

with ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(worker,i*3) for i in range(2)]
    results=[f.result() for f in futures]
errors=[error for _,items,_ in results for error in items]
print('HTTP stress:',sum(r[0] for r in results),'requests,',a.seconds,'seconds, failures=',len(errors),
      'max response seconds=',round(max(r[2] for r in results),3))
assert not errors, 'Transport/protocol failures observed: '+','.join(errors[:10])

# Reject/close an oversized declaration without waiting for its missing body.
with socket.create_connection((a.host,80),timeout=8) as sock:
    sock.settimeout(8)
    sock.sendall((f'POST /api/bench/evaluate HTTP/1.1\r\nHost: {a.host}\r\n'
                  'Content-Length: 100000000\r\n\r\n{').encode())
    oversized=b''
    while True:
        chunk=sock.recv(4096)
        if not chunk:break
        oversized+=chunk
assert b' 413 ' in oversized.split(b'\r\n',1)[0]
print('Oversized declaration rejected/closed without waiting for absent body PASS')

# Keep trickling bytes within the per-recv timeout, but beyond the overall body
# budget. This endpoint is pure even if an old firmware wrongly dispatches it.
body=b'{"rule":"return true","inputs":{}}'
with socket.create_connection((a.host,80),timeout=8) as sock:
    sock.settimeout(12)
    header=(f'POST /api/bench/evaluate HTTP/1.1\r\nHost: {a.host}\r\n'
            f'Content-Length: {len(body)}\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n').encode()
    sock.sendall(header+body[:1])
    for chunk in (body[1:2],body[2:3],body[3:]):
        time.sleep(2.2)
        sock.sendall(chunk)
    response=b''
    while True:
        chunk=sock.recv(4096)
        if not chunk:break
        response+=chunk
assert b' 408 ' in response.split(b'\r\n',1)[0], 'Slow body was not rejected'
print('Slow trickle rejected by total body deadline; worker released without controller reset PASS')
time.sleep(3)
after=b.get('/api/ota/status')
assert after['boot_id']==start['boot_id'] and after['healthy'] and after['runtime_watchdog_active']
assert b.get('/api/profile')==original
assert not b.get('/api/io/status')['gpio_active']
after_heap=heap()
assert after_heap>=before_heap-16384, 'Large retained heap change; investigate'
print('Same boot, progress leases healthy, profile/output isolation PASS; sampled heap',before_heap,'->',after_heap,
      '(short observation, not leak/long-term reliability proof)')
