#!/usr/bin/env python3
"""Read a Lepton Lab session and optionally export one full raw frame as CSV."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

def load_session(folder):
    folder=Path(folder)
    meta=json.loads((folder/'metadata.json').read_text())
    raw=folder/'frames.raw'
    frame_bytes=meta['width']*meta['height']*2
    available=raw.stat().st_size//frame_bytes
    with (folder/'frames.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    # A process killed mid-write can leave a partial trailing frame/index row.
    valid=[]
    for i,row in enumerate(rows):
        try:
            if int(row['frame_index'])!=i or row['utc_ns'] is None:break
            int(row['utc_ns']); int(row['monotonic_ns']); float(row['mean_raw'])
        except (TypeError,ValueError,KeyError):break
        valid.append(row)
    n=min(available,len(valid))
    if meta['completed']:n=min(n,meta['frame_count'])
    frames=np.memmap(raw,dtype='<u2',mode='r',shape=(n,meta['height'],meta['width'])) if n else np.empty((0,meta['height'],meta['width']),dtype='<u2')
    return meta,frames,valid[:n]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('session')
    p.add_argument('--frame',type=int,default=0)
    p.add_argument('--export-csv',help='New destination file for a full raw frame')
    args=p.parse_args()
    meta,frames,index=load_session(args.session)
    print(f'{len(frames)} frames, shape {frames.shape}, units: {meta["units"]}, source: {meta["source"]}')
    if args.export_csv:
        if not 0<=args.frame<len(frames):p.error('Frame index is outside this recording')
        with open(args.export_csv,'x') as f:np.savetxt(f,frames[args.frame],fmt='%d',delimiter=',')
        print('Saved',args.export_csv)
