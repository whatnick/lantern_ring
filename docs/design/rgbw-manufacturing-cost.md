# RGBW PCB manufacturing cost: preliminary estimate

**Historical estimate for the obsolete Cree-LED revision, not the current
QBLP679 redesign.** Requote both board variants before ordering.

For the redesign, [DigiKey listed QBLP679-RGBCW active](https://www.digikey.com/en/products/detail/qt-brightek-qtb/QBLP679-RGBCW/13278847)
on 22 November 2026 at $0.79 each in cut tape (five LEDs: $3.95 before
shipping). [JLCPCB C6629825](https://jlcpcb.com/partdetail/C6629825) reported
zero stock at that time. Customer-supplied-part feasibility, minimum quantities,
handling and any additional placement or inspection charges need an actual
quote. This snapshot is not a reservation or a complete redesign estimate.

**22 November 2026; USD; not a supplier quote.** This estimate is for five
assembled examples of **one** RGBW variant, not five of each. It excludes the
ring body, CR2032, pogo contacts, programming clip, firmware and testing.

## Important sourcing blocker

The specified Cree LED `CLQ6A-TKW-S1L1R1H1QBB7935BB3` is listed as
[obsolete by DigiKey](https://www.digikey.com/en/products/detail/cree-led/CLQ6A-TKW-S1L1R1H1QBB7935BB3/10658542)
and [Mouser](https://www.mouser.com/ProductDetail/Cree-LED/CLQ6A-TKW-S1L1R1H1QBB7935BB3?qs=Cb2nCFKsA8q1xuLCsMeFaw%3D%3D).
The checked Mouser listing has no available stock or price. The exact LED and
the QFN MCU were not found in the in-stock JLCPCB catalog snapshot. Do not
assume an available LED, an equivalent footprint or that JLCPCB will accept
customer-supplied parts. The later QBLP679 revision uses a different footprint
and pinout; its availability and revised BOM require a new assembly quote.

## Partial five-board example

The following is a **conditional partial subtotal, not a finished-board price**.
It assumes one standard 4-layer 1.6 mm design, single-sided Economic PCBA,
and all seven catalog-listed resistor, capacitor and MOSFET part types treated
as extended feeders. It assumes five of each component without assembly
wastage, minimum purchase quantities or shipping. Actual feasibility of
customer-supplied MCU/LED and Economic PCBA has not been confirmed.

| Item | Four single MOSFETs | Two dual MOSFETs |
| --- | ---: | ---: |
| Five known component sets, excluding LED | $8.23 | $7.70 |
| Economic setup and stencil | $9.71 | $9.71 |
| Seven extended feeder fees, if applicable | $21.49 | $21.49 |
| Approx. 73 solder joints per board at $0.0016 | $0.58 | $0.58 |
| Five QFN X-rays at $1.64 each, if charged | $8.20 | $8.20 |
| **Partial subtotal, before exclusions below** | **$48.21** | **$47.68** |

Known component values per board are $1.23 for the exact MCU at Mouser's
one-piece tier, approximately $0.058 for 14 resistors and two capacitors, and
$0.359 for four `DMG1012T-7` or $0.251 for two `NTZD3154NT1G` devices.
The eight non-LED component types were found in JLCPCB's 21 November 2026
catalog snapshot except the MCU, which is priced from Mouser. The snapshot
is not a live reservation; prices, feeder classification, stock, packaging,
required overage and MOQ may change. The small $0.53 five-board subtotal
difference is **not** evidence that the dual option will be cheaper to build.

| Exact part | Quantity per board | Snapshot unit price | Source |
| --- | ---: | ---: | --- |
| ATTINY85-20MU | 1 | $1.23 | [Mouser](https://www.mouser.com/ProductDetail/Microchip-Technology/ATTINY85-20MU) |
| RC0402FR-072K2L | 4 | $0.0014 | [C114762](https://jlcpcb.com/partdetail/C114762) |
| RC0402FR-071KL | 4 | $0.0012 | [C106235](https://jlcpcb.com/partdetail/C106235) |
| RC0402FR-07100KL | 5 | $0.0019 | [C60491](https://jlcpcb.com/partdetail/C60491) |
| RC0402FR-0710KL | 1 | $0.0014 | [C60490](https://jlcpcb.com/partdetail/C60490) |
| GRM155R71A104KA01D | 1 | $0.0117 | [C71687](https://jlcpcb.com/partdetail/C71687) |
| CL21A106KPFNNNE | 1 | $0.0251 | [C17024](https://jlcpcb.com/partdetail/C17024) |
| DMG1012T-7, single option | 4 | $0.0897 | [C20512](https://jlcpcb.com/partdetail/C20512) |
| NTZD3154NT1G, dual option | 2 | $0.1255 | [C145189](https://jlcpcb.com/partdetail/C145189) |

The subtotal **does not include** the bare boards, LED, procurement or
consignment fees for unavailable parts, any additional feeder or X-ray fees,
panel/fixture costs, shipping, taxes, duties, yield loss or assembly rework.
QFN via-in-pad fill/cap and stencil requirements may add material cost; confirm
them with the assembler. [JLCPCB advertises](https://jlcpcb.com/ads/pcb-manufacturer-comparison)
promotional bare PCB prices starting at $2 for five 1-4-layer boards, but that
is not a quote for this outline, surface finish, contact requirements or
via-in-pad treatment.

The [JLCPCB fee schedule](https://jlcpcb.com/help/article/pcb-assembly-price)
lists Economic setup $8.18, stencil $1.53, extended feeder $3.07/type,
SMT $0.0016/joint and X-ray $1.64/component for 1-10 pieces. It also lists
different Standard PCBA, fixture and handling charges. The board may require
Standard service or panelization; request an actual quote after sourcing the LED.
[JLCPCB's prototype overview](https://jlcpcb.com/solutions/pcb-prototype-assembly)
describes the service constraints.

The [two-layout comparison](rgbw-mosfet-comparison.md) covers placement,
routing and the unqualified physical/electrical risks. Neither PCB is
fabrication-release-ready merely because the digital ERC/DRC reports pass.
