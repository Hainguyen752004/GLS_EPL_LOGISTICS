# EPL Demo Stabilization Design

## Muc tieu

On dinh du an de trinh bay duoc luong nghiep vu that tu Bao gia den tai chinh, loai bo loi tieng Viet, nut chet, du lieu trung va cac hop dong frontend/backend khong dong nhat. Du lieu PostgreSQL hien tai co the xoa va tao lai bang bo seed chuan.

## Pham vi uu tien

1. Nguon frontend phai la UTF-8 dung, khong sua chu bang MutationObserver sau khi render.
2. Luong nghiep vu chinh phai chay that: Quotation -> Sales Order -> Delivery Order -> Trip -> Dispatch -> POD -> Actual Cost / Invoice.
3. Form hien truoc, du lieu tai sau voi trang thai loading tai cho; khong che ca man hinh khi API cham.
4. Cac thao tac ghi du lieu phai co schema, transaction va thong bao loi ro rang.
5. PostgreSQL duoc reset va seed mot bo du lieu lien ket day du de demo.

### Must-have truoc buoi demo

- Nguon UTF-8 sach va khong con hook sua encoding runtime.
- Golden path QT -> SO -> DO -> Trip -> Dispatch -> POD -> Actual Cost va AR Invoice chay qua API/CSDL that.
- Khong con nut chet, payload bi bo qua, trang thai DO duyet rieng hoac POD trung nguon tren golden path.
- Seed PostgreSQL co du lieu route/chang, tai nguyen, mot DO cho dieu phoi va mot DO da hoan thanh.

### Ngoai pham vi dot on dinh khan

- Khong viet lai toan bo giao dien hay tach het `app.js`/`index.html` thanh framework moi.
- Khong hoan thien tat ca tender, AP payment, settlement, GL reversal va AI; chi dam bao cac man nay khong pha golden path.
- Khong ho tro migration du lieu demo cu; schema duoc reset theo su dong y cua chu du an.

## Nguon su that nghiep vu

| Doi tuong | Trach nhiem | Trang thai chinh |
| --- | --- | --- |
| Quotation | De xuat thuong mai va gia ban | draft, approved |
| Sales Order | Cam ket ban hang tao tu bao gia | draft, confirmed |
| Delivery Order | Yeu cau giao hang tao tu SO | pending, in_transit, delivered, cancelled |
| DO analysis | Nhom hien thi suy ra tu han giao, incident va POD | near_late, pending, active, completed, incident |
| Freight Order | Nhu cau van tai noi bo dung de gom DO | draft, planned, dispatched, completed |
| Trip | Mot lan xe chay thuc te, co nhieu DO/chang | draft, planned, dispatched, in_transit, completed, cancelled |
| Dispatch | Gan xe, tai xe va lich cho Trip | planned, dispatched |
| POD | Bang chung giao theo DO, Trip, chang, xe va diem giao | completed, rejected |
| Actual Cost | Chi phi thuc te theo FO/Trip, gom dong chi phi tuy y | draft, submitted, approved, reversed |

DO khong co buoc duyet rieng. Transition hop le la `pending -> in_transit -> delivered`; `pending -> cancelled` chi khi chua co Trip dang chay. Incident la ban ghi rieng, khong phai lifecycle status. SO confirmed la dieu kien tao DO. Trip `dispatched` dau tien dua DO sang `in_transit`. DO nhieu Trip chi `delivered` khi moi diem giao bat buoc tren moi Trip khong cancelled co POD `completed`; POD `rejected` hoac giao mot phan giu DO o `in_transit` va tao incident. Huy mot Trip khong huy DO neu van con Trip hoat dong. "Gan tre" va "Gap su co" la nhom phan tich, khong ghi de trang thai vong doi.

## Luong du lieu

1. Bao gia duoc duyet va chuyen thanh mot SO.
2. SO duoc xac nhan; nguoi dung tao mot hoac nhieu DO tuy nhu cau giao.
3. Planner chon mot hoac nhieu DO de tao Trip. Tat ca DO phai cung mot route va khung gio tuong thich. Neu tat ca cung mot FO thi dung FO do; neu tat ca chua co FO thi command tao mot FO noi bo; tron DO da co FO voi DO chua co FO hoac nhieu FO khac nhau tra 409 va khong ghi gi. Command `POST /api/tms/trips/from-delivery-orders` tao FO neu can, Trip, bang lien ket DO va toan bo chang tu Master Data trong mot transaction. Idempotency key bat buoc; goi lai cung key/payload tra tai nguyen da tao, cung key/khac payload tra 409. Bat ky loi nao rollback FO, Trip, lien ket va chang.
4. Dispatcher gan xe, tai xe va khung gio cho Trip. He thong kiem tra trung lich, nang luc va tai trong.
5. Execution ghi su kien khoi hanh, den diem, giao hang, incident va GPS theo Trip/DO.
6. POD moi bat buoc day du `trip_id`, `leg_id`, `do_id`, `vehicle_id`, `stop_no`; khong chap nhan lineage NULL. CSDL giu unique `(trip_id, leg_id, do_id, vehicle_id, stop_no)`. Retry cung payload tra POD hien co; payload khac cung khoa tra 409. Khi du POD hop le, DO hoan thanh. Bang POD legacy chi duoc doc trong migration va khong con duoc ghi.
7. Chi phi phat sinh duoc them tu do thanh cac FreightChargeItem. Mot Trip chi co mot active cost. Tao/sua nhieu dong la transaction; mot dong sai rollback toan bo. Backend tinh Decimal subtotal/tax/total va ket qua phai doc lai dung trong session moi. Demo ket thuc tai Actual Cost va AR Invoice; AP/settlement sau demo khong nam trong critical path.

## API va tinh toan ven

- Dung Pydantic `extra="forbid"` cho create/update QT, SO, DO, Trip-from-DO, Dispatch, POD, Actual Cost, Route va tao/post AR Invoice. Loi theo envelope `{error:{code,message,fields,links}}`; cam truong la va tra HTTP 422. AR Invoice tao tu SO/DO da giao, tra `id`, `source_so_id`, `currency_code`, `subtotal`, `tax`, `total`, `status`; post hai lan cung idempotency key khong tao trung.
- Tao FO, Trip, lien ket DO va cac chang bang mot command transaction duy nhat.
- Cac transition trang thai nam o service, UI chi gui command.
- Tat ca datetime nghiep vu moi bat buoc ISO-8601 co offset; naive datetime tra 422. Luu PostgreSQL `timestamptz`, serialize UTC `Z`, hien thi Asia/Ho_Chi_Minh. Gan tre la `now <= due_at <= now + 24h`; qua tre la `due_at < now` va duoc danh dau rieng trong record.
- Tien dung Decimal/Numeric, khong dung Float cho du lieu moi.
- QT/SO/DO/Trip list tra `{items,total,page,page_size}` voi `page=1`, `page_size=50`, toi da 200, sap xep on dinh `created_at desc, id desc`; test qua ranh gioi trang.
- Route phai co it nhat mot chang, km huu han va khong am, thu tu lien tuc tu 1, diem den chang truoc khop diem di chang sau, diem dau/cuoi khop route, va tong km lech route khong qua `0.2 km`.

## Chien luoc UTF-8

- Chuyen cac chuoi mojibake co the phuc hoi ve Unicode dung.
- Cac chuoi da mat thanh dau hoi duoc thay bang ban dich Viet ngu xac dinh theo ngu canh.
- Xoa bo sua DOM runtime va bo bang thay the encoding.
- Giu mot test quet frontend/backend de cam marker mojibake va cum mat dau.
- Bo sung day du khoa i18n con thieu; van ban nghiep vu mac dinh la tieng Viet.

## UI phuc vu demo

- Moi module chi hien mot nhom nghiep vu tai mot thoi diem.
- Form/modal mo ngay voi skeleton/loading tai cac truong can API.
- Nut chi hien khi transition hop le; view-only khong co nut Luu/Duyet.
- Nut xem dung icon mat kem tooltip.
- Ghi chu nghiep vu nam trong modal rieng, khong do thanh cac dong dai trong trang.
- Giao hang chi theo doi Trip/DO dang van chuyen va POD; lap lich va canh bao tai nguyen nam o Dieu phoi & Thuc thi.

## Reset va seed

Reset schema PostgreSQL sau khi migration/model da on dinh. Seed tao it nhat hai chuoi lien ket: mot chuoi dang cho dieu phoi va mot chuoi dang van chuyen/co POD/chi phi. Moi route co chang va km hop le; moi ban ghi demo co ma de nhan biet.

## Kiem thu chap nhan

- Test source UTF-8 frontend/backend.
- Contract test QT -> SO -> DO khong co phe duyet DO.
- Transaction test tao Trip + chang va rollback khi mot chang sai.
- Test DO nhieu Trip/xe va POD theo tung lan giao.
- Test dong chi phi tuy y va tong Decimal.
- Test timezone gan tre/qua tre bang gio Viet Nam.
- Test request schema tu choi truong la, pagination va ordering.
- Test reset/migration/seed tren PostgreSQL rong va doc lai toan bo quan he.
- Test POD idempotency/conflict va Actual Cost commit/reload/rollback.
- Test route tu choi chặng am, dut chuoi va tong km lech hon 0.2 km.
- Golden path xac nhan AR Invoice tham chieu dung SO, tong Decimal dung va doc lai duoc tu API.
- Test strict UTF-8 va cam marker mojibake, dau hoi mat dau, MutationObserver/fixDocumentVietnamese.
- Full pytest, JavaScript syntax, i18n check va mot golden-path Playwright desktop co ket qua xac dinh; mobile chi smoke viewport trong dot khan.

## Thu tu trien khai

1. Tao test baseline va hop dong nghiep vu moi.
2. Sua model/service/API va migration/reset seed.
3. Noi frontend voi API that, bo cac payload/nhanh legacy.
4. Lam sach UTF-8 va i18n.
5. Don UI theo ranh gioi module.
6. Chay E2E, sua regression va chot kich ban thuyet trinh.
