# -*- coding: utf-8 -*-
"""Kiểm ngoại tuyến cho công cụ và tác tử — không gọi Gemini, không cần máy chủ EPL.

Cái dễ hỏng ở đây không phải mô hình mà là lớp cắt gọn và lớp khai báo:
  1. Khai báo công cụ phải đúng khuôn Gemini (type OBJECT, properties, required ⊆ properties).
  2. Dòng DO phải mang MÃ TIỀN TỆ nối từ báo giá — thiếu là mô hình mặc định VND và nói sai
     với khách dùng LAK.
  3. `rut_gon` phải bỏ hình học/sự kiện thô và chặt danh sách dài, không thì một câu hỏi
     ngốn hết ngữ cảnh.
  4. Lịch sử từ trình duyệt phải thành contents xen kẽ user/model.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import canh_bao     # noqa: E402
import cong_cu      # noqa: E402
import tac_tu       # noqa: E402


class GiaAPI:
    """Thay `goi_api` bằng bảng trả sẵn theo đường dẫn (bỏ phần truy vấn)."""
    def __init__(self, bang):
        self.bang, self.da_goi = bang, []

    def __call__(self, duong, tham_so=None, timeout=60):
        goc = duong.split("?")[0]
        self.da_goi.append((goc, tham_so))
        for k, v in self.bang.items():
            if goc == k or goc.startswith(k.rstrip("*")) and k.endswith("*"):
                return json.loads(json.dumps(v))
        raise cong_cu.LoiAPI("HTTP 404 tại %s" % goc)


class KhaiBao(unittest.TestCase):
    def test_khai_bao_dung_khuon_gemini(self):
        kb = cong_cu.khai_bao_gemini()
        self.assertEqual(len(kb), len(cong_cu.CONG_CU))
        for f in kb:
            self.assertRegex(f["name"], r"^[a-z_]+$")
            self.assertTrue(f["description"])
            if "parameters" in f:
                self.assertEqual(f["parameters"]["type"], "OBJECT")
                for ten, p in f["parameters"]["properties"].items():
                    self.assertIn(p["type"], ("STRING", "INTEGER", "NUMBER", "BOOLEAN"), ten)
                for bb in f["parameters"].get("required", []):
                    self.assertIn(bb, f["parameters"]["properties"], "%s.required lệch" % f["name"])

    def test_moi_cong_cu_deu_co_nhan_ba_ngon_ngu(self):
        for c in cong_cu.CONG_CU:
            nhan = cong_cu.NHAN.get(c["ten"])
            self.assertIsNotNone(nhan, c["ten"])
            self.assertEqual(set(nhan), {"vi", "en", "lo"}, c["ten"])
            self.assertTrue(all(nhan.values()), c["ten"])


class CatGon(unittest.TestCase):
    def test_rut_gon_bo_hinh_hoc_va_chat_danh_sach(self):
        x = {"id": "A", "duong_bo": [[1, 2]] * 500, "events": [{}] * 50, "rong": None, "trong": "",
             "ds": list(range(100)), "chu": "x" * 1000, "con": {"legs": [1], "ok": 1}}
        r = cong_cu.rut_gon(x, toi_da_muc=10, toi_da_chu=50)
        self.assertNotIn("duong_bo", r)
        self.assertNotIn("events", r)
        self.assertNotIn("rong", r)
        self.assertNotIn("trong", r)
        self.assertEqual(len(r["ds"]), 11)                     # 10 mục + dòng "… và N mục nữa"
        self.assertIn("90 mục nữa", r["ds"][-1])
        self.assertEqual(len(r["chu"]), 51)
        self.assertEqual(r["con"], {"ok": 1})

    def test_gon_cho_mo_hinh_chan_kich_thuoc(self):
        to = {"x": ["a" * 100] * 500}
        r = tac_tu._gon_cho_mo_hinh(to, toi_da=2000)
        self.assertIn("ghi_chu", r)
        self.assertLessEqual(len(r["mot_phan"]), 2000)
        nho = {"x": 1}
        self.assertEqual(tac_tu._gon_cho_mo_hinh(nho), nho)


class LenhGiaoHang(unittest.TestCase):
    def setUp(self):
        self.goc = cong_cu.goi_api
        cong_cu._dem.clear()
        cong_cu.goi_api = GiaAPI({
            "/api/delivery-orders": {"items": [
                {"id": "DO-1", "customer_id": "C1", "quotation_id": "QT-LAK", "canonical_status": "in_transit",
                 "unit_price": 1728118, "origin": "Vientiane", "destination": "Cửa Lò",
                 "delivery_window_end": "2026-09-16T16:59:00+00:00", "duong_bo": [[1, 2]],
                 "driver_id": "DRV-1"},
                {"id": "DO-2", "customer_id": "C2", "quotation_id": "QT-VND", "canonical_status": "pending",
                 "unit_price": 1406000, "origin": "Sóng Thần", "destination": "Cát Lái",
                 "delivery_window_end": "2026-09-13T10:00:00+00:00"},
            ]},
            "/api/quotations": {"items": [{"id": "QT-LAK", "currency_code": "LAK"},
                                          {"id": "QT-VND", "currency_code": "VND"}]},
            "/api/crm/customers": {"data": [{"id": "C1", "name": "Khách Lào"}, {"id": "C2", "name": "Vinamilk"}]},
            "/api/drivers": [{"id": "DRV-1", "full_name": "Somsak Phommachanh"}],
        })

    def tearDown(self):
        cong_cu.goi_api = self.goc
        cong_cu._dem.clear()

    def test_dong_do_mang_ma_tien_cua_bao_gia(self):
        r = cong_cu.lenh_giao_hang({})
        theo_ma = {d["id"]: d for d in r["lenh"]}
        self.assertEqual(theo_ma["DO-1"]["currency_code"], "LAK")
        self.assertEqual(theo_ma["DO-2"]["currency_code"], "VND")
        self.assertEqual(theo_ma["DO-1"]["customer_name"], "Khách Lào")
        self.assertNotIn("duong_bo", theo_ma["DO-1"])

    def test_dong_do_mang_ten_tai_xe_khong_chi_ma(self):
        """Đọc 'tài xế DEMO-DRV-010' thì người nghe không biết đó là ai."""
        theo_ma = {d["id"]: d for d in cong_cu.lenh_giao_hang({})["lenh"]}
        self.assertEqual(theo_ma["DO-1"]["driver_name"], "Somsak Phommachanh")

    def test_api_tai_xe_hong_thi_van_ra_danh_sach_lenh(self):
        """Tên tài xế là phần tô thêm; nó hỏng không được làm chết cả công cụ."""
        cong_cu._dem.clear()
        del cong_cu.goi_api.bang["/api/drivers"]
        r = cong_cu.lenh_giao_hang({})
        self.assertEqual(sorted(d["id"] for d in r["lenh"]), ["DO-1", "DO-2"])
        self.assertIsNone(r["lenh"][0].get("driver_name"))

    def test_loc_trang_thai_va_tim(self):
        self.assertEqual([d["id"] for d in cong_cu.lenh_giao_hang({"trang_thai": "pending"})["lenh"]], ["DO-2"])
        self.assertEqual([d["id"] for d in cong_cu.lenh_giao_hang({"tim": "vientiane"})["lenh"]], ["DO-1"])
        # Tìm theo TÊN khách (mô hình chỉ biết tên, không biết mã) — đã trả rỗng oan ngày 12/09.
        self.assertEqual([d["id"] for d in cong_cu.lenh_giao_hang({"tim": "vinamilk"})["lenh"]], ["DO-2"])
        self.assertEqual([d["id"] for d in cong_cu.lenh_giao_hang({"tim": "Khách Lào", "trang_thai": "in_transit"})["lenh"]], ["DO-1"])

    def test_in_transit_gom_ca_arrived(self):
        cong_cu.goi_api.bang["/api/delivery-orders"]["items"][1]["canonical_status"] = "arrived"
        cong_cu._dem.clear()
        self.assertEqual(sorted(d["id"] for d in cong_cu.lenh_giao_hang({"trang_thai": "in_transit"})["lenh"]), ["DO-1", "DO-2"])
        self.assertEqual([d["id"] for d in cong_cu.lenh_giao_hang({"trang_thai": "arrived"})["lenh"]], ["DO-2"])
        r = cong_cu.lenh_giao_hang({"gioi_han": 1})
        self.assertEqual(r["tong_khop"], 2)
        self.assertEqual(r["tra_ve"], 1)

    def test_loi_api_tra_ve_dang_chu_khong_nem(self):
        r = cong_cu.chay_cong_cu("ho_so_khach_hang", {"customer_id": "KHONG-CO"})
        self.assertIn("loi", r)
        self.assertIn("404", r["loi"])
        self.assertIn("loi", cong_cu.chay_cong_cu("khong_ton_tai", {}))
        self.assertIn("loi", cong_cu.chay_cong_cu("theo_doi_lenh", {}))   # thiếu do_id


class MocNgay(unittest.TestCase):
    """Máy chủ EPL từ chối mốc thời gian không có múi giờ (`TIMEZONE_REQUIRED`), còn mô hình
    thì luôn sinh ngày trần YYYY-MM-DD. Bù múi giờ phải làm ở công cụ."""
    def test_ngay_tran_duoc_bu_mui_gio(self):
        self.assertEqual(cong_cu._moc_ngay("2026-09-01"), "2026-09-01T00:00:00+07:00")
        self.assertEqual(cong_cu._moc_ngay("2026-09-30", cuoi_ngay=True), "2026-09-30T23:59:59+07:00")

    def test_khong_dung_den_gia_tri_da_du(self):
        day_du = "2026-09-01T08:30:00+07:00"
        self.assertEqual(cong_cu._moc_ngay(day_du), day_du)
        self.assertIsNone(cong_cu._moc_ngay(None))
        self.assertIsNone(cong_cu._moc_ngay(""))


class LichSu(unittest.TestCase):
    def test_lich_su_thanh_contents_xen_ke(self):
        ls = [{"vai": "user", "noi_dung": "a"}, {"vai": "model", "noi_dung": "b"},
              {"vai": "user", "noi_dung": "c"}, {"vai": "user", "noi_dung": "d"},
              {"vai": "model", "noi_dung": ""}]
        r, _ = tac_tu._noi_dung_tu_lich_su(ls)
        self.assertEqual([x["role"] for x in r], ["user", "model", "user"])
        self.assertEqual(r[2]["parts"][0]["text"], "c\n\nd")

    def test_loi_dan_co_ngon_ngu_va_ngay(self):
        chu = tac_tu.LOI_DAN.format(hom_nay="Saturday 12/09/2026 17:00", ngon_ngu="English",
                                    cach_viet_so=tac_tu.CACH_VIET_SO["en"])
        self.assertIn("English", chu)
        self.assertIn("12/09/2026", chu)
        self.assertIn("VNĐ", chu)
        self.assertIn("CHỈ ĐỌC", chu)


class GiamSat(unittest.TestCase):
    """so_sanh: phần chênh giữa hai ảnh phải ra đúng bốn loại thông báo, và KHÔNG báo gì cho
    những thứ đã có sẵn từ trước."""
    def setUp(self):
        self.goc = cong_cu.goi_api
        cong_cu._dem.clear()
        cong_cu.goi_api = GiaAPI({"/api/crm/customers": {"data": [{"id": "C1", "name": "Vinamilk"}]}})

    def tearDown(self):
        cong_cu.goi_api = self.goc
        cong_cu._dem.clear()

    def test_bon_loai_thong_bao(self):
        truoc = ({"QT-1": "sent"}, {"DO-1": "in_transit", "DO-2": "pending"}, {"TRIP-1": "dispatched", "TRIP-2": "in_transit"})
        sau = ({"QT-1": "sent", "QT-2": "draft"},
               {"DO-1": "delivered", "DO-2": "pending", "DO-3": "pending"},
               {"TRIP-1": "in_transit", "TRIP-2": "completed", "TRIP-3": "planned"})
        tho = ([{"id": "QT-2", "customer_id": "C1", "origin": "A → B", "selling_price": 1406000, "currency_code": "LAK",
                 "canonical_status": "draft"}],
               [{"id": "DO-1", "customer_id": "C1", "vehicle_id": "XE-1", "driver_id": "TX-1"},
                {"id": "DO-3", "customer_id": "C1", "quotation_id": "QT-1", "origin": "A → B"}],
               [{"id": "TRIP-1", "status": "in_transit", "vehicle_id": "XE-1", "driver_id": "TX-1", "delivery_order_ids": ["DO-1"]},
                {"id": "TRIP-2", "status": "completed", "vehicle_id": "XE-2", "driver_id": "TX-2", "delivery_order_ids": ["DO-3"]},
                {"id": "TRIP-3", "status": "planned", "vehicle_id": None}])
        ra = canh_bao.so_sanh(truoc, sau, tho)
        loai = sorted((x["loai"], x["ma"]) for x in ra)
        self.assertEqual(loai, [("bao_gia_moi", "QT-2"), ("do_giao_xong", "DO-1"), ("do_moi", "DO-3"),
                                ("xe_hoan_tat", "TRIP-2"), ("xe_xuat_phat", "TRIP-1")])
        bg = next(x for x in ra if x["loai"] == "bao_gia_moi")
        self.assertEqual((bg["khach"], bg["tien_te"], bg["gia"]), ("Vinamilk", "LAK", 1406000))
        xp = next(x for x in ra if x["loai"] == "xe_xuat_phat")
        self.assertEqual((xp["xe"], xp["khach"]), ("XE-1", "Vinamilk"))
        # TRIP-3 mới xuất hiện ở trạng thái planned: KHÔNG phải xuất phát, không báo.
        self.assertFalse(any(x["ma"] == "TRIP-3" for x in ra))

    def test_khong_doi_thi_khong_bao(self):
        anh = ({"QT-1": "sent"}, {"DO-1": "pending"}, {"TRIP-1": "in_transit"})
        self.assertEqual(canh_bao.so_sanh(anh, anh, ([], [], [{"id": "TRIP-1", "status": "in_transit"}])), [])


class NguCanh(unittest.TestCase):
    """Ngữ cảnh KHÔNG được nằm trong lượt của mô hình (nó sẽ bắt chước và bịa khối dữ liệu),
    mà trả ra ngoài để gắn vào lượt người dùng hiện tại."""
    def test_ngu_canh_gan_vao_luot_hoi_sinh_ra_no_khong_vao_luot_mo_hinh(self):
        ls = [{"vai": "user", "noi_dung": "a"}, {"vai": "model", "noi_dung": "b", "ngu_canh": "{XA}"},
              {"vai": "user", "noi_dung": "c"}, {"vai": "model", "noi_dung": "d", "ngu_canh": "{CU}"},
              {"vai": "user", "noi_dung": "e"}, {"vai": "model", "noi_dung": "f", "ngu_canh": "{CU}"},   # không tra gì, mang khối cũ
              {"vai": "user", "noi_dung": "g"}, {"vai": "model", "noi_dung": "h", "ngu_canh": "{MOI}"}]
        r, nc = tac_tu._noi_dung_tu_lich_su(ls)
        self.assertEqual([x["role"] for x in r], ["user", "model"] * 4)
        cua_mo_hinh = chr(10).join(p["text"] for x in r if x["role"] == "model" for p in x["parts"])
        self.assertNotIn("DỮ LIỆU", cua_mo_hinh, "khối dữ liệu không được nằm trong lượt của mô hình")
        # Khối {MOI} gắn vào lượt hỏi "g" (sinh ra nó); {CU} gắn vào lượt hỏi "e" — mỗi khối một lần; {XA} bỏ.
        khoi_theo_luot = {x["parts"][0]["text"]: [p["text"] for p in x["parts"][1:]] for x in r if x["role"] == "user"}
        self.assertTrue(any("{MOI}" in p for p in khoi_theo_luot["g"]))
        self.assertTrue(any("{CU}" in p for p in khoi_theo_luot["e"]))
        self.assertEqual(khoi_theo_luot["c"], [], "khối {CU} chỉ được gắn một lần")
        self.assertEqual(khoi_theo_luot["a"], [], "khối quá xa thì bỏ")
        self.assertEqual(nc, "{MOI}")

    def test_lich_su_xen_ke(self):
        ls = [{"vai": "user", "noi_dung": "a"}, {"vai": "user", "noi_dung": "b"}, {"vai": "model", "noi_dung": ""}]
        r, _ = tac_tu._noi_dung_tu_lich_su(ls)
        self.assertEqual([x["role"] for x in r], ["user"])
        self.assertEqual(r[0]["parts"][0]["text"], "a" + chr(10) + chr(10) + "b")

    def test_cat_khoi_du_lieu_mo_hinh_in_ra(self):
        chu = "Sự cố ở xe X." + chr(10) + chr(10) + "[DỮ LIỆU ĐÃ TRA]" + chr(10) + '{"bia": 1}'
        self.assertEqual(tac_tu._cat_khoi_du_lieu(chu), "Sự cố ở xe X.")
        self.assertEqual(tac_tu._cat_khoi_du_lieu("Bình thường."), "Bình thường.")

    def test_ngu_canh_bi_chan_kich_thuoc(self):
        r = tac_tu._ngu_canh({"x": ["a" * 100] * 200}, toi_da=1000)
        self.assertLessEqual(len(r), 1001)


if __name__ == "__main__":
    unittest.main(verbosity=2)
