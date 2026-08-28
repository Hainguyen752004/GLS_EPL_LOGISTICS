# DO Trip Board Design

Goal: Redesign the Operations Planning DO screen so it reads like a polished SO/QT module and separates Delivery Orders from actual Trips.

Approved direction:
- Keep the top folder choice between Delivery Orders and Trip / Return / Backhaul.
- Make Delivery Orders the primary operations board.
- Add three internal DO tabs: Can giao, Dang giao, Hoan thanh.
- Sort each tab by operational date: pending earliest first, active by ETA/delivery date, completed newest first.
- In the DO table, expose only one row action: Xem. Detail/edit workflows happen inside the DO form.
- Keep backend workflow semantics intact: SO creates DO, DO is planned/dispatched, Trip is the real vehicle execution that may group/split DOs.

UI shape:
- Polished white module with a compact header, search, and status summary tabs.
- Table columns: Ma DO, SO tham chieu, Khach hang, Tuyen, Lay hang, Giao hang, Trang thai, Hanh dong.
- Route summary panel remains as supporting context, not the visual driver of the screen.
