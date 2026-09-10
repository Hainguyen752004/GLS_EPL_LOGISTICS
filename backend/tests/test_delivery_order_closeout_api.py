import importlib


def test_delivered_demo_do_exposes_closeout_price_table_from_database(app_client):
    client, _, _ = app_client
    database = importlib.import_module("database")
    seed_service = importlib.import_module("services.demo_seed_service")

    with database.SessionLocal() as db:
        ids = seed_service.seed_demo(db, reset=True, verify=True)

    completed = ids["completed"]
    response = client.get(f"/api/delivery-orders/{completed['delivery_order_id']}/closeout")

    assert response.status_code == 200
    data = response.json()
    assert data["do_id"] == "DEMO-DO-2026-003"
    assert data["quotation_id"] == "DEMO-QT-2026-003"
    assert data["status"] == "delivered"
    assert data["currency"] == "VND"
    assert data["cost_formula"]["id"] == "DEMO-COST-FORMULA-20FT"
    assert data["cost_formula"]["components"]["fuel"] == "6250"
    # Bon dong CHI PHI. Ban truoc con mot dong thu nam —
    # `freight_rate` "Cuoc van chuyen theo tai trong" 12.750.000 d — nam trong
    # danh sach nay, va do la mot loi nghiem trong: cuoc phi /kg la tien THU
    # CUA KHACH, khong phai khoan chi. Cong no vao thi "gia thanh" cua chuyen
    # nay thanh 14.029.375 d trong khi gia ban chi 4.200.000 d — moi chuyen
    # deu lo nang tren giay. Cong thuc da phan biet san bang `terms[].kind`
    # (`cost` / `revenue`), nen chi can ton trong no.
    #
    # Ten dong lay tu `terms[].label` chu khong viet cung trong ma nguon, nen
    # doi nhan trong Cong thuc gia thanh la man nay doi theo.
    # `charge_type` la MA KHOAN MUC CHUAN, dung chung voi
    # `actual_cost_lines[].charge_type` va voi `freight_charge_items`.
    #
    # `code` la ma CAU PHAN cua cong thuc gia thanh, va hai bo do KHAC NHAU:
    # cung "Phi bai & luu kho" ma `code` ghi `warehouse` con khoan muc chuan
    # ghi `yard`. Ai doc goi nay de hach toan se anh xa theo mot danh sach roi
    # lech danh sach kia — va lech im lang, vi ca hai ma deu "trong dung". Giu
    # ca hai truong: `code` cho cho nao dang doc no, `charge_type` cho ben ngoai.
    #
    # So theo NAM TRUONG nghiep vu, khong so nguyen ca dict: goi nay con mang
    # them `cost_index`, `key`, `rate_source`, `unit_rate` cho he cong no, va
    # moi lan them mot truong cho ben doc ma bai kiem nay do thi no dang chot
    # HINH DANG chu khong chot NOI DUNG.
    NAM_TRUONG = ("code", "charge_type", "name", "original_amount", "calculation")
    rut = lambda d: {k: d[k] for k in NAM_TRUONG}
    assert [rut(d) for d in data["configured_cost_lines"]] == [
        {
            "code": "fuel",
            "charge_type": "fuel",
            "name": "Chi phí xăng dầu /km",
            "original_amount": 279375.0,
            "calculation": "44.7 km × 6.250 VND",
        },
        {
            "code": "driver",
            "charge_type": "driver",
            "name": "Phụ cấp chuyến tài xế",
            "original_amount": 500000.0,
            "calculation": "Theo chuyến × 500.000 VND",
        },
        {
            "code": "toll",
            "charge_type": "toll",
            "name": "Phí cầu đường / BOT",
            "original_amount": 300000.0,
            "calculation": "Theo chuyến × 300.000 VND",
        },
        {
            "code": "warehouse",
            "charge_type": "yard",
            "name": "Phí bãi & lưu kho",
            "original_amount": 200000.0,
            "calculation": "Theo chuyến × 200.000 VND",
        },
    ]
    # Moi dong chi phi theo cong thuc PHAI co cho de mang ma costindex, du trong.
    assert all("cost_index" in d and "rate_source" in d for d in data["configured_cost_lines"])
    # Va cuoc /kg KHONG duoc lan vao day nua.
    assert "freight_rate" not in [d["code"] for d in data["configured_cost_lines"]]
    # Tong gia thanh phai nho hon gia ban — khong thi con so vo nghia.
    tong_chi = sum(d["original_amount"] for d in data["configured_cost_lines"])
    assert tong_chi == 1279375.0, tong_chi
    assert tong_chi < data["commercials"]["base_selling_price"], tong_chi
    assert data["commercials"]["base_selling_price"] == 4200000.0
    assert data["commercials"]["customer_surcharge_total"] == 470000.0
    assert data["commercials"]["selling_price"] == 4670000.0
    assert data["commercials"]["actual_cost_total"] == 2380000.0
    assert data["commercials"]["margin_amount"] == 2290000.0
    assert [line["charge_type"] for line in data["actual_cost_lines"]] == ["driver", "fuel", "toll"]
    assert [pod["stop_no"] for pod in data["pod_records"]] == [1]
    assert data["pod_records"][0]["receiver_name"] == "Nguyễn Văn An"
    assert {document["file_name"] for document in data["pod_documents"]} == {
        "POD-DEMO-DO-2026-003.pdf",
        "signature-DEMO-DO-2026-003.png",
    }
    assert data["trip"]["id"] == "DEMO-TRIP-2026-003"


def test_ho_so_hoan_tat_tra_SO_THU_CHI_tung_dong_co_ma_costindex(app_client):
    """Goi ban giao cho he cong no: TUNG DONG thu / chi, moi dong mang MA COSTINDEX.

    Chu du an chi dich danh khoi "Ho so da hoan tat" la cho dong nghiep lay du
    lieu lap phieu thu / phieu chi, va noi: *"chi tiet tung dong luon — chi tiet
    tung cai chi cai thu … dem may cai phi cua xe cac thu ra luon"*. Vai con so
    tong khong lap duoc phieu.

    Ma costindex gan o tang CONG THUC (Du lieu goc) va phai di toi day qua ba
    duong khac nhau — bai nay kiem ca ba:

      · dong CHI theo cong thuc: doc thang tu `terms[].cost_index`;
      · dong CHI thuc te: bang `freight_charge_items` cua bo demo duoc ghi
        TRUOC khi co cot `cost_index` (NULL), nen ma phai duoc tra lai tu cong
        thuc theo `charge_type` — day la duong cua moi du lieu cu;
      · dong THU khach tra them: chi co TEN ("Phi cau duong"), ma suy tu ten.

    Va SO phai KHOP: tong thu = gia cuoi DO, tong chi = gia thanh dung tinh lai.
    """
    client, _, _ = app_client
    database = importlib.import_module("database")
    seed_service = importlib.import_module("services.demo_seed_service")
    with database.SessionLocal() as db:
        ids = seed_service.seed_demo(db, reset=True, verify=True)

    data = client.get(
        f"/api/delivery-orders/{ids['completed']['delivery_order_id']}/closeout").json()

    # 1. Dong CHI theo cong thuc mang ma cua cong thuc.
    ma_theo_khoan_muc = {d["charge_type"]: d["cost_index"] for d in data["configured_cost_lines"]}
    assert ma_theo_khoan_muc == {
        "fuel": "EPL-CP-XD", "driver": "EPL-CP-TX", "toll": "EPL-CP-BOT", "yard": "EPL-CP-BAI",
    }, ma_theo_khoan_muc

    # 2. So thu-chi: moi dong deu co ma — TRU dung mot dong, va dong do phai
    #    duoc NOI RA la thieu chu khong bi bia ma.
    #
    #    Bo demo co khoan khach tra them "Phi cho boc do" (charge_type
    #    `waiting`), ma cong thuc gia thanh cua loai xe KHONG co khoan muc nao
    #    ve phi cho. Vay khong co ma nao de tra, va ho so phai bao
    #    `missing_cost_index` de nguoi lam tai chinh vao Cong thuc gia thanh ma
    #    them khoan muc — chu khong duoc tu gan mot ma "trong dung".
    so = data["ledger_lines"]
    assert so, "phai co so thu-chi"
    thieu = [d["name"] for d in so if d["missing_cost_index"]]
    assert thieu == ["Phí chờ bốc dỡ"], "dong chua gan ma costindex: %s" % thieu
    assert data["ledger_totals"]["so_dong_thieu_ma"] == 1

    chi = {d["charge_type"]: d for d in so if d["kind"] == "chi"}
    thu = [d for d in so if d["kind"] == "thu"]
    # Chi phi thuc te cua bo demo ghi TRUOC khi co cot cost_index -> ma phai
    # duoc tra lai tu cong thuc, khong duoc rong.
    assert chi["fuel"]["cost_index"] == "EPL-CP-XD"
    assert chi["fuel"]["source"] in ("cost_formula", "vehicle")
    assert chi["fuel"]["actual_amount"] > chi["fuel"]["planned_amount"] or \
        chi["fuel"]["actual_amount"] == chi["fuel"]["planned_amount"]
    # Cuoc theo bao gia mang ma cua khoan muc DOANH THU.
    cuoc = next(d for d in thu if d["source"] == "quotation")
    assert cuoc["cost_index"] == "EPL-TH-CUOC"
    assert cuoc["actual_amount"] == data["commercials"]["base_selling_price"]
    # Khach tra them: dong nao TEN khop mot khoan muc cua cong thuc thi mang ma
    # cua khoan muc do (vi du "Phi cau duong" -> `toll` -> EPL-CP-BOT); dong
    # khong khop ("Phi cho boc do") thi rong va da duoc dem o tren.
    them = [d for d in thu if d["source"] == "customer_surcharge"]
    assert them, "bo demo co khoan khach tra them"
    co_ma = {d["name"]: d["cost_index"] for d in them if d["cost_index"]}
    assert co_ma, "phai co it nhat mot khoan khach tra them suy duoc ma: %s" % them
    assert all(d["cost_index"] or d["name"] == "Phí chờ bốc dỡ" for d in them), them

    # 3. SO PHAI KHOP voi ho so — bang so, khong bang co.
    tong = data["ledger_totals"]
    assert tong["khop_gia_cuoi"] is True and tong["khop_gia_thanh"] is True, tong
    assert abs(tong["tong_thu"] - data["commercials"]["final_selling_price"]) < 1
    assert abs(tong["tong_chi"] - data["commercials"]["actual_cost_total"]) < 1
    assert abs(tong["lai_gop"] - data["commercials"]["margin_amount"]) < 1
    # Va tung dong chi phi thuc te trong goi cung mang ma.
    assert all(l["cost_index"] for l in data["actual_cost_lines"]), data["actual_cost_lines"]
