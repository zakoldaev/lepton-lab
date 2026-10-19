"""Lepton internal-shutter FFC via FLIR CCI, without changing camera settings.

Register addresses, command IDs and word counts follow the FLIR Lepton SDK
LEPTON_SYS and LEPTON_I2C_Protocol. Linux I2C transactions follow raspi_I2C.
Source references and retained upstream notices: THIRD_PARTY_NOTICES.md and
FLIR-SDK-NOTICES.txt. Original contributions: BSD-2-Clause (see LICENSE);
third-party material retains its own terms.
"""
import fcntl
import os
import struct
import time

STATUS, COMMAND, LENGTH, DATA = 0x0002, 0x0004, 0x0006, 0x0008
GET_SHUTTER_MODE, RUN_FFC, GET_FFC_STATUS = 0x023c, 0x0242, 0x0244

class LinuxI2C:
    def __init__(self, device='/dev/i2c-1'):
        self.fd=os.open(device,os.O_RDWR)
        try:
            fcntl.ioctl(self.fd,0x0703,0x2a)  # I2C_SLAVE (not FORCE)
            fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except Exception:
            os.close(self.fd)
            raise

    def _write(self,data):
        if os.write(self.fd,data)!=len(data):raise OSError('Short I2C write')

    def read_words(self,register,count):
        self._write(struct.pack('>H',register))
        data=os.read(self.fd,count*2)
        if len(data)!=count*2:raise OSError('Short I2C read')
        return struct.unpack('>'+str(count)+'H',data)

    def write_word(self,register,value):self._write(struct.pack('>HH',register,value))
    def close(self):os.close(self.fd)

def uint32(words):return words[0] | (words[1]<<16)

class LeptonCCI:
    def __init__(self,io,clock=time.monotonic,sleep=time.sleep):
        self.io,self.clock,self.sleep=io,clock,sleep

    def ready(self,deadline,check_error=False):
        while self.clock()<deadline:
            status=self.io.read_words(STATUS,1)[0]
            if not status&1:
                code=(status>>8)&255
                if check_error and code:
                    raise RuntimeError(f'Camera rejected the command (CCI error {code-256 if code>=128 else code})')
                return
            self.sleep(.02)
        raise TimeoutError('Timed out waiting for the camera command interface')

    def command(self,command,length,deadline):
        self.ready(deadline)
        self.io.write_word(LENGTH,length)
        self.io.write_word(COMMAND,command)
        self.ready(deadline,check_error=True)
        if length:
            if self.io.read_words(LENGTH,1)[0]!=length:
                raise RuntimeError('Unexpected camera response length')
            return self.io.read_words(DATA,length)
        return ()

    def perform_ffc(self):
        deadline=self.clock()+15
        config=self.command(GET_SHUTTER_MODE,16,deadline)
        mode=uint32(config[:2]); lockout=uint32(config[2:4])
        if mode not in (0,1):
            raise RuntimeError('Camera is in external or unknown FFC mode. Internal-shutter FFC was not sent; check its shutter configuration.')
        if lockout!=0:
            raise RuntimeError('Camera reports shutter temperature lockout. FFC was not sent.')
        self.command(RUN_FFC,0,deadline)
        while self.clock()<deadline:
            status=uint32(self.command(GET_FFC_STATUS,2,deadline))
            if status==0:return
            if status not in (1,2):raise RuntimeError(f'Camera reported FFC failure (status 0x{status:08x})')
            self.sleep(.05)
        raise TimeoutError('Camera did not confirm completion of FFC')

def perform_ffc(device='/dev/i2c-1'):
    io=LinuxI2C(device)
    try:LeptonCCI(io).perform_ffc()
    finally:io.close()
