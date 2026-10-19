#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
sudo apt update
sudo apt install -y g++ python3-numpy python3-pil python3-pil.imagetk python3-tk
g++ -O2 -std=c++17 -Wall -Wextra -pthread capture.cpp -o lepton_capture
./lepton_capture --self-test
python3 -m unittest discover -s tests -v
printf '\nInstallation complete. Close the old camera viewer.\nFrom a terminal inside the Pi desktop, run: bash start.sh\n'
