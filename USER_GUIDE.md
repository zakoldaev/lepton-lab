# Using Lepton Lab

For wiring and setup, see [WIRING.md](WIRING.md) and [INSTALL.md](INSTALL.md). These instructions apply to Raspberry Pi 4 Model B and Pi 5.

## Controls

**Perform FFC:** leave the lens uncovered and click this button before capturing a baseline. Lepton Lab commands the Lepton's internal-shutter correction over I2C, waits for the camera's completion status, then discards a few frames before resuming analysis. The previous baseline is cleared, including after an uncertain outcome. Capture a new baseline when video resumes. FFC is disabled while recording or averaging a baseline. Existing automatic/manual FFC mode and timing settings are preserved. External FFC mode or a shutter temperature lockout produces an error instead of issuing the correction. The app does not automatically switch modes.

1. **Select an area:** drag on the image. A click selects one pixel. The right panel shows the mean, minimum, maximum, and standard deviation. `Select whole image` resets the area. Area changes are logged per recorded frame.
2. **Capture baseline:** keep the camera and reference scene stationary for 30 incoming frames (normally about 3–4 seconds). The app averages each pixel, saves the baseline, and shows progress. This is reference subtraction, not FLIR FFC; the app does not move the shutter or alter calibration. A timeout retains the previous baseline.
3. **Show baseline difference:** see the current raw frame minus the averaged baseline. Blue is below the reference, white unchanged, red above it. The difference colour range stays fixed until you change it. Statistics use the original numbers even when display colours saturate.
4. **Start recording:** save all complete frames delivered to this app, plus timestamped measurements. Baseline changes are disabled during recording so a session has one reference. ROI selection remains available. Stop recording before choosing a new baseline or destination folder.
5. **Stop recording:** closes and flushes the files. Closing the viewer also stops recording. Camera failure or a five-second stall stops the recording and marks it incomplete rather than pretending it continued.

The live image defaults to **GroupGets ironblack**, using the exact RGB palette from the original GroupGets viewer, and **Auto contrast**. The range is recalculated from each frame's nonzero minimum and maximum. Adding a hot object can therefore change the background colour even if its raw values stay constant. Clear `Auto contrast` to hold the current range. You can also choose grayscale or the earlier Lepton Lab heat palette. These controls change only the display; raw recordings and measurements are unaffected. The baseline difference view retains its independent fixed blue/white/red scale.

## Units and FFC

Measurements are deliberately labelled **raw counts**. The app does not read or change AGC, radiometry, gain, TLinear resolution, or telemetry configuration. Do not label these values degrees Celsius without first verifying all relevant camera settings. FLIR radiometric/TLinear output can be converted later when its scale and mode are known; a colour screenshot cannot supply those settings.

Your camera's existing automatic shutter/FFC behaviour continues. FFC, gain changes, scene movement, and camera temperature drift can change the reference comparison. **Recapture the baseline after a known FFC or settings change.** This version does not log automatic FFC events. Avoid an FFC during the 30-frame baseline capture. It averages received frames, which can include a frozen frame during a shutter event.

The FFC button uses `/dev/i2c-1`, address `0x2a`. A different bus can be selected with `bash start.sh --i2c-device /dev/i2c-N`. Do not run another Lepton control program concurrently. For permission errors, see [INSTALL.md](INSTALL.md).

For a change experiment, take a baseline of the actual initial scene. If you cover the lens, the baseline will instead describe the cover, so uncovering it will produce a difference across the new scene. A uniform cover is not an absolute temperature calibration.

## Recording format

Default destination: `~/LeptonRecordings/DATE-TIME-UNIQUEID/`.

- `frames.raw`: original received pixel values, unsigned 16-bit **little-endian**, row-major, 160 columns × 120 rows, 38,400 bytes per frame. No subtraction, colour mapping, normalization, or lossy compression. Packet headers are removed.
- `frames.csv`: one row per saved frame; UTC nanoseconds and monotonic nanoseconds at complete frame assembly on the Pi, capture sequence, ROI coordinates, mean/min/max/std, and baseline differences when available. Timestamps are host receipt times, not sensor exposure timestamps. `x1`/`y1` are exclusive; origin is top-left.
- `baseline.npy`: the exact float32 full-frame baseline used for that session, if one was captured.
- `metadata.json`: dimensions, units, format, source (camera or simulation), baseline details, completion status, and saved frame count.

Standalone baselines are also saved in the recording root as `.npy` and `.json`. Recording sessions copy the baseline so later baseline changes cannot change their interpretation.

Raw frames consume roughly 1.2 GB/hour at 8.6 delivered frames/s, plus measurement logs. Keep sufficient storage available. Recording is synchronous to avoid a hidden unbounded memory queue; slow storage can delay capture. This does not guarantee every sensor frame, and capture sequence numbers count delivered complete frames, not missing sensor frames.

## Read data on the Pi or Mac

`frames.csv` can be opened in Excel. For full frames, use Python with NumPy:

```bash
python3 read_recording.py ~/LeptonRecordings/YOUR-SESSION
python3 read_recording.py ~/LeptonRecordings/YOUR-SESSION --frame 0 --export-csv first-frame.csv
```

Or in Python, from this folder:

```python
from read_recording import load_session
import numpy as np

metadata, frames, index = load_session('/path/to/session')
first_frame = frames[0]  # shape (120, 160), raw uint16
baseline = np.load('/path/to/session/baseline.npy')
change = first_frame.astype(np.float32) - baseline
```

`load_session` uses memory mapping rather than loading a whole recording into RAM. It ignores incomplete trailing frames after an interrupted write. Only completed frame/index pairs should be analysed after an unexpected power loss. `metadata.json` is finalized when recording stops.

## Capture limitations

The capture bridge uses SPI mode 3 at 20 MHz and requires Lepton 3.x 160 × 120 raw video with telemetry disabled. It accepts only ordered packets and segments 1–4, but does not check packet CRC. It never sends an I²C reboot or calibration command while recovering SPI synchronisation.

See [INSTALL.md](INSTALL.md#troubleshooting) for missing frames, interface permissions and desktop display problems.

## Validation and references

Hardware-free tests cover packet order, missing segments, pixel placement, endianness, truncated streams, baseline averaging, negative differences, ROI boundaries, lossless storage, and interrupted recordings. Demo mode exercises the same binary frame bridge and analysis pipeline without SPI. Live video on the author's Pi 4 Model B was confirmed on 27 October 2026. Hardware-free tests do not validate physical FFC operation or temperature accuracy.

- FLIR interfaces: https://oem.flir.com/learn/thermal-integration-made-easy/spi-and-i2c-with-lepton/
- FLIR radiometry: https://oem.flir.com/learn/thermal-integration-made-easy/radiometry-with-lepton/
- Reference viewer: https://github.com/groupgets/LeptonModule/tree/master/software/raspberrypi_video

No internet service is used by the viewer. Data stays in the folder you choose.

## Palette attribution

`palettes.json` contains the ironblack and grayscale lookup tables from GroupGets' `LeptonModule/software/raspberrypi_video/Palettes.cpp`. Copyright (c) 2014, Pure Engineering LLC. The redistribution notice and disclaimer are included in `GROUPGETS-LICENSE.txt`. Lepton Lab is not an official GroupGets or FLIR product.

## Licensing

Original contributions are covered by [LICENSE](LICENSE). Palette attribution is
preserved in [GROUPGETS-LICENSE.txt](GROUPGETS-LICENSE.txt). See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for FFC source references,
[FLIR-SDK-NOTICES.txt](FLIR-SDK-NOTICES.txt) for their retained notices, and
requirements when redistributing source or binaries.
