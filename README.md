# Lepton Lab

Start here: [Step-by-step installation and how to run it afterwards](INSTALL.md).

A Raspberry Pi desktop application for viewing, recording and comparing thermal-camera data from a FLIR Lepton 3.5.

This project turns the camera into a small monitoring and measurement tool: watch a live thermal image, select an area, record its signal, and compare changes against an averaged reference scene. It is useful for exploring how hot or cold regions change over time.

## What it does

- Displays a live 160 × 120 image with ironblack, grayscale or heat colours.
- Offers automatic contrast or a fixed display range.
- Measures mean, minimum, maximum and standard deviation in a selected area or single pixel.
- Averages 30 frames to capture a reference baseline and displays changes relative to it.
- Performs an internal-shutter flat-field correction (FFC) on request.
- Records original pixel values, timestamps, area measurements and session metadata.
- Includes a simulated-camera mode for trying the interface without hardware.

Measurements are currently **raw counts, not degrees Celsius**. Colours are a display aid; changing the palette or contrast does not change saved measurements. Temperature conversion requires verification of the camera's radiometry and TLinear settings.

## Hardware and software

The intended setup is:

| Component | Requirement |
| --- | --- |
| Camera | FLIR Lepton 3.5, 160 × 120 |
| Interface board | Lepton Breakout Board v2.0 |
| Computer | Raspberry Pi 5 with Raspberry Pi OS and a desktop session |
| Camera connection | SPI for images; I²C for the FFC control button |
| Software | Python 3, NumPy, Pillow, Tkinter and a C++17 compiler; installed by `install.sh` |

The viewer runs on the Pi desktop, including through Raspberry Pi Connect. It is not a browser application or Arduino/ESP32 firmware. Other Linux systems need suitable SPI/I²C hardware and have not been validated here. Saved recordings can be analysed separately on a Mac or another computer with Python and NumPy.

Use your existing working camera wiring. SPI and I²C must be enabled, and telemetry must be disabled for this capture implementation. Default interfaces are `/dev/spidev0.0` and `/dev/i2c-1` (camera address `0x2a`). This repository does not yet include a verified wiring walkthrough; do not infer pin connections from the software defaults.

## Install for the first time

### Download from GitHub

While signed in to an account with access to this private repository, select **Code → Download ZIP**. Transfer the ZIP to the Raspberry Pi and extract it. The extracted directory is usually `lepton-lab-main`.

Open a terminal in that directory on the Pi desktop and run:

```bash
bash install.sh
bash start.sh
```

The installer installs dependencies, builds the capture program and runs hardware-free checks. Close any other Lepton viewer before starting: only one program should read the camera at a time.

### Or use Git

If Git is installed and GitHub authentication for this private repository is already configured on your Pi:

```bash
cd ~
git clone https://github.com/zakoldaev/lepton-lab.git lepton-lab-github
cd ~/lepton-lab-github
bash install.sh
bash start.sh
```

The separate folder keeps an existing `~/lepton-lab` installation intact. A private repository requires authenticated access; a GitHub account password alone does not work for HTTPS Git authentication.

## Already using the original archive?

If you previously extracted `lepton-lab-colours.tar.gz` into your home directory, keep starting that installation with:

```bash
cd ~/lepton-lab
bash start.sh
```

You do not need to extract it again. Importing this code into GitHub does not update the files already on your Pi.

## First recording

1. Start the viewer from a terminal inside the Pi desktop. Check that the image updates.
2. Choose a colour palette. Auto contrast helps you see detail; turn it off to keep a fixed colour range when comparing a scene over time.
3. Drag over the image to select an area, or click to select one pixel. The measurement panel updates automatically.
4. For a reference comparison, keep the camera and scene stationary. If needed, click **Perform FFC**, wait for video to resume, then click **Capture baseline**. It averages the next 30 received frames.
5. Select **Show baseline difference** to see decreases in blue and increases in red relative to the reference. This is a signal difference, not a temperature difference in °C.
6. Choose the recording destination and click **Start recording**. Stop recording before changing the baseline or destination.
7. Click **Stop recording** before shutting down. Each session is stored in its own folder.

Recapture the baseline after FFC, camera movement or camera-setting changes. Baseline subtraction and FFC are different operations: the first compares scenes; the second corrects the camera using its internal shutter.

## Try without a camera

After installation, from the project directory:

```bash
bash start.sh --demo
```

Demo mode uses simulated data. It lets you try the controls and recording workflow but does not test camera wiring or physical FFC.

## Where recordings go

The default location is `~/LeptonRecordings/`, with a separate timestamped folder for every recording.

| File | Contents |
| --- | --- |
| `frames.raw` | Original 160 × 120 pixel frames, unsigned 16-bit little-endian |
| `frames.csv` | Host timestamps, selected area and per-frame statistics |
| `baseline.npy` | Reference image, when a baseline was captured |
| `metadata.json` | Format, source, frame count and completion status |

Full-rate raw recording uses approximately 1.2 GB per hour at 8.6 delivered frames/s. This version records every complete frame delivered to the app; it does not offer scheduled or interval recording.

Open `frames.csv` in a spreadsheet, or inspect full images using the included reader:

```bash
python3 read_recording.py ~/LeptonRecordings/YOUR-SESSION
python3 read_recording.py ~/LeptonRecordings/YOUR-SESSION --frame 0 --export-csv first-frame.csv
```

Replace `YOUR-SESSION` with the actual folder name. See [the detailed user guide](USER_GUIDE.md#recording-format) for the exact format and Python examples.

## Updates

For the separate Git checkout above, stop the viewer and run:

```bash
cd ~/lepton-lab-github
git pull --ff-only
bash install.sh
bash start.sh
```

If Git reports local changes or conflicts, preserve those edits before updating. A ZIP/archive installation is not a Git checkout; download a new ZIP into a separate folder instead.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Window does not open over SSH | Use a terminal inside the Pi desktop or Raspberry Pi Connect desktop session. |
| No live frames | Close other camera programs; confirm the original viewer still works and check SPI/CS wiring. |
| Camera uses CE1 | Run `bash start.sh --device /dev/spidev0.1`. |
| SPI or I²C permission denied | Check device permissions and group membership; see the detailed guide. Do not run the GUI as root. |
| Background colours change when a hot object enters | Auto contrast rescales the display. Turn it off to keep the range fixed. |
| Reference comparison suddenly shifts | FFC, camera movement or drift may have changed the reference. Capture a fresh baseline. |

For FFC behaviour, storage limitations and advanced options, read [USER_GUIDE.md](USER_GUIDE.md).

## Project status

This repository starts from the uploaded `lepton-lab-colours.tar.gz` package. The camera application code is unchanged in this import; the README and repository housekeeping were added for clarity. This identifies the imported snapshot, not a claim that every earlier local edit is included.

This is an experimental personal project, not a validated temperature-measurement instrument. The included tests use synthetic data and simulated I²C responses. Physical camera timing and shutter operation need checking on the actual Pi. Automatic FFC events are not logged, and capturing every sensor frame is not guaranteed.

## Files and attribution

| File | Role |
| --- | --- |
| `capture.cpp` | Linux SPI acquisition and binary frame output |
| `viewer.py` | Desktop interface and controls |
| `core.py` | Analysis, baseline, colour mapping and recording |
| `ffc.py` | I²C internal-shutter FFC control |
| `read_recording.py` | Recorded-data reader and export |
| `palettes.json` | Colour lookup tables |
| `tests/` | Hardware-free checks and GUI smoke test |

The ironblack and grayscale palettes come from GroupGets / Pure Engineering LLC. Their notice is preserved in [GROUPGETS-LICENSE.txt](GROUPGETS-LICENSE.txt); it applies to the attributed third-party material. No additional project-wide open-source licence is granted by this import. Lepton Lab is not an official FLIR or GroupGets product.
