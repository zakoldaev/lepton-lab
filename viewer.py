#!/usr/bin/env python3
"""Lepton Lab: raw recording, mouse-selected ROI and averaged baseline."""
import argparse
import json
import queue
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
from core import Baseline, Recorder, WIDTH, HEIGHT, read_frame, roi_bounds, stats, colour_image, display_limits
from ffc import perform_ffc

class Viewer:
    def __init__(self,root,args):
        self.root,self.args=root,args
        self.lock=threading.RLock()
        self.events=queue.Queue()
        self.baseline=Baseline()
        self.roi=(0,0,WIDTH,HEIGHT)
        self.recorder=None
        self.latest=None
        self.received_at=0
        self.previous_mono=None
        self.fps=0
        self.closing=False
        self.ffc_busy=False
        self.ffc_thread=None
        self.skip_frames=0
        self.drag_start=None
        self.last_drawn=None
        self.fixed_limits=None
        self.output=Path(args.output).expanduser().resolve()
        self.output.mkdir(parents=True,exist_ok=True)
        root.title('Lepton Lab' + (' — DEMO' if args.demo else ''))
        root.geometry(f'1000x{min(790,max(600,root.winfo_screenheight()-80))}')
        root.minsize(980,600)
        root.configure(bg='#101a27')
        style=ttk.Style(root)
        style.theme_use('clam')
        style.configure('.',background='#101a27',foreground='#e7eef7',font=('Arial',11))
        style.configure('TButton',background='#24465c',foreground='white',padding=(10,9))
        style.map('TButton',background=[('active','#35647c')],foreground=[('disabled','#8191a5')])
        style.configure('Title.TLabel',font=('Arial',24,'bold'))
        style.configure('Muted.TLabel',foreground='#a5b6c9')
        style.configure('Stats.TLabel',font=('Arial',13),padding=(0,5))
        # Keep every control reachable on smaller remote-desktop resolutions.
        viewport=tk.Canvas(root,bg='#101a27',highlightthickness=0)
        scroll=ttk.Scrollbar(root,orient='vertical',command=viewport.yview)
        scroll.pack(side='right',fill='y'); viewport.pack(side='left',fill='both',expand=True)
        viewport.configure(yscrollcommand=scroll.set)
        outer=ttk.Frame(viewport,padding=20)
        content=viewport.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda e:viewport.configure(scrollregion=viewport.bbox('all')))
        viewport.bind('<Configure>',lambda e:viewport.itemconfigure(content,width=e.width))
        title=ttk.Frame(outer); title.pack(fill='x')
        ttk.Label(title,text='Lepton Lab',style='Title.TLabel').pack(side='left')
        ttk.Label(title,text='SIMULATED DATA' if args.demo else 'LEPTON 3.5  /  160 × 120',style='Muted.TLabel').pack(side='right')
        ttk.Label(outer,text='Raw pixel values • temperature output not verified • drag across the image to select an area',style='Muted.TLabel').pack(anchor='w',pady=(7,16))
        toolbar=ttk.Frame(outer); toolbar.pack(fill='x',pady=(0,14))
        self.record_button=ttk.Button(toolbar,text='● Start recording',command=self.toggle_record)
        self.record_button.pack(side='left',padx=(0,8))
        self.ffc_button=ttk.Button(toolbar,text='Perform FFC',command=self.start_ffc)
        self.ffc_button.pack(side='left',padx=(0,8))
        self.capture_button=ttk.Button(toolbar,text='Capture baseline',command=self.capture_baseline)
        self.capture_button.pack(side='left',padx=(0,8))
        self.clear_button=ttk.Button(toolbar,text='Clear baseline',command=self.clear_baseline)
        self.clear_button.pack(side='left',padx=(0,8))
        ttk.Button(toolbar,text='Select whole image',command=self.full_roi).pack(side='left')
        displaybar=ttk.Frame(outer); displaybar.pack(fill='x',pady=(0,12))
        ttk.Label(displaybar,text='Live colours:').pack(side='left',padx=(0,8))
        self.palette=tk.StringVar(value='GroupGets ironblack')
        palettes=ttk.Combobox(displaybar,textvariable=self.palette,values=['GroupGets ironblack','Grayscale','Heat'],state='readonly',width=22)
        palettes.pack(side='left',padx=(0,16)); palettes.bind('<<ComboboxSelected>>',lambda e:self.redraw())
        self.auto_contrast=tk.BooleanVar(value=True)
        ttk.Checkbutton(displaybar,text='Auto contrast (adapt to scene)',variable=self.auto_contrast,command=self.change_contrast).pack(side='left')
        ttk.Label(displaybar,text='Difference view uses its own fixed scale',style='Muted.TLabel').pack(side='right')
        main=ttk.Frame(outer); main.pack(fill='x')
        self.canvas=tk.Canvas(main,width=640,height=480,bg='#050b12',highlightthickness=1,highlightbackground='#345065')
        self.canvas.pack(side='left')
        self.canvas.create_text(320,240,text='Waiting for camera frames…',fill='#b9c9d8',font=('Arial',17),tags='waiting')
        self.canvas.bind('<ButtonPress-1>',self.drag_begin)
        self.canvas.bind('<B1-Motion>',self.drag_move)
        self.canvas.bind('<ButtonRelease-1>',self.drag_end)
        panel=ttk.Frame(main,padding=(20,0,0,0)); panel.pack(side='left',fill='both',expand=True)
        ttk.Label(panel,text='SELECTED AREA',style='Muted.TLabel').pack(anchor='w')
        self.roi_text=tk.StringVar(value='Whole image · 19,200 pixels')
        ttk.Label(panel,textvariable=self.roi_text,wraplength=270).pack(anchor='w',pady=(8,15))
        self.stat_text=tk.StringVar(value='Waiting for data')
        ttk.Label(panel,textvariable=self.stat_text,style='Stats.TLabel',justify='left').pack(anchor='w')
        ttk.Separator(panel).pack(fill='x',pady=15)
        self.delta_text=tk.StringVar(value='Capture a baseline\nto measure changes.')
        ttk.Label(panel,textvariable=self.delta_text,justify='left',wraplength=260).pack(anchor='w')
        self.difference=tk.BooleanVar(value=False)
        ttk.Checkbutton(panel,text='Show baseline difference',variable=self.difference,command=self.redraw).pack(anchor='w',pady=(20,6))
        ttk.Label(panel,text='Difference colour range (± raw)',style='Muted.TLabel').pack(anchor='w')
        self.span=tk.IntVar(value=500)
        ttk.Spinbox(panel,from_=1,to=65535,textvariable=self.span,width=10,command=self.redraw).pack(anchor='w',pady=7)
        ttk.Label(panel,text='Baseline = average of 30 frames.\nKeep the scene still while capturing.\nThis does not perform camera FFC.',style='Muted.TLabel',wraplength=255,justify='left').pack(anchor='w',pady=12)
        self.scale_text=tk.StringVar(value='')
        ttk.Label(outer,textvariable=self.scale_text,style='Muted.TLabel').pack(anchor='w',pady=(10,6))
        self.baseline_text=tk.StringVar(value='No baseline captured')
        ttk.Label(outer,textvariable=self.baseline_text).pack(anchor='w')
        dest=ttk.Frame(outer); dest.pack(fill='x',pady=(10,5))
        self.folder_button=ttk.Button(dest,text='Recording folder…',command=self.select_folder)
        self.folder_button.pack(side='left')
        self.folder_text=tk.StringVar(value=str(self.output))
        ttk.Label(dest,textvariable=self.folder_text,style='Muted.TLabel',wraplength=750).pack(side='left',padx=10)
        self.status=tk.StringVar(value='Starting capture…')
        ttk.Label(outer,textvariable=self.status,wraplength=950).pack(anchor='w',pady=8)
        binary=Path(__file__).resolve().with_name('lepton_capture')
        command=[str(binary),'--demo'] if args.demo else [str(binary),args.device,str(args.speed)]
        self.process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        self.reader=threading.Thread(target=self.read_loop,daemon=True); self.reader.start()
        threading.Thread(target=self.error_loop,daemon=True).start()
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.tick)

    def read_loop(self):
        try:
            while not self.closing:
                frame,seq,mono,utc=read_frame(self.process.stdout)
                with self.lock:
                    if self.ffc_busy:continue  # Drain SPI; do not analyse shutter frames.
                    if self.skip_frames:
                        self.skip_frames-=1
                        continue
                    if self.previous_mono is not None and mono>self.previous_mono:
                        self.fps=1e9/(mono-self.previous_mono)
                    self.previous_mono=mono
                    completed=self.baseline.add(frame,utc)
                    if completed:
                        self.events.put('Baseline captured: average of 30 frames. Select the difference view to compare.')
                        try:
                            p=self.output/('baseline-'+str(utc))
                            np.save(str(p)+'.npy',self.baseline.value,allow_pickle=False)
                            Path(str(p)+'.json').write_text(json.dumps(self.baseline.metadata,indent=2))
                        except OSError as e: self.events.put('Baseline is in memory, but could not save it: '+str(e))
                    if self.recorder:
                        try: self.recorder.write(frame,seq,mono,utc,self.roi)
                        except Exception as e:
                            self.stop_record('Recording error: '+str(e))
                    self.latest=(frame,seq,mono,utc)
                    self.received_at=time.monotonic()
        except Exception as e:
            if not self.closing:
                with self.lock:
                    self.baseline.cancel()
                    self.stop_record('Camera stopped: '+str(e))
                self.events.put('Camera stopped: '+str(e)+'. Close this window, check the connection, and relaunch.')

    def error_loop(self):
        for line in iter(self.process.stderr.readline,b''):
            self.events.put(line.decode(errors='replace').strip())

    def stop_record(self,error=None):
        if self.recorder:
            rec=self.recorder; self.recorder=None
            try:
                rec.close(error)
                self.events.put(('Recording stopped: ' if error is None else error+'; saved partial recording: ')+str(rec.path))
            except Exception as e: self.events.put('Could not finish recording: '+str(e)+'. Files remain in '+str(rec.path))

    def toggle_record(self):
        with self.lock:
            if self.recorder: self.stop_record(); return
            if self.ffc_busy:return
            if self.baseline.active:
                messagebox.showinfo('Baseline in progress','Wait for the baseline capture to finish first.'); return
            if not self.latest or time.monotonic()-self.received_at>2:
                messagebox.showinfo('No live data','Wait for live camera frames before starting recording.'); return
            try:
                self.recorder=Recorder(self.output,self.baseline.value,self.baseline.metadata,self.args.demo)
                self.events.put('Recording to '+str(self.recorder.path))
            except Exception as e: messagebox.showerror('Cannot record',str(e))

    def capture_baseline(self):
        with self.lock:
            if self.recorder or self.ffc_busy: return
            if not self.latest or time.monotonic()-self.received_at>2:
                messagebox.showinfo('No live data','Wait for camera frames before capturing a baseline.'); return
            self.baseline.start()
            self.events.put('Capturing 30 frames. Keep the camera and reference still; avoid FFC during capture.')

    def start_ffc(self):
        with self.lock:
            if self.ffc_busy or self.recorder or self.baseline.active:return
            if not self.latest or time.monotonic()-self.received_at>2:return
            self.ffc_busy=True
            # Even an uncertain command outcome can have changed calibration.
            self.baseline.cancel(); self.baseline.value=None; self.baseline.metadata=None
            self.latest=None; self.received_at=0; self.previous_mono=None
        self.difference.set(False)
        self.redraw()
        self.stat_text.set('FFC in progress…')
        self.delta_text.set('Baseline cleared.\nCapture a new one after FFC.')
        self.canvas.create_text(320,240,text='Performing FFC…',fill='white',font=('Arial',20,'bold'),tags='ffc')
        self.events.put('Performing internal-shutter FFC. Leave the lens uncovered.')
        self.ffc_thread=threading.Thread(target=self.ffc_worker,daemon=True)
        self.ffc_thread.start()

    def ffc_worker(self):
        try:
            if self.args.demo:time.sleep(.3)
            else:perform_ffc(getattr(self.args,'i2c_device','/dev/i2c-1'))
            # Keep draining frames briefly after completion, then reject a few
            # more to avoid carrying a partially acquired shutter frame forward.
            time.sleep(.5)
            message=('Demo FFC complete' if self.args.demo else 'Camera confirmed FFC complete')+'. Wait for live video, then capture a new baseline.'
        except PermissionError:
            message='FFC failed: I2C permission denied. Add your Pi account to the i2c group, then log out and back in. Baseline cleared.'
        except Exception as e:
            message='FFC was not confirmed: '+str(e)+'. Baseline cleared; retry after resolving the error.'
        with self.lock:
            self.skip_frames=3
            self.ffc_busy=False
            self.events.put(message)

    def clear_baseline(self):
        with self.lock:
            if self.recorder:return
            self.baseline.cancel(); self.baseline.value=None; self.baseline.metadata=None
        self.difference.set(False); self.redraw()

    def select_folder(self):
        if self.recorder:return
        folder=filedialog.askdirectory(initialdir=self.output)
        if folder:
            with self.lock:self.output=Path(folder); self.folder_text.set(folder)

    def full_roi(self):
        with self.lock:self.roi=(0,0,WIDTH,HEIGHT)
        self.redraw()

    def pixel(self,event):return (max(0,min(WIDTH-1,event.x//4)),max(0,min(HEIGHT-1,event.y//4)))
    def drag_begin(self,event):
        self.drag_start=self.pixel(event); self.drag_move(event)
    def drag_move(self,event):
        if self.drag_start is None:return
        with self.lock:self.roi=roi_bounds(self.drag_start,self.pixel(event))
        self.redraw()
    def drag_end(self,event):self.drag_move(event); self.drag_start=None

    def redraw(self):
        self.last_drawn=None

    def change_contrast(self):
        with self.lock:
            self.fixed_limits=None if self.auto_contrast.get() or self.latest is None else display_limits(self.latest[0])
        self.redraw()

    def tick(self):
        if self.closing:return
        with self.lock:
            latest=self.latest
            age=time.monotonic()-self.received_at
            if self.baseline.active and time.monotonic()-self.baseline.started>15:
                self.baseline.cancel(); self.events.put('Baseline cancelled: not enough frames. Previous baseline retained.')
            if self.recorder and age>5:self.stop_record('Recording stopped because the camera stalled')
            recording=self.recorder is not None
            count=self.recorder.count if recording else 0
            roi=self.roi; base=self.baseline.value
            collecting=self.baseline.active
            correcting=self.ffc_busy
            progress=self.baseline.count
        while not self.events.empty():
            try:self.status.set(self.events.get_nowait())
            except queue.Empty:break
        self.record_button.configure(text=f'■ Stop recording ({count} frames)' if recording else '● Start recording',state='normal' if recording or (latest and age<2 and not collecting and not correcting) else 'disabled')
        self.capture_button.configure(state='disabled' if recording or collecting or correcting or not latest or age>2 else 'normal')
        self.ffc_button.configure(text='FFC in progress…' if correcting else 'Perform FFC',state='disabled' if recording or collecting or correcting or not latest or age>2 else 'normal')
        self.clear_button.configure(state='disabled' if recording else 'normal')
        self.folder_button.configure(state='disabled' if recording or collecting else 'normal')
        if collecting:self.baseline_text.set(f'Capturing baseline: {progress}/30 frames')
        elif base is not None:self.baseline_text.set('Baseline ready · average of 30 frames · recapture after FFC, camera movement, or settings changes')
        else:self.baseline_text.set('No baseline captured')
        if not latest:
            self.stat_text.set('FFC in progress…' if correcting else 'Waiting for live frames…')
            if not correcting:self.canvas.itemconfigure('ffc',text='Waiting for live video…')
        if latest:
            frame,seq,mono,utc=latest
            x0,y0,x1,y1=roi
            self.roi_text.set(f'({x0}, {y0}) to ({x1-1}, {y1-1})\n{x1-x0} × {y1-y0} = {(x1-x0)*(y1-y0):,} pixels')
            s=stats(frame,roi,base)
            freshness='STALE — no new frames' if age>2 else f'{self.fps:.1f} received frames/s'
            self.stat_text.set(f'Mean     {s["mean"]:,.2f}\nMinimum  {s["minimum"]:,.0f}\nMaximum  {s["maximum"]:,.0f}\nStd dev  {s["std"]:,.2f}\n\nRaw counts\n{freshness}')
            self.delta_text.set('CHANGE FROM BASELINE\n\n'+f'Mean  {s["delta_mean"]:+.2f}\nMin   {s["delta_min"]:+.2f}\nMax   {s["delta_max"]:+.2f}\nRaw counts' if base is not None else 'Capture a baseline\nto measure changes.')
            try:span=max(1,int(self.span.get()))
            except (ValueError,tk.TclError):span=500
            if not self.auto_contrast.get() and self.fixed_limits is None:
                self.fixed_limits=display_limits(frame)
            limits=None if self.auto_contrast.get() else self.fixed_limits
            key=(seq,roi,id(base),self.difference.get(),span,self.palette.get(),limits)
            if key!=self.last_drawn:
                rgb,label=colour_image(frame,base if self.difference.get() else None,span,self.palette.get(),limits)
                self.photo=ImageTk.PhotoImage(Image.fromarray(rgb).resize((640,480),Image.Resampling.NEAREST))
                self.canvas.delete('all'); self.canvas.create_image(0,0,image=self.photo,anchor='nw')
                self.canvas.create_rectangle(x0*4,y0*4,x1*4-1,y1*4-1,outline='#51f8ed',width=2)
                self.scale_text.set(label)
                self.last_drawn=key
        self.root.after(80,self.tick)

    def close(self):
        self.closing=True
        self.process.terminate()
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:self.process.kill(); self.process.wait()
        self.reader.join(timeout=3)
        if self.ffc_thread:self.ffc_thread.join(timeout=1)
        with self.lock:self.stop_record()
        self.root.destroy()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo',action='store_true',help='Use simulated raw data; no camera access')
    parser.add_argument('--device',default='/dev/spidev0.0')
    parser.add_argument('--speed',type=int,default=20000000)
    parser.add_argument('--i2c-device',default='/dev/i2c-1',help='Lepton control interface for FFC')
    parser.add_argument('--output',default='~/LeptonRecordings')
    args=parser.parse_args()
    root=tk.Tk()
    try:Viewer(root,args)
    except Exception as e:messagebox.showerror('Cannot start Lepton Lab',str(e)); root.destroy(); return
    root.mainloop()

if __name__=='__main__':main()
