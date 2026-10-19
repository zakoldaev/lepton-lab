# Install and run Lepton Lab

These instructions are for Raspberry Pi 5 with Raspberry Pi OS Desktop and an already connected, working Lepton 3.5 camera. Use a terminal inside the Pi desktop, locally or through Raspberry Pi Connect. Plain SSH will usually not display the application window.

## A. Your existing installation

If you already installed the `lepton-lab-colours.tar.gz` archive, you do not need to install it again. Close other camera viewers, open Terminal on the Pi desktop and run:

```bash
cd ~/lepton-lab
bash start.sh
```

This starts your existing copy. It does not download updates from GitHub.

## B. First installation from GitHub — download method

### 1. Download

On the Raspberry Pi, open a browser and sign in to GitHub with an account that can access this private repository:

https://github.com/zakoldaev/lepton-lab

Click **Code → Download ZIP**. Save the ZIP in your **Downloads** folder. The expected filename is `lepton-lab-main.zip`. You can also download it on another computer and copy it to the Pi's Downloads folder.

### 2. Extract into a separate folder

Open Terminal on the Pi desktop and run these commands one line at a time:

```bash
sudo apt update
sudo apt install -y unzip
mkdir -p ~/LeptonGitHub
unzip -n ~/Downloads/lepton-lab-main.zip -d ~/LeptonGitHub
cd ~/LeptonGitHub/lepton-lab-main
```

If the download has a different filename, replace `lepton-lab-main.zip` with that name. This directory keeps the GitHub copy separate from an existing `~/lepton-lab` installation. These are first-install instructions: `unzip -n` deliberately does not overwrite existing files and is not an update command.

### 3. Install once

From that same terminal:

```bash
bash install.sh
```

Internet access is needed to install packages. The script installs Python dependencies and the compiler, builds the camera capture program, and runs hardware-free checks. Wait until you see **Installation complete**. If an error appears, save the terminal output rather than continuing as if installation succeeded.

### 4. Start the camera

Close the old Lepton viewer and any other program using the camera. Then run:

```bash
bash start.sh
```

The application window should open on the Pi desktop.

## C. Run it again later

After restarting the Pi, or after closing the application, open Terminal on the Pi desktop and run:

```bash
cd ~/LeptonGitHub/lepton-lab-main
bash start.sh
```

No repeat download, extraction or installation is needed. Use these commands for the GitHub ZIP copy; use section A for the older archive copy. Do not run both at the same time.

## D. Try the interface without the camera

After completing installation:

```bash
cd ~/LeptonGitHub/lepton-lab-main
bash start.sh --demo
```

This uses simulated data. Close the demo window and run `bash start.sh` without `--demo` to use the real camera.

## E. Finish a session

1. If recording, click **Stop recording**.
2. Close the application window.
3. Recordings remain in `~/LeptonRecordings/`, unless you selected a different destination.

For controls, baseline capture and reading recordings, see [README.md](README.md#first-recording).

## If it does not work

- **No such file or directory:** check that the ZIP was downloaded and that you are using the correct extracted folder name.
- **No window / display error:** open Terminal inside the Pi desktop, not a plain SSH connection.
- **No camera frames:** close other camera viewers and confirm the original camera viewer still works. SPI and I²C must already be enabled; this installer does not configure wiring or camera modes.
- **Permission denied for SPI or I²C:** see [the user guide](USER_GUIDE.md#camera-connection-and-troubleshooting). Do not start the GUI with `sudo`.

For a Git-based installation and subsequent Git updates, see [README.md](README.md#or-use-git). ZIP updates should be extracted to a new folder so that local edits are preserved.
