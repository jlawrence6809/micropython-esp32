#!/usr/bin/env python3
"""Offline original-ESP32/S3 separation tests; no serial/network/device access."""
import hashlib,json,os,struct,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
import controller_release as release
import controller_ota as ota
from test_controller_release import fixture,snapshot
from test_controller_ota import Fake
ROOT=Path(__file__).resolve().parent.parent

def original_image():
    b=bytearray(fixture());struct.pack_into('<H',b,12,0)
    b[-32:]=hashlib.sha256(b[:-32]).digest();return bytes(b)

def original_snapshot():
    s=snapshot(False)
    s['config']['chip_target']='esp32'
    s['ota'].update(chip_target='esp32',image_chip_id=0,update_partition_bytes=0x180000)
    return s

class Tests(unittest.TestCase):
    def test_explicit_image_selection(self):
        self.assertEqual(release.image_info(original_image(),'esp32')['image_chip_id'],0)
        with self.assertRaises(ValueError):release.image_info(original_image())
        with self.assertRaises(ValueError):release.image_info(fixture(),'esp32')
        with self.assertRaises(ValueError):release.image_info(fixture(),'esp32c3')
    def test_targets_cannot_cross(self):
        esp=release.image_info(original_image(),'esp32');s3=release.image_info(fixture())
        release.validate_snapshot(original_snapshot(),'123456abcdef',esp)
        release.validate_snapshot(snapshot(False),'123456abcdef',s3)
        with self.assertRaises(ValueError):release.validate_snapshot(snapshot(False),'123456abcdef',esp)
        with self.assertRaises(ValueError):release.validate_snapshot(original_snapshot(),'123456abcdef',s3)
    def test_required_metadata_and_slot_bound(self):
        info=release.image_info(original_image(),'esp32')
        for key,value in [('chip_target','esp32s3'),('image_chip_id',9),('image_chip_id',False),('image_chip_id',None),('update_partition_bytes',None),('update_partition_bytes',100),('update_partition_bytes','1572864')]:
            s=original_snapshot();s['ota'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):release.validate_snapshot(s,'123456abcdef',info)
        s=original_snapshot();s['config']['chip_target']='esp32s3'
        with self.assertRaises(ValueError):release.validate_snapshot(s,'123456abcdef',info)
    def test_executor_rejects_wrong_target_before_io(self):
        t=mock.Mock()
        with self.assertRaises(ValueError):ota.execute(t,original_image(),'123456abcdef',{},lambda:None)
        t.get.assert_not_called();t.upload.assert_not_called()
    def test_original_executor_success_and_lost_reply_no_replay(self):
        for mode in ('ok','lost_reply'):
            f=Fake(mode)
            for s in (f.before,f.after):
                s['config']['chip_target']='esp32'
                s['ota'].update(chip_target='esp32',image_chip_id=0,update_partition_bytes=0x180000)
            journal={};ticks=iter(range(1000))
            result=ota.execute(f,original_image(),'123456abcdef',journal,lambda:None,chip_target='esp32',timeout=4,pause=lambda _:None,now=lambda:next(ticks))
            self.assertTrue(result['confirmed']);self.assertEqual(len(f.uploads),1)
            self.assertEqual(journal['image']['chip_target'],'esp32')
    def test_original_target_preflight_mismatch_never_posts(self):
        f=Fake()
        with self.assertRaises(ValueError):ota.execute(f,original_image(),'123456abcdef',{},lambda:None,chip_target='esp32')
        self.assertEqual(f.uploads,[])
    def test_esp32_image_corruption_rejected(self):
        for offset in (12,48,80,176,len(original_image())-1):
            b=bytearray(original_image());b[offset]^=128
            with self.subTest(offset=offset),self.assertRaises(ValueError):release.image_info(b,'esp32')
    def test_real_target_pin_policy(self):
        board=(ROOT/'main/board_io.c').read_text();start=board.index('bool io_pin_allowed(');end=board.index('\nint relay_gpio_level',start)
        source='#include <assert.h>\n#include <stdbool.h>\n#include "target_board.h"\n'+board[start:end]+r'''
int main(void) {
 assert(io_pin_allowed(4));assert(!io_pin_allowed(-1));assert(!io_pin_allowed(64));
 #if defined(CONFIG_IDF_TARGET_ESP32)
 int relays[]={32,33,25,26,27,14,12,13};
 for(unsigned i=0;i<8;i++)assert(io_pin_allowed(relays[i]));
 int forbidden[]={0,1,2,3,6,7,8,9,10,11,20,24,28,29,30,31,34,35,36,37,38,39,40,41,42,47,48};
 for(unsigned i=0;i<sizeof(forbidden)/sizeof(forbidden[0]);i++)assert(!io_pin_allowed(forbidden[i]));
 assert(GARDEN_IMAGE_CHIP_ID==0);
 #else
 int relays[]={39,38,42,41,40,48,47,21};
 for(unsigned i=0;i<8;i++)assert(io_pin_allowed(relays[i]));
 int forbidden[]={0,3,19,20,26,27,32,33,35,36,37,43,44,45,46};
 for(unsigned i=0;i<sizeof(forbidden)/sizeof(forbidden[0]);i++)assert(!io_pin_allowed(forbidden[i]));
 assert(GARDEN_IMAGE_CHIP_ID==9);
 #endif
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'test.c').write_text(source)
            for target in ('ESP32','ESP32S3'):
                subprocess.run(['cc','-Wall','-Wextra','-Werror','-DCONFIG_IDF_TARGET_'+target+'=1','-I'+str(ROOT/'main'),str(p/'test.c'),'-o',str(p/'test')],check=True)
                subprocess.run([str(p/'test')],check=True)
    def test_build_target_and_config_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'scripts').mkdir();(p/'idf').mkdir();(p/'env/bin').mkdir(parents=True)
            (p/'scripts/build.sh').write_text((ROOT/'scripts/build.sh').read_text())
            (p/'scripts/fetch-lua.sh').write_text('exit 0\n')
            (p/'idf/export.sh').write_text('true\n')
            fake=p/'env/bin/idf.py';fake.write_text('#!/usr/bin/env python3\nimport sys,json\nprint(json.dumps(sys.argv[1:]))\n');fake.chmod(0o700)
            env=dict(os.environ,IDF_PATH=str(p/'idf'),IDF_PYTHON_ENV_PATH=str(p/'env'))
            for flags,target,directory,defaults in [([], 'esp32s3','build','sdkconfig.defaults'),(['--controller'],'esp32s3','build-esp32s3-controller','sdkconfig.defaults;sdkconfig.controller.defaults'),(['--target','esp32'],'esp32','build-esp32','sdkconfig.esp32.defaults'),(['--target','esp32','--controller'],'esp32','build-esp32-controller','sdkconfig.esp32.defaults;sdkconfig.controller.defaults')]:
                args=json.loads(subprocess.check_output(['bash',str(p/'scripts/build.sh'),*flags],env=env,text=True))
                self.assertIn('-DIDF_TARGET='+target,args);self.assertIn('-DSDKCONFIG_DEFAULTS='+defaults,args)
                self.assertIn('-DSDKCONFIG='+str(p/directory/'sdkconfig'),args)
                self.assertEqual(args[args.index('-B')+1],directory);self.assertEqual(args[-1],'build')
            for flags in [['--target','esp32c3'],['-DIDF_TARGET=esp32'],['--controller','-DSDKCONFIG_DEFAULTS=wrong']]:
                self.assertNotEqual(subprocess.run(['bash',str(p/'scripts/build.sh'),*flags],env=env,capture_output=True).returncode,0)
    def test_relay_x8_template_is_inert(self):
        p=json.loads((ROOT/'profiles/relay_x8_unarmed.json').read_text())
        self.assertEqual([r['pin'] for r in p['relays']],[32,33,25,26,27,14,12,13])
        self.assertTrue(all(not r[k] for r in p['relays'] for k in ('value','auto','isInverted','defaultValue','defaultAuto')))
        self.assertTrue(all(v==-1 for v in p['sensor_pins'].values()))
        self.assertIsNone(p['timezone']);self.assertEqual(p['clock_source'],'manual')
        self.assertNotIn('arm_v1',p)
    def test_partition_geometry(self):
        for file,size,slot in [('partitions.csv',0x1000000,0x300000),('partitions.esp32.csv',0x400000,0x180000)]:
            end=0
            for line in (ROOT/file).read_text().splitlines():
                if not line.strip() or line.startswith('#'):continue
                name,typ,sub,offset,length=[x.strip() for x in line.split(',')];off=int(offset,0);n=int(length,0)
                self.assertGreaterEqual(off,end);end=off+n;self.assertLessEqual(end,size)
                if typ=='app':self.assertEqual(n,slot);self.assertEqual(off%0x10000,0)
if __name__=='__main__':unittest.main()
