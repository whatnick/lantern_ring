# Lantern Ring: pricing and market feasibility

**Decision summary:** the Lantern Ring could be viable as a small-batch,
premium cosplay collectible, but the evidence supports a controlled market test,
not a production launch. Start by testing an original, unbranded version at
**A$119, A$129 and A$149** with one interchangeable crown. At the current
estimated fully loaded cost of about **A$57 per ring**, A$129 is a plausible
starting price; direct-to-customer contribution is about A$57 before general
overhead, while an Etsy sale leaves about A$50 under the assumptions below.
Sell crowns separately only after their material, finishing and packing costs
are measured.

The product is not yet commercially ready: its prototype is electrically and
mechanically unqualified, its LED circuit has no explicit current limiter, a
CR2032 is subject to Australian button-battery requirements, and the existing
Lantern Corps imagery needs a licence for commercial use. Resolve those gates
before taking paid orders.

This is a planning document, not a supplier quote, legal opinion, safety
certification or forecast. Monetary values are Australian dollars unless marked
otherwise. All scenario conversion rates, labor and component estimates are
assumptions intended to be replaced with measured results.

## Product and evidence boundary

The current v2 design is a twist-lock, serviceable PCB/battery cassette, with a
CR2032 and interchangeable illuminated crowns. The repository describes three
permanent solder joints and characterizes the ring as an unprinted,
electrically unqualified prototype. Its current 3D-printing feasibility review
also says the fit, small features and flexing band need physical qualification.
The complete product BOM and assembly time have not yet been costed from
production quotes.

The owner-reported print order is **US$30 including shipping for two rings**,
or US$15 per ring before any other costs. For translation only, this report uses
the RBA's published **A$1 = US$0.6979** rate on 9 October 2026, making the print
share approximately **A$21.49 per ring**. Exchange rates and supplier prices
move; refresh them before making a purchase or setting a fixed international
price.

The two specified Mill-Max 0965 pogo pins are a small but known cost: a search
result for Mouser Australia showed approximately A$0.89 each at single-unit
quantity. The remaining electronics, PCB, cell, wiring, fasteners, print
finishing and packaging have not been quoted at production quantities.

## Per-ring cost model

| Cost element | Low | Base | High | Basis |
| --- | ---: | ---: | ---: | --- |
| Printed parts, shipping allocated | A$21.50 | A$21.50 | A$21.50 | User's US$30/two-ring order; converted at the stated RBA rate |
| PCB and electrical BOM | A$8 | A$11.50 | A$15 | Planning allowance; includes two pogo pins, CR2032, PCB allocation, wire and small electrical parts |
| Assembly labor | A$10 | A$15 | A$20 | 20 / 30 / 40 minutes at A$30 per hour |
| Finishing, QC and rework reserve | A$4 | A$5 | A$8 | Assumption for inspection, minor finishing and a modest defect allowance |
| Packaging | A$3 | A$4 | A$6 | Assumption; excludes parcel postage |
| **Fully loaded unit cost** | **A$46.50** | **A$57** | **A$70.50** | Before business overhead, product qualification, design time, tax, and outgoing shipping |

The range is deliberately conservative about unknown work. In particular,
assembly time, yield, PCB landed cost, finishing and warranty/rework rate should
be timed and recorded across the first ten assembled units. The A$30/hour labor
rate is a value assigned to maker time, not a claimed wage or contractor quote.
If labor is excluded, the apparent base cash cost falls to A$42, but that is
not a sustainable price floor for a repeatable product.

The print figure may be optimistic for saleable parts: the prior model is a
two-ring print order and the repository's Elecrow review says the design has
unresolved process, tolerance, wear and fit questions. Include rejected prints
and finishing in the next quote rather than assuming every ordered part is
usable.

### Cost-plus and channel economics

At the base A$57 unit cost, indicative cost-plus prices are:

| Pricing rule | Indicative price | What it means |
| --- | ---: | --- |
| 1.8× loaded cost | A$103 | Low-price floor; little room for overhead, support or product improvement |
| 2.0× loaded cost | A$114 | Basic cost-plus reference, still tight for a low-volume handmade item |
| 2.25× loaded cost | A$128 | Supports a suggested A$129 test price |
| 2.5× loaded cost | A$143 | More room for overhead and small-batch variability |

For an Australian GST-registered seller, retail prices below are treated as
GST-inclusive. A$129 therefore represents about A$117.27 sales revenue before
deducting costs. GST registration, input tax credits, and GST treatment of
marketplace fees can change the exact accounting; use an accountant for the
actual business model. The current ATO registration threshold is A$75,000 in
GST turnover.

| Customer price | Revenue ex-GST* | Direct card fee assumption** | Etsy fee estimate*** | Base-cost contribution, direct | Base-cost contribution, Etsy |
| ---: | ---: | ---: | ---: | ---: | ---: |
| A$119 | A$108.18 | A$2.68 | A$11.56 | A$48.50 | A$39.63 |
| A$129 | A$117.27 | A$2.88 | A$12.51 | A$57.39 | A$47.77 |
| A$149 | A$135.45 | A$3.28 | A$14.41 | A$75.17 | A$64.05 |

\* Assumes the seller is GST-registered and advertised price includes GST;
revenue is price / 1.1. If not registered, the cash collected is not reduced
by an output-GST allocation, but registration obligations still need monitoring.

\** Direct card fee is a placeholder assumption of 2% + A$0.30 per sale, not a
verified quote for a selected payment provider. Replace with the chosen
provider's fee.

\*** Uses Etsy's published Australian 6.5% transaction fee plus 3% + A$0.25
payment processing fee, applied to item price only. Etsy fees may also apply
to shipping and other charges; this estimate excludes listing, advertising,
currency-conversion and tax-on-fee effects.

Contributions above are before rent, insurance, travel, software, website,
marketing, returns, income tax and the seller's unallocated business time. The
table is not gross profit after all business expenses. A$129 is a useful
starting hypothesis, not a proven willingness-to-pay point.

### Value-based price positioning

Search results for current Etsy Australia listings showed simpler illuminated
Lantern-style cosplay rings around **A$50–70**. This is a weak comparison:
marketplace listings vary in construction, seller reputation, size, lighting,
shipping and licensed status, and listing prices do not prove completed sales.
The v2 product can justify testing a premium if customers value its low-profile
wearability, replaceable crown system, illuminated translucent top and
serviceable battery/PCB cassette. Those benefits need to be shown in person and
validated with paid conversion, not assumed from the CAD render.

Test three clear offers, all with one crown:

| Offer to test | Test price | Positioning |
| --- | ---: | --- |
| Entry | A$119 | Introductory test; use only if measured cost and event feedback support it |
| Core | **A$129** | Recommended first test price; supports the base cost model |
| Premium finish | A$149 | Test only if finishing, presentation and reliability visibly warrant the step-up |

Offer additional original-design crowns as a separate accessory, initially
testing **A$19–29 each** or a modest multi-crown bundle. This is a test range,
not a cost-derived price: measure each crown's print yield, sanding/finishing,
packing and any assembly time first. Avoid giving away the interchangeable
value in an eight-crown bundle until repeat demand is demonstrated.

## Market size: use an event funnel, not a headline cosplay TAM

There is no reliable official census of cosplay participants or of buyers for
illuminated cosplay rings. Broad global estimates for the costume or cosplay
market do not translate into demand for this single product. The useful
near-term question is how many relevant prospective buyers can be reached,
what proportion buys, and how many units can be made safely.

Published audience figures are **event attendances/visits, not unique ring
buyers**. Supanova expects more than **135,000 visits across six Australian
cities in 2026**. SMASH! reported more than **47,500 attendees in 2025**. These
are from different years and audiences may overlap; do not add them to claim a
unique Australian TAM. Oz Comic-Con does not publish verified attendance for
its 2025/2026 shows in the official sources reviewed.

Use Supanova's 135,000 annual event-visits as a measurable Australia pilot
reach proxy. For planning only, assume 50–75% are distinct visitors across its
shows (67,500–101,250 people) and 0.1–0.5% of that audience eventually buys this
specific product. That yields roughly **70–510 annual units** and
**A$9,000–66,000** in gross sales at A$129 each, if the assumptions hold.
Rounded scenarios:

| Scenario | Unique event-reach assumption | Purchase rate | Annual units | Gross retail sales at A$129 |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 67,500 | 0.1% | 68 | A$8,772 |
| Working case | 85,000 | 0.3% | 255 | A$32,895 |
| Upside | 101,250 | 0.5% | 506 | A$65,274 |

This is **not an independently measured market size**; it is a sensitivity
calculation from a published attendance figure and explicit assumed rates.
Supanova's attendance forecast may include repeat visits, and the proposed
conversion rates have no sales history behind them. Excluding SMASH! avoids
claiming a combined unique audience; the event is a separate opportunity to
test. Track qualified conversations, email signups, deposits/orders, and
sell-through at each event to replace these assumptions with evidence.

For a first-year serviceable obtainable market, capacity matters more than
theoretical audience. A maker capacity of 50–150 qualified units/year (an
assumption of about 4–12 units a month) implies **A$6,450–19,350** annual gross
sales at A$129. This range is a practical pilot target, not a sales forecast.
International demand is not quantified here: Anime Expo's official 2025
recap reported more than 410,000 attendees, and gamescom reported 357,000
visitors, but neither figure establishes the share interested in this ring,
the licensing position, or the cost of shipping a coin-cell wearable
internationally. Treat international markets as later experiments, not as a
multiplier on Australian event traffic.

## Customers, communities and ways to reach them

Best initial audiences are:

- Cosplayers and prop-makers who want a wearable illuminated accessory rather
  than a static display replica.
- Convention attendees and collectors drawn to configurable color/top
  accessories, especially those who already make themed costumes.
- Makers and electronics hobbyists who value the serviceable PCB/battery
  design; these may be easier to reach on hardware-focused channels, but they
  are not equivalent to cosplay buyers.
- Original fantasy/sci-fi jewelry buyers, if the designs are sufficiently
  distinct from protected franchises.

Practical Australia options:

| Channel | Opportunity | Cost / limitation |
| --- | --- | --- |
| Supanova | Six-city audience; submit through the official exhibitor portal. Test Artist Alley or retail/vendor category fit with the organizer. | 2026 attendance forecast is over 135,000 across events; current sales-kit pricing is behind the portal. Applications require approval; insurance requirements apply. |
| SMASH! Sydney | Strong anime, cosplay and creator context; official exhibit application/info pack. | 2025 reported attendance exceeded 47,500; application and booth costs must be confirmed for the applicable year. |
| Oz Comic-Con | Artist Alley is a potential low-footprint test if the product fits its selection/category rules; otherwise submit an exhibitor EOI. | 2026 Artist Alley rates are A$472.50–551.25 + GST by city. These are not general vendor-booth rates; acceptance is curated. |
| Local cosplay/maker markets | Smaller, lower-risk product demonstrations, feedback and presales; seek cosplay-oriented markets and maker events in the seller's own city first. | Stall, travel and public-liability-insurance cost vary; verify the specific organizer's terms. |
| Etsy Australia | Search discovery for handmade cosplay jewelry and gift purchases. | 6.5% transaction plus 3% + A$0.25 processing under the current published policy; shipping charges can also attract fees. IP enforcement risk is material for franchise designs. |
| Tindie | Potential fit for open-hardware/electronics customers and DIY variants. | Tindie states a 5% marketplace fee; payment processing and international currency conversion may be additional. Audience likely narrower than a cosplay marketplace. |
| Direct web/social sales | Best margin and direct feedback once a tested product page, support process and safe fulfillment exist. | Requires discovery, payment, customer service, product liability planning and a working supply process. |

Internationally, test English-language cosplay and anime/gaming communities
before trying to serve every region. Anime Expo in Los Angeles, gamescom in
Cologne and Japan's AnimeJapan/World Cosplay Summit are examples of large
communities, not a recommended first set of booths: overseas travel, vendor
fees, customs, consumer rules and shipping create substantial fixed cost.
Begin with an original product page that accepts international interest
registrations; consider shipping only after checking the destination's product
rules and the postal/carrier restrictions for CR2032 cells. Shipping without
the coin cell may be safer operationally, but the battery-safety obligations
for the product itself still need assessment.

## Similar products and projects

There are already direct Lantern-ring offers and adjacent open-hardware builds.
The product is not entering an empty category. These examples are useful for
benchmarking and product differentiation; listings can change or disappear,
and the descriptions do not establish independently verified quality or sales.

| Example | What it overlaps | How it differs / what to learn |
| --- | --- | --- |
| [LED Lantern Corps rings on Etsy](https://www.etsy.com/market/led_lantern_ring) and [example Etsy listing](https://www.etsy.com/listing/4299243325/lantern-corps-ring-cosplay-green-red) | Directly competes for Lantern cosplay/collector interest; some listings offer multiple color variants. | The v2 proposition should be one maintained, serviceable ring platform with replaceable crowns—not merely another fixed-color ring. Confirm any exact offer, pricing and stock on the live listing before benchmarking. |
| [Lantern rings on eBay](https://www.ebay.com/itm/257196641750) | Working illuminated, character-themed ring listings are a direct finished-product substitute. | Compare sizing, activation, serviceability, lighting uniformity and finish in person where possible; listing copy alone does not prove durability. |
| [Cults3D “Lantern Corps LED rings Set All 9”](https://cults3d.com/en/3d-model/jewelry/lantern-corps-led-rings-set-all-9) and [Printables Lantern Corps ring files](https://www.printables.com/model/1346358-lantern-corps-rings/files) | Low-cost digital/DIY substitutes for makers with printers and basic assembly skills. | Compete on a tested assembled experience, fit guidance, documented repairability and customer support rather than the downloadable geometry alone. Check each model's license before commercial use or adaptation. |
| [Qtrocious/Radiant](https://github.com/Qtrocious/Radiant) | Open project for a 3D-printed, electronically controlled illuminated wearable ring, inspired by *Detroit: Become Human*. | It is a temple-worn LED ring using a XIAO ESP32-C3, not a finger ring or interchangeable cosplay-crown product. It is a useful adjacent reference for wearable electronics and enclosure design. |
| [lightcafe-lab/ModsRing](https://github.com/lightcafe-lab/ModsRing) | Open modular smart-ring hardware with 3D-printable cover and separate electronics modules. | It targets smart-ring functions rather than cosplay display. Its modular PCB/system packaging is a useful technical precedent, not a direct buyer substitute. The repository describes Arduino examples and KiCad hardware; verify its current license and files before reuse. |
| [Whatnick Lantern Rings on Tindie](https://www.tindie.com/products/whatnick/lantern-rings/) | This is the project's own existing product listing, not an independent competitor. | Treat it as the legacy baseline to refresh with measured v2 photos, clear module/crown options, size and safety limits, and an updated price only after qualification. |

The clearest defensible difference to test is **one illuminated ring body that
accepts low-profile themed tops**, backed by repeatable fit and serviceability.
Competitors and downloadable files can imitate the visual theme, so durability,
comfortable sizing, safe battery access, optical quality and dependable
after-sales support will matter more than the number of available emblems.
Because franchise marks appear in many competing listings, their presence on
marketplaces is not evidence of permission; do not use them commercially
without appropriate rights.

### Event break-even example

The 2026 Oz Comic-Con Artist Alley fee in Sydney is listed as A$551.25 plus
GST, or about **A$606** including GST. At A$129, using the base cost and the
direct card-fee assumption above, estimated contribution is about A$57 per ring
after allocating output GST. The table fee alone therefore takes about
**11 sales** to recover (A$606 / A$57.39). This is before transport, accommodation,
insurance, display materials, meals, GST treatment/input credits and time at
the show. A practical decision should use a full event budget and a target of
at least twice the bare table-fee break-even.

## Commercial readiness and launch gates

1. **Electrical:** Add or otherwise validate appropriate LED current
   limiting for the actual battery, LED and operating conditions. The current
   ring README specifically warns that the mono PCB has no explicit LED series
   current limiter. Measure current, temperature and battery behavior; do not
   assume the CR2032's internal resistance makes the circuit safe.
2. **Button-cell compliance:** Australia's mandatory button/coin battery
   standards include standards for consumer products containing these
   batteries and required information/warnings. Have the exact product
   classified against the current standards, test the enclosure/retention
   design as required, and prepare compliant labeling and instructions before
   supplying it. The prototype's screw-retained battery access is not evidence
   of compliance.
3. **Mechanical and materials:** Complete physical print coupons and wear,
   flex, drop, fit and repeated-cassette-cycle tests. The current repository
   assessment says Elecrow's public material/tolerance data is insufficient to
   qualify the small features or flexing band.
4. **IP:** Obtain written permission/licensing for any protected Lantern
   Corps/DC names, marks or recognizable symbols used commercially, or replace
   them with original designs and names. Calling a product "inspired by" does
   not itself grant rights. Etsy also places responsibility for IP compliance
   on sellers.
5. **Consumer obligations and insurance:** Check Australian Consumer Law
   guarantees, product safety/recall responsibilities, appropriate public and
   product liability insurance, event prop policies and the seller's support
   and repair/replacement process. A disclaimer cannot substitute for product
   compliance.
6. **Cost validation:** Obtain landed production quotes for print, PCB,
   electrical components and packing; time ten complete assemblies; measure
   failure/rework rates; then recalculate price, GST, platform fees and event
   break-even.

## Recommended validation sequence

1. Resolve the circuit and coin-cell safety design questions and prepare an
   original-design, unbranded sample; do not take paid orders for the current
   unqualified franchise-logo prototype.
2. Cost and assemble ten units, record labor and defects, and collect material
   and supplier quotes. Use this to replace the A$57 planning cost.
3. Conduct low-cost customer tests with three price points (A$119/A$129/A$149)
   using a working demonstrator and a simple preorder/waitlist. Report actual
   qualified interest and paid conversion, not likes or general event
   attendance.
4. Apply for one suitable local convention/market after confirming vendor
   category, booth price, insurance and event rules. Proceed only with a
   budget and a break-even target that includes travel and labor.
5. Add a second event or international shipping only if the first test
   demonstrates repeatable demand, manufacturing yield and safe fulfillment.

## Sources

Primary sources and time-sensitive references checked for this assessment:

- [RBA exchange rates overview](https://www.rba.gov.au/exchange-rates-overview.html) — conversion basis, 9 October 2026.
- [Mill-Max 0965 manufacturer drawing](https://www.mill-max.com/sites/default/files/external/assets/2020-04/ultra_low_profile_spring_pins_rev._04.14.20.pdf) and [Mouser Australia product page](https://au.mouser.com/en/ProductDetail/Mill-Max/0965-0-15-20-80-14-11-0?qs=nWJT1%252BT7xrY1kmn7EUHYmQ%3D%3D) — specification and indicative pin price.
- [Supanova exhibitors](https://www.supanova.com.au/exhibitors/) and [exhibitor portal](https://exhibitors.supanova.com.au/) — 2026 multi-city events and application path; pricing via sales kit.
- [SMASH! exhibit information](https://smash.org.au/get-involved/exhibit) and [2025 event site](https://2025.smash.org.au/) — exhibitor information and prior event context.
- [Oz Comic-Con Artist Alley fees and inclusions](https://ozcomiccon.com/artist-alley-fees-and-inclusions/) and [exhibitor expressions of interest](https://ozcomiccon.com/expressions-of-interest/) — 2026 fees and category/application paths.
- [Etsy Fees & Payments Policy](https://www.etsy.com/legal/fees/) — Australian transaction and payment processing rates.
- [Tindie seller information](https://www.tindie.com/about/sell/) — stated marketplace commission.
- Comparable work: [Etsy LED Lantern ring search](https://www.etsy.com/market/led_lantern_ring), [eBay working LED ring example](https://www.ebay.com/itm/257196641750), [Cults3D nine-ring model](https://cults3d.com/en/3d-model/jewelry/lantern-corps-led-rings-set-all-9), [Printables ring files](https://www.printables.com/model/1346358-lantern-corps-rings/files), [Radiant](https://github.com/Qtrocious/Radiant), and [ModsRing](https://github.com/lightcafe-lab/ModsRing). Marketplace pages are mutable; open-source licenses should be checked before reuse.
- [Anime Expo 2025 official recap](https://www.anime-expo.org/2025/07/14/anime-expo-2025-wraps-four-days-of-celebration-with-attendees-from-over-65-countries-1300-hours-of-programming-and-discussions-on-its-future/) and [gamescom 2025 official recap](https://www.gamescom.global/en/2025-excites-the-community-worldwide-and-sets-new-standards) — context only, not ring demand.
- [Australian button/coin battery mandatory standards](https://www.productsafety.gov.au/business/search-mandatory-standards/button-and-coin-batteries-mandatory-standards) and [ACCC product safety responsibilities](https://www.accc.gov.au/business/selling-products-and-services/product-safety-responsibilities).
- [IP Australia: use of copyright content](https://www.ipaustralia.gov.au/tools-and-research/professional-resources/data-research-and-reports/australian-ip-report-2026/copyright/use-of-copyright-content) and [Etsy intellectual property policy](https://www.etsy.com/legal/ip/).
- [ATO: when to register for GST](https://www.ato.gov.au/business/gst/registering-for-gst/when-to-register-for-gst).
- Repository product evidence: [Lantern Ring v2 hardware README](../../hardware/v2.0/ring_3d/README.md) and [Elecrow print feasibility assessment](elecrow-3d-print-feasibility.md).

Event attendance and prices, marketplace fees, component prices and exchange
rates are date-sensitive. Confirm them directly with the organizer, supplier or
authority before acting.
