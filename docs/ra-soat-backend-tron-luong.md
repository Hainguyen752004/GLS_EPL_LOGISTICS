# Rà soát backend trọn luồng: Dữ liệu gốc → Báo giá → DO → Chuyến → Điều phối → Thực thi → Hoàn tất

Rà ngày 09/09/2026, trên mã nguồn đang chạy và đối chiếu với bộ 16 case demo vừa
đi lại end-to-end trên PostgreSQL (144 bước OK / 0 lỗi). Mỗi chặng ghi: **điểm
cuối** người dùng đi qua, **cửa kiểm** máy chủ chặn, **trạng thái** đổi ra sao,
và **chỗ còn hở**. Phần hở gom ở §9; 9.1, 9.2, 9.4, 9.5 đã sửa theo quyết định của anh.
§9.3 (nhánh SO) đã đóng **phía giao diện**: không còn đường tạo DO tay, DO sinh
tự động từ báo giá khi khách chấp nhận (xem §2 và §9.3).

Ký hiệu: ✅ có cửa kiểm, đã đi qua bằng dữ liệu thật · ⚠️ hở hoặc lệch, cần quyết.

---

## 1. Dữ liệu gốc (Master data)

| Đối tượng | Điểm cuối | Cửa kiểm hiện có | Nhận xét |
|---|---|---|---|
| Khách hàng | `POST/PUT /api/customers` | mã bắt buộc, không trùng | ✅ |
| Tuyến đường | `POST /api/routes` | mã bắt buộc; `distance_km` mặc định 0; `segments_json` phải là mảng | ✅ Tuyến 0 km bị chặn **ở bước báo giá** ("Tuyến chưa có số km"), không chặn lúc tạo — chấp nhận được vì tạo tuyến rồi nhập km sau là việc thường. |
| Loại xe | `POST /api/vehicle-types` | mã bắt buộc; sức chở 3 chiều (kg / m³ / pallet) | ✅ Ba chiều này là căn cứ cửa chặn tải trọng ở báo giá và điều phối. |
| Phương tiện | `POST /api/vehicles` | biển số bắt buộc; ba hạn pháp lý (đăng kiểm, bảo hiểm, bảo dưỡng) là chuỗi tự do | ✅ (sửa 09/09) `type` đổi tên → mã, chuỗi lạ → 422 kèm danh mục — xem §9.1 |
| Tài xế | `POST /api/drivers`, `POST /api/tms/driver-qualifications`, `POST /api/tms/scheduling/driver-shifts` | bằng lái có hiệu lực từ/đến; ca trực có `availability_kind` | ✅ Điều phối đòi cả ba: bằng lái đúng hạng còn hạn, ca làm việc phủ trọn chuyến, xe của ca khớp xe điều. |
| Công thức giá thành | `POST /api/cost-formulas` | mỗi loại xe + tiền tệ một công thức (`vehicle-type::<vt>::<cur>`); khoản mục có `kind` (chi/thu), hệ số nhân, **Acc code**; chống ghi đè chéo bằng `expected_updated_at` | ✅ Acc code là ô chọn, danh mục từ `GET /api/acc-codes` ← `EPL_ACC_CODE_API` (chưa nối → ô chờ). |
| Ghi đè theo xe | `PUT /api/vehicles/{id}/cost-overrides` | cấu phần phải có trong công thức loại; mỗi cấu phần một dòng | ✅ Chỉ lưu phần chênh; hồ sơ hoàn tất ghi `rate_source = vehicle`. |
| Kỳ kế toán, mã thuế, tiền tệ | `/api/master-data/*`, `/api/currencies*` | kỳ phải **mở** mới hạch toán được | ✅ Hoá đơn AR ở bước hoàn tất đòi kỳ mở bao trùm ngày ghi sổ. |

## 2. Báo giá (QT) — `services/bao_gia_service.py`

```
draft ──send──▶ sent ──accept──▶ accepted ──split──▶ split
  │              │  └─reject──▶ rejected           (N lệnh giao hàng)
  │              └── quá valid_to → expired (tính lúc đọc)
  └─send (biên < ngưỡng)──▶ pending_approval ──internal-approve──▶ sent
                                              └──return-to-draft──▶ draft
```

| Bước | Điểm cuối | Cửa kiểm |
|---|---|---|
| Xem trước giá | `POST /api/quotations/price-preview` | trả **danh sách việc còn thiếu** thay vì đoán: thiếu tuyến/km, thiếu loại xe, thiếu tải trọng, loại xe chưa có công thức, **loại xe không đủ năng lực** (nói rõ chiều nào vượt). Không tính ra giá cho lô vượt tải. ✅ |
| Tạo / sửa | `POST /api/quotations`, `PUT /api/quotations/{id}/items` | bảng hàng hoá phải ≥ 1 dòng, số lượng hợp lệ; khoá sửa khi đã tách (`LOCKED_RECORD`) ✅ |
| Gửi khách | `POST …/send` | (1) có hạn hiệu lực và chưa qua; (2) đủ giá thành + cước; (3) **không lỗ** (cước ≥ giá thành); (4) loại xe đủ tải; (5) **biên < 15 %** (hoặc ngưỡng riêng) → `pending_approval` thay vì `sent`. Cấp `quote_no` khi thật sự gửi. ✅ |
| Duyệt nội bộ | `POST …/internal-approve` | chỉ từ `pending_approval`; ghi người duyệt ✅ |
| **Khách chấp nhận → SINH DO** | `POST …/accept` | chỉ từ `sent`/`approved`; **hết hạn thì chặn**; và **sinh ngay N lệnh giao hàng trong cùng một giao dịch** — trả `do_ids`, báo giá sang `split`. Thân tuỳ chọn `{"dos": [...]}` để khai từng DO (giờ lấy, số seal); bỏ trống thì N = tổng số lượng ở bảng Hàng hoá (1 DO = 1 cont / 1 xe). ✅ |
| Khách từ chối | `POST …/reject` | không từ chối được báo giá đã tách ✅ |
| Gia hạn | `POST …/extend` | ngày mới không được ở quá khứ ✅ |
| Tách DO (đường trong) | `POST …/split` | chỉ từ `accepted`; phải có tuyến; ≥ 1 dòng; **giá khoá** `gia_moi_chuyen` > 0; **một giao dịch** cho cả N DO. DO kế thừa `quotation_id`, `route_id`, `unit_price` (giá khoá), khung giờ, chia đều kg/m³/pallet, `seal_no` theo dòng. ✅ Nay `accept` gọi thẳng hàm này, nên giao diện **không còn bước tách tay** — điểm cuối giữ lại để tách tiếp khi khách tăng hàng. |

Chứng từ đính kèm (`POST …/attachments`) khoá khi đã tách. Lịch sử phiên bản
(`quotation_versions`) ghi ở mỗi lần gửi.

## 3. Lệnh giao hàng (DO) — `services/workflow_service.py`

```
pending ──dispatch (qua Trip)──▶ in_transit ──arrival──▶ arrived ──complete-delivery──▶ delivered
   └──status: cancelled                       └────────complete-delivery────────────▶ delivered
```

| Bước | Điểm cuối | Cửa kiểm |
|---|---|---|
| Sửa DO | `PUT /api/delivery-orders/{id}` | **chặn đổi tuyến** với DO sinh từ báo giá (giá khoá theo tuyến cũ); muốn đổi thì sửa báo giá rồi tách lại ✅ |
| Đổi trạng thái tay | `PUT …/status` | bảng chuyển hợp lệ: `pending→{in_transit, cancelled}`, `in_transit→{arrived, delivered}`, `arrived→{delivered}`; `in_transit/arrived` đòi đã có xe + tài xế; `cancelled` chặn khi còn chuyến đang chạy; `delivered` đòi có POD ✅ |
| Xoá DO | `DELETE …` | chỉ khi `pending` ✅ |
| ~~Tạo DO tay~~ | `POST /api/delivery-orders` | **đòi Đơn hàng (SO) đã xác nhận**. Giao diện **không còn gọi**: form DO chỉ còn để XEM, nhánh tạo mới dừng lại và chỉ người dùng sang màn Báo giá. DO là thứ báo giá sinh ra. | ⚠️ điểm cuối còn sống — §9.3 |
| ~~Điều phối lẻ (cũ)~~ | `PUT /api/delivery-orders/{id}/dispatch` | **ĐÃ ĐÓNG PHẦN GHI (10/09).** Trả `DISPATCH_VIA_TRIP_REQUIRED` kèm hai bước phải làm. Thêm cửa không chữa được: đường này không lập Chuyến nên DO đi qua nó không có đường ra, và xe cùng tổ lái bị giữ vĩnh viễn. Xem §9.7 | ✅ |
| Huỷ chuyến | `POST /api/tms/trips/{id}/cancel` | **MỚI (10/09).** Lý do bắt buộc; `expected_version`; chặn khi chuyến đã hoàn tất/quyết toán hoặc đã có POD. Trả DO về `pending`, xe và tổ lái về sẵn sàng, phân công và chặng sang `cancelled`. Xem §9.8 | ✅ |

## 4. Chuyến (Trip) — `services/tms_trip_service.py`

| Bước | Điểm cuối | Cửa kiểm |
|---|---|---|
| Lập chuyến từ DO | `POST /api/tms/trips/from-delivery-orders` | mọi DO phải `pending`; **cùng một tuyến Master Data**; tuyến phải có chặng hợp lệ; loại chuyến (`one_way / round_trip / backhaul / multi_stop`) và mục đích chặng về khớp nhau; chặng về phải bắt đầu ở điểm kết của chặng đi; DO chiều về không trùng chiều đi; idempotent theo mã Trip ✅ |
| Kết quả | | tạo `freight_orders` (1 FO / chuyến, cửa sổ giờ lấy từ DO), `transport_trip_legs` (ETA theo km × tốc độ + dwell), `trip_delivery_orders` (thành viên). Chặng chỉ tồn tại cho DO là thành viên (khoá ngoại kép) ✅ |

Luật "1 DO = 1 cont (1 xe) = 1 chuyến" là **luật của bộ gieo và bản thiết kế**,
máy chủ **cho phép** nhiều DO cùng tuyến trong một chuyến (multi-stop). Chấp nhận.

## 5. Điều phối — `services/tms_dispatch_service.dispatch_trip`

`PUT /api/tms/trips/{id}/dispatch` — cửa kiểm theo đúng thứ tự mã nguồn:

1. `expected_version` khớp (chống hai người điều cùng lúc) ✅
2. Chuyến ở `planned` ✅
3. Xe, tài xế, phụ xe **có thật** trong dữ liệu gốc ✅
4. Xe `Sẵn sàng` (đúng một chuỗi trạng thái) ✅
5. Khoảng điều phối hợp lệ và **nằm trong cửa sổ giờ của Freight Order** ✅
6. Tổ lái không có ca **nghỉ / không sẵn sàng** trùng giờ ✅
7. Tổ lái có **ca làm việc phủ trọn** khoảng điều phối ✅
8. Ca của tài xế gắn xe khác → chặn; xe đang thuộc ca của tài xế khác → chặn ✅
9. **Ba hạn pháp lý của xe** còn hạn ở ngày chạy ✅
10. **Bằng lái** đang hiệu lực, đúng hạng, phủ ngày chạy ✅
11. Không trùng phân công đang hoạt động (xe hoặc người) ✅
12. Mọi DO trong chuyến còn `pending` ✅
13. **Hàng đếm theo kiện: Packing List đã quét đủ (`loaded`)**; hàng nguyên khối: có **số niêm phong**; hàng rời: có khối lượng ✅ (`packing_control_policy`)

Kết quả: `resource_assignments` (active), xe → "Đang thực hiện TRIP-…", tài xế →
đang chạy, DO → `in_transit`, FO → `dispatched`, mở `vehicle_tracking`.

## 6. Thực thi — `services/tms_execution_service.py`

`POST /api/tms/freight-orders/{fo}/events`, chuỗi bắt buộc
`check_in → pickup → departure → arrival → unloading → delivered` (+ sự kiện
ngoại lệ). Mỗi mốc: khoá idempotency bắt buộc, `expected_version` của FO, toạ
độ/tốc độ hợp lệ, sự kiện từ thiết bị phải có mã thiết bị, `delivered` phải kèm
chứng từ POD hợp lệ. Mốc được **gắn vào chuyến đang chạy mới nhất** của FO.

- `arrival` → DO sang `arrived` ("Đã đến nơi — chờ POD"), tra qua **cả** liên
  kết đơn cũ **và** `trip_delivery_orders` ✅ (sửa hôm nay — trước chỉ tra đường
  đơn cũ nên luồng thật không bao giờ tới `arrived`).
- `delivered` **không** tự đóng DO — đóng là việc của bước hoàn tất (cần POD,
  chữ ký, chốt giá trong một giao dịch) ✅ đúng.

Tháp kiểm soát (`GET /api/tracking/control-tower`) gom GPS 4 trạng thái
(mới / mô phỏng theo tuyến / cũ / chưa có), sự cố mở, POD chờ.

## 7. Hoàn tất giao hàng — `services/delivery_completion_service.complete_delivery`

`POST /api/delivery-orders/{id}/complete-delivery` (multipart: payload + tệp POD + ảnh ký). Một giao dịch:

1. Khoá idempotency; nội dung khác cùng khoá → 409 ✅
2. DO ở `in_transit` **hoặc `arrived`** ✅ (sửa hôm nay — trước chỉ nhận `in_transit`, nên sau khi `arrival` chạy đúng thì 5/5 case vỡ ở đây)
3. Trip thuộc DO (`trip_delivery_orders`) và đang `dispatched/in_transit` ✅
4. Đồng bộ Packing List → `dispatched/delivered` ✅
5. **POD cho đúng mọi chặng giao của DO**, mỗi chặng có tệp POD (≤10 MB, JPG/PNG/PDF) + ảnh chữ ký; xe trên POD khớp xe điều; kết quả giao chỉ `delivered_full` (giao thiếu / từ chối đi đường sự cố) ✅
6. Khoản khách trả thêm (`charge_adjustments`) → `delivery_order_charge_adjustments`, mang **Acc code** ✅
7. Chốt giá: `base_selling_price_snapshot` (từ giá khoá của DO/báo giá) + phụ phí = `final_selling_price` → `delivery_order_closeouts` ✅
8. DO → `delivered` ("Đã hoàn tất"); chặng → `completed`; chuyến → `completed` khi không còn chặng/DO mở; FO → `delivered`; phân công → `completed`; **giải phóng xe & tổ lái** (chỉ khi họ không còn DO đang chạy khác) ✅
9. **Hoá đơn AR** hạch toán ngay (`post_ar_invoice`) — đòi kỳ kế toán mở, mã thuế; bút toán 131/511 ✅

Sau đó, tách rời và có **quy tắc bốn mắt**:

- Chi phí thực tế: `PUT /api/tms/finance/trips/{id}/actual-cost` (chuyến phải `completed`; mỗi dòng gốc/thực tế/vượt, `charge_type`, **Acc code** tự tra từ công thức của xe) → `submit` → `approve` (**người tạo không được duyệt**) ✅
- Hồ sơ hoàn tất `GET /api/delivery-orders/{id}/closeout`: **sổ thu–chi từng dòng** (`ledger_lines`) + hai phép đối chiếu (`khop_gia_cuoi`, `khop_gia_thanh`); `actual_cost_total` là chi phí thực (không còn là phần vượt) ✅
- Báo cáo doanh thu chỉ cộng **giá thành đã duyệt** ✅

## 8. Những chỗ đã đo và đúng

- Toàn bộ 16 case đi qua đúng cửa ở trên, không có bước nào đi tắt; 3 lỗi luồng
  thật lộ ra khi đi lại đã sửa gốc, có bài kiểm (arrival → arrived; hoàn tất nhận
  `arrived`; tệp duyệt trỏ nhầm `.env.sqlite`).
- Schema PostgreSQL thật khớp `models.py` về bảng và ràng buộc trạng thái (bài
  `test_schema_postgres_khop_voi_models`); 36 cột thời gian khai lệch múi giờ đã
  ghim danh sách, chờ quyết.

## 9. Chỗ hở — cần anh quyết, chưa sửa

### 9.1 Phương tiện: `type` là chữ tự do — **ĐÃ SỬA**
`POST /api/vehicles` nay đổi TÊN loại xe về MÃ, và trả 422 `VEHICLE_TYPE_UNKNOWN`
kèm danh mục khi chuỗi không khớp gì (danh mục trống thì cho qua). Bài kiểm:
`test_xe_phai_co_loai_hop_le.py`.

`POST /api/vehicles` nhận `type` bất kỳ, không kiểm có trong `vehicle_types`.
Hậu quả đã gặp thật: hai xe ghi `"Container 20FT"` (tên) thay vì `DEMO-VT-20FT`
(mã) → điều phối không so được năng lực, giá thành không tìm được công thức, và
bộ gieo phải có một bước "chuẩn lại" chỉ để sửa việc này. **Đề nghị:** chặn ở
`POST /api/vehicles` — `type` phải là mã loại xe có thật (chấp nhận nhập tên
rồi tự đổi về mã). Sửa nhỏ, một chỗ.

### 9.2 Đường điều phối tắt: `PUT /api/delivery-orders/{id}/dispatch` — **ĐÃ ĐÓNG**
Hai việc: (a) nút *Lưu điều phối* trong hộp đổi xe/tổ lái đi qua điều phối
**chuyến** (`PUT /api/tms/trips/{id}/dispatch`), chuyến chưa `planned` thì nói rõ
và không làm gì; (b) điểm cuối cũ nay có **đủ cửa** như điều phối chuyến (hạn
pháp lý xe, bằng lái, ca làm việc, Packing List / niêm phong) và **từ chối** DO
đã có chuyến (`DO_HAS_TRIP`). Bài kiểm: `test_do_lifecycle_contract.py::
test_duong_dieu_phoi_le_KHONG_con_la_duong_tat` chốt từng cửa theo thứ tự.

Đường này đưa DO thẳng sang `in_transit` với xe/tài xế mà **bỏ qua** 9 trong 13
cửa của điều phối chuẩn (hạn pháp lý xe, bằng lái, ca trực, Packing List, niêm
phong, cửa sổ giờ, trùng phân công…) và **không tạo Trip / Freight Order /
Resource Assignment**. DO đi đường này **không hoàn tất được** (bước hoàn tất
đòi Trip) và xe không bao giờ được giải phóng đúng cách. Giao diện còn **một chỗ
gọi**: nút *đổi xe / tổ lái* trên màn Điều phối (`applyDispatchResourceChange`).
**Đề nghị:** đổi nút đó sang đường chuẩn (hoặc chặn đổi khi chuyến đã điều, bắt
huỷ chuyến rồi điều lại), rồi **tắt** điểm cuối này.

### 9.3 Nhánh Đơn hàng (SO) — **ĐÃ ĐÓNG PHÍA GIAO DIỆN (09/09)**
Chủ dự án chốt: *"cái DO kế thừa từ cái QT nhé kiểu gen tự động khi mà QT được
duyệt hết"*. Đã làm:

* `POST /api/quotations/{id}/accept` **sinh DO ngay** trong cùng giao dịch
  (`bao_gia_service.chap_nhan_va_sinh_do`). Hoặc cả hai, hoặc không gì — một
  báo giá `accepted` mà không có DO chính là trạng thái cũ mà anh muốn bỏ.
* Form "Tạo lệnh giao hàng" **không tạo mới nữa**: nhánh tạo dừng lại, không
  gửi `so_id`; ô tham chiếu đổi nhãn thành **"Báo giá gốc (QT)"** và chỉ đọc;
  nút đầu trang đổi thành *"Lệnh giao hàng sinh từ báo giá →"* và dẫn sang màn
  Báo giá. `createDOFromSO` cũng dẫn về đó.
* Mục 6 của phiếu báo giá đổi từ "Tách lệnh giao hàng" sang **"Lệnh giao hàng
  (DO) sinh từ báo giá"**; nút ghi nhận chấp nhận hỏi lại trước khi sinh.

**Còn lại (chưa chốt):** `POST /api/delivery-orders` và 9 điểm cuối
`/api/sales-orders*` vẫn sống ở tầng máy chủ — 24 tệp kiểm / 98 chỗ gọi dựa vào
chúng. Không hại dữ liệu (SO không sinh từ luồng mới, `so_id` của DO mới là
rỗng). **Đề nghị:** tắt hẳn khi có thời gian gỡ phần kiểm đó.

Bài kiểm: `test_chap_nhan_bao_gia_sinh_do.py` (máy chủ),
`tests/do-sinh-tu-bao-gia.test.js` (giao diện).

### 9.7 Điều phối lẻ tạo một trạng thái không có đường ra — **ĐÃ ĐÓNG (10/09)**
`PUT /api/delivery-orders/{id}/dispatch` đưa DO sang `in_transit` **mà không lập
Chuyến và không tạo phân công**. Hậu quả đo được: nộp POD trả
`POD_LINEAGE_INVALID`; đổi sang đã giao trả `ATOMIC_COMPLETION_REQUIRED`; bảng
chuyển trạng thái không cho `in_transit` sang huỷ; lập chuyến để chữa trả
`DELIVERY_ORDER_NOT_PENDING`; ghi mốc đòi một phân công đang mở. Và mọi đường
giải phóng xe đều đi qua chuyến, nên **xe và cả hai tài xế bị giữ vĩnh viễn** —
không có API nào đặt lại `status` của xe.

Đã đóng phần ghi. Mười bảy chỗ gọi trong bộ kiểm chuyển sang
`conftest.dieu_phoi_qua_chuyen`. Bài kiểm mới:
`test_duong_dieu_phoi_le_DA_DONG_PHAN_GHI` và
`test_dieu_phoi_chuyen_co_DU_CUA_theo_dung_thu_tu`.

### 9.8 Không có đường huỷ chuyến — **ĐÃ THÊM (10/09)**
Không một chỗ nào trong mã ghi trạng thái huỷ cho chuyến, nên nhánh `cancelled`
của cửa chặn huỷ DO **không bao giờ tới được**: khách huỷ sau khi đã lập chuyến
thì huỷ DO bị 409 và màn Chuyến không có nút nào — đường duy nhất còn lại là xoá
cứng DO trong khi `trip_delivery_orders` vẫn trỏ vào nó.

`POST /api/tms/trips/{id}/cancel` trả DO về `pending`, giải phóng xe và tổ lái
qua `release_resources`, đóng phân công và chặng. Bài kiểm:
`test_huy_chuyen_van_tai.py`.

### 9.9 Cửa điều phối quyết theo nhãn tiếng Việt — **ĐÃ CHUYỂN SANG LỊCH (10/09)**
Thêm `services/lich_xe.py`: một chỗ duy nhất trả lời "xe / tổ lái có rảnh trong
khung giờ này không", đọc phân công đang mở, lịch xưởng và ca làm việc. Bỏ hai
cửa `vehicle.status != "Sẵn sàng"` và phép so nhãn rảnh trong `require_crew`.
Nhãn vẫn được ghi cho màn hình, nhưng không còn quyết định gì.

### 9.6 DO đã huỷ vẫn nằm trong hàng đợi điều phối — **ĐÃ SỬA (09/09)**
Đo được trên bộ demo thật: một DO khách đã huỷ hiện ở tab **"Gần trễ"** của màn
Lệnh giao hàng. `_delivery_order_analysis_record` coi mọi trạng thái không phải
đã-giao / đang-chạy là `pending` rồi so hạn lấy/giao với hiện tại — nên một đơn
đã chết vẫn báo sắp trễ, và hàng "cần xử lý" bị làm bẩn.

Đã thêm rổ riêng `cancelled` ("Đã huỷ"), xếp **cuối** thang cấp bách, ở cả hai
phía: `DO_ANALYSIS_STAGE` / `DO_STAGE_URGENCY` (máy chủ) và `DoBoard.BUCKETS`
(bản soi gương ở trình duyệt). Sự cố vẫn xét **trước** huỷ: một DO đã huỷ mà còn
sự cố chưa đóng thì sự cố đó vẫn phải có người đóng lại. Bài kiểm:
`test_do_da_huy_khong_nam_hang_doi.py`, `tests/do-board.test.js`.

### 9.4 Duyệt báo giá đường cũ không qua cửa biên mỏng — **ĐÃ SỬA**
`approve_quotation` (dùng bởi `PUT …/approve` và `PUT …/status`) nay rẽ sang
`pending_approval` khi biên dưới ngưỡng, y như "Gửi khách". Bài kiểm:
`test_bao_gia_duong_cu_cung_cua_voi_duong_moi.py`.

`PUT /api/quotations/{id}/approve` (và `PUT …/status`) duyệt thẳng `draft/sent`
→ `approved`, có kiểm lỗ/hết hạn/tải trọng nhưng **không** rẽ sang
`pending_approval` khi biên < 15 %. `accept` nhận cả `approved`, nên một báo giá
biên 5 % có thể được khách chấp nhận và tách DO mà không ai duyệt nội bộ. Giao
diện **không còn** nút nào gọi (hàm cũ `approveQuotation` đã mất nút). **Đề nghị:**
tắt hai điểm cuối này, hoặc cho chúng gọi cùng `gui_khach`.

### 9.5 Sửa báo giá đã gửi không buộc gửi lại — **ĐÃ SỬA**
Sửa báo giá đang `sent` → về `draft`, xoá `sent_at`, ghi nhật ký
`QUOTATION_REOPENED_AFTER_SENT`; phải gửi lại (đi lại cửa lỗ/biên mỏng),
`quote_no` giữ nguyên. Bài kiểm cùng tệp trên.

`PUT /api/quotations/{id}` cho sửa giá của báo giá đang `sent` (khách đã cầm
bản cũ) — tăng `version` nhưng không ghi phiên bản gửi mới, không đổi `quote_no`,
không về `draft`. **Đề nghị:** sửa khi `sent` thì đưa về `draft` và buộc gửi lại
(có phiên bản mới), để bản khách cầm và bản trong hệ luôn là một.

### 9.6 Nhỏ, ghi để biết
- Tuyến `distance_km = 0` tạo được; chặn ở báo giá là đủ.
- Máy chủ cho nhiều DO cùng tuyến trong một chuyến; bộ gieo cố ý một DO một chuyến.
- 36 cột thời gian `models.py` khai trần trong khi PostgreSQL là `timestamptz`
  (đã ghim danh sách trong bài kiểm) — sửa khai báo, không cần mốc nâng cấp.
