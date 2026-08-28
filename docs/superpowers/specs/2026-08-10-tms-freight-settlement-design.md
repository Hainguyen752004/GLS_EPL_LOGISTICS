# TMS Core 5 – Actual Charges, AP và Freight Settlement

## Mục tiêu

Hoàn thiện tài chính vận tải sau giao hàng theo chuỗi `Freight Order delivered → cước thực tế → chi phí carrier → đối soát → AP Invoice → settlement → journal/report`, tái sử dụng sổ kế toán hiện có và không thay thế AR Invoice.

## Nguyên tắc

- Tiền dùng `Numeric/Decimal`, không dùng `float`; mỗi chứng từ chụp lại currency, exchange rate và tax rate.
- Chỉ Freight Order `delivered` mới được chốt chi phí và lập AP.
- Bản ghi đã duyệt/đã hạch toán không sửa hoặc xóa; điều chỉnh bằng reversal/credit note liên kết chứng từ gốc.
- Mọi command có version, idempotency, actor/IP và AuditLog.
- Thiếu carrier, bảng giá, tỷ giá, thuế hoặc account mapping trả lỗi tiếng Việt kèm navigation target tới Master Data.
- Functional currency mặc định lấy từ cấu hình (`VND`), không suy ra từ giao diện. Tỷ giá có hướng rõ ràng: số đơn vị functional currency cho một đơn vị transaction currency.

## Mô hình dữ liệu

### FreightActualCost

Mỗi Freight Order chỉ có một cost active; `version` là optimistic-lock counter, không phải revision identity. Lưu currency/exchange-rate snapshot, planned distance, actual GPS distance, subtotal, tax, total, status `draft|submitted|approved|reversed` và audit metadata. Cost mới sau reversal liên kết cost bị đảo bằng `reversal_of_cost_id`; cấm reversal-of-reversal và chu kỳ.

### FreightChargeItem

Các dòng cước/chi phí: `fuel`, `toll`, `driver`, `waiting`, `loading`, `unloading`, `carrier_base`, `surcharge`, `discount`, `other`. Mỗi dòng lưu quantity, unit price, tax rate, amount trước thuế, thuế và tổng. Discount là loại duy nhất được phép âm; các loại còn lại không âm.

### FreightCostDocument

Metadata chứng từ carrier: URL, tên file, MIME, checksum, số hóa đơn nhà cung cấp, ngày chứng từ. Không lưu blob trong PostgreSQL.

### APInvoice và APInvoiceLine

AP header liên kết carrier và FreightActualCost, có số hóa đơn vendor chuẩn hóa, ngày hóa đơn, hạn thanh toán, currency/rate/tax snapshot, subtotal/tax/total theo transaction và functional currency, status `draft|submitted|approved|posted|partially_paid|paid|reversed`, version và reversal link. Dòng AP chụp charge item, tax code và account mapping. Unique `(carrier_id, normalized_vendor_invoice_no, document_kind)`; một AP active cho mỗi cost bằng partial unique index. Reversal/credit memo có document kind riêng nhưng chỉ một reversal cho một chứng từ gốc.

### FreightSettlement và SettlementPayment

Settlement liên kết AP, lưu kỳ đối soát, approved amount, paid amount, remaining amount, status và version; constraint `0 <= paid <= approved` và `remaining = approved-paid`. Payment chỉ ghi thêm, amount dương, có currency/rate snapshot, posting date/period, bank/cash mapping, phương thức, reference và thời điểm thanh toán. Payment có void/reversal một-một; không sửa/xóa payment đã post.

### Journal source evolution

Migration `007` nâng cấp JournalBatch từ AR-only sang nguồn đa loại: thêm `source_type` (`ar_invoice|ap_invoice|ap_payment|ap_reversal|payment_reversal`) và `source_id`, backfill batch cũ thành `ar_invoice`, sau đó bỏ ràng buộc bắt buộc/unique đơn lẻ trên `invoice_id` nhưng giữ FK nullable để tương thích. Unique `(source_type, source_id)` bảo đảm exactly-once. Check yêu cầu AR batch có `invoice_id`, nguồn AP/payment không có `invoice_id`. JournalLine bổ sung transaction amount/currency/rate và functional debit/credit; tổng functional debit phải bằng credit trước khi post.

## Luồng nghiệp vụ

1. Tạo cost draft cho Freight Order đã delivered.
2. Thêm charge items và chứng từ; service tính lại tổng hoàn toàn ở server.
3. Submit cost; đối chiếu planned distance với GPS actual distance và ghi variance.
4. Approve cost theo principal có quyền finance approver; khóa cost/items/documents.
5. Tạo AP draft từ snapshot cost đã approved; một active AP cho mỗi cost.
6. Submit/approve/post AP; kiểm tra accounting period mở, tax/FX/account mappings đầy đủ.
7. Khi post, tạo JournalBatch/JournalLine cân bằng: debit expense/tax input, credit accounts payable. Không ghi trực tiếp GL rời rạc.
8. Tạo settlement và ghi nhiều payment. Mỗi payment post JournalBatch `Dr Accounts Payable / Cr Bank|Cash`; chênh lệch tỷ giá realized post vào FX gain/loss mapping. Trạng thái tự chuyển `partially_paid|paid`; overpayment bị từ chối.
9. Void/reverse payment tạo payment đối ứng và journal đảo, mở lại payable tương ứng.
10. Reversal AP chỉ cho phép AP `posted` chưa có payment active; tạo credit memo âm và reversing journal trong kỳ mở. AP đã partial/full paid phải reverse payment trước. Cost không được reverse khi còn AP không reversed.

## Đối soát và khoảng cách

Actual distance được tính từ TransportEvent có tọa độ hợp lệ bằng Haversine, sắp `event_time, recorded_at, id`; bỏ điểm trùng liên tiếp và không dùng dữ liệu ngoài biên. Cần ít nhất hai điểm, nếu thiếu trả trạng thái `insufficient_gps_data`. Client không được tự khai tổng khoảng cách. Kết quả Float GPS được chuyển sang Decimal và làm tròn 3 chữ số km. Variance phần trăm là null khi planned distance bằng 0. Ngưỡng cảnh báo lấy từ Master Data, không hardcode.

## Chính sách Decimal, thuế và FX

- Money lưu `Numeric(24,6)` để không mất precision; quantity `Numeric(18,4)`; tax/rate `Numeric(18,8)`; distance `Numeric(18,3)`. Giá trị hiển thị/posting được quantize theo `CurrencyDefinition.minor_units` (VND/JPY=0, USD=2, KWD=3) bằng `ROUND_HALF_UP`.
- Tính amount từng line = quantity × unit price rồi quantize theo minor unit; thuế tính và quantize trên line. Header là tổng line, không tính lại thuế trên subtotal. Nếu tổng document-level yêu cầu phân bổ residual do inclusive tax/FX, phân bổ từng minor unit vào line có absolute amount lớn nhất (tie-break bằng line id) và lưu `rounding_adjustment`; journal luôn cân bằng sau phân bổ.
- Tax mode của line là `exclusive|inclusive|exempt`; inclusive tách net/tax bằng tax rate. Cho phép nhiều tax code/rate trên cùng chứng từ.
- Functional amount = transaction amount × exchange-rate snapshot, quantize theo minor units của functional currency. Rate lấy từ `CurrencyRateHistory(currency_code, functional_currency, rate_date, rate, source)`; `Currency.exchange_rate Float` cũ không dùng cho posting và giữ chỉ để tương thích UI.
- Trong Core 5, payment bắt buộc cùng `currency_code` với AP; cross-currency payment ngoài phạm vi. Settlement `approved_amount`, `paid_amount`, `remaining_amount` đều định danh bằng AP currency. Payment rate tại posting date chỉ chuyển cùng transaction currency sang functional currency. Realized FX = functional amount của phần AP được thanh toán theo AP rate trừ functional payment theo payment rate, sau quantization/residual allocation. Overpayment so sánh amount trong AP currency.

## Phân quyền và bảo mật

- Các API tài chính yêu cầu principal đã xác thực.
- Middleware principal phải được resolve sang `User.role_id → Role.permissions`; permissions lưu dạng danh sách allowlist. Matrix: create/edit draft=`finance_creator`, approve=`finance_approver`, post/reverse=`finance_poster`, payment/void=`finance_payment`, read=`finance_read`. Thiếu user/role/permission fail closed 403.
- Separation-of-duties cấu hình trong `FinanceControlConfig`, mặc định bật: creator không được approve/post cùng chứng từ; approver không được post nếu policy yêu cầu ba người.
- Token/DB exception/SQL không xuất hiện trong response hoặc log nghiệp vụ.
- Input có schema, giới hạn độ dài/số dòng/chứng từ và từ chối NaN/Infinity.
- Scope hiện tại là single-tenant; không tuyên bố tenant isolation khi chưa có tenant model.

## Master Data bổ sung

- `CurrencyRateHistory` lưu lịch sử tỷ giá Numeric theo ngày/nguồn.
- `CurrencyDefinition` lưu currency code, `minor_units` (0..6) và trạng thái; bắt buộc tồn tại cho transaction và functional currency.
- `TaxCode` lưu code, rate, mode, hiệu lực.
- `FinanceControlConfig` lưu functional currency, SOD policy và distance variance threshold.
- `AccountMapping` dùng các key bắt buộc: carrier expense theo charge type, input tax, accounts payable, bank/cash, realized FX gain/loss.
- Carrier lấy từ Tender đã `awarded` và snapshot tên/tax code vào AP. Internal fleet không có tender phải chọn carrier nội bộ đã cấu hình; không tự sinh vendor. Carrier phải active. Accepted TenderOffer có thể seed `carrier_base` nhưng actual charge vẫn cần submit/approve.

## API

- Cost: list/get/create, add item/document, submit, approve, reverse.
- AP: list/get/create-from-cost, submit, approve, post, reverse.
- Settlement: create/list/get, add payment.
- Dashboard: planned/actual/variance, payable, paid, outstanding theo Freight Order/carrier/kỳ.
- Draft cho phép thêm/sửa/xóa charge item và document trước submit bằng version; sau submit không có edit/delete. Document thuộc cost/AP cụ thể, URL allowlist, checksum unique trong chứng từ và cascade chỉ áp dụng khi xóa draft chưa submit.

Mutation trả `{message, data}`; xung đột trả mã 409 ổn định; validation trả 422 tiếng Việt. Mọi mutation yêu cầu header `Idempotency-Key` 1..128, scope theo `(actor, method, path, key)`, lưu canonical request hash và response trong cùng transaction; same hash replay, khác hash 409. Draft item/document DELETE không xóa header tài chính; không có DELETE cho submitted/approved/posted.

Concurrency dùng row lock cho approve/post/payment và compare-and-swap `WHERE id=? AND version=?`. DB unique là hàng rào cuối cho vendor invoice, active cost/AP, journal source và payment idempotency. Audit, response idempotency, trạng thái, journal/payment commit nguyên tử.

## Migration và tương thích

Migration `007_tms_freight_settlement` tạo bảng mới, indexes/partial unique/check/FK; nâng cấp journal schema như trên và backfill dữ liệu v001-v006 đã populate. ARInvoice giữ nguyên. Migration có schema validation trước marker/readiness, repeat-run, PostgreSQL/SQLite DDL và rollback guard; rollback journal chỉ được phép với restore authorization và phải khôi phục cấu trúc AR-only nếu không còn dữ liệu AP. Test không kết nối PostgreSQL.

## Kiểm thử

- Decimal/tax/rounding, discount và tổng server-side.
- Delivered-only, state machine, version, idempotency, separation-of-duties.
- AP active uniqueness, reversal, closed period và missing master configuration.
- Journal debit = credit; failure rollback toàn cost/AP/journal/settlement.
- Haversine từ event store và distance variance.
- Concurrent approve/post/payment; exactly-once audit/journal/payment.
- Vendor-number race, same/different idempotency payload, closed-period payment, FX gain/loss, payment reversal và partial-payment AP reversal prohibition.
- Auth fail-closed và permission/SOD matrix.
- Upgrade từ v001-v006 có AR journal populate, repeat-run, injected migration failure/rollback và exhaustive schema drift validation.
- Migration drift/rollback guard/readiness và PostgreSQL SQL dry-run offline.
- Full backend regression, không đọc/ghi PostgreSQL Linux đang tắt.

## Ngoài phạm vi

Cross-currency payment, kết nối ngân hàng thật, e-invoice vendor, OCR hóa đơn, ERP/SAP posting, approval UI và object storage thật thuộc increment sau.
