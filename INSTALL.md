# Install and run

For Raspberry Pi 4 Model B and Raspberry Pi 5 running Raspberry Pi OS Desktop. Use a terminal inside the Pi desktop, locally or through Raspberry Pi Connect. A plain SSH session does not normally provide a graphical display.

## 1. Connect the camera

Follow [WIRING.md](WIRING.md) with the Pi powered off. The same physical header positions apply to both Pi models.

## 2. Enable SPI and I²C

Boot the Pi and run:

```bash
sudo raspi-config
```

Under Interface Options, enable SPI and I2C. Finish, then reboot:

```bash
sudo reboot
```

After logging back in, check:

```bash
ls -l /dev/spidev0* /dev/i2c-1
groups
```

Expect `/dev/spidev0.0`, `/dev/spidev0.1` and `/dev/i2c-1`. Your account should belong to `spi` and `i2c`. If either group is missing:

```bash
sudo usermod -aG spi,i2c "$USER"
sudo reboot
```

The installer does not enable these interfaces or change camera output settings.

## 3. Download and install once

```bash
sudo apt update
sudo apt install -y git
cd ~
git clone https://github.com/zakoldaev/lepton-lab.git lepton-lab-github
cd ~/lepton-lab-github
bash install.sh
```

Wait for `Installation complete`. The script installs dependencies, compiles the capture program and runs hardware-free checks. If installation fails, resolve the terminal error before starting.

Only Git is needed; the GitHub CLI (`gh`) is not required. A public repository can be cloned without signing in. If the repository is made private, authenticated Git access will be required.

If `~/lepton-lab-github` already exists, use your existing installation or the update instructions below; do not clone over it.

## 4. Start the camera

Close other Lepton viewers, then run:

```bash
cd ~/lepton-lab-github
bash start.sh
```

The window should show a changing thermal image. The default chip select is CE0, physical pin 24. If you deliberately wired CS to CE1, physical pin 26, use:

```bash
bash start.sh --device /dev/spidev0.1
```

For a demonstration without hardware:

```bash
bash start.sh --demo
```

## Run again later

After closing the app or restarting the Pi:

```bash
cd ~/lepton-lab-github
bash start.sh
```

Use the CE1 option every time if that is your wiring. No repeat installation is needed. Stop recording and close the application before shutting down.

## Update an existing Git installation

Close the viewer, then:

```bash
cd ~/lepton-lab-github
git pull --ff-only
bash install.sh
bash start.sh
```

If Git reports local changes or conflicts, preserve those edits before updating.

## Alternative: ZIP or older archive

You can use GitHub's Code → Download ZIP, extract it, open a terminal in the extracted folder and run `bash install.sh`, then `bash start.sh`. Use that extracted folder for later launches. ZIP installations cannot use `git pull`; extract a new download into a separate folder.

If you still use the original archive in `~/lepton-lab`, run `cd ~/lepton-lab` followed by `bash start.sh`. That copy is separate from `~/lepton-lab-github`.

## Troubleshooting

### Window opens but no image

1. Close all camera viewers. Check for a leftover capture process with `pgrep -af lepton_capture`.
2. Check that CS matches the selected device: physical pin 24 for `spidev0.0`, or pin 26 for `spidev0.1`.
3. Shut down and disconnect power before checking loose wires, common ground and board power. Check against [the wiring table](WIRING.md). Reconnecting the wiring resolved this symptom on the author's Pi 4.
4. Confirm the device files and group membership using step 2.
5. With the GUI closed, run a 15-second capture diagnostic:

```bash
cd ~/lepton-lab-github
timeout 15s ./lepton_capture /dev/spidev0.0 > /dev/null
```

Substitute `/dev/spidev0.1` for CE1. The command hides binary frame data but leaves errors visible. Timeout exit status 124 is expected. Repeated `No complete frame` messages mean complete frames are not being assembled; they do not identify a single cause or prove camera failure. No messages alone do not prove that frames arrived.

The capture program expects Lepton 3.x 160 × 120 raw video with telemetry disabled. It does not change those settings.

### Other problems

| Symptom | Action |
| --- | --- |
| Permission denied for SPI or I²C | Repeat the group check in step 2 and reboot after changing membership. Do not run the GUI with sudo. |
| No window / display error | Launch from a terminal inside the Pi desktop. |
| No such file or directory | Check the installation folder and whether install.sh completed. |
| FFC fails but the image works | Check SDA, SCL and I²C access; see the user guide. |
| Background colours change | Turn off Auto contrast to hold the display range. |
| Baseline comparison suddenly shifts | Capture a fresh baseline after FFC, movement or camera-setting changes. |

See [USER_GUIDE.md](USER_GUIDE.md) for controls and recording details.

Interface configuration reference: [Raspberry Pi documentation](https://www.raspberrypi.com/documentation/computers/configuration.html).
