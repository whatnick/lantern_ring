# Repository baseline review

Reviewed 2026-10-06 for the FreeCAD v2 physical-hardware revision.

## Consolidation

The remote default is `main`. There were **no open PRs** when work began.
Previous mono-colour, Qi, TV-B-Gone routing and decorative-model feature PRs
were already merged, including #17 at baseline `dc84f6d`. Local `main` was
behind that baseline and was fast-forwarded without dropping any work.

The sole remaining unmerged remote branch, `feat/dotstar-colour` at `b5a6b6a`,
added an independent APA102/ATtiny85 board experiment in its own directory.
It was merged with history preserved, not squashed over another variant.
It remains explicitly **experimental**, not a routed or fabrication-ready board.
All existing feature tips are included in consolidated `main`.

## Design inventory and findings

| Area | Evidence and consequence |
| --- | --- |
| v1 FreeCAD | Large historical document containing the multi-colour PCB, CR2032 and many cosmetic variants. Preserve it; do not assume its 17.78 mm octagon is the v2 PCB profile. |
| v2 mono | Six LED footprints, front `/GND` test pads and a rear VCC plane with exposed central contact. Actual outline is 17.78 x 19.05 mm. The new contact deck derives its outline and net assignments from this board. |
| v2 IR | ATtiny85/IR design with a separate ground/power/programming pad map. Its existing routed PCB and Gerbers were retained unchanged; v2 mono contact compatibility does not imply IR compatibility. |
| DotStar | APA102/ATtiny85 schematic and initial board placement, with **five unconnected items**. Do not fabricate until power, routing, ERC/DRC and battery suitability are completed. |
| Battery interface | Existing mono ground is on the front, while VCC is exposed on the rear. Two arbitrary rear-facing pogo pins would not make a functional contact interface. New hardware uses a permanent insulated loom and pogo tips on opposite cell faces. |
| LED power | The mono board has no explicit series-current limiter. Geometry does not establish safe LED/cell current or temperature; these remain release blockers for a wearable assembly. |
| Qi proposal | Documentation only, not a CR2032 charging design. A primary CR2032 must never be charged. |
| Firmware | Separate legacy Arduino/ATtiny85 TV-B-Gone port with upstream attribution/license. The mono ring needs no firmware; no firmware changes were made. |
| Materialator | Separate numpy-stl experiment. Its existing test calls missing `somefile.stl`; it is not a CAD-generation or hardware acceptance test. Metal-density/mesh-unit handling is outside this enclosure change. |

KiCad 10 read-only DRC of the mono baseline reported **zero unconnected items,
zero errors and 12 warnings**: six library-footprint mismatches and six
silkscreen/mask clipping warnings. The DotStar baseline reported two
library-footprint warnings and five unconnected items. These pre-existing
issues were not hidden or represented as newly repaired. No PCB source or
fabrication data was changed by the physical-hardware revision.

## v2 physical implementation

See [assembly, contact BOM, regeneration and release gates](../../hardware/v2.0/ring_3d/README.md).
The new design contains a keyed 30-degree three-lug bayonet carrier, removable
PCB/contact deck, screw-retained bezel, insulated CR2032 well, two specified
spring contacts and a mandatory anti-unlock screw. Both battery contacts are
serviceable without soldering to the cell.

The repository now includes Copilot instructions, a tool-neutral reconstruction
skill, portable interface/invariant regression tests and provenance checks.
Native FreeCAD and manufacturing exports are committed with their validation
report. Virtual checks are **not** a claim of printing, electrical testing,
drop/wear qualification, waterproofing or battery-compartment certification.
