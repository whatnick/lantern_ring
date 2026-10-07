# Pogo pin comparison for the v2 battery contacts

The v2 ring uses **two opposing SMT pogo pins** between the CR2032 and the
cassette. The negative pin sits in the Carrier and touches the inset bottom face
of the cell. The positive pin is soldered to the rear VCC pad of the PCB and
touches the top face of the cell. This document compares the current Mill-Max
part with low-cost AliExpress SMT pins and screens their fit in the current
tolerance stack. It is a **screening document, not a qualification**: no pin
listed here has been bought, measured, cycled or fitted.

## Sources

- **Mill-Max 0965-0-15-20-80-14-11-0**: official Mill-Max spring-loaded
  connector catalogue, page 24. The part numbers in
  `hardware/v2.0/ring_3d/parameters.json` match this catalogue.
- **AliExpress "100pcs SMT Pogo Pin Connector 1.8-22mm Test Probe"**:
  [listing 1005011917887337](https://www.aliexpress.com/item/1005011917887337.html).
  - The heights come from the seller's "POGO PIN SMT common sizes" table:
    total length A, plunger B, barrel C, compressed height.
  - The flange and tip diameters come from the seller's drawing of the 2.0 mm pin:
    [image](https://ae-pic-a1.aliexpress-media.com/kf/S9ab0259f409f43fd8efaef80ae22f9f5P.jpg).
  - The seller gives no tolerances, spring force, plating thickness, cycle
    life or current rating. The other sizes in the listing may not share the
    2.0 mm drawing's flange or tip dimensions.

## Dimensions

| Part | Free height | Compressed | Stroke | Barrel Ø | Flange Ø x thickness | Tip Ø | Height tolerance |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Mill-Max 0965 (current) | 2.54 | 1.93 | 0.61 | 1.626 | 1.829 x 0.711 | 1.067 | ±0.1524 (published) |
| AliExpress 1.6 mm | 1.60 | 1.34 | 0.26 | ? | ? | ? | not stated |
| AliExpress 1.8 mm | 1.80 | 1.48 | 0.32 | ? | ? | ? | not stated |
| AliExpress 2.0 mm | 2.00 | 1.60 | 0.40 | 1.5 | 2.0 x 0.3 | 0.9 | not stated |
| AliExpress 2.5 mm | 2.50 | 2.0 or 1.75 | 0.50 or 0.75 | ? | ? | ? | not stated |
| AliExpress 3.0 mm | 3.00 | 2.30 | 0.70 | ? | ? | ? | not stated |

All dimensions are in mm. "?" means the listing does not give the value. The
seller's table shows two compressed heights for the 2.5 mm pin; check which
version you receive.

## Tolerance-stack screen

The current design reserves **±0.05 mm** for the printed stack and **±0.05 mm**
for cell thickness. The working compression must stay inside the stroke after
adding those to the pin's own height tolerance:

`worst = 0.05 + 0.05 + pin tolerance`

The working range is `worst ≤ compression ≤ stroke − worst`. If that range is
empty, a worst-case pin either loses contact or bottoms out on the cell.

| Part | Pin tolerance | Usable compression | Margin | Two-pin height saving vs Mill-Max |
| --- | ---: | --- | ---: | ---: |
| Mill-Max 0965 | ±0.1524 | 0.252–0.357 | 0.105 | baseline |
| AliExpress 1.6 mm | ±0.05 | **none** | — | — |
| AliExpress 1.8 mm | ±0.05 | 0.150–0.170 | 0.020 | +1.19 |
| AliExpress 1.8 mm | ±0.10 | **none** | — | — |
| AliExpress 2.0 mm | ±0.05 | 0.150–0.250 | 0.100 | +0.87 |
| AliExpress 2.0 mm | ±0.10 | **none** | — | — |
| AliExpress 2.5 mm (2.0 compressed) | ±0.10 | 0.200–0.300 | 0.100 | −0.03 |
| AliExpress 2.5 mm (2.0 compressed) | ±0.15 | **none** | — | — |
| **AliExpress 2.5 mm (1.75 compressed)** | ±0.10 | 0.200–0.550 | 0.350 | +0.22 |
| **AliExpress 2.5 mm (1.75 compressed)** | ±0.15 | 0.250–0.500 | 0.250 | +0.22 |
| AliExpress 3.0 mm | ±0.15 | 0.250–0.450 | 0.200 | −0.83 (taller) |

Height saving compares two pins at mid-window compression against the
Mill-Max working height of 2.2352 mm. A positive value lowers the crown.

## Assessment

| Option | Verdict | Reason |
| --- | --- | --- |
| Mill-Max 0965 | **Keep as the reference design** | Published tolerance, force and plating. The current CAD and validator are built around it. |
| AliExpress 2.5 mm, 1.75 mm compressed | **Best low-cost candidate** | Has the most margin: it still has a 0.25 mm working range at ±0.15 mm pin tolerance. Saves about 0.2 mm of height. |
| AliExpress 2.5 mm, 2.0 mm compressed | Marginal | Fails if the pin tolerance is worse than about ±0.10 mm. |
| AliExpress 2.0 mm | Not recommended | Only 0.4 mm of stroke. It works only if the pins are held to ±0.05 mm, which is unlikely for unspecified parts. |
| AliExpress 1.6 / 1.8 mm | Reject | Too little stroke to cover the printed-part and cell tolerances. |
| AliExpress 3.0 mm | Works, but taller | Plenty of margin, but it raises the crown by about 0.8 mm. |

A thinner PCB is the more reliable way to lower the crown.
[OSH Park's 2oz-0.8mm service](https://docs.oshpark.com/services/two-layer-hhdc/)
(0.8 mm ±0.07 mm) would lower it by 0.8 mm without reducing the pin travel. The
generator reads the thickness from `ring_mono.kicad_pcb`.

## CAD changes needed for an AliExpress pin

With the current pocket geometry, `validate_parameters()` rejected every 2.5 mm
variant screened, using 0.3 or 0.5 mm flanges at ±0.10 or ±0.15 mm tolerance.
Adopting one requires:

1. **Measured pin parameters.** Set `pin_initial_height`, `pin_max_stroke`,
   `pin_body_diameter`, `pin_body_length`, `pin_flange_diameter`,
   `pin_flange_thickness`, `pin_tip_diameter` and `pin_height_tolerance` from
   measured samples, not from the listing.
2. **Bores.** Reduce `pin_bore_diameter` from 1.75 mm to about 1.6 mm so a
   1.5 mm barrel does not tilt. Keep `pin_flange_bore_diameter` larger than the
   measured flange, and keep the barrel bore smaller than the flange.
3. **Flange capture.** A 0.3 mm flange is too thin for the current positive pin
   shoulder in the ContactDeck. Raise `deck_floor_top` or redesign the shoulder,
   and keep the 0.6 mm wiring clearance under the PCB support lip.
4. **Compression.** Set `pin_compression` to the middle of the working range,
   about 0.375 mm for the 2.5/1.75 pin. The stack then moves `battery_bottom`
   and `pcb_bottom`. The validator requires the positive flange to sit 0.05 mm
   below the PCB.
5. **Rebuild.** Regenerate the CAD and roadmap renders, update the
   height-dependent tests and checks, and review the same-scale comparison.

## Sample measurement plan

Buy the 2.5 mm size, plus the 2.0 mm size if you are curious. Measure at least
10 pins of each with a micrometer or calibrated height gauge:

- Free height A, compressed (bottomed) height and barrel length C.
- Flange diameter and thickness; barrel and tip diameters.
- Force at the planned working compression and at full stroke, measured with a
  gram gauge or scale on a fixture.
- Contact resistance against a CR2032 face before and after 500 compression
  cycles and a short sweat/humidity exposure.
- Plating: check for exposed base metal after cycling. Avoid pins where the tip
  plating wears through.
- Solder: reflow or hand-solder a sample to a rear VCC pad and confirm that the
  plunger still moves freely without wicked solder.

Use the measured maximum deviation as `pin_height_tolerance`. Reject the batch
if the free height or the stroke differs from the seller's table by more than
the assumed tolerance.

## Safety and electrical notes

- The CR2032 rim and top are positive. The negative tip must stay on the inset
  bottom face. The validator checks the tip radius plus the 0.1 mm cell
  tolerance against a 6 mm minimum negative-face radius. Narrow tips are fine.
- Do not compensate for a short pin with shims, solder blobs or conductive
  adhesive under the plunger.
- None of these options is qualified for wear, sweat exposure, drop or battery
  safety. Bench and wear testing are still required before giving rings to
  users.
