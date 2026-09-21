# EPL Delivery Order — how the software currently works, and the business questions we need EPL to confirm

Dear Mr. Khampla, Mr. Ped and the colleagues in charge of transport operations at EPL,

We have built most of the transport management software following the *EPL Transport Report* Excel
workbook and the *Delivery Order circulation* process that EPL sent us. Before going further, we would
like to present **how the software currently works** and **ask you to confirm a number of business
points** that we did not want to decide on our own. Each question comes with options to tick; where
none of the options fits, please write your own answer.

---

## Part A. What the software does today

### A1. The steps a delivery order goes through

A delivery order (EPL calls it a *Delivery Order*, numbered like `T4-0428-08/EPL`) has six sections,
as on paper: I Truck information · II Transport information · III Fuel expenses · IV Travel expenses ·
V Repair expenses · VI Other expenses. Each section goes through the chain:

**Thabok warehouse ENTERS → Accounting VERIFIES → Accounting BOOKS → Cashier PAYS**

Who does which step is taken exactly from the *Duties* sheet in EPL's Excel:

| Section | Entered by | Verified by | Booked by | Paid by |
|---|---|---|---|---|
| I. Truck information | Thabok warehouse | Receipts/Payments Accountant, Vientiane | — | — |
| II. Customer and transport information | Thabok warehouse | Receipts/Payments Accountant, Vientiane | — | — |
| III. Fuel expenses | Thabok warehouse | Fuel Warehouse Accountant, VTE | Fuel Warehouse Accountant, VTE | Treasurer, VTE |
| IV. Travel expenses | Thabok warehouse | Expense Accountant, VTE | Expense Accountant, VTE | Thabok petty cash |
| V. Repair expenses | Thabok warehouse | Expense Accountant, VTE | Expense Accountant, VTE | Thabok petty cash |
| VI. Other expenses | Thabok warehouse | Expense Accountant, VTE | Expense Accountant, VTE | Thabok petty cash |
| Transport invoice | Revenue Accountant, VTE | — | Revenue Accountant, VTE | — |

Locking rule: the person who enters data can only edit while the section is still *waiting* or
*entered*. Once accounting has **verified** it, the section is locked; to change it, accounting must
**return** it to the warehouse. Only the administrator account (the Boss) can unlock.

### A2. What the Thabok warehouse cannot see

The Thabok warehouse **sees every EXPENSE**, because they are the ones spending and entering it: litres
and the price of fuel bought on the road, expressway fees, travel money, repair costs, the purchase price
of fuel and spare parts entering the store, weights, dates.

The Thabok warehouse **does not see SELLING money**: the freight rate the customer pays, the amount of a
trip, invoices and money collected from customers, the hire rate for sub-contracted trucks and the
deductions from truck owners, the profit per trip, and account codes. Those fields are visible only to
accounting, the cashiers and the Boss.

Our reason for drawing the line there: expenses are the warehouse's daily work and hiding them would stop
them working, while **the difference between what the customer pays and what the hired truck costs is the
company's margin** and is not needed at the warehouse. If you want it differently (the warehouse also
sees the freight rate, or on the contrary sees no money at all), please write it here: ......................

### A3. Fuel — two paths

1. **Refuelling at an EPL fuel depot:** the warehouse enters litres and the depot → the software prints
   a **fuel requisition slip with a QR code** that the driver takes to the depot → the depot keeper scans
   the code, issues the fuel, enters the actual litres → stock is reduced immediately, a stock issue note
   is created, booked 625/371 (EPL truck) or 4022/371 (hired truck).
2. **Refuelling on the road in Vietnam:** the driver reports on the phone (litres, station, unit price
   in VND) → the fuel warehouse accountant approves → it becomes an outside purchase line in section III,
   automatically converted to LAK at the exchange rate written on the order.

### A4. Road money — paid at the right time, as noted in EPL's Excel

| Item | Note in Excel | What the software does |
|---|---|---|
| Vietnam trip expenses, phone | Paid immediately when the driver departs | **Advance slip with QR code**; the cashier scans it to pay; until the money is received the driver cannot press *Depart* |
| Water money, ore trip money | Paid per trip together with salary | **Monthly driver settlement**: how much was advanced, how much was actually spent, positive = company pays extra, negative = driver returns |
| Lao shipping, Vietnamese shipping | Owed to suppliers, paid in batches | **Supplier tracking** screen, paid in batches, not counted in the driver settlement |
| Expressway | Paid by card, topped up 15 million kip each time | Currently recorded as an ordinary expense — **see question C6.1** |

### A5. Truck back, order locked, invoice, hired trucks

- Truck arrives → the warehouse presses *Truck arrived*, enters the **final weight**, actual return km
  and return date.
- Accounting presses **Lock order**: the software checks return km against the estimate, weight loss
  (red flag above 1.5 %), whether the ore slip is attached, and whether any section has expenses not yet
  verified. Once locked, the warehouse can no longer edit.
- **Only a locked order can be invoiced** (booked 1211/70) and only then can a receipt be recorded.
- **Hired trucks (sub-contractors):** the customer pays EPL at the contract rate; EPL pays the truck owner
  = hire rate × tonnes − 2 % management fee per order − 1 USD per tonne above 40 t − whatever EPL advanced
  for the trip; profit = customer payment − hire payment. The cashier presses *Pay truck owner* after the
  order is locked.

### A6. Document register for accounting

Every step that creates money or goods leaves **one numbered document** that accounting can pull:
fuel stock issue, spare parts stock issue, advance payment voucher, repair payment voucher, invoice,
receipt, driver settlement, payment to truck owner, stock receipt, supplier payment, and three documents
for **selling spare parts / fuel to outside parties** (sales stock issue, sales invoice, sales receipt).

---

## Part B. The most important question — which trip is one delivery order?

In EPL's Excel, **the same order number `T4-0428-08/EPL`** appears as:

- sheet *Delivery Order*: origin **Kasi** → destination **Kalo**;
- sheet *Transport Report*: origin **EPL yard** → destination **Kalo port**, with only the **arrival
  weight 42.06 t**; the departure weight is empty.

We understand the real flow to be: **truck goes from the yard to the mine to load ore → brings it back
to the yard/warehouse → then from the yard delivers it to the port**. Please confirm:

**B1.** One delivery order covers:
- [ ] the whole round: yard → mine → yard → port (one number for the whole round)
- [ ] only the **mine → yard** leg (collecting goods into the warehouse)
- [ ] only the **yard → port** leg (delivering to the customer)
- [ ] every time the truck leaves is one order, i.e. **two orders**: one collection order, one delivery order

**B2.** Does the ore **stay in the warehouse** before being delivered? Is it ever delivered by a
**different truck**?
- [ ] No, the truck that collects it also delivers it
- [ ] Yes, goods stay in the warehouse for several days and another truck delivers them
- [ ] Both, depending on the lot

**B3.** The customer invoice is based on:
- [ ] each **delivery trip to the port** (port weight × rate)
- [ ] each **round** mine → port
- [ ] a **monthly** total per customer

**B4.** If there are two orders, does the **collection** order (mine → yard) carry a freight rate, or only
expenses?
- [ ] No freight, only expenses are recorded
- [ ] A separate freight rate (the customer pays for the collection leg)

---

## Part C. Questions by section

### C1. User roles

- **C1.1** The software follows the *Duties* table exactly: the *Receipts/Payments Accountant, Vientiane*
  is one account (verifies sections I and II) and the *Expense Accountant, VTE* is another account
  (verifies and books sections IV–VI). Please confirm who holds each account:
  Receipts/Payments Accountant: .................. · Expense Accountant: ..................
- **C1.2** The written process mentions the *Thabok spare parts store* and the *Thabok repair team*.
  These are:
  - [ ] Separate people, need separate accounts — [ ] Also staff of the Thabok warehouse
- **C1.3** Can drivers use a phone (to receive slips, report refuelling, report breakdowns, share
  location)?
  - [ ] Yes, all drivers — [ ] Only some — [ ] No, the warehouse enters on their behalf

### C2. Section I — Truck information

- **C2.1** Who records the return date and the actual return km?
  - [ ] The warehouse, when the truck arrives — [ ] The driver, by phone — [ ] Accounting, from paper
- **C2.2** After accounting has verified section I, does the warehouse still need to change anything
  (besides return date and return km)?
  - [ ] No — [ ] Yes, for example: ..............................

### C3. Section II — Transport, weights, price

- **C3.1** Where does the **initial weight** come from?
  - [ ] The mine's scale, written on the ore slip handed over by the customer — [ ] EPL's yard scale when the truck returns to the yard — [ ] There is no initial weight
- **C3.2** Where does the **final weight** come from? (The invoice in Excel is based on *arrival weight
  41.3 t*.)
  - [ ] The port / delivery point scale — [ ] EPL's yard scale — [ ] Other: ...........
- **C3.3** Who brings the port weighbridge ticket back, and in what form?
  - [ ] The driver brings the paper to the yard — [ ] The driver sends a photo — [ ] The port sends it directly to accounting
- **C3.4** Is the **loss** (initial weight − final weight) deducted or penalised by the customer?
  - [ ] No, tracking only — [ ] Yes, above ....... % deducted at .......
- **C3.5** Where does the **freight rate** come from?
  - [ ] Customer contract, fixed per route (USD/tonne) — [ ] Agreed per trip — [ ] A price list that changes by season
- **C3.6** The rate is applied to:
  - [ ] Tonnes at destination — [ ] Tonnes at origin — [ ] Per trip (not per tonne)
- **C3.7** Who enters the ore slip number and date?
  - [ ] The warehouse, at loading (with a photo attached) — [ ] Accounting, on receiving the paper — [ ] Other

### C4. Hired trucks (sub-contractors)

- **C4.1** Who enters the hire rate (USD/tonne) for outside trucks?
  - [ ] The warehouse (who calls the truck) — [ ] Vientiane accounting (who signs with the owner) — [ ] The Boss
- **C4.2** The **2 % per order** management fee and the **1 USD/tonne above 40 t** overload charge are:
  - [ ] Fixed for all truck owners — [ ] Different per owner / contract
- **C4.3** Truck owners are paid:
  - [ ] Per order, right after the order is locked — [ ] Once at month end — [ ] In agreed batches
- **C4.4** Are the amounts EPL advances for a hired truck's trip (fuel from EPL depot, expressway, road
  money) **fully deducted** from the owner's payment, or does EPL bear some of them?
  - [ ] Fully deducted — [ ] EPL bears: ..............................

### C5. Section III — Fuel

- **C5.1** Drivers refuel in Vietnam and pay cash at the station; **may the driver enter the unit price**?
  - [ ] Yes, the driver enters litres + price + station, accounting verifies — [ ] No, the driver enters litres only, accounting enters the price
- **C5.2** How many EPL fuel depots are there? (The software currently has *Thabok depot* and *Vientiane
  depot*.)
  - [ ] Exactly two — [ ] Add: ..............................
- **C5.3** The fuel issue price is:
  - [ ] Latest purchase price — [ ] Average price — [ ] A fixed price set by accounting
- **C5.4** What is the **stock** account code? The written process says **37**, the Delivery Order sheet
  says **371**, the current chart of accounts has **137**.
  - [ ] 371 — [ ] 37 — [ ] 137 — [ ] Other: ......
- **C5.5** **Supplier** code: the process says **4021**, the sheet says **402**. Which one?
  - [ ] 402 — [ ] 4021 — [ ] Both, split by: ..............................
- **C5.6** What is the **cash / bank** account code for the credit side of payment and receipt vouchers?
  ..............

### C6. Section IV — Travel

- **C6.1** Expressway card: who holds the card, which fund tops it up, and should the software track the
  **card balance**?
  - [ ] Yes, track the balance and deduct each order from the card — [ ] No, record the expense as now
- **C6.2** Is the ore trip money (ເງີນຖ້ຽວແກ່ແຮ່) and water money calculated **per trip or per tonne**?
  - [ ] Fixed per trip — [ ] Per tonne — [ ] Per route

### C7. Section V — Repairs

- **C7.1** When a truck breaks down on the road, whom does the driver call?
  - [ ] Thabok warehouse — [ ] Thabok repair team — [ ] Both
- **C7.2** Who decides whether to repair with parts from stock or send the truck to an outside garage?
  - [ ] The warehouse — [ ] Thabok repair team — [ ] Accounting approves first
- **C7.3** Repairs **at the yard** while the truck is idle (maintenance) are recorded against which
  delivery order?
  - [ ] The most recent order — [ ] Not linked to an order, recorded per truck — [ ] A separate repair order

### C8. Section VI — Other expenses, and invoicing

- **C8.1** Examples of items that usually fall under section VI: ..............................
- **C8.2** Does a customer receive **one consolidated invoice** per month or **one invoice per order**?
  - [ ] One invoice per order — [ ] Monthly consolidated — [ ] Consolidated per shipment lot
- **C8.3** Customers pay by:
  - [ ] Bank transfer — [ ] Cash — [ ] Both; are there partial payments followed by the balance? [ ] Yes [ ] No

### C9. Screens

- **C9.1** The software is changing the delivery order screen to **tabs per section**: each role sees its
  own tab when it logs in, fields outside its authority are hidden or read-only, and the last tab is
  *Whole order* for viewing and printing. Is this suitable?
  - [ ] Suitable — [ ] Keep the long paper-like form — [ ] Other: ..............................
- **C9.2** Default language when the computer is opened at the yard: [ ] Lao — [ ] Vietnamese — [ ] Vietnamese + Lao

---

We will implement as far as your answers go; anything not yet answered stays as it currently runs.
Thank you, Mr. Khampla, Mr. Ped and the EPL team.
