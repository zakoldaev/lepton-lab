"""Raw frame storage and analysis, independent of the desktop interface."""
from __future__ import annotations
import csv
import json
import os
import struct
import time
import uuid
from pathlib import Path
import numpy as np

WIDTH, HEIGHT = 160, 120
HEADER = struct.Struct('<4sHHQQQ')
FRAME_BYTES = WIDTH * HEIGHT * 2
PALETTES = {name: np.array(colours,dtype=np.uint8) for name,colours in
            json.loads(Path(__file__).with_name('palettes.json').read_text()).items()}

def display_limits(frame):
    # Match the normal min/max contrast approach of the GroupGets viewer.
    # Skip zeros for range estimation, as its reference code does.
    valid=frame[frame>0]
    if not valid.size:return 0.,1.
    lo,hi=float(valid.min()),float(valid.max())
    return lo,max(lo+1,hi)

def read_exact(stream, n):
    chunks = bytearray()
    while len(chunks) < n:
        b = stream.read(n-len(chunks))
        if not b:
            if not chunks:
                raise EOFError('Camera stream ended')
            raise EOFError('Incomplete camera frame')
        chunks.extend(b)
    return bytes(chunks)

def read_frame(stream):
    magic, w, h, seq, mono, utc = HEADER.unpack(read_exact(stream, HEADER.size))
    if (magic, w, h) != (b'LPT1', WIDTH, HEIGHT):
        raise ValueError('Invalid capture stream header')
    frame = np.frombuffer(read_exact(stream, FRAME_BYTES), dtype='<u2').reshape(HEIGHT, WIDTH).copy()
    return frame, seq, mono, utc

def roi_bounds(a, b):
    x0, x1 = sorted((max(0,min(WIDTH-1,int(a[0]))), max(0,min(WIDTH-1,int(b[0])))))
    y0, y1 = sorted((max(0,min(HEIGHT-1,int(a[1]))), max(0,min(HEIGHT-1,int(b[1])))))
    return x0, y0, x1+1, y1+1

def stats(frame, roi, baseline=None):
    x0,y0,x1,y1 = roi
    values = frame[y0:y1,x0:x1].astype(np.float64)
    result = dict(mean=float(values.mean()), minimum=float(values.min()), maximum=float(values.max()), std=float(values.std()))
    if baseline is not None:
        delta = values - baseline[y0:y1,x0:x1]
        result.update(delta_mean=float(delta.mean()), delta_min=float(delta.min()), delta_max=float(delta.max()))
    return result

class Baseline:
    def __init__(self, target=30):
        self.target=target
        self.cancel()
        self.value=None
        self.metadata=None

    def start(self):
        self.count=0
        self.total=np.zeros((HEIGHT,WIDTH), dtype=np.float64)
        self.active=True
        self.started=time.monotonic()
        self.first_utc=None

    def cancel(self):
        self.active=False
        self.count=0

    def add(self, frame, utc):
        if not self.active: return False
        if self.first_utc is None: self.first_utc=utc
        self.total += frame
        self.count += 1
        if self.count < self.target: return False
        self.value=(self.total/self.count).astype(np.float32)
        self.metadata=dict(frame_count=self.count,first_utc_ns=self.first_utc,last_utc_ns=utc,units='raw_counts',method='per_pixel_arithmetic_mean')
        self.active=False
        return True

FIELDS=['frame_index','capture_sequence','utc_ns','monotonic_ns','x0','y0','x1_exclusive','y1_exclusive','mean_raw','min_raw','max_raw','std_raw','delta_mean_raw','delta_min_raw','delta_max_raw']

class Recorder:
    def __init__(self, root, baseline, baseline_meta, demo=False):
        root=Path(root).expanduser()
        root.mkdir(parents=True,exist_ok=True)
        name=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
        self.path=root/name
        self.path.mkdir()
        self.count=0
        self.closed=False
        self.last_end=0
        self.baseline=None if baseline is None else baseline.copy()
        self.meta=dict(format_version=1, camera='Lepton 3.5', width=WIDTH,height=HEIGHT,dtype='<u2',
            order='frame,y,x',frame_bytes=FRAME_BYTES,units='raw_counts',temperature_mode_verified=False,
            pixel_processing='original received values, no subtraction, scaling or clipping',
            timestamp='host timestamp after complete frame assembly; not sensor exposure time',
            roi_convention='zero-based, origin top-left, exclusive upper bounds',
            packet_validation='packet numbers and segment order checked; packet CRC not checked',
            baseline=baseline_meta,source='SIMULATED' if demo else 'camera',
            created_utc_ns=time.time_ns(),completed=False,frame_count=0,
            capture_sequence_note='counts delivered complete frames, not all sensor frames; capture gaps can occur')
        self._metadata()
        if baseline is not None: np.save(self.path/'baseline.npy',baseline,allow_pickle=False)
        self.raw=open(self.path/'frames.raw','wb')
        self.index=open(self.path/'frames.csv','w',newline='')
        self.writer=csv.writer(self.index)
        self.writer.writerow(FIELDS)
        self.index.flush()

    def _metadata(self):
        temp=self.path/'metadata.json.tmp'
        temp.write_text(json.dumps(self.meta,indent=2)+'\n')
        temp.replace(self.path/'metadata.json')

    def write(self,frame,seq,mono,utc,roi):
        if self.closed: raise RuntimeError('Recording is closed')
        if frame.shape != (HEIGHT,WIDTH) or frame.dtype != np.dtype('uint16'):
            raise ValueError('Expected a 120×160 uint16 frame')
        values=stats(frame,roi,self.baseline)
        self.raw.write(frame.astype('<u2',copy=False).tobytes(order='C'))
        self.raw.flush()
        self.writer.writerow([self.count,seq,utc,mono,*roi,values['mean'],values['minimum'],values['maximum'],values['std'],values.get('delta_mean',''),values.get('delta_min',''),values.get('delta_max','')])
        self.index.flush()
        self.count+=1
        self.last_end=self.index.tell()

    def close(self,error=None):
        if self.closed: return
        self.closed=True
        try:
            self.raw.truncate(self.count*FRAME_BYTES)
            if self.last_end: self.index.seek(self.last_end); self.index.truncate()
            self.raw.flush(); self.index.flush()
            os.fsync(self.raw.fileno()); os.fsync(self.index.fileno())
        finally:
            self.raw.close(); self.index.close()
        self.meta.update(completed=error is None,frame_count=self.count,ended_utc_ns=time.time_ns(),error=error)
        self._metadata()

def colour_image(frame,baseline=None,span=500,palette='GroupGets ironblack',limits=None):
    """Display only. Original data never pass through this function for storage."""
    if baseline is None:
        lo,hi=display_limits(frame) if limits is None else limits
        v=np.clip((frame.astype(float)-lo)/max(hi-lo,1),0,1)
        if palette=='Heat':
            rgb=np.stack([np.minimum(v*3,1),np.clip(v*3-1,0,1),np.clip(v*3-2,0,1)],axis=-1)
            rgb=(rgb*255).astype(np.uint8)
        else:rgb=PALETTES[palette][(v*255).astype(np.uint8)]
        label=f'Display scale: {lo:.0f} – {hi:.0f} raw ({"auto contrast" if limits is None else "fixed contrast"}) · {palette}'
        return rgb,label
    else:
        delta=frame.astype(float)-baseline
        v=np.clip(delta/max(float(span),1),-1,1)
        rgb=np.stack([1-np.maximum(-v,0),1-np.abs(v),1-np.maximum(v,0)],axis=-1)
        label=f'Difference scale: −{span:g} to +{span:g} raw; blue = lower, red = higher'
    return (rgb*255).astype(np.uint8),label
