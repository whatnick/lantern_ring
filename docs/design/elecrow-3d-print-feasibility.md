# Elecrow 3D-print feasibility: Lantern Ring v2

**Assessment: suitable to quote and coupon-test, not yet qualified for a
wearable functional ring.** This covers only the non-PCB parts: RingBase,
Carrier, ContactDeck, Bezel and optional Lantern Corps crown.

## What Elecrow documents

Elecrow's [3D-printing service](https://www.elecrow.com/porder/maker/view3d)
lists photosensitive-resin choices, including a yellow high-toughness resin,
plus transparent and translucent resins. The service information describes the
high-toughness resin as stronger and tougher than its standard 9400 resin and
quotes dimensional precision of **±0.15 mm per 100 mm**. That specification
does not clarify the minimum absolute tolerance on parts this small, orientation
effects, or post-processing variation.

The public material options reviewed for this assessment do **not** establish
that PA12/SLS or MJF is available through this service. Do not submit this
design assuming nylon is selectable. Ask Elecrow for the process and material
datasheet, minimum wall and hole sizes, small-part tolerance, and fatigue/
elongation data for the exact material and finish before placing a functional
order.

## Fit against the current CAD

| Part | Current feature | Preliminary assessment |
| --- | --- | --- |
| RingBase | 1.0 mm open spring arms; 1.0 mm shoulder walls and bayonet lugs; 0.8 mm outer bayonet wall | **Not suitable for repeated wear-flex in an unspecified photopolymer.** The arm is a cyclic spring, not a static shell. Elecrow's listed tougher resin has no published ring-arm fatigue/recovery data in the service information reviewed. |
| Carrier | 0.5 mm battery-well wall; screw pillars 1.5 mm OD with 0.8 mm pilot, leaving 0.35 mm radial material | **High risk.** Thin walls and pilot-hole annuli can chip or split; toughness, drilling and screw retention require an actual coupon. |
| ContactDeck | Thin support floor and PCB pocket with 0.25 mm per-edge PCB clearance | **Fit is unproven.** The clearance is smaller than a conservative two-part tolerance stack if the quoted ±0.15 mm is an absolute per-part error. Have Elecrow confirm the small-part tolerance; print a deck/pocket gauge first. |
| Bezel | 0.6 mm clamp; M1 screw clearances and ground-lead relief | **Fragile as a handling/fastened part.** Confirm minimum wall and hole capability. Expect to finish or enlarge holes only after measuring a sample. |
| Corps crown | 0.4 mm lens, 0.6 mm logo relief and 0.2 mm nominal LED clearance | **Plausible as a visual prototype, not yet a guaranteed optical/mechanical fit.** The service lists translucent resin, but does not establish transmission, diffusion, or accuracy at these feature sizes. |

The model's controlled print-stack allowance is ±0.05 mm; Elecrow's published
precision statement does not confirm that tolerance for these parts. Likewise,
the current carrier/socket radial gap is 0.20 mm and bayonet axial clearance is
0.20 mm. A nominally small printing error, cure shrinkage, or finish build-up
could consume those clearances and jam the cassette. Do not compensate by
forcing the ring together or by assuming a single sample establishes a
production tolerance.

## Recommended first order

1. Request a manual quote for all five non-PCB parts and confirm the exact
   process/material. If only photopolymer is offered, treat the RingBase as a
   non-wearable fit mock-up until cyclic bending and recovery are demonstrated.
2. Print small coupons for 0.5, 0.6, 0.8 and 1.0 mm walls, an M1 pilot/clearance
   pair, and a bayonet/pocket gauge with 0.20, 0.35 and 0.50 mm clearances.
   Record material, orientation, finish and measured dimensions.
3. Print Carrier, ContactDeck and Bezel as a static fit prototype only after
   coupon results show the battery, PCB and screw interfaces can be adjusted
   without damaging parts. Check pogo bores and pin retention separately.
4. Print a translucent crown coupon with the lens and relief. Verify LED
   clearance, light spread, and the screw counterbores before printing all
   eight crowns.
5. For the RingBase, request a material with published cyclic-flex performance
   (ideally a qualified nylon process if Elecrow can source it), then test
   split-band coupons on the intended bore gauges for force, cracking and
   permanent set before any wear trial.

**Bottom line:** Elecrow is a reasonable path for a quote, cosmetic crown
samples and rigid-part fit coupons. Publicly available specifications are not
enough to approve the current tight-fit stack or the flexing RingBase for use.
No physical print, dimensional report or material qualification is implied by
this assessment.
