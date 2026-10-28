# Elecrow bare-PCB quotation package

**Prototype quotation only, not production authorization. No parts or assembly.**

| Separate job / upload ZIP | Quantity | Finished outline (mm) | Use per clip |
| --- | --- | --- | --- |
| `ring_ir_prog_probe_elecrow.zip` | 10 | 15.500 x 27.700 | Two identical boards: populated upper probe and unpopulated lower guide |
| `ring_ir_prog_anvil_elecrow.zip` | 5 | 22.526 x 29.150 | Front-side GND contact |
| `ring_ir_prog_fence_elecrow.zip` | 5 | 22.526 x 22.150 | Mechanical locator |

This assumes a five-clip prototype batch. The three ZIPs are **three different
designs**, not three copies of a single panel. Quote them separately and combine
dispatch if possible. No fourth PCB or modification of the target IR ring is
included. The user will supply and hand-assemble all parts.

## Browser quote recorded 2026-10-28

| Job | Elecrow cart SKU | Discounted batch price (USD) |
| --- | --- | --- |
| 10 probe / guide PCBs | PCB1028108218 | 45.47 |
| 5 GND-contact anvils | PCB1028108219 | 39.00 |
| 5 fences | PCB1028108220 | 39.00 |

**PCB subtotal: USD 123.47**, excluding finalized freight and tax.
All jobs are purple with white silkscreen and immersion gold.
These are automatic browser cart quotes, not paid orders or manual engineering
acceptance. No checkout, payment or production authorization was submitted.
Supplier-hosted ZIP downloads matched each recorded local raw SHA256.
The site's Gerber preview was unavailable; DFM still needs supplier review.
See `submission.json` for the exact submitted package hashes and settings.

## Quote settings

- FR-4, two copper layers, **1.6 mm finished thickness**, 1 oz outer copper.
- Purple solder mask on both sides for this order; white silkscreen as supplied.
- **ENIG / immersion gold**, including the anvil's exposed P8 GND contact.
  Do not substitute HASL: solder buildup is unsuitable for this flat contact.
- Separated routed boards with the supplied internal windows and slots; no
  V-scoring, customer panel, castellations or gold fingers.
- Electrical test for the copper-bearing probe and anvil. The fence is a
  copper-free mechanical PCB, deliberately retaining two-layer fabrication files.
- **No component sourcing, BOM, placement/CPL, soldering, assembly or stencil.**

Preserve the mask openings, seven 1.15 mm finished PTH pogo holes, 0.30 mm probe
vias, 0.70 mm wire holes and the two 2.2 x 3.4 mm NPTH mounting slots.
Probe and guide are the same PCB artwork; do not make a separately drilled or
mirrored guide. Do not add a maker/order code on contacts or seating surfaces.
Ask before changing any artwork, hole, internal route or mask opening.

## Files and submission

`lantern_ring_ir_clip_elecrow_quote.zip` is the complete handoff bundle: it
contains the **three individual upload ZIPs**, `RFQ.txt`, `manifest.json` and
the five freshly generated ERC/DRC reports in `validation`.
Do not upload the handoff bundle as one PCB design. For Elecrow's web form, use
the corresponding individual ZIP for each separate job.

Each upload ZIP contains RS-274-X Gerbers for top/bottom copper, mask,
silkscreen and the sole Edge.Cuts profile, plus fabrication notes.
Metric absolute Excellon drills are named `*-PTH.txt` and `*-NPTH.txt` to make
plating unambiguous. Empty drill sets are omitted; the fence has no drill files.
The profile centreline defines the board size: KiCad's Gerber-job bounding box
includes the 0.1 mm plot stroke and is not the finished-outline measurement.
No paste, assembly or native design files are needed for this bare-PCB quote.

`manifest.json` records exact archive/member SHA256 values, source commit,
newline-normalized design hashes, actual polygon dimensions and fresh zero-error
ERC/DRC evidence. ZIP hashes are raw binary hashes.

Submit through the authenticated
[Elecrow PCB fabrication form](https://www.elecrow.com/pcb-manufacturing.html)
using Playwright. Upload each individual ZIP to its own job, select the settings
above and paste the relevant `RFQ.txt` notes. The form's different-design count
is **one per upload**, not three designs in each job. After Gerber analysis,
verify the dimensions against the table instead of blindly accepting detected
plot-stroke extents. Select PCB fabrication, not PCB assembly; do not buy a stencil.
Capture the resulting quote/cart references and specifications before claiming
submission. Stop before payment or authorization to begin production.

The supplied request asks for fabrication cost, ENIG/engineering fees, DFM
feedback and lead time. Shipping requires a later destination confirmation.
No payment or manufacturing start is authorized by the RFQ.
`submission.json` records actual browser submission status; package creation
alone is not evidence that Elecrow received a quote request.

## Validation and prototype limits

All three boards receive fresh DRC, including schematic parity for probe and
anvil, and both schematics receive fresh ERC with all severities included.
The package is refused if any violation is present or the existing validated
sources/target have changed. Actual Edge.Cuts polygons provide the dimensions.

The existing FreeCAD fit is virtual, using partly estimated clip/pogo geometry.
The physical pad-spacing discrepancy remains unresolved; these files retain
the saved IR board's 3.05 mm pad grid. Elecrow lists ordinary 1.6 mm board
thickness tolerance as +/-10%, and profile tolerance can exceed this fixture's
nominal registration budget. The RFQ therefore requests actual thickness,
hole/slot and routed-profile tolerances plus DFM feedback.
Supplier capability is not established by a clean KiCad DRC.
First-board dimensional inspection, physical fit, contact continuity and
programming tests remain necessary before a larger order.

## Recreate

From the repository root, with installed KiCad 10:

```powershell
python hardware\v2.0\ring_ir_prog_clip\package_elecrow.py --sets 5 --color purple
python -m unittest discover -s hardware\v2.0\ring_ir_prog_clip -p "test_*.py"
```

The script exports directly from the validated saved clip boards; it does not
regenerate or edit the target ring, board geometry or fabrication sources.
Existing project/editor settings are preserved. Recreating archives changes
their timestamps/hashes; any prior email attachments remain a distinct release.
