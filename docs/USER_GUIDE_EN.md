# EPL Logistics — User Guide

An operator's manual: every screen, every button, and what happens after you press it.

Updated: 12 Sep 2026 · Applies to branch `EPL_11_9_26`

---

## Contents

1. [Before you start](#1-before-you-start)
2. [The shared frame](#2-the-shared-frame)
3. [The flow, end to end](#3-the-flow-end-to-end)
4. [Master data](#4-master-data)
5. [Customers and opportunities](#5-customers-and-opportunities)
6. [Freight quotations](#6-freight-quotations)
7. [Delivery orders](#7-delivery-orders)
8. [Dispatch and execution](#8-dispatch-and-execution)
9. [Tracking and control](#9-tracking-and-control)
10. [Completing a delivery](#10-completing-a-delivery)
11. [Posting to the sales ledger](#11-posting-to-the-sales-ledger)
12. [The driver app](#12-the-driver-app)
13. [Home and dashboard](#13-home-and-dashboard)
14. [Common refusals](#14-common-refusals)
15. [Glossary](#15-glossary)

---

## 1. Before you start

**Opening the system.** Enter the server address in your browser. This system is a
module inside a larger platform, so it has no sign-in screen of its own — the parent
platform handles authentication.

**Three things to know up front:**

- The system works in **four currencies**: VND, USD, THB, LAK. Every document carries
  its own currency and the screen always shows that currency — nothing is silently
  converted.
- **Every amount has a source.** Cost comes from the vehicle type's cost formula; the
  price comes from the quotation agreed with the customer. Nowhere can you type a
  figure with no origin.
- **The system refuses often, and always says why.** When a button is blocked, read the
  message — it names the exact thing that is missing and the screen to go fix it.
  Section 14 lists the refusals you will meet most.

---

## 2. The shared frame

This part is the same on every screen.

### 2.1. Top navigation

| Menu | Opens |
|---|---|
| **⌂ Today** | Home — what needs doing today |
| **Operations** | Delivery orders · Shipments · Dispatch · Tracking · Completion · Packing list |
| **Sales** | Customers and opportunities · Freight quotations |
| **Master data** | 10 tabs of foundation data |
| **Reports and more** | Revenue and cost analysis · AI checkpoint |

Click a group name to open its menu, then click an item.

### 2.2. The Back button

It sits at the **top of the page, left of the screen title**. Press it to return to the
previous screen.

Three ways back, all equivalent:

- The **← Back** button on the page
- Your browser's **Back** button
- Swipe back on a phone, or `Alt + ←`

The button hides itself on the first screen — there is nowhere to go back to, so no
button is shown.

> **Tip:** the browser address carries the screen code (for example `#dispatch`).
> Reloading (F5) keeps you on the same screen, and a link you send a colleague opens
> exactly where you are.

### 2.3. Changing language

The flag button in the top right: **Tiếng Việt · English · ລາວ**. Your choice is
remembered next time.

### 2.4. Confirmation dialogs

Anything you cannot undo — deleting, posting to the ledger, cancelling a shift — asks
first, in a dialog belonging to the application. It states what will happen, and its
**two buttons name the actual action** — for example `[ Keep it ]` and
`[ Delete vehicle ]`, not OK/Cancel. Press `Esc` or click outside to cancel.

---

## 3. The flow, end to end

```
 Opportunity ──►  Quotation  ──►  Customer accepts
                                        │
                                        ▼  (automatic — never typed by hand)
                                 Delivery Order (DO)
                                        │
                                        ▼
                                   Create a Trip
                                        │
                                        ▼
                             Dispatch: assign vehicle + crew
                                        │
                                        ▼
                          Driver records milestones on the phone
                                        │
                                        ▼
                       Completion: proof of delivery + final price
                                        │
                                        ▼
                    Post to the sales ledger → accounts receivable
```

**Three layers to keep apart:**

| Layer | What it is | Belongs to |
|---|---|---|
| **Quotation (QT)** | The agreement: which lane, which vehicle type, what price | The customer and the price |
| **Delivery Order (DO)** | One specific delivery: this consignment, collected on this day, delivered before this hour | The customer's demand |
| **Trip** | A real vehicle movement: which truck, which driver, departing when | How the company performs it |

One quotation produces many delivery orders. One trip may carry several orders, and one
order may need several trips.

> **There is no way to create a delivery order by hand.** An order exists only because a
> customer accepted a quotation — that is what gives it a locked price. A hand-typed
> order has no quotation behind it, and settlement would have no figure to draw on.

---

## 4. Master data

**Go to:** Master data in the top navigation.

This screen has 10 tabs. **The order matters** — later tabs consume what earlier ones
declare.

| Tab | What you declare | Needs first |
|---|---|---|
| **0. Setup A–Z** | The recommended order, with a jump to each tab | — |
| **1. Transport routes** | Legs A → B → C, planned km, toll fees | — |
| **2. Cost formula & fuel** | Unit rates per line item, per vehicle type | Vehicle types |
| **3. Vehicle types** | Max weight, volume, pallet count | — |
| **4. Vehicle and driver scheduling** | Weekly shifts | Vehicles, drivers |
| **5. Drivers & licences** | Driver records, licence class and expiry | — |
| **6. Currency rates** | VND · USD · THB · LAK | — |
| **7. Customer catalogue** | Name, contacts, payment terms | — |
| **8. Carriers / vendors** | Subcontracted hauliers | — |
| **9. Account mapping** | Acc code for each cost line item | — |

### 4.1. Routes

**Adding a route:** enter the route code, a name, then each leg (origin → destination,
km).

On save the system **looks up coordinates** for the points and draws the real road
line. If a point cannot be resolved, the message names it — enter its coordinates by
hand, otherwise the tracking map will be missing a point and the simulated vehicle
position will sit in the wrong place.

> A cross-border route should declare **its actual legs**, for example
> `Vientiane → Cau Treo border → Cua Lo Port`. Declared as one straight line, the map
> draws through mountains and the border stop never appears.

### 4.2. Cost formula

The formula has **two levels**: a standard formula per **vehicle type**, and per-vehicle
overrides for the few figures that differ.

Each line item carries an **Acc code** — the cost classification issued by the accounts
department. Without it, the handover package reports that line as unclassified.

> **Important:** in the component table, "Freight rate /kg" is a **selling price**, not a
> cost. Only the other four components (fuel, driver allowance, tolls, yard) make up the
> cost. Never add all five into one figure.

### 4.3. Drivers & licences

Every driver needs a **record** (name, licence class, role) and **a licence row** that is
valid and whose class matches the record.

**Role** decides whether a person can drive as lead. Someone recorded as "co-driver"
cannot be assigned as the main driver at dispatch.

**Shifts** (tab 4) must cover the trip's time window. No shift means dispatch is blocked.

---

## 5. Customers and opportunities

**Go to:** Sales → Customers and opportunities.

This is **the first step of the flow**: recording what a customer wants, before any
quotation exists.

### 5.1. Three views

| Button | Shows |
|---|---|
| **Opportunity board** | Kanban — drag opportunities between stages |
| **List** | A flat table, with filters and search |
| **Customers** | A 360° profile per customer: opportunities, quotations, orders, revenue |

### 5.2. The buttons

| Button | What it does |
|---|---|
| **+ Opportunity** | Create one. Enter the customer (or a prospect name with no code yet), contact, source, lane, cargo type, weight, trips per month, the price the customer expects |
| **+ Opportunity for this customer** | The same, pre-filled with the customer you are viewing |
| **Create quotation** | **This is the step change.** It creates a draft quotation inheriting the customer, lane, cargo and volume; the opportunity moves to *Quoted* |
| **View quotation** | Opens the quotation linked to this opportunity |
| **Won / Lost** | Record the outcome. Choosing *Lost* **requires a reason** |
| **Reopen** | Return a closed opportunity to active |

**Six stages:** New · Contacted · Negotiating · Quoted · Won · Lost.

> *Quoted* and *Won* are **set by the system** — when a quotation is created and when
> the customer accepts. Do not drag into those two by hand.

---

## 6. Freight quotations

**Go to:** Sales → Freight quotations.

### 6.1. Top bar

| Button | What it does |
|---|---|
| **+ Quotation** | Start a new one |
| **↻ Refresh** | Reload the list |
| **↓ Export Excel** | Export the current filtered list |

### 6.2. Inside a quotation

The form is grouped into three tabs:

- **Customer and itinerary** — customer, lane, vehicle type, collection/delivery windows
- **Quotation & delivery orders** — goods, cost, price, discount
- **Documents & notes** — attachments, internal notes, notes for the customer

| Button | What it does |
|---|---|
| **+ Add goods line** | Item, quantity, unit of measure |
| **Save draft** | Saves it; nobody is notified |
| **Submit for internal approval** | Used when the margin is **below the company threshold** — the quotation waits for a manager |
| **Approve and send to customer** | A manager approves and sends in one step |
| **Send to customer** | Send it (used directly when the margin clears the threshold) |
| **Customer declined** | Record a refusal; **a reason is required** |
| **Duplicate** | Copy this into a new quotation |
| **Price history** | Every price revision of this quotation |
| **Print (internal)** | Full print: cost per line, margin, internal notes |
| **☁ Choose file and attach** | Attach a file |

### 6.3. How the price is built

1. The system reads the **cost formula** of the chosen vehicle type and computes the
   trip cost.
2. You choose a **margin** → that gives the price.
3. A **discount**, if any, is a percentage off that price.

Currency is chosen per quotation. Choose Lao kip and the cost is converted using the
rate declared in master data.

> A quotation **below cost** is refused when you try to send it.

### 6.4. When the customer accepts

Press the accept button on the quotation. In **a single transaction** the system:

- Moves the quotation to *Split*
- **Creates the delivery order**, carrying the lane, the locked price and the time
  windows
- Moves the opportunity to *Won*

One quotation can produce several orders (one per consignment) — state how many when
accepting.

---

## 7. Delivery orders

**Go to:** Operations → Delivery orders (DO).

### 7.1. The counters

Six clickable counters that filter the list: **Delivery orders · Referenced routes ·
Needs action · In transit · Completed · Cancelled · All**.

### 7.2. The buttons

| Button | What it does |
|---|---|
| **Orders come from quotations →** | Takes you to the quotation screen. There is **no** blank order form here |
| **Create trip** | Select one or more orders on the same lane and build a trip |
| **View quotation** | Opens the order's source quotation |
| **Add charge / Save cost** | Record an extra cost against the order |

### 7.3. Creating a trip

Enter: trip code, departure date and time, planned speed, dwell time per leg.

**Trip types:**

| Type | When to use it |
|---|---|
| **One way** | Delivered and done |
| **Multi-stop** | One trip carrying several orders, each with its own drop point. Only possible on a route with **two legs or more** |
| **Round trip (with return leg)** | Includes the run back to the yard. You must choose a **return route**, and it must start where the outbound route ends |

> **Carrying cargo on the return leg is temporarily unavailable.** A return-leg delivery
> order cannot yet be signed for, so the trip would never close and the vehicle would
> stay held. Choose *Empty return*, or build a separate trip for the return load.

---

## 8. Dispatch and execution

**Go to:** Operations → Dispatch and execution.

This is where **vehicles** and **crews** are assigned to trips.

### 8.1. Filter bar

| Control | What it does |
|---|---|
| **Scope** | Filter by yard and by vehicle type |
| **Search** | Find an order code, customer or lane |
| **‹ · date · ›** | One day back / forward |
| **Today** | Return to the current date |
| **⚡ Assign remaining orders** | Auto-assign vehicles to orders that have none |

> **This screen filters by DATE.** If the order column is empty, read the line beneath
> it — it says how many orders are waiting on other days and gives a button straight to
> that day. The amber **Backlog** button means orders whose collection day has already
> passed with no vehicle assigned — more urgent than tomorrow's work.

### 8.2. The counters

**Orders today · Departed · Awaiting assignment · Missing trip · Vehicles free/total ·
Drivers on shift**

### 8.3. Left column — orders awaiting dispatch

Grouped **by lane · by customer · by deadline**. Tick several orders to assign them in
one go.

### 8.4. Middle column — fleet by yard

Each yard shows vehicles **free / running / in workshop**. Select an order and the
column filters to suitable vehicles.

Sorting: **Best fit · Same yard · Free soonest**.

### 8.5. Assignment buttons

| Button | What it does |
|---|---|
| **Pick vehicle first** | Choose the vehicle, then the order |
| **Change** | Swap an assigned vehicle or driver |
| **Add** | Add a co-driver |
| **Save assignment** | Save it without releasing the vehicle |
| **Confirm dispatch & depart** | Confirm and send the vehicle out |

### 8.6. Right column — exceptions to approve

What the system blocked or flagged: vehicle papers expiring, licences expiring, a
vehicle type that differs from the quotation. Click one for detail;
**← Back to exception list** returns.

---

## 9. Tracking and control

**Go to:** Operations → Tracking and control.

The map and progress of trips **currently running**.

| Button | What it does |
|---|---|
| **Refresh GPS** | Fetch the latest positions |
| **Reload** | Reload the whole list |
| **Refresh timeline** | Refresh the milestone timeline |
| **+ New incident** | Record type, severity, location, description |
| **Send incident report** | Save the incident |

**On the map:**

- The **solid red** line is distance covered, the **grey dashed** line is what remains
- A pin marks the vehicle; vehicles in the same spot are spread slightly so they do not
  overlap
- Stop points are pinned and numbered in order

**Simulated position.** When a device has sent nothing for 15 minutes, the system infers
the position from progress along the route and marks it clearly as **simulated**. That
is not real GPS — the milestones the driver records are the real evidence.

---

## 10. Completing a delivery

**Go to:** Operations → Delivery completion.

Two tabs: **Awaiting completion** and **Completed**.

### 10.1. "Awaiting completion"

Each row is an order waiting to be signed for.

| Button | What it does |
|---|---|
| **View order** | Order detail and pricing |
| **Complete delivery** | Opens the proof-of-delivery form |
| **↻** (beside the price) | Reload the price if the cell reads *Price not loaded* |

### 10.2. The completion form

**Part 1 — Proof of delivery.** One block per drop point:

- Delivery time · Recipient · Phone
- Outcome: *Delivered in full · Short delivery · Refused by customer*
- **Photo of the delivery note** (required)
- **Recipient's signature** — signed directly on the screen
- Cargo condition / notes

**Part 2 — Final price.** The cost line items from the formula, each with a **Customer
pays extra** field. The total feeds *Final price*.

| Button | What it does |
|---|---|
| **Add charge** | Add a surcharge line outside the table |
| **Back** | Close without saving |
| **Complete delivery & lock price** | Submit the proof, lock the price, close the order |

> A multi-stop trip **requires every point to be signed** before the order can close.

> For a foreign-currency quotation with no cost formula in that currency, the table
> falls back to the VND formula and **says so**. Those cells are for reference only and
> are not added to the selling price. Extra charges can still be entered, in the
> quotation's own currency.

### 10.3. "Completed"

The record of closed orders. **View record** opens:

- Five figures: Quoted price · Customer extras · Final price · Internal cost · Profit
- Full order detail
- **Income–expense ledger**: every income and expense line with its **Acc code**, in
  columns *Originally agreed* / *Actual* / *Customer extra or variance*
- Proof-of-delivery photos and signatures

| Button | What it does |
|---|---|
| **Update actual cost / Lock freight** | Revise actual costs once invoices arrive |
| **Post to sales ledger** | Push to accounts receivable — see section 11 |

---

## 11. Posting to the sales ledger

This button sits on a **completed record**, beside *Update actual cost / Lock freight*.

**What it does:** pushes a delivered order to the accounts system to create a **sales
order** and **record the receivable** at the locked final price.

**How to use it:**

1. Press **Post to sales ledger**
2. Read the confirmation, press **Post**
3. On success the button becomes a green chip **Posted to sales ledger · SO-…**

The *Handover to accounts* marker on the record also shows the sales order code and the
opening receivable.

> **It happens once.** The accounts system offers no edit or delete from here. Once
> posted, the button disappears.

> The receivable is recorded in **the quotation's own currency** — a Lao kip order is
> booked in kip, not converted to dong.

If it is refused, the button remains and a line shows the last error. Three common ones:

| Error | Meaning | Who fixes it |
|---|---|---|
| Customer code not found in the accounts system | That customer has not been created there | Accounts team |
| Integration not enabled | The accounts system is not accepting pushes | Accounts team |
| Currency not supported | It accepts only VND, USD, LAK | Agree an approach with accounts |

---

## 12. The driver app

A separate page for drivers, used on a **phone**. It is a standalone application, not
part of the main system.

**To open:** run `python chay.py` in the `EPL_TaiXe` folder, then open the address it
prints, on a phone on the same network.

### 12.1. Trip list

Tap **your name** at the top to select yourself (remembered next time). The list shows
**only that driver's trips**.

Each card shows: order code · customer · lane · status · legs completed · vehicle ·
delivery deadline.

### 12.2. Trip detail

Tap a card to open it. The screen has:

- A **map** — distance covered in red, the rest dashed, pins for the vehicle and stops
- **Four figures**: progress % · km remaining · speed · estimated arrival
- A **milestone bar** of six steps: Check in → Collect → Depart → Arrive → Unload →
  Delivered
- **Order details** and the **leg list**
- **← Back** in the top corner

### 12.3. Three action buttons (fixed at the bottom)

| Button | What it does |
|---|---|
| **📍 Record milestone: …** | Records the next milestone in sequence. It is **real** — the vehicle moves on the dispatcher's map. It cannot be undone |
| **✍ Complete delivery** | Opens the signing form. **Enabled only after the *Arrive* milestone** |
| **⚠ Report incident** | Type, severity, location, description — dispatch sees it immediately |

### 12.4. Signing on the phone

One block per drop point: delivery time · recipient · phone · outcome · **photo of the
delivery note** (taken with the camera) · **hand-drawn signature** · notes. A price
table lets the driver enter what the customer paid extra.

> **Demo limitation:** this page has **no sign-in**. "Each driver sees only their own
> trips" is presentation filtering, not a security boundary — anyone who opens the page
> can select someone else's name.

---

## 13. Home and dashboard

### 13.1. Today

- **Today's figures**: delivery orders · trips running · opportunities to call ·
  incidents · **records ready for handover**
- **Needs attention now**: overdue orders, quotations expiring, open incidents
- **Today's flow**: six connected stations — Opportunity → Quotation → Delivery order →
  Dispatch → Running → Completed. The amber station is where work is piling up
- **Today's resources**: vehicles free / running / in workshop, drivers free, and **two
  document warnings** — vehicles whose inspection is expiring and drivers whose licence
  is expiring

> Those two warnings count exactly what will **block dispatch**, including records where
> the date has never been entered. Finding out at assignment time is too late.

### 13.2. Dashboard

Overall figures and an A–Z flow diagram of the eight function groups.

### 13.3. Revenue and cost analysis

**Go to:** Reports and more → Revenue and cost analysis. Cost, quoted price and profit
by lane, by vehicle and by customer.

---

## 14. Common refusals

The system blocks where there is real risk. This table explains the refusals you will
meet most often.

| The system says | It means | Where to fix it |
|---|---|---|
| Vehicle type does not match the quotation | The chosen vehicle differs from the type priced for the customer | Pick the right type, or revise the quotation |
| Vehicle papers missing or expired | Inspection / insurance / servicing expired **or never entered** | Master data → Vehicles |
| Licence unsuitable or expired | Missing, expired, or a class that differs from the record | Master data → Drivers & licences |
| No working shift covers this time | The driver has no shift in the trip's window | Master data → Vehicle and driver scheduling |
| Person selected is not a lead driver | They are recorded as a co-driver | Choose someone else, or change the role |
| Vehicle/driver is busy | Holding a trip that has not closed | Complete it, confirm the return to yard, or cancel that trip |
| Weight / volume exceeded | The cargo declared is beyond capacity | Choose a larger vehicle, or split the consignment |
| Assignment outside the window | The assignment time falls outside the order's collection/delivery window | Change the window on the order first |
| Proof of delivery required for all delivery legs | A multi-stop trip still has an unsigned point | Sign the remaining points |
| Settlement only after the trip completes | A round trip has not confirmed the return to yard | Confirm the return first |
| Quotation below cost | The price is under the cost | Revise the price or the margin |
| No cost formula for this vehicle type | This type has no formula yet | Master data → Cost formula |

**The general rule when blocked:** read the message, do the one thing it names, press
again. The system always names the specific record and the screen to go to.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **Opportunity** | A customer's request, recorded before any quotation |
| **Quotation (QT)** | The agreed price for a lane and vehicle type |
| **Delivery Order (DO)** | One specific delivery, created from an accepted quotation |
| **Trip** | A real vehicle movement: truck, driver, departure time |
| **Leg** | One segment of a trip, from one point to the next |
| **POD** | Proof of delivery: the delivery-note photo and the recipient's signature |
| **Milestone** | The six steps: check in, collect, depart, arrive, unload, delivered |
| **Cost** | What the trip costs the company |
| **Freight price** | What the customer pays |
| **Margin** | The gap between price and cost, as a percentage |
| **Acc code** | Cost classification code, issued by the accounts department |
| **Handover package** | The full data of a closed order, for accounts to raise documents |
| **Post to sales ledger** | Push a delivered order to accounts to create a sales order |
| **Empty return** | The leg back to the yard, carrying nothing |
| **Backlog** | Orders whose collection day has passed with no vehicle assigned |
