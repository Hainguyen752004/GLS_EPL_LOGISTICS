/* Nén tệp TRƯỚC KHI tải lên (chủ dự án chốt 24/09): mỗi ngày hàng nghìn chuyến, mỗi chuyến vài ảnh — ảnh điện thoại
 * 3–6 MB đưa lên nguyên cỡ thì máy chủ, sao lưu và mạng ngoài hiện trường đều nặng. Ảnh nén còn ≤ 200 KB ngay trên máy
 * (chữ trên phiếu cân vẫn đọc rõ ở ~1280 px); PDF không nén được đáng tin trong trình duyệt nên chỉ chặn quá 2 MB.
 * Máy chủ chặn thêm lần nữa (services/tep.py) phòng máy cũ không nén được.
 *
 *   f = await EPL.nenTep(file)       → File (ảnh JPEG đã nén · PDF giữ nguyên) — ném lỗi nếu PDF quá lớn
 */
(function () {
  const MUC_TIEU = 200 * 1024, PDF_TOI_DA = 2 * 1024 * 1024;
  const CANH = [1600, 1280, 1024, 800], CHAT = [0.72, 0.6, 0.5];

  function mo(file) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(file), img = new Image();
      img.onload = () => { URL.revokeObjectURL(url); res(img); };
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error('decode')); };
      img.src = url;
    });
  }
  const thanhBlob = (c, q) => new Promise(res => c.toBlob(res, 'image/jpeg', q));

  EPL.nenTep = async function (file) {
    if (!file) return file;
    if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name || '')) {
      if (file.size > PDF_TOI_DA) throw new Error(EPL.NN.t('nen_pdf_lon').replace('{mb}', (file.size / 1048576).toFixed(1)));
      return file;
    }
    if (!/^image\//.test(file.type || '')) return file;
    if (file.size <= MUC_TIEU && /jpe?g|webp/.test(file.type)) return file;
    let img;
    try { img = await mo(file); } catch (e) { return file; }        // ảnh máy không đọc được (HEIC trên Chrome) → để máy chủ báo
    let tot = null;
    for (const canh of CANH) {
      const tl = Math.min(1, canh / Math.max(img.naturalWidth, img.naturalHeight));
      const c = document.createElement('canvas');
      c.width = Math.max(1, Math.round(img.naturalWidth * tl)); c.height = Math.max(1, Math.round(img.naturalHeight * tl));
      const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height);
      for (const q of CHAT) {
        const b = await thanhBlob(c, q);
        if (!b) continue;
        tot = b;
        if (b.size <= MUC_TIEU) return new File([b], (file.name || 'anh').replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
      }
    }
    return tot ? new File([tot], (file.name || 'anh').replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' }) : file;
  };
})();
