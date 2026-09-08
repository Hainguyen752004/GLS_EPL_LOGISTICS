"""Don nao PHAI quet du kien moi cho xuat ben, va don nao chi can niem phong.

VAN DE DA CO. Cua chan xuat ben `require_loaded_for_dispatch` truoc day chi soi
nhung Packing List DA TON TAI: don khong co Packing List thi di qua tu do. Nghia
la quy tac "phai quet du kien" bi tat bang cach KHONG lap phieu — mot cua ma ai
cung tat duoc thi khong phai cua. O quy mo nam tram xe, dieu phoi vien dang gap
se bo buoc lap phieu, va he thong khong con biet hang co du hay khong.

VI SAO KHONG AP CHO MOI DON. Container nguyen khoi la MOT don vi niem phong:
kiem la kiem SO NIEM PHONG, khong phai quet hai muoi hai nhan kien ben trong —
xe khong mo cont ra de dem. Bat in nhan cho hang nguyen cont la mot viec vo
nghia, va nguoi van hanh se lach bang cach lap mot phieu mot kien gia. Luc do
con so "da quet du kien" khong con noi len dieu gi ca, va do la ket cuc te nhat:
mot phep kiem van xanh trong khi khong ai kiem gi.

NEN QUY TAC GAN VAO LOAI HANG, va do DU LIEU quyet chu khong do nguoi bam:

  · Hang le, thung carton, pallet  -> PHAI co Packing List da quet du kien.
    Day dung la cho kien bi that lac, nen day dung la cho can dem.
  · Container nguyen khoi          -> KHONG can Packing List, nhung PHAI co so
    niem phong. Kiem soat cua no la niem phong, khong phai dem kien.

Quy cach doc tu `delivery_orders.packaging_spec` — truong da co san, khong phai
them cot moi cho viec phan loai.
"""

import re

from services.errors import conflict


#: Nhung quy cach la MOT DON VI NIEM PHONG.
#:
#: Khop bang tu khoa, khong bang danh sach dong chuoi chinh xac: truong
#: `packaging_spec` la chu nguoi dung nhap, nen thuc te co "Container nguyen
#: khoi", "Cont 40 nguyen khoi", "FCL 20'"... Doi mot danh sach chinh xac thi
#: mot chu viet khac di la don roi tu nhom "niem phong" sang nhom "phai dem",
#: va nguoi dung bi chan xuat ben ma khong hieu vi sao.
MAU_NGUYEN_KHOI = re.compile(
    r"nguyên\s*khối|nguyen\s*khoi|\bFCL\b|nguyên\s*cont|nguyen\s*cont",
    re.IGNORECASE,
)

#: Nhung quy cach RO RANG la hang dem duoc theo kien.
MAU_DEM_KIEN = re.compile(
    r"carton|thùng|thung|pallet|kiện|kien|bao|thùng\s*giấy|LCL|hàng\s*lẻ|hang\s*le",
    re.IGNORECASE,
)


def la_nguyen_khoi(quy_cach):
    """Quy cach nay co phai mot don vi niem phong khong."""
    return bool(MAU_NGUYEN_KHOI.search(str(quy_cach or "")))


def phai_quet_kien(don):
    """Don nay co phai quet du kien truoc khi xuat ben khong.

    Tra ve `True` cho hang dem duoc theo kien, `False` cho hang nguyen khoi.

    QUY CACH TRONG hoac LA MOT CHU KHONG NHAN RA thi tra ve `True` — nghieng ve
    phia CAN kiem. Doan sai theo huong "khong can kiem" thi hang di ma khong ai
    dem; doan sai theo huong "can kiem" thi nguoi dung bi hoi thêm mot buoc va
    ho sua duoc quy cach. Cai sai thu hai re hon nhieu.
    """
    quy_cach = str(getattr(don, "packaging_spec", "") or "")
    if la_nguyen_khoi(quy_cach):
        return False
    return True


def so_niem_phong(don):
    """So niem phong cua don, doc tu cac ten truong co the co."""
    for ten in ("seal_no", "seal_number", "container_seal_no"):
        gia_tri = getattr(don, ten, None)
        if gia_tri is not None and str(gia_tri).strip():
            return str(gia_tri).strip()
    return ""


def kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau):
    """Chan xuat ben khi don chua du dieu kien kiem soat hang.

    `phieu_dat_yeu_cau` la `True` khi don DA co mot Packing List da quet du kien
    (trang thai `loaded` tro len). Ben goi tu tra loi cau do, vi no da nam san
    cac dong Packing List.

    Nem `conflict` kem MA LOI RIENG cho tung tinh huong, chu khong dung chung
    mot ma: tang giao dien dua vao ma loi de dan nguoi dung tới dung cho phai
    sua — lap phieu, quet tiep, hay dien so niem phong la ba viec khac nhau.
    """
    if phai_quet_kien(don):
        if not phieu_dat_yeu_cau:
            raise conflict(
                "PACKING_LIST_REQUIRED",
                "Chưa thể xuất bến. Lệnh %s là hàng đếm theo kiện (%s) nên phải lập "
                "Packing List và quét đủ kiện trước khi cho xe đi." % (
                    don.id, str(getattr(don, "packaging_spec", "") or "chưa khai quy cách")),
                ["parking-list"],
            )
        return

    # Hang nguyen khoi: khong dem kien, nhung phai co so niem phong — do la
    # bang chung duy nhat cho biet hang khong bi mo tren duong.
    if not so_niem_phong(don):
        raise conflict(
            "SEAL_NUMBER_REQUIRED",
            "Chưa thể xuất bến. Lệnh %s là hàng nguyên khối nên không cần đếm kiện, "
            "nhưng phải ghi số niêm phong trước khi cho xe đi." % don.id,
            ["delivery-orders"],
        )
