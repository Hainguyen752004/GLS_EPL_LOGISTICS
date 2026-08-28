# Responsive Driver Scheduling Design

## Muc tieu

Giao dien EPL phai tu thich nghi theo kich thuoc man hinh ma khong dung CSS `zoom` hay `transform: scale`. Workbench sap ca phai hien du danh sach tai xe, lich tuan va chi tiet ca tren desktop, tablet va dien thoai.

## Thiet ke

- Nen dung chung: viewport theo chieu rong thiet bi, cac container duoc phep co lai voi `min-width: 0`, noi dung bang/lich rong dung khu vuc cuon rieng thay vi lam tran ca trang.
- Desktop: workbench dung ba cot co gioi han linh hoat; lich nhan phan khong gian con lai.
- Tablet: danh sach va lich nam cung hang, inspector chuyen xuong hang duoi.
- Dien thoai: toolbar va ba khu vuc xep doc; danh sach tai xe thanh luoi ngang gon; lich giu kich thuoc thao tac va cuon ngang; inspector nam ben duoi.
- Du lieu: frontend dung dung global `window.TmsCockpit`. Bon API duoc tai doc lap; API lich quay dau loi khong duoc lam mat danh sach tai xe, xe va ca lam viec da tai thanh cong.
- Cache: tang version static asset de trinh duyet khong giu utility JavaScript cu.

## Kiem thu

- Static UI test xac nhan viewport, breakpoint, khong dung scale/zoom va dung dung global utility.
- Test xac nhan tai du lieu bang `Promise.allSettled` va co trang thai loi tai tung panel.
- Chay toan bo frontend tests sau khi sua.
