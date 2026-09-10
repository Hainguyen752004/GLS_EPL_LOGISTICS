/**
 * CUA CHAN TAI TRONG cua buoc bao gia.
 *
 * Bai kiem nay TRUOC DAY chot man Bao gia CU (`#qtv2-khoi-cu`): no ghim bon o
 * `qt-weight-kg / qt-volume-m3 / qt-pallet-count / qt-vehicle-recommendations`
 * va ham `refreshQuotationVehicleRecommendations` — cua chan DUY NHAT luc do.
 * Chinh vi bai kiem nay ma khoi cu tung bi bo roi phai HOAN NGUYEN: bo no la
 * xoa mat cua chan, va mo lai duong bao gia mot lo 20 tan tren xe 5 tan.
 *
 * NAY KHOI CU DA BO HAN, vi ca hai ben deu da chan that:
 *
 *   · Man moi (`bao-gia-v2.js`) chan ngay luc BAM vao the loai xe, va noi ro
 *     CHIEU nao vuot cung con so vuot.
 *   · May chu (`bao_gia_service.xem_truoc_gia`) tra `tinh_duoc: False` kem
 *     viec con thieu — tuc KHONG TINH RA GIA cho lo vuot tai, chu khong chi
 *     canh bao. Chot boi `backend/tests/test_bao_gia_cua_chan_tai_trong.py`.
 *
 * Nen phan chot man cu da bo khoi bai kiem nay. Phan con lai duoi day la nua
 * phia giao dien cua cua chan that.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// MAN BAO GIA DANG CHAY (`bao-gia-v2.js`) cung phai co cua chan tai trong.
//
// Mot lo that da do duoc: `do_vua_tai` o may chu TRUOC DAY chi xet `max_weight`,
// nen mot lo 40 m3 tren xe lanh 22 m3 duoc cham la "phu hop" va 30 pallet tren
// xe 8 pallet cung vay. Nguoi ban chon dung cai the mau xanh do, luu lai, roi
// nhan 409 tu cua chan o duong ghi — man hinh noi mot cau, may chu noi cau khac.
//
// Nay ca hai ben dung CUNG MOT BO DANH GIA ba chieu. Phia may chu co
// `backend/tests/test_bao_gia_cua_chan_tai_trong.py` chot lai; day la nua phia
// giao dien.
{
  const quotationSource = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'bao-gia-v2.js'), 'utf8');

  // The loai xe "khong du tai" phai bi chan khi bam, khong chi doi mau.
  assert.match(quotationSource, /if \(n\.dataset\.hong\)/,
    'New quotation screen must block clicking an unsuitable vehicle type.');
  assert.match(quotationSource, /khong_du_tai/,
    'New quotation screen must read the server capacity verdict.');

  // Va thong bao phai noi DUNG CHIEU vuot. Noi "khong du tai" cho mot lo hang
  // nhe ma khoi lon la noi sai: nguoi ban doi sang xe nang hon roi van vuong.
  assert.match(quotationSource, /function lyDoKhongDu\(/,
    'New quotation screen must explain which capacity dimension is exceeded.');
  assert.match(quotationSource, /WorkflowUIUtils\.evaluateVehicleCapacity/,
    'It must reuse the shared evaluator, not compute capacity on its own — two '
    + 'separate implementations drift and then only one gets fixed.');
  ['tải trọng', 'thể tích', 'số pallet'].forEach(chieu => {
    assert.ok(quotationSource.includes(chieu),
      `Capacity message must be able to name "${chieu}".`);
  });
}

console.log('QUOTATION_CAPACITY_RECOMMENDATION_UI_OK');
