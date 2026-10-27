# Connect Lepton to Raspberry Pi 4 Model B or Pi 5

This guide is for a FLIR Lepton 3.5 in the FLIR Lepton Breakout Board v2.0, part 250-0577-00. Other breakout boards can have different connectors.

The connections below use the same physical positions on the 40-pin GPIO header of both Pi models. This camera connects through GPIO, not the Pi's ribbon-camera connector.

## Before connecting

Shut down the Pi and disconnect its power. Identify pin 1 on each connector using the board markings and manufacturer drawing; do not count from an arbitrary corner or a rotated photograph.

- Pi physical pin numbers count header positions 1–40.
- GPIO numbers identify signals and are different from physical positions.
- J2 is the breakout board's 20-pin signal header.
- J3 is its separate power connector; FLIR identifies its square pin as pin 1, ground.
- Leave the breakout board's factory J5–J9 jumpers installed for normal operation.

Use short female-to-female jumper wires where both connectors have male pins.

## Required connections

| Breakout connector and pin | Signal | Pi 4 Model B physical pin | Pi 5 physical pin | Pi GPIO / supply |
| --- | --- | --- | --- | --- |
| J3 pin 1 (square pin) | Ground | 6 | 6 | GND |
| J3 pin 2 | VIN | 2 | 2 | 5 V supply |
| J2 pin 5 | SDA | 3 | 3 | GPIO2 / I²C SDA |
| J2 pin 8 | SCL | 5 | 5 | GPIO3 / I²C SCL |
| J2 pin 12 | SPI_MISO | 21 | 21 | GPIO9 / SPI0 MISO |
| J2 pin 7 | SPI_CLK | 23 | 23 | GPIO11 / SPI0 SCLK |
| J2 pin 10 | SPI_CS | 24 | 24 | GPIO8 / SPI0 CE0 |

The 5 V connection goes only to the breakout board's VIN, which accepts 3–5.5 V. Never connect 5 V to a Pi GPIO signal or the breakout's low-voltage rail pins. Do not power VIN from two sources at once.

This table uses J3 for power following FLIR's guide. The v2.0 datasheet notes that board revision R120 has a reversed D1 diode that prevents powering through J2 pin 2; J3 pin 2 is the documented alternative. A working supply arrangement need not be changed solely to match this table.

## Connections this application does not require

| Breakout pin | Signal | Corresponding Pi physical pin | Use in Lepton Lab |
| --- | --- | --- | --- |
| J2 pin 9 | SPI_MOSI | 19 / GPIO10 | Not required for this receive-only video capture |
| J2 pin 15 | GPIO3 / VSYNC | 11 / GPIO17 | Not used by this capture implementation |

FLIR's own software guide connects VSYNC, but Lepton Lab does not use it. An existing correctly wired connection can remain. Leave other unused breakout pins unconnected; do not remove the factory jumpers.

## Optional CE1 connection

If CS is connected to Pi physical pin 26 (GPIO7 / CE1), use:

```bash
bash start.sh --device /dev/spidev0.1
```

Connect CS to only one chip-select pin. Physical pin 24 uses the default command `bash start.sh`.

## After connecting

1. Check the wiring and connector orientation, then power on the Pi.
2. Follow [INSTALL.md](INSTALL.md) to enable SPI/I²C and install the application.
3. Once the live image works, photograph the wiring for future reference.

Defaults: SPI mode 3 at 20 MHz, `/dev/spidev0.0`; I²C `/dev/i2c-1`, camera address `0x2a`.

## References

- [FLIR Raspberry Pi connection guide](https://github.com/FLIR/Lepton/blob/main/docs/RaspberryPiGuide.md): J2 signal connections and J3 power connector identification. Its GPIO labels are logical GPIO numbers; the table above converts them to physical header positions.
- FLIR, “Lepton Camera Breakout Board v2.0,” part 250-0577-00, January 2021 datasheet, page 2: connector pinout, input-voltage range and R120 diode note.
- [Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio): physical pin numbering and SPI signals.
