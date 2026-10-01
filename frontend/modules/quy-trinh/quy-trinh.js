/* Quy trình & trách nhiệm — mỗi công đoạn ai làm, làm gì, máy chặn gì, IN RA PHIẾU gì, SINH CHỨNG TỪ gì.
 *
 * Hai phần dữ liệu:
 *   · KHUNG ở đây (CHUYEN, NGOAI, VIEC): công đoạn, người làm, màn, chứng từ sinh ra. Soạn theo đúng mã đang chạy (câu trả lời
 *     của anh Khampla) — thêm / bớt công đoạn thì sửa ở đây. CHỮ của từng công đoạn (tên, làm gì, máy tự làm, máy chặn, phiếu
 *     in, lúc nào sinh chứng từ, trạng thái sau) ở từ điển ngon_ngu.js, đủ ba tiếng — xem khối "chữ" bên dưới.
 *   · Lấy từ máy chủ (/api/quy-trinh): ma trận quyền, vai nào thấy / nhập tiền, và ĐỊNH KHOẢN từng loại chứng từ
 *     tính bằng chính hàm ghi sổ — nên Nợ / Có trên màn không bao giờ lệch với cái máy thật sự ghi.
 */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, D = null, xem = 'chuyen';
  const q = (s) => root.querySelector(s);

  /* ================================================================ khung: một chuyến theo giai đoạn · ngoài chuyến · việc
   * vai: mã vai · man: id màn · o: nơi làm ngoài trang này (kho · tune) · ct: mã chứng từ sinh ra (định khoản lấy từ máy chủ) */
  const CHUYEN = [
    { gd: 'qt_gd_c1', buoc: [
      { so: 1, vai: ['yard'], man: 'phieu-xuat-xe', ct: ['DO'] },
      { so: 2, vai: ['yard'], man: 'phieu-xuat-xe', ct: ['PLNL'] },
      { so: 3, vai: ['yard'], man: 'phieu-xuat-xe', ct: ['PTU'] },
      { so: 4, vai: ['yard'], man: 'phieu-xuat-xe' },
    ] },
    { gd: 'qt_gd_c2', buoc: [
      { so: 5, vai: ['acct'], man: 'phieu-xuat-xe' },
      { so: 6, vai: ['fuel', 'expacct'], man: 'phieu-xuat-xe' },
    ] },
    { gd: 'qt_gd_c3', buoc: [
      { so: 7, vai: ['depot'], man: 'cap-phat', o: 'kho', ct: ['PXK_NL'] },
      { so: 8, vai: ['expacct', 'cash'], man: 'de-nghi-chi' },
    ] },
    { gd: 'qt_gd_c4', buoc: [
      { so: 9, vai: ['driver', 'yard'], man: 'phieu-cua-toi' },
      { so: 10, vai: ['driver', 'fuel'], man: 'phieu-cua-toi' },
      { so: 11, vai: ['driver', 'repair', 'yard'], man: 'theo-doi-tuyen', ct: ['PXK_PT'] },
      { so: 12, vai: ['yard'], man: 'phieu-xuat-xe' },
      { so: 13, vai: ['yard', 'driver'], man: 'theo-doi-tuyen', ct: ['PXK_HH', 'PNK_HH'] },
    ] },
    { gd: 'qt_gd_c5', buoc: [
      { so: 14, vai: ['expacct', 'cash'], man: 'phieu-xuat-xe', ct: ['PC_SC'] },
      { so: 15, vai: ['acct'], man: 'phieu-xuat-xe', ct: ['PDT'] },
    ] },
    { gd: 'qt_gd_c6', buoc: [
      { so: 16, vai: ['rev'], man: 'de-nghi-thu', o: 'tune', ct: ['HD'] },
      { so: 17, vai: ['rev'], man: 'khach-hang', o: 'tune', ct: ['PT'] },
    ] },
    { gd: 'qt_gd_c7', buoc: [
      { so: 18, vai: ['acct', 'cash', 'treasury'], man: 'xe-lien-ket', o: 'tune', ct: ['PC_CX'] },
      { so: 19, vai: ['expacct', 'cash', 'treasury'], o: 'tune', ct: ['QT_TU', 'TT_CHI', 'TT_THU'] },
      { so: 20, vai: ['acct', 'expacct', 'rev', 'treasury', 'cash', 'admin'], man: 'chung-tu' },
    ] },
  ];
  const NGOAI = [
    { gd: 'qt_gd_n1', buoc: [
      { so: 'K1', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o: 'kho', ct: ['PNK_NL'] },
      { so: 'K2', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o: 'kho', ct: ['PNK_NL', 'PXK_NL', 'CK_NL'] },
      { so: 'K3', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o: 'kho', ct: ['CK_NL'] },
      { so: 'K4', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o: 'kho' },
    ] },
    { gd: 'qt_gd_n2', buoc: [
      { so: 'P1', vai: ['parts'], man: 'kho-phu-tung', o: 'kho', ct: ['PNK_PT', 'PXK_PT'] },
      { so: 'P2', vai: ['repair', 'expacct', 'cash'], man: 'sua-chua', o: 'kho', ct: ['PXK_PT', 'PC_SC'] },
    ] },
    { gd: 'qt_gd_n3', buoc: [
      { so: 'B1', vai: ['acct', 'rev', 'fuel'], o: 'tune', ct: ['PXK_BAN', 'HD_BAN'] },
      { so: 'B2', vai: ['rev', 'cash', 'treasury'], o: 'tune', ct: ['PT_BAN'] },
      { so: 'B3', vai: ['acct', 'rev', 'fuel', 'cash', 'treasury'], o: 'tune', ct: ['PXK_BAN', 'HD_BAN'] },
    ] },
    { gd: 'qt_gd_n4', buoc: [
      { so: 'T1', vai: ['yard'], man: 'phieu-xuat-xe', ct: ['DO', 'PNK_HH'] },
      { so: 'T2', vai: ['yard'], man: 'kho-hang', o: 'kho', ct: ['DC_HH'] },
      { so: 'T3', vai: ['yard'], man: 'phieu-xuat-xe', ct: ['DO', 'PXK_HH'] },
      { so: 'T4', vai: ['rev'], man: 'de-nghi-thu', o: 'tune', ct: ['HD', 'PT'] },
    ] },
    { gd: 'qt_gd_n5', buoc: [
      { so: 'C1', vai: ['acct', 'cash', 'treasury'], man: 'the-cao-toc' },
      { so: 'C2', vai: ['expacct'], man: 'nha-cung-cap' },
      { so: 'C3', vai: ['expacct', 'cash', 'treasury'], o: 'tune', ct: ['PC_NCC'] },
    ] },
  ];
  const VIEC = [
    ['qt_viec1', ['yard']],
    ['qt_viec2', ['acct']],
    ['qt_viec3', ['repair']],
    ['qt_viec4', ['yard']],
    ['qt_viec5', ['yard', 'fuel']],
    ['qt_viec6', ['depot', 'fuel']],
    ['qt_viec7', ['acct']],
    ['qt_viec8', ['rev']],
    ['qt_viec9', ['acct']],
    ['qt_viec10', ['acct']],
    ['qt_viec11', ['fuel', 'acct']],
    ['qt_viec12', ['parts']],
    ['qt_viec13', ['acct', 'rev', 'fuel']],
    ['qt_viec14', ['rev', 'cash', 'treasury']],
    ['qt_viec15', ['repair', 'expacct', 'cash']],
    ['qt_viec16', ['expacct', 'cash', 'treasury']],
    ['qt_viec17', ['expacct', 'cash', 'treasury']],
    ['qt_viec18', ['acct', 'cash', 'treasury']],
    ['qt_viec19', ['acct', 'rev']],
    ['qt_viec20', ['acct']],
    ['qt_viec21', ['acct', 'expacct', 'rev', 'treasury', 'cash']],
  ];

  /* ================================================================ chữ: tất cả ở từ điển (ngon_ngu.js)
   * Mỗi công đoạn một tiền tố khoá theo SỐ của nó: qt_b<số>_ten · _lam1, _lam2… · _may1… · _chan1… · _giay1… (đọc lần lượt tới
   * khi hết khoá) · _khi_<mã chứng từ> (lúc nào sinh tờ đó) · _sau (trạng thái sau bước). Nhóm: qt_gd_c<n> (một chuyến) ·
   * qt_gd_n<n> (ngoài chuyến). Việc ngoài phiếu: qt_viec<n>. Sửa nội dung luồng thì sửa ở từ điển (cả ba tiếng); thêm / bớt
   * công đoạn, đổi vai, đổi màn, đổi chứng từ thì sửa khung ở trên. Rà 01/10: trước đây cả màn viết cứng tiếng Việt — đổi
   * sang tiếng Lào / Anh vẫn ra tiếng Việt. */
  const coKhoa = (k) => NN.t(k) !== k;
  const goc = (b) => 'qt_b' + String(b.so).toLowerCase();
  const khoaDs = (b, loai) => { const ra = []; for (let i = 1; coKhoa(goc(b) + '_' + loai + i); i++) ra.push(goc(b) + '_' + loai + i); return ra; };
  const khoaKhi = (b, ma) => goc(b) + '_khi_' + ma.toLowerCase();
  const khoaSau = (b) => goc(b) + '_sau';

  /* ================================================================ vẽ */
  const tenVai = (v) => NN.h('r_' + v);
  const ctCua = (ma) => (D && D.chung_tu.find(c => c.ma === ma)) || null;
  // tên chứng từ / tên tài khoản: máy chủ gửi bản Việt và bản Lào (danh mục thật bên kế toán) — như màn Chứng từ
  const tenCt = (c) => (c ? (NN.lang === 'lo' && c.ten_lo ? c.ten_lo : c.ten) : '');
  // tên loại chứng từ đủ ba tiếng ở từ điển (qt_loai_<mã>); mã máy chủ mới thêm mà từ điển chưa có thì dùng tên máy chủ gửi
  const tenLoai = (ma, c) => (coKhoa('qt_loai_' + ma.toLowerCase()) ? NN.h('qt_loai_' + ma.toLowerCase()) : esc(c ? tenCt(c) : ma));
  const tenTk = (o, ve) => (NN.lang === 'lo' && o[ve + '_ten_lo'] ? o[ve + '_ten_lo'] : o[ve + '_ten']) || '';
  // "Trường hợp" máy chủ ghép từ mảnh tiếng Việt ("xe nhà · tiền mặt Kíp") — dịch từng mảnh, giữ dấu " · "
  const KHI = { 'xe nhà': 'qt_khi_xe_nha', 'xe liên kết': 'qt_khi_xe_lk', 'tiền mặt Kíp': 'qt_khi_tm_kip', 'tiền mặt ngoại tệ': 'qt_khi_tm_ngoai',
    'ngân hàng Kíp': 'qt_khi_nh_kip', 'ngân hàng ngoại tệ': 'qt_khi_nh_ngoai', 'sửa chữa': 'qt_khi_sua', 'chi khác': 'qt_khi_chi_khac',
    'bán cho khách': 'qt_khi_ban_khach', 'bán cho chủ xe liên kết — trừ vào tiền trả': 'qt_khi_ban_cx' };
  const khiDich = (s) => String(s || '').split(' · ').map(x => (KHI[x] ? NN.t(KHI[x]) : x)).join(' · ');
  // "Nợ 625 · 4022 / Có 1371" — gom các biến thể cho gọn; chi tiết đủ ở tab Danh mục chứng từ
  function dkGon(c) {
    if (!c || !c.dinh_khoan) return NN.t('qt_khong_dk');
    const u = (a) => [...new Set(a.filter(Boolean))];
    const no = u(c.bien_the.map(b => b.no)), co = u(c.bien_the.map(b => b.co));
    if (!no.length && !co.length) return NN.t('qt_ngoai_bang');
    return NN.t('qt_dk_gon', { no: no.join(' · ') || '—', co: co.join(' · ') || '—' });
  }
  // Mã con của khách (1371 · 4021 · 4022) chưa có trong danh mục bên kế toán — hiện rõ, đừng để người đọc tưởng là mã thật
  const chuaMo = (tt) => tt === 'ma_con_khach' ? ` <span class="qt-chua-mo" title="${esc(NN.t('qt_chua_mo_t'))}">${NN.h('qt_chua_mo')}</span>`
    : tt === 'nhom' || tt === 'khong_co' ? ` <span class="qt-chua-mo">${NN.h('qt_khong_ghi')}</span>` : '';
  const oMa = (ma, ten, tt) => `<span class="acct">${esc(ma)}</span>${chuaMo(tt)} <span class="small muted" ${NN.lang === 'lo' ? 'lang="lo"' : ''}>${esc(ten || '')}</span>`;
  const ds = (khoa, cls) => khoa.length ? `<ul class="${cls || ''}">${khoa.map(k => `<li>${NN.h(k)}</li>`).join('')}</ul>` : '';

  // Chứng từ của một bước là ĐỀ NGHỊ của trang điều xe, hay tờ bên kho / bên kế toán lập THEO đề nghị (chủ dự án 30/09:
  // trang mình chỉ làm phiếu đề nghị — kho là của anh Toàn, tiền là của anh Tune).
  const DE_NGHI = ['DO', 'PLNL', 'PTU', 'PDT'];
  const BEN_KHO = ['PXK_NL', 'PXK_PT', 'PNK_NL', 'PNK_PT', 'CK_NL', 'PNK_HH', 'PXK_HH', 'DC_HH', 'PXK_BAN'];
  const benLap = (ma) => DE_NGHI.includes(ma) ? ['de-nghi', 'qt_ben_de_nghi'] : BEN_KHO.includes(ma) ? ['kho', 'qt_ben_kho'] : ['ke-toan', 'qt_ben_ke_toan'];
  // Nút sang màn khác chỉ cho vai VÀO ĐƯỢC màn đó (sếp 30/09): không thì người không có quyền bấm sang, thấy việc — và
  // tiền — của vai khác. Máy chủ vẫn lọc tiền theo vai; đây là để không bày lối vào sai ngay trên màn.
  const vaoDuoc = (man) => AUTH.role === 'admin' || (EPL.manCuaVai(AUTH.role) || []).some(m => m.id === man);
  const tenMan = (man) => NN.t(((EPL.MODULES || []).find(m => m.id === man) || {}).nav || man);

  // Nơi làm của công đoạn không ở trang điều xe (01/10, bỏ phần tiền trang kế toán tạm): kho (cấp dầu QR, kho nhiên liệu, phụ
  // tùng, hàng gửi bãi, lệnh sửa chữa) ở KHO TẠM; tiền (hoá đơn, thu, trả chủ xe, tất toán, trả nhà cung cấp, bán hàng) ở hệ
  // kế toán anh Tune. Bước kho thì `man` là màn bên kho tạm — không bày nút sang; bước tiền có `man` là màn trang điều xe xem lại.
  const NOI = { kho: 'qt_o_kho', tune: 'qt_o_tune' };
  function theBuoc(b) {
    const ct = (b.ct || []).map(ma => {
      const c = ctCua(ma), [lop, ben] = benLap(ma);
      return `<button class="qt-ct-chip qt-ben-${lop}" data-ct="${ma}" title="${esc(NN.t('qt_ct_xem'))}">
        <b>${ma}</b> <span ${NN.lang === 'lo' ? 'lang="lo"' : ''}>${tenLoai(ma, c)}</span><em class="qt-ben">${NN.h(ben)}</em><small>${esc(dkGon(c))}</small>${coKhoa(khoaKhi(b, ma)) ? `<i>${NN.h(khoaKhi(b, ma))}</i>` : ''}</button>`;
    }).join('');
    const may = khoaDs(b, 'may'), chan = khoaDs(b, 'chan'), giay = khoaDs(b, 'giay');
    return `<article class="qt-buoc">
      <div class="qt-b-dau"><span class="so">${esc(String(b.so))}</span>
        <div class="grow"><h4>${NN.h(goc(b) + '_ten')}</h4>
          <div class="qt-b-vai">${b.vai.map(v => `<span class="qt-vai">${tenVai(v)}</span>`).join('')}
            ${b.o ? `<span class="qt-man qt-man-kt qt-o-${b.o}">${NN.h(NOI[b.o])}</span>` : ''}
            ${b.o === 'kho' || !b.man ? ''
              : vaoDuoc(b.man) ? `<button class="qt-man" data-man="${b.man}">${NN.h('qt_man', { ten: tenMan(b.man) })}</button>`
              : `<span class="qt-man qt-man-khoa" title="${esc(NN.t('qt_man_khoa_t'))}">${NN.h('qt_man_khoa', { ten: tenMan(b.man) })}</span>`}</div></div>
        ${coKhoa(khoaSau(b)) ? `<span class="qt-sau">${NN.h(khoaSau(b))}</span>` : ''}</div>
      <div class="qt-b-than">
        <div class="qt-b-cot"><div class="l">${NN.h('qt_l_lam')}</div>${ds(khoaDs(b, 'lam'))}
          ${may.length ? `<div class="l">${NN.h('qt_l_may')}</div>${ds(may, 'may')}` : ''}
          ${chan.length ? `<div class="l">${NN.h('qt_l_chan')}</div>${ds(chan, 'chan')}` : ''}</div>
        <div class="qt-b-cot qt-b-ra">
          <div class="l">${NN.h('qt_cg_giay')}</div>${giay.length ? giay.map(k => `<div class="qt-giay">${NN.h(k)}</div>`).join('') : '<div class="muted small">—</div>'}
          <div class="l">${NN.h('qt_l_ct')}</div>${ct || `<div class="muted small">${NN.h('qt_khong_ct')}</div>`}</div>
      </div></article>`;
  }
  function veLuong(dsGd, dich) {
    q(dich).innerHTML = dsGd.map((g, i) => `<section class="qt-gd"><h3><span>${i + 1}</span>${NN.h(g.gd)}</h3>${g.buoc.map(theBuoc).join('')}</section>`).join('');
  }

  // mã chứng từ → các công đoạn sinh ra nó (cho tab Danh mục)
  function noiSinh(ma) {
    const ra = [];
    [...CHUYEN, ...NGOAI].forEach(g => g.buoc.forEach(b => { if ((b.ct || []).includes(ma)) ra.push(`${b.so}. ${NN.t(goc(b) + '_ten')}`); }));
    return ra;
  }
  function veChungTu() {
    q('#qt-ct-than').innerHTML = D.chung_tu.map(c => {
      const bt = c.dinh_khoan && c.bien_the.length ? c.bien_the : [{ khi: '', no: null, co: null }];
      const sinh = noiSinh(c.ma);
      return bt.map((b, i) => `<tr id="qt-ct-${c.ma}" class="${i ? 'tiep' : 'dau'}">
        ${i ? '' : `<td rowspan="${bt.length}" class="mono"><b>${c.ma}</b></td><td rowspan="${bt.length}"><b>${tenLoai(c.ma, c)}</b>${NN.lang === 'vi' ? `<div class="small muted" lang="lo">${esc(c.ten_lo)}</div>` : ''}</td>
          <td rowspan="${bt.length}" class="small">${sinh.length ? sinh.map(esc).join('<br>') : '<span class="muted">—</span>'}</td>`}
        <td class="small">${b.khi ? esc(khiDich(b.khi)) : NN.h(c.dinh_khoan ? 'qt_moi_th' : 'qt_chi_luu')}</td>
        <td>${b.no ? oMa(b.no, tenTk(b, 'no'), b.no_tt) : (c.dinh_khoan ? `<span class="muted small">${NN.h('qt_ngoai_bang2')}</span>` : '—')}</td>
        <td>${b.co ? oMa(b.co, tenTk(b, 'co'), b.co_tt) : '—'}</td></tr>`).join('');
    }).join('');
    // nhãn dòng chi: máy chủ gửi mã nhãn (dk_dau_kho…) — chữ ở từ điển
    const cap = (x) => `<td>${oMa(x.no, tenTk(x, 'no'), x.no_tt)}</td><td>${oMa(x.co, tenTk(x, 'co'), x.co_tt)}</td>`;
    q('#qt-dc-than').innerHTML = (D.dong_chi || []).map(r => `<tr><td><b>${coKhoa(r.nhan) ? NN.h(r.nhan) : esc(r.nhan)}</b></td>${cap(r.EPL)}${cap(r.joint)}</tr>`).join('');
    const dm = D.danh_muc || {};
    q('#qt-dc-nguon').innerHTML = NN.h('qt_dc_nguon', { so: dm.so_ma || '?', ngay: dm.chup_ngay || '?' }) + ' '
      + ((dm.ma_con_khach || []).length ? NN.h('qt_dc_ma_con', { ds: dm.ma_con_khach.map(x => x.ma + ' (' + NN.t('qt_con_cua', { cha: x.cha }) + ')').join(' · ') })
        : NN.h('qt_dc_da_mo'));
  }

  // "Được nhập đơn giá" THẬT: luật cho phép (nhap_gia) VÀ vai đó nhập hoặc kiểm ít nhất một mục chi III–VI
  const nhapGiaThat = (v) => D.tien[v].nhap_gia && ['fuel', 'travel', 'repair', 'other'].some(m => D.quyen[v].edit.includes(m) || D.quyen[v].verify.includes(m));
  function veMaTran() {
    const vai = D.vai.filter(v => v !== 'admin');
    const dau = (khoa) => `<tr><th>${NN.h(khoa)}</th>${vai.map(v => `<th>${tenVai(v)}</th>`).join('')}</tr>`;
    q('#qt-mt-dau').innerHTML = dau('qt_mt_muc');
    const MUC = ['info', 'trans', 'fuel', 'travel', 'repair', 'other'];
    // N · K · G · C (nhập · kiểm · ghi sổ · chi) — chữ viết tắt theo tiếng đang dùng, khớp dòng chú giải dưới bảng
    const o = (v, m) => { const p = D.quyen[v]; const viec = [['edit', 'qt_vt_n'], ['verify', 'qt_vt_k'], ['book', 'qt_vt_g'], ['pay', 'qt_vt_c']].filter(([k]) => p[k].includes(m));
      const loai = !viec.length ? 'trong' : viec[0][0] === 'edit' ? 'nhap' : viec[0][0] === 'pay' ? 'chi' : 'kiem';
      return `<td class="qt-o ${loai}">${viec.length ? viec.map(x => esc(NN.t(x[1]))).join(' ') : '—'}</td>`; };
    const co = (b) => `<td class="qt-o ${b ? 'nhap' : 'trong'}">${b ? '✓' : '✗'}</td>`;
    q('#qt-mt-than').innerHTML = MUC.map(m => `<tr><td><b>${NN.h('qt_mt_m_' + m)}</b></td>${vai.map(v => o(v, m)).join('')}</tr>`).join('')
      + `<tr class="qt-mt-nhom"><td colspan="${vai.length + 1}">${NN.h('qt_mt_tien')}</td></tr>`
      + [['thay_tien_ban', 'qt_mt_thay_ban'], ['thay_tien_chi', 'qt_mt_thay_chi'], ['thay_gia_kho', 'qt_mt_gia_kho'], ['nhap_gia', 'qt_mt_nhap_gia']]
        .map(([k, khoa]) => `<tr><td>${NN.h(khoa)}</td>${vai.map(v => co(k === 'nhap_gia' ? nhapGiaThat(v) : D.tien[v][k])).join('')}</tr>`).join('');
    q('#qt-mt2-dau').innerHTML = dau('qt_mt_viec');
    q('#qt-mt2-than').innerHTML = VIEC.map(([khoa, ai]) => `<tr><td>${NN.h(khoa)}</td>${vai.map(v => co(ai.includes(v))).join('')}</tr>`).join('');
  }

  function doiXem(x) {
    xem = x;
    root.querySelectorAll('.qt-tab button').forEach(b => b.classList.toggle('active', b.dataset.xem === x));
    ['chuyen', 'ngoai', 'ma-tran', 'chung-tu'].forEach(k => { q('#qt-' + k).hidden = k !== x; });
  }
  function noiNut() {
    root.querySelectorAll('[data-man]').forEach(b => b.addEventListener('click', () => EPL.di(b.dataset.man)));
    root.querySelectorAll('[data-ct]').forEach(b => b.addEventListener('click', () => {
      doiXem('chung-tu');
      const tr = q('#qt-ct-' + b.dataset.ct);
      if (tr) { root.querySelectorAll('.qt-ctb tr.soi').forEach(x => x.classList.remove('soi')); root.querySelectorAll('#qt-ct-' + b.dataset.ct).forEach(x => x.classList.add('soi')); tr.scrollIntoView({ block: 'center' }); }
    }));
  }
  function veHet() { veLuong(CHUYEN, '#qt-chuyen-ds'); veLuong(NGOAI, '#qt-ngoai-ds'); veMaTran(); veChungTu(); noiNut(); doiXem(xem); }

  EPL.modules['quy-trinh'] = {
    async init(r) {
      root = r; xem = 'chuyen';
      root.querySelectorAll('.qt-tab button').forEach(b => b.addEventListener('click', () => doiXem(b.dataset.xem)));
      q('#qt-mo-so').addEventListener('click', () => EPL.di('chung-tu', { tab: 'so' }));
      D = await API.get('/api/quy-trinh');
      veHet();
    },
    onLang() { if (root && D) veHet(); },
    // cho màn Tài khoản dùng lại: vai này sinh những chứng từ nào, làm những công đoạn nào — tên công đoạn đã dịch
    buocCuaVai(v) { return EPL.QUY_TRINH.CHUYEN.concat(EPL.QUY_TRINH.NGOAI).flatMap(g => g.buoc).filter(b => b.vai.includes(v)); },
  };
  // Màn Tài khoản đọc `ten` của công đoạn và `[tên, vai]` của việc: trả bản ĐÃ DỊCH theo tiếng đang dùng (getter — đổi tiếng
  // là đọc lại ra tiếng mới), giữ đúng dạng cũ để màn đó không phải đổi.
  const dichNhom = (dsGd) => dsGd.map(g => ({ gd: NN.t(g.gd), buoc: g.buoc.map(b => Object.assign({}, b, { ten: NN.t(goc(b) + '_ten') })) }));
  EPL.QUY_TRINH = {
    get CHUYEN() { return dichNhom(CHUYEN); },
    get NGOAI() { return dichNhom(NGOAI); },
    get VIEC() { return VIEC.map(([k, ai]) => [NN.t(k), ai]); },
  };
})();
