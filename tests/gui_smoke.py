"""Optional desktop integration check: python3 tests/gui_smoke.py (requires a display)."""
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from viewer import Viewer
from read_recording import load_session

with tempfile.TemporaryDirectory() as folder:
    root=tk.Tk()
    root.withdraw()
    app=Viewer(root,SimpleNamespace(demo=True,device='/dev/spidev0.0',speed=20000000,output=folder))
    def pump(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            root.update()
            time.sleep(.015)
    try:
        pump(.5)
        assert app.latest is not None,'No demo frames'
        assert app.palette.get()=='GroupGets ironblack'
        assert 'auto contrast' in app.scale_text.get()
        app.auto_contrast.set(False);app.change_contrast();pump(.2)
        held=app.fixed_limits
        pump(.2)
        assert app.fixed_limits==held and 'fixed contrast' in app.scale_text.get()
        app.palette.set('Grayscale');app.redraw();pump(.2)
        assert 'Grayscale' in app.scale_text.get()
        app.auto_contrast.set(True);app.change_contrast()
        app.palette.set('GroupGets ironblack');app.redraw()
        app.drag_begin(SimpleNamespace(x=40,y=80))
        app.drag_end(SimpleNamespace(x=120,y=160))
        assert app.roi==(10,20,31,41),app.roi
        app.capture_baseline()
        pump(4)
        assert app.baseline.value is not None,'Baseline did not complete'
        assert app.baseline.metadata['frame_count']==30
        app.difference.set(True);app.redraw();pump(.2)
        assert 'Difference scale:' in app.scale_text.get()
        assert 'CHANGE FROM BASELINE' in app.delta_text.get()
        app.start_ffc()
        assert app.ffc_busy and app.baseline.value is None
        app.capture_baseline();app.toggle_record()
        assert not app.baseline.active and app.recorder is None
        pump(1.5)
        assert not app.ffc_busy and app.latest is not None
        assert 'Demo FFC complete' in app.status.get()
        app.capture_baseline();pump(4)
        assert app.baseline.value is not None
        app.toggle_record();pump(.7)
        path=app.recorder.path
        assert app.recorder.count>=3
        app.start_ffc()
        assert not app.ffc_busy and app.baseline.value is not None,'FFC allowed during recording'
        app.full_roi();pump(.3)
        app.toggle_record();pump(.1)
        meta,frames,rows=load_session(path)
        assert meta['completed'] and len(frames)>=5
        assert rows[0]['x0']=='10' and rows[-1]['x0']=='0'
        assert (path/'baseline.npy').exists()
        app.toggle_record();pump(.3)
        path2=app.recorder.path
        app.process.terminate();pump(.3)
        assert app.recorder is None
        assert not load_session(path2)[0]['completed']
        print('GUI passed: palettes, auto/fixed contrast, live frames, ROI, baseline, difference, FFC, recording guards, disconnect handling')
    finally:app.close()
