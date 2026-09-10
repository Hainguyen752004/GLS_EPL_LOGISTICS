# Sổ thu–chi của lệnh giao hàng và Acc code

Tài liệu bàn giao cho bên **công nợ khách hàng** (anh Khang). Nó trả lời ba câu:
lấy dữ liệu ở đâu, mỗi dòng có gì, và Acc code đi từ đâu tới.

> **Tên gọi.** Trên giao diện và trong tài liệu này gọi là **Acc code** (mã tài khoản
> kế toán của bên công nợ). Trong cơ sở dữ liệu và gói JSON, cột/khoá gốc là
> `cost_index`; gói trả thêm khoá `acc_code` cùng giá trị để bên đọc dùng tên quen.

## 1. Lấy ở đâu

```
GET /api/delivery-orders/{do_id}/closeout
```

Gọi với principal API như mọi đường khác. Chỉ lệnh giao hàng đã **hoàn tất**
(`status = delivered`) mới có sổ đầy đủ; lệnh chưa hoàn tất vẫn trả sổ nhưng
phần chi là **tạm tính** theo công thức (`margin_is_provisional = true`).

Hai khoá cần đọc:

| Khoá | Là gì |
|---|---|
| `ledger_lines` | **Sổ thu–chi từng dòng.** Đây là thứ để lập phiếu. |
| `ledger_totals` | Tổng thu, tổng chi, lãi gộp, và hai cờ đối chiếu. |

Các khoá cũ vẫn còn (`configured_cost_lines`, `actual_cost_lines`,
`customer_charge_adjustments`, `commercials`) — sổ được gộp từ chúng, không thay
chúng.

### Trên màn hình thì bấm ở đâu

Khối **"Hồ sơ đã hoàn tất"** ở màn *Hoàn tất giao hàng* — chỗ chủ dự án chỉ đích
danh cho bên công nợ lấy số.

Trước đây khối đó chỉ hiện **năm con số tổng** (giá SO, khách trả thêm, giá cuối,
chi phí nội bộ, margin) trong khi cùng một lời gọi máy chủ đã trả `ledger_lines`
— và chỉ màn *Theo dõi* vẽ ra. Nghĩa là số cần cho phiếu thu/phiếu chi có sẵn
trong phong bì nhưng bị bỏ đi đúng ở màn người ta vào lấy.

Nay cả hai màn dùng **chung một bản vẽ** (`renderDeliveryOrderCloseout(data,
target)` — tham số `target` là ô đích). Hai màn không thể lệch nhau nữa, vì lệch
được thì phải sửa hai chỗ và sớm muộn quên một chỗ.

## 2. Mỗi dòng có gì

```json
{
  "kind": "chi",                       // "thu" | "chi"
  "cost_index": "…",                   // ACC CODE — rỗng nếu công thức chưa chọn
  "acc_code": "…",                     // cùng giá trị với cost_index
  "missing_cost_index": false,
  "charge_type": "fuel",               // mã nội bộ cố định của hệ (để nhóm)
  "name": "Chi phí xăng dầu /km",
  "planned_amount": 359835.0,          // chốt ban đầu (theo công thức, đã áp đơn giá của xe)
  "actual_amount": 361767.0,           // thực tế (theo bảng chi phí thực tế của chuyến)
  "variance": 1932.0,                  // thực tế − ban đầu
  "customer_extra": 0.0,               // chỉ dòng THU khách trả thêm mới khác 0
  "source": "cost_formula",            // xem bảng dưới
  "calculation": "57.6 km × 6.250 VND",
  "actual_cost_line_id": "…"           // id dòng trong freight_charge_items, nếu có
}
```

| `source` | Nghĩa |
|---|---|
| `cost_formula` | Chi theo công thức của **loại xe** |
| `vehicle` | Chi theo công thức, nhưng đơn giá là **ghi đè của chiếc xe** chạy chuyến ("phí của xe") |
| `actual_cost` | Khoản chi **phát sinh** lúc chốt, không có trong công thức |
| `quotation` | Thu: cước cơ sở theo **báo giá** |
| `customer_surcharge` | Thu: khoản **khách trả thêm** khi hoàn tất |

**Quy tắc cộng sổ:**

- `tong_thu` = cước cơ sở + Σ `customer_extra` của các dòng khách trả thêm.
  Phải bằng `commercials.final_selling_price` → cờ `khop_gia_cuoi`.
- `tong_chi` = Σ `actual_amount` của dòng `chi`. Phải bằng
  `commercials.cost_basis` (giá thành dùng tính lãi) → cờ `khop_gia_thanh`.
- Khi **đã có** bảng chi phí thực tế, dòng công thức không có dòng thực tế tương
  ứng được coi là **không phát sinh** (`actual_amount = 0`) — nó vẫn hiện để thấy
  khoản kế hoạch đã rơi đi đâu.
- `so_dong_thieu_ma` = số dòng chưa có Acc code. **Khác 0 nghĩa là công thức giá
  thành còn khoản mục chưa chọn mã** — chọn ở Dữ liệu gốc → Công thức giá thành.

## 3. Acc code đi từ đâu tới

```
Dữ liệu gốc → Công thức giá thành (theo loại xe)
   mỗi khoản mục có Ô CHỌN "Acc code"           terms[].cost_index
   (danh mục lấy từ API bên công nợ qua GET /api/acc-codes ← biến EPL_ACC_CODE_API)
        │  (ghi đè theo xe chỉ đổi ĐƠN GIÁ, mã kế thừa từ loại)
        ▼
Báo giá → tách Lệnh giao hàng
        ▼
Chốt chi phí thực tế của chuyến               freight_charge_items.cost_index
   (màn không gửi mã thì máy chủ tự tra từ công thức của xe chạy chuyến)
        ▼
Hoàn tất giao hàng — khoản khách trả thêm     delivery_order_charge_adjustments.cost_index
        ▼
Hồ sơ hoàn tất → ledger_lines[].cost_index
```

Hai bộ mã song song, có chủ ý: `charge_type` là mã cố định của hệ này (để máy
mình nhóm và tính); `cost_index` là mã của hệ kế toán bên ngoài, người dùng đặt
và có thể đổi. Không suy cái này từ cái kia ngoài một chỗ: khi dòng cũ chưa có
mã, hồ sơ tra lại từ công thức theo `charge_type` / tên; không tra được thì để
rỗng và bật `missing_cost_index` — **không bịa mã**.

## 4. Trạng thái dữ liệu hiện tại

- Mốc nâng cấp `044_ma_costindex` đã áp lên PostgreSQL thật (hai cột mới).
- Công thức giá thành **thật** trên PostgreSQL chưa gán mã nào → sổ của **5 DO
  đã hoàn tất** trong bộ demo hiện ra đủ dòng, đủ số, khớp cả hai phép đối chiếu,
  nhưng cột mã là "chưa gán mã". Nhập mã trên màn Công thức giá thành là đủ;
  không cần chạy lại gì. Đo ngày 09/09 trên DO đầu bộ: 6 dòng, thu 2.666.000,
  chi 1.731.767, `khop_gia_cuoi` và `khop_gia_thanh` đều đúng,
  `so_dong_thieu_ma = 6`.
- **Danh mục Acc code chờ API của bên công nợ.** Máy chủ nối sang API đó qua biến
  môi trường `EPL_ACC_CODE_API` (đặt trong `.env`, trả JSON `{"data":[{"code","name"}]}`
  hoặc một mảng chuỗi). Chưa đặt thì ô chọn ở trạng thái chờ, không có mã nào —
  hệ này **không tự đặt mã**.
