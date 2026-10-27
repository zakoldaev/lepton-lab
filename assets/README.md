# Wiring illustration

`lepton-pi-wiring.svg` is an original vector illustration created for Lepton Lab on 27 October 2026, covered by the repository's [BSD-2-Clause licence](../LICENSE).

It shows the connections required by Lepton Lab with the FLIR Lepton Breakout Board v2.0 (250-0577-00), using J3 power and CE0. It is a connector schematic, not a scale drawing of either board. Pi pin numbers are physical header positions.

## Technical sources

- [FLIR Raspberry Pi guide](https://github.com/FLIR/Lepton/blob/main/docs/RaspberryPiGuide.md): J2 signal assignments, J3 power and square-pad identification.
- FLIR, *Lepton Camera Breakout Board v2.0*, part 250-0577-00, January 2021 datasheet, page 2: pin assignments, input voltage and R120 power-input note.
- [Raspberry Pi hardware documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio): physical header positions and GPIO functions.

The supplied photographs and online Raspberry Pi illustration were used as reference material only; their pixels, board artwork and logos are not included. These links credit technical sources, not a licence grant for third-party images.

Unlike FLIR's example software, Lepton Lab does not require VSYNC. MOSI is also unused by its receive-only video capture. See [WIRING.md](../WIRING.md) for the full explanation and CE1 alternative.
