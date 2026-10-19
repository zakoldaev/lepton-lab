import csv
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
from core import Baseline, Recorder, WIDTH, HEIGHT, HEADER, FRAME_BYTES, read_frame, roi_bounds, stats, colour_image
from read_recording import load_session

class Fragmented(io.BytesIO):
    def read(self,n=-1):return super().read(min(n,7))

class AnalysisTests(unittest.TestCase):
    def test_binary_transport_partial_reads_and_endian(self):
        values=np.arange(WIDTH*HEIGHT,dtype=np.uint16).reshape(HEIGHT,WIDTH)
        values[0,0]=65535
        wire=HEADER.pack(b'LPT1',WIDTH,HEIGHT,17,123,456)+values.astype('<u2').tobytes()
        f,seq,mono,utc=read_frame(Fragmented(wire))
        np.testing.assert_array_equal(f,values)
        self.assertEqual((seq,mono,utc),(17,123,456))
        with self.assertRaises(EOFError):read_frame(io.BytesIO(wire[:-1]))
        with self.assertRaises(ValueError):read_frame(io.BytesIO(b'FAIL'+wire[4:]))

    def test_roi_inclusive_mouse_pixels_and_edges(self):
        self.assertEqual(roi_bounds((159,119),(159,119)),(159,119,160,120))
        self.assertEqual(roi_bounds((500,500),(-20,-20)),(0,0,160,120))
        self.assertEqual(roi_bounds((20,30),(10,5)),(10,5,21,31))
        f=np.arange(WIDTH*HEIGHT,dtype=np.uint16).reshape(HEIGHT,WIDTH)
        self.assertEqual(stats(f,(159,119,160,120))['mean'],19199)

    def test_baseline_averages_future_frames_and_signed_difference(self):
        b=Baseline()
        b.start()
        for i in range(30):
            ready=b.add(np.full((HEIGHT,WIDTH),100+i,dtype=np.uint16),i)
            self.assertEqual(ready,i==29)
        np.testing.assert_array_equal(b.value,np.full((HEIGHT,WIDTH),114.5))
        s=stats(np.full((HEIGHT,WIDTH),90,dtype=np.uint16),(0,0,WIDTH,HEIGHT),b.value)
        self.assertEqual(s['delta_mean'],-24.5)
        b.start(); b.add(np.zeros((HEIGHT,WIDTH),np.uint16),40); b.cancel()
        self.assertEqual(b.value[0,0],114.5)

    def test_lossless_recording_roi_changes_and_baseline_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            b=np.full((HEIGHT,WIDTH),30000,dtype=np.float32)
            rec=Recorder(root,b,{'frame_count':30},demo=True)
            a=np.arange(WIDTH*HEIGHT,dtype=np.uint16).reshape(HEIGHT,WIDTH)
            a[0,0]=65535
            rec.write(a,10,100,200,(0,0,1,1))
            b[:]=0 # session baseline must be immutable
            rec.write(a,12,110,220,(159,119,160,120))
            rec.close()
            meta,frames,index=load_session(rec.path)
            self.assertTrue(meta['completed'])
            self.assertEqual(meta['source'],'SIMULATED')
            np.testing.assert_array_equal(frames[0],a)
            np.testing.assert_array_equal(frames[1],a)
            self.assertEqual(float(index[0]['mean_raw']),65535)
            self.assertEqual(float(index[1]['delta_mean_raw']),19199-30000)
            self.assertEqual((rec.path/'frames.raw').stat().st_size,2*FRAME_BYTES)
            np.testing.assert_array_equal(np.load(rec.path/'baseline.npy'),np.full((HEIGHT,WIDTH),30000))

    def test_recover_interrupted_session_without_guessing_partial_frame(self):
        with tempfile.TemporaryDirectory() as root:
            r=Recorder(root,None,None)
            r.write(np.zeros((HEIGHT,WIDTH),np.uint16),0,1,2,(0,0,160,120))
            r.close('simulated disconnection')
            with (r.path/'frames.raw').open('ab') as f:f.write(b'partial')
            meta,frames,index=load_session(r.path)
            self.assertFalse(meta['completed']); self.assertEqual(len(frames),1)
            self.assertEqual(len(index),1)

    def test_recording_disk_write_error_keeps_prior_complete_frames(self):
        with tempfile.TemporaryDirectory() as root:
            r=Recorder(root,None,None)
            f=np.ones((HEIGHT,WIDTH),np.uint16)
            r.write(f,0,1,2,(0,0,160,120))
            class BrokenWriter:
                def writerow(self,row):raise OSError('disk full')
            r.writer=BrokenWriter()
            with self.assertRaises(OSError):r.write(f,1,2,3,(0,0,160,120))
            r.close('disk full')
            meta,frames,index=load_session(r.path)
            self.assertEqual(len(frames),1)
            self.assertEqual((r.path/'frames.raw').stat().st_size,FRAME_BYTES)
            self.assertFalse(meta['completed'])

    def test_display_handles_uniform_frame_and_never_mutates_raw(self):
        f=np.full((HEIGHT,WIDTH),65535,np.uint16)
        rgb,_=colour_image(f)
        self.assertEqual(rgb.shape,(HEIGHT,WIDTH,3))
        self.assertTrue(np.isfinite(rgb).all())
        base=f.astype(np.float32)
        rgb,_=colour_image(f,base)
        self.assertTrue((rgb==255).all())
        self.assertTrue((f==65535).all())

    def test_hot_object_changes_auto_background_but_not_fixed_background(self):
        f=np.full((HEIGHT,WIDTH),1050,np.uint16)
        f[0,0]=1000; f[0,1]=1100
        auto_before,_=colour_image(f)
        fixed_before,_=colour_image(f,limits=(1000,1100))
        hotter=f.copy(); hotter[0,1]=1200
        auto_after,_=colour_image(hotter)
        fixed_after,label=colour_image(hotter,limits=(1000,1100))
        self.assertFalse(np.array_equal(auto_before[60,80],auto_after[60,80]))
        np.testing.assert_array_equal(fixed_before[60,80],fixed_after[60,80])
        self.assertIn('fixed contrast',label)
        self.assertEqual(hotter[60,80],f[60,80])

    def test_groupgets_palette_endpoints_and_difference_independence(self):
        f=np.full((HEIGHT,WIDTH),1000,np.uint16);f[-1,-1]=2000
        rgb,_=colour_image(f)
        np.testing.assert_array_equal(rgb[0,0],[255,255,255])
        np.testing.assert_array_equal(rgb[-1,-1],[255,255,24])
        base=np.full((HEIGHT,WIDTH),1500,np.float32)
        a,_=colour_image(f,base,span=500,palette='GroupGets ironblack')
        b,_=colour_image(f,base,span=500,palette='Heat',limits=(1000,2000))
        np.testing.assert_array_equal(a,b)

if __name__=='__main__':unittest.main()
