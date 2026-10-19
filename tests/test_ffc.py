import unittest
from unittest.mock import patch
from ffc import LinuxI2C,LeptonCCI,STATUS,COMMAND,LENGTH,DATA,GET_SHUTTER_MODE,RUN_FFC,GET_FFC_STATUS

class FakeCamera:
    def __init__(self,mode=1,lockout=0,states=(1,2,0)):
        self.mode=mode; self.lockout=lockout; self.states=list(states)
        self.writes=[]; self.command=None; self.length=0; self.error=0; self.busy=False
    def write_word(self,reg,value):
        self.writes.append((reg,value))
        if reg==COMMAND:self.command=value
        if reg==LENGTH:self.length=value
    def read_words(self,reg,count):
        if reg==STATUS:return (1 if self.busy else self.error,)
        if reg==LENGTH:return (self.length,)
        if reg==DATA:
            if self.command==GET_SHUTTER_MODE:return (self.mode,0,self.lockout,0)+(0,)*12
            if self.command==GET_FFC_STATUS:
                value=self.states.pop(0) if len(self.states)>1 else self.states[0]
                return (value&65535,(value>>16)&65535)
        raise AssertionError((reg,count,self.command))

class FFCTests(unittest.TestCase):
    def cci(self,camera):
        now=[0.]
        def sleep(s):now[0]+=s
        return LeptonCCI(camera,clock=lambda:now[0],sleep=sleep)
    def test_runs_shutter_ffc_polls_completion_and_never_sets_mode(self):
        cam=FakeCamera()
        self.cci(cam).perform_ffc()
        commands=[v for reg,v in cam.writes if reg==COMMAND]
        self.assertEqual(commands,[GET_SHUTTER_MODE,RUN_FFC,GET_FFC_STATUS,GET_FFC_STATUS,GET_FFC_STATUS])
        self.assertEqual([v for reg,v in cam.writes if reg==LENGTH],[16,0,2,2,2])
    def test_manual_mode_also_allowed(self):self.cci(FakeCamera(mode=0,states=(0,))).perform_ffc()
    def test_external_or_locked_shutter_never_runs(self):
        for cam in [FakeCamera(mode=2),FakeCamera(mode=5),FakeCamera(lockout=1)]:
            with self.assertRaises(RuntimeError):self.cci(cam).perform_ffc()
            self.assertNotIn((COMMAND,RUN_FFC),cam.writes)
    def test_busy_and_ffc_timeouts_are_bounded(self):
        cam=FakeCamera();cam.busy=True
        with self.assertRaises(TimeoutError):self.cci(cam).perform_ffc()
        with self.assertRaises(TimeoutError):self.cci(FakeCamera(states=(1,))).perform_ffc()
    def test_camera_errors_never_report_success(self):
        with self.assertRaises(RuntimeError):self.cci(FakeCamera(states=(0xffffffff,))).perform_ffc()
        cam=FakeCamera();cam.error=0xff00
        with self.assertRaisesRegex(RuntimeError,'CCI error -1'):self.cci(cam).perform_ffc()
    def test_linux_register_byte_order_and_short_transfers(self):
        io=LinuxI2C.__new__(LinuxI2C);io.fd=7
        with patch('ffc.os.write',return_value=2) as w,patch('ffc.os.read',return_value=b'\x12\x34\xab\xcd'):
            self.assertEqual(io.read_words(8,2),(0x1234,0xabcd))
            w.assert_called_once_with(7,b'\x00\x08')
        with patch('ffc.os.write',return_value=4) as w:
            io.write_word(COMMAND,RUN_FFC)
            w.assert_called_once_with(7,b'\x00\x04\x02\x42')
        with patch('ffc.os.write',return_value=1):
            with self.assertRaises(OSError):io.write_word(COMMAND,RUN_FFC)
        with patch('ffc.os.write',return_value=2),patch('ffc.os.read',return_value=b'\x00'):
            with self.assertRaises(OSError):io.read_words(STATUS,1)
