/* Biên bản giao nhận hàng (POD) — ໃບເຊັນຮັບສິນຄ້າ. Tờ in / lưu PDF gửi khách (chốt 24/09): thông tin chuyến, hàng,
 * cân, người nhận, tình trạng, CHỮ KÝ, ảnh biên bản, giờ ký, vị trí. Mở một cửa sổ riêng rồi gọi in — người dùng chọn
 * "Lưu thành PDF" trong hộp in (chữ Lào in đúng dấu, không nhúng phông). Không có số tiền nào trên tờ này.
 *
 *   EPL.bienBan.in(P, dsTep)   P = gói phiếu (/api/trips/{id}), dsTep = /api/trips/{id}/tep
 */
(function () {
  const { NN, esc } = EPL;
  const T = (k) => esc(NN.t(k));

  function html(P, tep) {
    const tk = encodeURIComponent(EPL.API.token());
    const ky = tep.filter(t => t.kind === 'pod_sign'), anh = tep.filter(t => t.kind === 'pod');
    const hang = (P.goods || []).filter(g => g.loai !== 'hao_hut');
    const o = (nhan, gt) => `<div class="o"><span>${nhan}</span><b>${gt || '—'}</b></div>`;
    const luc = P.pod_at ? EPL.ngayGio(P.pod_at) : EPL.ngay(P.pod_date);
    const viTri = P.pod_lat != null ? `<a href="https://maps.google.com/?q=${P.pod_lat},${P.pod_lng}">${Number(P.pod_lat).toFixed(5)}, ${Number(P.pod_lng).toFixed(5)}</a>` : '';
    const tt = P.pod_condition ? T('gh_tt_' + P.pod_condition) : '';
    return `<!doctype html><html lang="${esc(document.documentElement.lang || 'vi')}"><head><meta charset="utf-8">
<title>${esc(P.pod_no || 'POD')} · ${esc(P.doc_no)}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&family=Noto+Sans+Lao:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  @page{size:A4 portrait;margin:14mm}
  *{box-sizing:border-box} body{font-family:'Be Vietnam Pro','Noto Sans Lao',system-ui,sans-serif;color:#1c2229;font-size:12.5px;margin:0}
  [lang="lo"],.lo{font-family:'Noto Sans Lao','Be Vietnam Pro',sans-serif}
  header{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #145C4A;padding-bottom:8px;margin-bottom:12px}
  header h1{margin:0;font-size:18px} header .sub{color:#4a5560;font-size:12px}
  header .so{font-family:ui-monospace,Consolas,monospace;font-size:14px;font-weight:700;text-align:right}
  .luoi{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;margin-bottom:12px}
  .o{display:flex;justify-content:space-between;gap:10px;border-bottom:1px dotted #c9d1cc;padding:3px 0}
  .o span{color:#4a5560} .o b{text-align:right}
  h2{font-size:13px;margin:14px 0 6px;color:#145C4A;text-transform:uppercase;letter-spacing:.04em}
  table{width:100%;border-collapse:collapse} th,td{border:1px solid #c9d1cc;padding:5px 7px;text-align:left} th{background:#eef3f0}
  td.num,th.num{text-align:right}
  .tt{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:700}
  .tt.du{background:#DDEDE6;color:#145C4A} .tt.thieu{background:#F6E9D0;color:#A86B12} .tt.hong{background:#F5DDDD;color:#A83232}
  .ky{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:10px}
  .ky .khung{border:1px solid #c9d1cc;border-radius:8px;padding:8px;min-height:130px;text-align:center}
  .ky img{max-width:100%;max-height:120px}
  .ky .ten{margin-top:6px;font-weight:600}
  .anh{display:flex;flex-wrap:wrap;gap:8px} .anh img{height:150px;border:1px solid #c9d1cc;border-radius:6px}
  .chan{margin-top:16px;color:#7a858f;font-size:11px}
  a{color:#145C4A}
  @media screen{body{max-width:820px;margin:24px auto;padding:0 20px}}
</style></head><body>
<header><div><h1>${T('pod_title')}</h1><div class="sub">EPL · ${T('nav_dispatch')}</div></div>
  <div class="so">${esc(P.pod_no || '')}<div class="sub">${esc(P.doc_no)}</div></div></header>
<div class="luoi">
  ${o(T('customer'), `<span lang="lo">${esc(P.customer_name || '')}</span>`)}
  ${o(T('hd_van_chuyen'), esc(P.contract_no || ''))}
  ${o(T('route'), `<span lang="lo">${esc(P.origin || '')} → ${esc(P.destination || '')}</span>`)}
  ${o(T('truck_no'), `${esc(P.truck_no || '')} · <span lang="lo">${esc(P.plate_head || '')}${P.plate_trailer ? ' / ' + esc(P.plate_trailer) : ''}</span>`)}
  ${o(T('driver'), `<span lang="lo">${esc(P.driver_name || '')}</span>`)}
  ${o(T('d_out'), EPL.ngay(P.out_date))}
</div>
<h2>${T('goods_lines')}</h2>
<table><thead><tr><th>${T('goods_name')}</th><th class="num">${T('qty_t')}</th></tr></thead><tbody>
  ${hang.length ? hang.map(g => `<tr><td lang="lo">${esc(g.goods_name || '')}</td><td class="num">${EPL.so(g.qty_t, 2)}</td></tr>`).join('') : `<tr><td colspan="2">—</td></tr>`}
  <tr><td>${T('w_origin')}</td><td class="num">${P.weight_origin != null ? EPL.so(P.weight_origin, 2) + ' t' : '—'}</td></tr>
  <tr><td>${T('w_dest')}</td><td class="num">${P.weight_dest != null ? EPL.so(P.weight_dest, 2) + ' t' : '—'}</td></tr>
</tbody></table>
<h2>${T('gh_nhan_hang')}</h2>
<div class="luoi">
  ${o(T('pod_receiver'), `<span lang="lo">${esc(P.pod_receiver || '')}</span>`)}
  ${o(T('gh_sdt'), esc(P.pod_phone || ''))}
  ${o(T('gh_tinh_trang'), tt ? `<span class="tt ${esc(P.pod_condition)}">${tt}</span>` : '')}
  ${o(T('gh_luc'), luc)}
  ${o(T('gh_vi_tri'), viTri)}
  ${o(T('note'), `<span lang="lo">${esc(P.pod_note || '')}</span>`)}
</div>
<div class="ky">
  <div class="khung"><div>${T('gh_chu_ky_nhan')}</div>${ky.length ? `<img src="${esc(ky[ky.length - 1].url)}?tk=${tk}" alt="">` : '<div style="height:90px"></div>'}
    <div class="ten" lang="lo">${esc(P.pod_receiver || '')}</div></div>
  <div class="khung"><div>${T('gh_tai_xe_giao')}</div><div style="height:90px"></div><div class="ten" lang="lo">${esc(P.driver_name || '')}</div></div>
</div>
${anh.length ? `<h2>${T('pod_anh')}</h2><div class="anh">${anh.filter(a => a.la_anh).map(a => `<img src="${esc(a.url)}?tk=${tk}" alt="">`).join('')}</div>` : ''}
<div class="chan">${T('gh_chan')} ${esc(P.pod_by || '')} · ${luc}</div>
<script>window.onload=function(){setTimeout(function(){window.print()},400)}<\/script>
</body></html>`;
  }

  EPL.bienBan = {
    in(P, tep) {
      const w = window.open('', '_blank');
      if (!w) return EPL.toast(NN.t('gh_mo_cua_so'), 'loi');
      w.document.open(); w.document.write(html(P, tep || [])); w.document.close();
    },
  };
})();
