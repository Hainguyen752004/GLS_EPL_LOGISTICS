/* Xuất báo cáo — Excel thật (.xlsx) và PDF, dùng chung cho mọi màn (yêu cầu chủ dự án 23/09).
 *
 * Excel: tự ghi tệp .xlsx (zip không nén + XML của Excel) — KHÔNG dùng thư viện ngoài, nên vẫn chạy khi mất mạng
 * và mở được bằng Excel 2007 trở lên. Đọc ĐÚNG những bảng đang hiện trên màn: cột tiền mà vai đó không được thấy
 * (lớp .tien / .tien-chi bị ẩn) thì cũng không lọt vào tệp. Số giữ là SỐ (cộng trừ được trong Excel), đơn vị và
 * tiền tệ của từng ô đi theo định dạng ô — "1,693.30 USD" thành 1693.3 với định dạng #,##0.00 "USD".
 *
 * PDF: đi qua bộ in của trình duyệt (chọn "Lưu thành PDF") — cách duy nhất in chữ Lào đúng dấu mà không nhúng
 * phông vài MB. Màn báo cáo in khổ ngang kèm đầu trang (tên báo cáo · bộ lọc · người xuất · lúc xuất); màn đang
 * mở một tờ phiếu (phiếu xuất xe, hoá đơn, chứng từ…) thì giữ nguyên khổ in phiếu của nó.
 *
 * Màn nào muốn tự quyết nội dung thì khai EPL.modules[id].xuatExcel() trả về danh sách sheet (xem SHEET bên dưới).
 */
(function () {
  const { NN } = EPL;
  const enc = new TextEncoder();

  /* ------------------------------------------------------------------ zip không nén */
  const BANG_CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = (b) => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = BANG_CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  function zip(tep) {                        // tep: [[tên, chuỗi]]
    const phan = [], trungTam = []; let vt = 0;
    const d = new Date(), gio = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
      ngay = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    for (const [ten, noiDung] of tep) {
      const tn = enc.encode(ten), dl = enc.encode(noiDung), crc = crc32(dl);
      const dau = new DataView(new ArrayBuffer(30));
      [[0, 0x04034b50, 4], [4, 20, 2], [6, 0x0800, 2], [8, 0, 2], [10, gio, 2], [12, ngay, 2], [14, crc, 4], [18, dl.length, 4], [22, dl.length, 4], [26, tn.length, 2], [28, 0, 2]]
        .forEach(([o, v, n]) => n === 4 ? dau.setUint32(o, v, true) : dau.setUint16(o, v, true));
      phan.push(new Uint8Array(dau.buffer), tn, dl);
      const tt = new DataView(new ArrayBuffer(46));
      [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, 0x0800, 2], [10, 0, 2], [12, gio, 2], [14, ngay, 2], [16, crc, 4], [20, dl.length, 4], [24, dl.length, 4], [28, tn.length, 2],
        [30, 0, 2], [32, 0, 2], [34, 0, 2], [36, 0, 2], [38, 0, 4], [42, vt, 4]]
        .forEach(([o, v, n]) => n === 4 ? tt.setUint32(o, v, true) : tt.setUint16(o, v, true));
      trungTam.push(new Uint8Array(tt.buffer), tn);
      vt += 30 + tn.length + dl.length;
    }
    const coTT = trungTam.reduce((a, b) => a + b.length, 0);
    const cuoi = new DataView(new ArrayBuffer(22));
    [[0, 0x06054b50, 4], [4, 0, 2], [6, 0, 2], [8, tep.length, 2], [10, tep.length, 2], [12, coTT, 4], [16, vt, 4], [20, 0, 2]]
      .forEach(([o, v, n]) => n === 4 ? cuoi.setUint32(o, v, true) : cuoi.setUint16(o, v, true));
    return new Blob([...phan, ...trungTam, new Uint8Array(cuoi.buffer)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }

  /* ------------------------------------------------------------------ xlsx */
  const x = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '');
  const tenCot = (i) => { let s = ''; i++; while (i) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; };
  const tenSheet = (s, daCo) => {
    let t = String(s || 'Sheet').replace(/[\[\]:*?/\\]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 31) || 'Sheet';
    let n = 2; const goc = t; while (daCo.has(t.toLowerCase())) t = (goc.slice(0, 28) + ' ' + n++);
    daCo.add(t.toLowerCase()); return t;
  };

  /* Kiểu ô (chỉ số cellXfs): 0 thường · 1 đầu cột · 2 tên báo cáo · 3 chữ có viền · 4 dòng phụ · 5 chữ dòng tổng ·
     6+ số theo định dạng (thường / đậm cho dòng tổng) — sinh động theo các định dạng thật sự gặp. */
  function kieuSo(dsDinhDang) {
    const numFmts = dsDinhDang.map((f, i) => `<numFmt numFmtId="${164 + i}" formatCode="${x(f)}"/>`).join('');
    const xfSo = dsDinhDang.map((f, i) => `<xf numFmtId="${164 + i}" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>`
      + `<xf numFmtId="${164 + i}" fontId="1" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>`).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
${dsDinhDang.length ? `<numFmts count="${dsDinhDang.length}">${numFmts}</numFmts>` : ''}
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font><font><i/><sz val="10"/><color rgb="FF5B6770"/><name val="Calibri"/></font></fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE3EDE7"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF3F5F4"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"><color rgb="FFC9D1CC"/></left><right style="thin"><color rgb="FFC9D1CC"/></right><top style="thin"><color rgb="FFC9D1CC"/></top><bottom style="thin"><color rgb="FFC9D1CC"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="${6 + dsDinhDang.length * 2}">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
${xfSo}
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;
  }

  /** SHEET = { ten, tieuDe: [dòng chữ trên đầu], dong: [[ô]], soDongDau: số dòng đầu cột, dongTong: Set chỉ số dòng tổng,
   *            gop: ['A5:C5'] } — ô là chuỗi, số, null, hoặc { v: số, f: 'định dạng' } / { d: số ngày Excel, f }. */
  function taoXlsx(sheets) {
    const dinhDang = [], viTri = new Map();
    const idSo = (f, dam) => { if (!viTri.has(f)) { viTri.set(f, dinhDang.length); dinhDang.push(f); } return 6 + viTri.get(f) * 2 + (dam ? 1 : 0); };
    const daCo = new Set(), xmlSheets = [], ten = [], loc = [];
    sheets.forEach((sh, si) => {
      const dau = sh.tieuDe || [], batDau = dau.length ? dau.length + 1 : 0;       // một dòng trống giữa đầu trang và bảng
      const soCot = Math.max(1, ...sh.dong.map(r => r.length));
      const rong = new Array(soCot).fill(8);
      const hang = [];
      dau.forEach((t, i) => hang.push(`<row r="${i + 1}"><c r="A${i + 1}" t="inlineStr" s="${i === 0 ? 2 : 4}"><is><t xml:space="preserve">${x(t)}</t></is></c></row>`));
      sh.dong.forEach((r, ri) => {
        const so = batDau + ri + 1, laDau = ri < (sh.soDongDau || 0), laTong = sh.dongTong && sh.dongTong.has(ri);
        const o = r.map((c, ci) => {
          const ref = tenCot(ci) + so;
          if (c === null || c === undefined || c === '') return laDau || laTong ? `<c r="${ref}" s="${laDau ? 1 : 5}"/>` : `<c r="${ref}" s="3"/>`;
          if (typeof c === 'number') c = { v: c, f: Number.isInteger(c) ? '#,##0' : '#,##0.##' };
          if (typeof c === 'object' && (c.v !== undefined || c.d !== undefined)) {
            const v = c.v !== undefined ? c.v : c.d;
            rong[ci] = Math.max(rong[ci], Math.min(24, String(Math.round(Math.abs(v))).length + 6 + (c.f.match(/"([^"]*)"/) || ['', ''])[1].length));
            return `<c r="${ref}" s="${laDau ? 1 : idSo(c.f, laTong)}"><v>${v}</v></c>`;
          }
          const s = String(c);
          const dai = Math.max(...s.split('\n').map(l => [...l].length));
          rong[ci] = Math.max(rong[ci], Math.min(laDau ? 28 : 48, dai + 2));
          return `<c r="${ref}" t="inlineStr" s="${laDau ? 1 : laTong ? 5 : 3}"><is><t xml:space="preserve">${x(s)}</t></is></c>`;
        }).join('');
        hang.push(`<row r="${so}">${o}</row>`);
      });
      const hangDau = batDau + (sh.soDongDau || 0);
      const cuoiBang = batDau + sh.dong.length;
      const vung = sh.soDongDau && sh.dong.length > sh.soDongDau ? `A${hangDau}:${tenCot(soCot - 1)}${cuoiBang}` : '';
      const gop = [...(sh.gop || []).map(g => g.replace(/(\d+)/g, (_, n) => String(Number(n) + batDau))),
        ...dau.map((_, i) => `A${i + 1}:${tenCot(Math.max(0, Math.min(soCot, 8) - 1))}${i + 1}`)].filter(g => !/^([A-Z]+)(\d+):\1\2$/.test(g));
      const ghim = hangDau ? `<pane ySplit="${hangDau}" topLeftCell="A${hangDau + 1}" activePane="bottomLeft" state="frozen"/>` : '';
      const tenS = tenSheet(sh.ten, daCo); ten.push(tenS);
      if (vung) loc.push(`<definedName name="_xlnm._FilterDatabase" localSheetId="${si}" hidden="1">'${x(tenS.replace(/'/g, "''"))}'!$${vung.replace(':', ':$').replace(/([A-Z]+)(\d+)/g, '$1$$$2')}</definedName>`);
      xmlSheets.push(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheetViews><sheetView workbookViewId="0">${ghim}</sheetView></sheetViews>
<cols>${rong.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join('')}</cols>
<sheetData>${hang.join('')}</sheetData>
${vung ? `<autoFilter ref="${vung}"/>` : ''}
${gop.length ? `<mergeCells count="${gop.length}">${gop.map(g => `<mergeCell ref="${g}"/>`).join('')}</mergeCells>` : ''}
<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>
<pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>
</worksheet>`);
    });
    const tep = [
      ['[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
${xmlSheets.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')}</Types>`],
      ['_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>`],
      ['docProps/core.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:creator>EPL</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString().slice(0, 19)}Z</dcterms:created></cp:coreProperties>`],
      ['xl/workbook.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${ten.map((t, i) => `<sheet name="${x(t)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')}</sheets>${loc.length ? `<definedNames>${loc.join('')}</definedNames>` : ''}</workbook>`],
      ['xl/_rels/workbook.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${xmlSheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')}<Relationship Id="rId${xmlSheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
      ...xmlSheets.map((s, i) => [`xl/worksheets/sheet${i + 1}.xml`, s]),
    ];
    tep.splice(4, 0, ['xl/styles.xml', kieuSo(dinhDang)]);         // styles cuối cùng mới biết đủ định dạng
    return zip(tep);
  }

  /* ------------------------------------------------------------------ đọc bảng trên màn */
  const hien = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  const BO_QUA = 'button, .btn, svg, .no-print, script, style, template, .xuat-bo';
  const KHOI = /^(DIV|P|LI|TR|BR|H[1-6]|SECTION|UL|OL|TABLE)$/;
  /** Chữ NGƯỜI ĐỌC thấy trong ô — bỏ nút, ô ẩn; ô nhập lấy giá trị; khối con xuống dòng. */
  function chu(el) {
    let s = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { s += n.nodeValue; continue; }
      if (n.nodeType !== 1 || n.matches(BO_QUA) || !hien(n)) continue;
      if (n.tagName === 'BR') { s += '\n'; continue; }
      if (n.tagName === 'SELECT') { s += n.selectedIndex >= 0 ? n.options[n.selectedIndex].text : ''; continue; }
      if (n.tagName === 'INPUT') { if (!/^(button|submit|checkbox|radio|file|hidden)$/.test(n.type)) s += n.value; else if (n.type === 'checkbox') s += n.checked ? '✓' : ''; continue; }
      if (n.tagName === 'TEXTAREA') { s += n.value; continue; }
      const t = chu(n);
      s += KHOI.test(n.tagName) && s && t ? '\n' + t : t;
    }
    return s;
  }
  const gon = (s) => s.split('\n').map(l => l.replace(/\s+/g, ' ').trim()).filter(Boolean).join('\n');

  /** Chuỗi hiển thị → ô Excel. "1,693.30 USD" → số + định dạng "USD"; "23/09/2026" → ngày; "12.5%" → phần trăm. */
  const DON_VI = /^(LAK|USD|THB|VND|VNĐ|CNY|L|t|km|kg|ngày|ວັນ|ໂຕນ|lít|m³)$/;
  function sangO(s) {
    const t = s.trim();
    if (!t || t === '—' || t === '-') return null;
    if (t.includes('\n')) return t;
    let m = t.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?$/);
    if (m) {
      const ms = Date.UTC(+m[3], +m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0));
      if (!isNaN(ms)) return { d: +(ms / 86400000 + 25569).toFixed(6), f: m[4] ? 'dd/mm/yyyy hh:mm' : 'dd/mm/yyyy' };
    }
    m = t.match(/^([+\-−]?)\s?([\d,]*\d)(?:\.(\d+))?\s*(%|[^\d\s].{0,5})?$/);
    if (!m) return t;
    const [, dau, nguyen, le = '', dv = ''] = m;
    if (!/^\d{1,3}(,\d{3})*$|^\d+$/.test(nguyen)) return t;                       // "625/1371", "20,5" … giữ chữ
    if (!nguyen.includes(',') && nguyen.length > 1 && nguyen[0] === '0' && !le) return t;   // mã có số 0 đầu
    if (dv && dv !== '%' && !DON_VI.test(dv.trim())) return t;
    if (!nguyen.includes(',') && nguyen.length >= 16) return t;                     // số điện thoại / mã dài
    let v = Number((dau && dau !== '+' ? '-' : '') + nguyen.replace(/,/g, '') + (le ? '.' + le : ''));
    if (!isFinite(v)) return t;
    const soLe = le.length, mau = '#,##0' + (soLe ? '.' + '0'.repeat(soLe) : '');
    if (dv === '%') return { v: v / 100, f: '0' + (soLe ? '.' + '0'.repeat(soLe) : '') + '%' };
    return { v, f: dv ? `${mau} "${dv.trim()}"` : mau };
  }

  /** Một bảng HTML → lưới ô (có colspan/rowspan), chỉ phần đang hiện. */
  function docBang(tb) {
    const hangHtml = [...tb.rows].filter(r => hien(r) && !r.matches('.no-print'));
    const luoi = [], gop = [], dongTong = new Set();
    let soDongDau = 0;
    hangHtml.forEach((tr, ri) => {
      luoi[ri] = luoi[ri] || [];
      const laDau = tr.parentElement.tagName === 'THEAD' || (ri === soDongDau && [...tr.cells].every(c => c.tagName === 'TH') && tr.parentElement.tagName !== 'TFOOT');
      if (laDau && ri === soDongDau) soDongDau++;
      if (tr.parentElement.tagName === 'TFOOT' || tr.matches('.tong, .total, .dong-tong')) dongTong.add(ri);
      let ci = 0;
      for (const td of tr.cells) {
        if (!hien(td) || td.matches('.no-print')) continue;
        while (luoi[ri][ci] !== undefined) ci++;
        const cs = Math.max(1, td.colSpan || 1), rs = Math.max(1, td.rowSpan || 1);
        const s = gon(chu(td));
        const o = td.classList.contains('empty') ? s : (laDau ? s : sangO(s));
        for (let a = 0; a < rs; a++) for (let b = 0; b < cs; b++) {
          luoi[ri + a] = luoi[ri + a] || [];
          luoi[ri + a][ci + b] = (a === 0 && b === 0) ? o : '';
        }
        if (cs > 1 || rs > 1) gop.push(`${tenCot(ci)}${ri + 1}:${tenCot(ci + cs - 1)}${ri + rs}`);
        ci += cs;
      }
    });
    // bỏ cột trống từ đầu tới cuối (cột nút bấm)
    const soCot = Math.max(0, ...luoi.map(r => r.length));
    const giu = [...Array(soCot).keys()].filter(c => luoi.some(r => r[c] !== undefined && r[c] !== '' && r[c] !== null));
    const dong = luoi.map(r => giu.map(c => r[c] === undefined ? '' : r[c]));
    const doiCot = new Map(giu.map((c, i) => [c, i]));
    const gopMoi = gop.map(g => g.replace(/([A-Z]+)(\d+)/g, (_, c, n) => {
      let i = 0; for (const ch of c) i = i * 26 + ch.charCodeAt(0) - 64; i--;
      let gan = i; while (gan >= 0 && !doiCot.has(gan)) gan--;
      return tenCot(Math.max(0, doiCot.has(gan) ? doiCot.get(gan) : 0)) + n;
    })).filter(g => { const [a, b] = g.split(':'); return a !== b; });
    // Cột ghi tiền tệ ở ĐẦU CỘT ("Thành tiền (LAK)", "Quy về Kíp") → ô số trong cột mang định dạng tiền tệ đó
    for (let c = 0; c < giu.length; c++) {
      const dau = dong.slice(0, soDongDau).map(r => String(r[c] || '')).join(' ');
      const m = dau.match(/\((LAK|USD|THB|VND|CNY)\)|(LAK|USD|THB|VND|CNY)|(Kíp|ກີບ)/);
      if (!m) continue;
      const ma = m[1] || m[2] || 'LAK';
      for (let r = soDongDau; r < dong.length; r++) {
        const o = dong[r][c];
        if (o && typeof o === 'object' && o.v !== undefined && !/"/.test(o.f)) o.f += ` "${ma}"`;
      }
    }
    // Bảng chỉ còn dòng báo trống ("Tháng này không có phiếu…") — một ô duy nhất trải qua nhiều cột
    const than = dong.slice(soDongDau);
    const trong = than.length > 0 && than.every(r => r.filter(o => o !== '' && o !== null).length <= 1) && gopMoi.length > 0 && than.length <= 1;
    return { dong, soDongDau, dongTong, gop: gopMoi, trong };
  }

  const goc = () => document.querySelector('#noi-dung .mod-root') || document.getElementById('noi-dung');
  const tieuDeMan = () => { const h = document.getElementById('pageTitle'); if (!h) return 'EPL'; const c = h.cloneNode(true); c.querySelectorAll('.sub').forEach(e => e.remove()); return c.textContent.trim() || 'EPL'; };
  function tenBang(tb, i) {
    const the = tb.closest('.card, section, .panel, .tab-noi-dung');
    const h = the && the.querySelector('h3, h4, .hd b, .hd .t');
    const t = h && hien(h) ? gon(chu(h)).split('\n')[0] : '';
    return t || (tieuDeMan() + (i ? ' ' + (i + 1) : ''));
  }

  /** Bộ lọc đang chọn trên màn (ô chọn / ô tìm ngoài bảng) → một dòng chữ cho đầu báo cáo. */
  function boLoc(r) {
    const ra = [];
    r.querySelectorAll('select, input[type="search"], input[type="text"], input[type="date"]').forEach(o => {
      if (!hien(o) || o.closest('table, dialog, .hop-thoai, form.px-phieu, .px-phieu')) return;
      const gt = o.tagName === 'SELECT' ? (o.selectedIndex >= 0 ? o.options[o.selectedIndex].text : '') : o.value;
      if (!gt || !gt.trim()) return;
      const nhan = (o.id && r.querySelector(`label[for="${o.id}"]`)) || (o.closest('.field, label, .tx-field') || {}).querySelector?.('label, .lb, span:not(.sub)');
      const tn = nhan && nhan !== o ? gon(chu(nhan)).split('\n')[0] : '';
      ra.push((tn && tn !== gt ? tn + ': ' : '') + gt.trim());
    });
    return [...new Set(ra)].slice(0, 8).join(' · ');
  }
  function nguoiXuat() {
    const u = (EPL.AUTH && EPL.AUTH.user) || {};
    const bay = new Date(), hai = (n) => String(n).padStart(2, '0');
    const luc = `${hai(bay.getDate())}/${hai(bay.getMonth() + 1)}/${bay.getFullYear()} ${hai(bay.getHours())}:${hai(bay.getMinutes())}`;
    return `${NN.t('xuat_nguoi')}: ${u.full_name || u.username || '—'} · ${NN.t('xuat_luc')}: ${luc}`;
  }
  const tenTep = (duoi) => {
    const bo = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D');
    const t = bo(tieuDeMan()).replace(/[^\w຀-໿]+/g, '-').replace(/^-|-$/g, '') || 'bao-cao';
    return `EPL_${t}_${new Date().toISOString().slice(0, 10)}.${duoi}`;
  };

  /** Các sheet mặc định: mỗi bảng đang hiện một sheet; màn không có bảng thì lấy các ô số (.kpi). */
  function sheetMacDinh(r) {
    const loc = boLoc(r), dau = [`EPL · ${tieuDeMan()}`, ...(loc ? [`${NN.t('xuat_loc')}: ${loc}`] : []), nguoiXuat()];
    const bang = [...r.querySelectorAll('table')].filter(tb => hien(tb) && !tb.closest('dialog, .hop-thoai, .leaflet-container') && !tb.parentElement.closest('table'));
    const ds = bang.map((tb, i) => ({ ten: tenBang(tb, i), tieuDe: [dau[0] + (bang.length > 1 ? ' — ' + tenBang(tb, i) : ''), ...dau.slice(1)], ...docBang(tb) }))
      .filter(s => s.dong.length > s.soDongDau);
    const coSo = ds.filter(s => !s.trong);
    if (coSo.length) return coSo;
    if (ds.length) return ds;
    const o = [...r.querySelectorAll('.kpi, [data-xuat-o]')].filter(hien).map(k => {
      const l = k.querySelector('.l, .lb, .nhan'), v = k.querySelector('.v, .so, .gt');
      return l && v ? [gon(chu(l)), sangO(gon(chu(v)).replace(/\n/g, ' '))] : null;
    }).filter(Boolean);
    return o.length ? [{ ten: tieuDeMan(), tieuDe: dau, dong: [[NN.t('xuat_chi_tieu'), NN.t('xuat_gia_tri')], ...o], soDongDau: 1 }] : [];
  }

  EPL.xuatExcel = async () => {
    const r = goc(); const mod = EPL.modules[r && r.dataset.mod];
    let ds;
    try { ds = mod && mod.xuatExcel ? await mod.xuatExcel(r) : sheetMacDinh(r); } catch (e) { return EPL.baoLoi(e); }
    if (!ds || !ds.length) return EPL.toast(NN.t('xuat_khong_co'), 'loi');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(taoXlsx(ds)); a.download = tenTep('xlsx');
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    EPL.toast(`${NN.t('xuat_da_tai')} · ${a.download}`, 'ok');
  };
  EPL._xlsx = { taoXlsx, sangO, docBang, sheetMacDinh };      // cho bộ kiểm

  /* Cho màn tự dựng sheet từ dữ liệu của nó (màn vẽ bằng thẻ, không có bảng):
       EPL.xuatSheet('Theo xe', ['Xe', 'Số chuyến', …], [[…], …], { tong: [...] })
     Ô tiền: EPL.oTien(so, 'USD') — số thật, định dạng mang tiền tệ của chính chứng từ đó. */
  EPL.oTien = (v, ma) => (v === null || v === undefined || v === '' || isNaN(Number(v))) ? null
    : { v: Number(v), f: `#,##0${EPL.leTien(ma) ? '.00' : ''} "${String(ma || 'LAK').toUpperCase()}"` };
  EPL.oSo = (v, d = 0, dv = '') => (v === null || v === undefined || v === '' || isNaN(Number(v))) ? null
    : { v: Number(v), f: `#,##0${d ? '.' + '0'.repeat(d) : ''}${dv ? ` "${dv}"` : ''}` };
  EPL.oNgay = (s) => { if (!s) return null; const [y, m, d] = String(s).slice(0, 10).split('-').map(Number); return y ? { d: Date.UTC(y, m - 1, d) / 86400000 + 25569, f: 'dd/mm/yyyy' } : String(s); };
  EPL.xuatSheet = (ten, cot, dong, tuy = {}) => {
    const r = goc(), loc = r ? boLoc(r) : '';
    const ds = [cot, ...dong, ...(tuy.tong ? [tuy.tong] : [])];
    return { ten, tieuDe: [`EPL · ${tieuDeMan()} — ${ten}`, ...(loc ? [`${NN.t('xuat_loc')}: ${loc}`] : []), nguoiXuat()],
      dong: ds, soDongDau: 1, dongTong: tuy.tong ? new Set([ds.length - 1]) : undefined };
  };

  /* ------------------------------------------------------------------ PDF */
  // Tờ phiếu có khổ in riêng (dọc) — đang hiện một trong các khối này thì in đúng tờ đó, không thêm đầu trang.
  const GIAY = '.px-phieu, .hd-giay, .ct-giay, [data-giay-in]';
  EPL.xuatPDF = (giuLai) => {             // giuLai: bộ kiểm giữ bản in lại để chụp PDF, tự gọi hàm dọn trả về
    const r = goc(); if (!r) return;
    const giay = [...r.querySelectorAll(GIAY)].some(hien);
    const cu = document.title;
    let dau = null, trang = null;
    if (!giay) {
      const loc = boLoc(r);
      dau = document.createElement('div'); dau.className = 'in-dau';
      dau.innerHTML = `<b>EPL · ${EPL.esc(tieuDeMan())}</b>${loc ? `<span>${EPL.esc(NN.t('xuat_loc'))}: ${EPL.esc(loc)}</span>` : ''}<span>${EPL.esc(nguoiXuat())}</span>`;
      r.prepend(dau);
      trang = document.createElement('style'); trang.textContent = '@page{size:A4 landscape;margin:10mm}';
      document.head.appendChild(trang); document.body.classList.add('in-bao-cao');
    }
    document.title = tenTep('pdf').replace(/\.pdf$/, '');           // Chrome lấy tên này làm tên tệp PDF
    const don = () => { document.title = cu; if (dau) dau.remove(); if (trang) trang.remove(); document.body.classList.remove('in-bao-cao'); window.removeEventListener('afterprint', don); };
    if (giuLai === true) return don;
    window.addEventListener('afterprint', don);
    window.print();
    setTimeout(don, 500);
  };

  /* ------------------------------------------------------------------ hai nút trên thanh đầu trang */
  EPL.veNutXuat = (modId) => {
    const o = document.getElementById('xuatNut'); if (!o) return;
    const m = (EPL.MODULES || []).find(z => z.id === modId);
    o.hidden = !m || !!m.khong_xuat;
  };
  document.addEventListener('DOMContentLoaded', () => {
    const e = document.getElementById('btnExcel'), p = document.getElementById('btnPDF');
    if (e) e.addEventListener('click', () => EPL.xuatExcel());
    if (p) p.addEventListener('click', () => EPL.xuatPDF());
  });
})();
