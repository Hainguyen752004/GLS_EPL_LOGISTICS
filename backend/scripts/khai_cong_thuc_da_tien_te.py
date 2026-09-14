# -*- coding: utf-8 -*-
"""Khai công thức giá thành cho các loại xe còn trống ở những đồng tiền ngoài VNĐ.

VÌ SAO CẦN. Công thức giá thành đánh mã kèm đơn vị tiền — `vehicle-type::<loại xe>::<tiền>`.
Trong cơ sở dữ liệu chỉ có bản VNĐ (và một bản USD của Container 20FT toàn số 0), nên mở màn
"Công thức giá thành" rồi chọn LAK / THB / USD là mọi thẻ loại xe đều hiện "Chưa cấu hình
công thức" với đơn giá 0 — trông như hệ thống hỏng, trong khi thật ra chỉ là dữ liệu thiếu.

CÁCH LÀM. Bản VNĐ là NGUỒN SỰ THẬT: mọi đơn giá ngoại tệ đều quy đổi từ nó theo tỷ giá đang
lưu trong bảng `currencies` (1 USD = 26.173,5 VNĐ · 1 THB = 710 VNĐ · 1 LAK = 1,18 VNĐ).
Không tự bịa một biểu giá riêng cho từng đồng — hai biểu giá độc lập sẽ trôi khỏi nhau và
không ai biết bên nào đúng.

Giữ nguyên hình dạng năm cấu phần và mã Acc code của bản VNĐ, kể cả việc `rate`
(cước phí vận chuyển /kg) là `kind='revenue'` — giá BÁN, không bao giờ cộng vào giá thành.

Chạy:  python backend/scripts/khai_cong_thuc_da_tien_te.py           # chỉ xem, không ghi
       python backend/scripts/khai_cong_thuc_da_tien_te.py --ghi     # ghi thật qua API
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, 'backend', 'app'))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(GOC, '.env'))

API = os.getenv('EPL_API_BASE', 'http://127.0.0.1:8001')
TOKEN = (os.getenv('EPL_TMS_API_TOKEN') or '').strip()

# Số lẻ khi quy đổi. Đơn giá /km ở USD nhỏ hơn 1 đô nên phải giữ bốn số lẻ, còn LAK
# thì một kíp lẻ chẳng nói lên điều gì — làm tròn về số nguyên cho dễ đọc.
SO_LE = {'USD': 4, 'THB': 2, 'LAK': 0, 'VND': 0}
# Khoản theo chuyến là con số người ta đọc to lên trong cuộc họp, nên bo về mốc chẵn.
MOC_CHAN_THEO_CHUYEN = {'LAK': 100, 'THB': 1, 'USD': 0.01, 'VND': 1000}


def lam_tron(gia_tri, tien, theo_chuyen):
    if gia_tri <= 0:
        return 0.0
    if theo_chuyen:
        moc = MOC_CHAN_THEO_CHUYEN.get(tien, 1)
        return round(round(gia_tri / moc) * moc, SO_LE.get(tien, 2))
    return round(gia_tri, SO_LE.get(tien, 2))


def dinh_dang(gia_tri, tien):
    n = SO_LE.get(tien, 2)
    return ('{:,.%df}' % n).format(gia_tri).replace(',', '.') if n == 0 else ('{:,.%df}' % n).format(gia_tri)


def goi(duong, du_lieu=None):
    dau = {'Accept': 'application/json'}
    if TOKEN:
        dau['Authorization'] = 'Bearer ' + TOKEN
    than = None
    if du_lieu is not None:
        than = json.dumps(du_lieu, ensure_ascii=False).encode('utf-8')
        dau['Content-Type'] = 'application/json'
    yeu_cau = urllib.request.Request(API + duong, data=than, headers=dau,
                                     method='POST' if than else 'GET')
    with urllib.request.urlopen(yeu_cau, timeout=30) as tra:
        return json.loads(tra.read().decode('utf-8'))


def main():
    bo = argparse.ArgumentParser()
    bo.add_argument('--ghi', action='store_true', help='ghi thật; không có cờ này thì chỉ in ra xem')
    bo.add_argument('--tien', default='LAK,THB,USD', help='danh sách đồng tiền cần khai')
    tham_so = bo.parse_args()
    can_khai = [m.strip().upper() for m in tham_so.tien.split(',') if m.strip()]

    ty_gia = {c['id']: float(c['exchange_rate']) for c in goi('/api/currencies')}
    print('Tỷ giá đang lưu: ' + ' · '.join('1 %s = %s VNĐ' % (k, v) for k, v in ty_gia.items()))

    cong_thuc = goi('/api/cost-formulas')
    ban_vnd = {ct['vehicle_type_id']: ct for ct in cong_thuc
               if ct.get('vehicle_type_id') and ct.get('currency') == 'VND'}
    da_co = {(ct.get('vehicle_type_id'), ct.get('currency')): ct for ct in cong_thuc}
    loai_xe = {lx['id']: lx for lx in goi('/api/vehicle-types')}

    them, de_nguyen = 0, 0
    for ma_loai, goc in sorted(ban_vnd.items()):
        ten = loai_xe.get(ma_loai, {}).get('name') or goc.get('name') or ma_loai
        for tien in can_khai:
            if tien not in ty_gia or ty_gia[tien] <= 0:
                print('  ! bỏ qua %s — chưa khai tỷ giá' % tien)
                continue
            cu = da_co.get((ma_loai, tien))
            # Đã có đơn giá thật thì KHÔNG đè — chỉ lấp chỗ trống và chỗ toàn số 0.
            if cu and any(float(t.get('rate') or 0) > 0 for t in (cu.get('terms') or [])):
                de_nguyen += 1
                continue

            hang_tu, thanh_phan = [], {}
            for t in goc.get('terms') or []:
                so = float(t.get('rate') or 0) / ty_gia[tien]
                so = lam_tron(so, tien, t.get('factor') == 'per_trip')
                hang_tu.append({**t, 'rate': so})
                thanh_phan[{'wh': 'warehouse', 'rate': 'freight_rate'}.get(t['key'], t['key'])] = \
                    dinh_dang(so, tien)

            print('\n  %s · %s  (%s)' % (ten, tien, ma_loai))
            for t in hang_tu:
                print('      %-8s %-28s %-8s %12s %s' % (
                    t['key'], t.get('label', '')[:28], t.get('kind'), dinh_dang(t['rate'], tien), tien))

            if not tham_so.ghi:
                them += 1
                continue
            goi_tin = {
                'vehicle_type_id': ma_loai,
                'name': '%s — %s' % (ten, tien),
                'currency': tien,
                'terms': hang_tu,
                'expressions': goc.get('expressions') or None,
                'expected_updated_at': (cu or {}).get('updated_at'),
                'fuel': thanh_phan.get('fuel', '0'),
                'driver': thanh_phan.get('driver', '0'),
                'toll': thanh_phan.get('toll', '0'),
                'warehouse': thanh_phan.get('warehouse', '0'),
                'freight_rate': thanh_phan.get('freight_rate', '0'),
            }
            if goi_tin['expressions'] is None:
                goi_tin.pop('expressions')
            try:
                ket = goi('/api/cost-formulas', goi_tin)
                print('      -> %s' % ket.get('message'))
                them += 1
            except urllib.error.HTTPError as loi:
                print('      -> LỖI %s: %s' % (loi.code, loi.read().decode('utf-8', 'replace')[:200]))

    print('\n%s %d công thức; giữ nguyên %d công thức đã có đơn giá.'
          % ('Đã khai' if tham_so.ghi else 'Sẽ khai', them, de_nguyen))
    if not tham_so.ghi:
        print('Chạy lại với --ghi để lưu thật.')


if __name__ == '__main__':
    main()
