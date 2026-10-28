# Attribution and included libraries

- Original I–V tester concept, code and hardware: **Marc Dusseiller / dusjagr**, [dusjagr/IVcurve_tester](https://github.com/dusjagr/IVcurve_tester). The MIT copyright notice is retained verbatim in [LICENSE](LICENSE).
- This repository is maintained by **Shih-Wei Chieh / weiweiweiopen**. Its basic USB carrier is a derivative implementation, with LOLIN S3 Mini, ADG706, ADS1115 and Adafruit 4814 pin/display adaptations; it is not presented as an unchanged upstream PCB.
- The charging / energy-harvesting derivative hardware design was completed by **Sol 6.1**, as credited by the project maintainer. This credit concerns the design work; hardware validation status is documented separately.
- Standard footprint/model references use KiCad 10 libraries: [KiCad library license and exception](https://www.kicad.org/libraries/license/). The locally included Omron G6K-2F-Y STEP is from that library; the source project's missing local model reference has been supplied without changing PCB bytes.
- Project-local LOLIN S3 Mini and Adafruit 4814 VRML models are detailed visual reconstructions. The charging board's laid-down PHB model is provisional. These models are not manufacturer-qualified stack-height or tolerance evidence.
- Basic firmware includes Adafruit ADS1X15 2.6.2, BusIO 1.17.4, GFX 1.12.6 and EPD 4.6.13 sources. Their license notices remain in each library. The EPD driver has a local bounded-wait patch, included as `firmware/basic/epd-4.6.13-local.patch`; source origins are recorded in `library-sources.json`.
