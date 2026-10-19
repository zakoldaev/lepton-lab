# Third-party notices and source references

## Scope of the project licence

[LICENSE](LICENSE) applies to original Lepton Lab contributions to the extent the
contributors hold rights in them. Third-party material retains its own notices
and terms; the project licence does not replace them.

## GroupGets / Pure Engineering palettes

- Material: ironblack and grayscale lookup tables in `palettes.json`.
- Source: [Palettes.cpp](https://github.com/groupgets/LeptonModule/blob/907520ba463b3056b5b5224ef33fac5080c7f5ee/software/raspberrypi_video/Palettes.cpp).
- Copyright: 2014, Pure Engineering LLC.
- Licence: BSD-2-Clause; full text in [GROUPGETS-LICENSE.txt](GROUPGETS-LICENSE.txt).
- Transformation: RGB lookup tables stored as JSON and loaded by Python.
- The GroupGets SPI viewer also served as an interface and display reference.

## FLIR SDK references for FFC

`ffc.py` implements a small subset of the Lepton CCI protocol in Python.
Its command IDs, register layout, word lengths and transaction sequence reference
`LEPTON_SYS`, `LEPTON_I2C_Protocol`, `LEPTON_I2C_Reg` and `raspi_I2C`
in the FLIR SDK distributed with GroupGets LeptonModule.

The Python implementation uses its own classes, exceptions, deadlines and
shutter-state checks; it does not bundle or link the full SDK. Code comparison
alone cannot establish the complete authorship history or legal derivative status.
To preserve attribution for any adapted material, the referenced upstream
copyright, redistribution, disclaimer, non-endorsement and other header text is
included verbatim in [FLIR-SDK-NOTICES.txt](FLIR-SDK-NOTICES.txt).

Those file-specific terms differ from the GroupGets root licence. In particular,
the FLIR notices include a non-endorsement condition. Do not describe this project
as approved, sponsored or certified by FLIR, Indigo Systems or GroupGets.

## Separately installed dependencies

The installer obtains the compiler, Python, NumPy, Pillow and Tkinter from the
operating system's package repositories. Their implementations are not vendored
in this source repository and retain their respective licences. If distributing
a bundled executable, container or complete operating-system image, review the
licence and notice requirements of the exact included packages separately.

## Redistribution

- Keep `LICENSE`, `GROUPGETS-LICENSE.txt`, `FLIR-SDK-NOTICES.txt` and this file
  in source distributions.
- Include the relevant third-party notices and disclaimers in documentation or
  accompanying materials for binary distributions.
- Preserve notices when modifying attributed material.
- Use FLIR and GroupGets names only to identify compatibility or acknowledge
  sources, without implying endorsement.

This records the source-level review performed on 19 October 2026. It is a
provenance record and notice-preservation measure, not a legal certification.
