/**
 * Bảng xếp ca tài xế: ma trận NGƯỜI × NGÀY.
 *
 * Vì sao đổi dạng trình bày:
 *
 * Bản cũ có hai phần rời nhau. Dải 7 ngày chỉ hiện SỐ TỔNG ("0 ca · 0 chuyến"),
 * nên nhìn vào không biết AI làm KHI NÀO — mà đó chính là câu hỏi duy nhất của
 * người xếp ca. Bấm vào một ngày thì bảng chi tiết mở trong hộp thoại che kín
 * màn hình, nên mất luôn ngữ cảnh tuần và mỗi lần chỉ xem được một ngày.
 *
 * Việc thật của màn này là xếp ca: gán tài xế vào ca sáng/chiều/đêm suốt một
 * tuần, tránh trùng, tránh ngày nghỉ, tránh chuyến đã khóa lịch. Dạng đúng cho
 * việc đó là ma trận người × ngày — cả tuần của cả đội trong một lần nhìn, và
 * chỗ trống hiện ra như chỗ trống thật.
 *
 * Không dùng hộp thoại. Chọn một ô thì chi tiết hiện ở khung bên cạnh
 * (#driver-shift-inspector đã có sẵn trong markup), nên ngữ cảnh tuần vẫn còn.
 *
 * Quy ước màu — dùng token sẵn có của ứng dụng:
 *   đã xếp ca   #059669  (--accent-emerald)
 *   nghỉ        #d97706  (--accent-amber)
 *   khóa lịch   #1d4ed8  (--lao-blue)   ← là một SỰ THẬT từ Điều phối, không
 *                                          phải lỗi, nên không dùng màu đỏ
 * Bộ ba này đã qua kiểm tra bằng máy: nằm trong dải độ sáng, đủ sắc độ, ΔE
 * người nhìn bình thường 23.7 giữa cặp gần nhất. ΔE cho người mù màu đỏ-lục là
 * 7.9 — mức chỉ được phép khi có mã hóa phụ, nên mỗi ô ca đều mang CHỮ (S/C/Đ)
 * cùng icon, không bao giờ chỉ có màu.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DriverRoster = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SHIFTS = [
    { key: 'morning', letter: 'S', label: 'Ca sáng', time: '06:00 – 14:00' },
    { key: 'afternoon', letter: 'C', label: 'Ca chiều', time: '14:00 – 22:00' },
    { key: 'night', letter: 'Đ', label: 'Ca đêm', time: '22:00 – 06:00' },
  ];

  const STATE = {
    assigned: { color: '#059669', soft: '#ecfdf5', icon: 'fa-circle-check', label: 'Đã xếp ca' },
    absence: { color: '#d97706', soft: '#fffbeb', icon: 'fa-user-clock', label: 'Nghỉ' },
    locked: { color: '#1d4ed8', soft: '#eff6ff', icon: 'fa-lock', label: 'Khóa lịch từ Điều phối' },
    free: { color: '#94a3b8', soft: '#ffffff', icon: 'fa-plus', label: 'Còn trống' },
  };

  const ABSENCE_LABELS = {
    leave: 'Nghỉ phép',
    sick: 'Nghỉ bệnh',
    off: 'Nghỉ ca',
    unavailable: 'Không sẵn sàng',
  };

  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /** Escape cho giá trị nằm trong chuỗi JavaScript bên trong thuộc tính HTML. */
  function escAttr(value) {
    if (value === null || value === undefined) return '';
    return esc(String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'"));
  }

  /** Trạng thái của một ô ca: khóa lịch > nghỉ > đã xếp > trống. */
  function cellState(cell) {
    if (cell && cell.trip) return 'locked';
    if (cell && cell.shift) {
      const kind = cell.shift.kind || 'work';
      return kind === 'work' ? 'assigned' : 'absence';
    }
    return 'free';
  }

  function cellTooltip(person, day, shiftDef, cell) {
    const who = `${person.name || person.id}`;
    const when = `${day.label} · ${shiftDef.label} ${shiftDef.time}`;
    if (cell && cell.trip) {
      const vehicle = cell.trip.vehicle_id ? ` · Xe ${cell.trip.vehicle_id}` : '';
      return `${who} — ${when}\nKhóa lịch: chuyến ${cell.trip.trip_id}${vehicle}`;
    }
    if (cell && cell.shift) {
      const kind = cell.shift.kind || 'work';
      if (kind !== 'work') {
        return `${who} — ${when}\n${ABSENCE_LABELS[kind] || kind}`;
      }
      const vehicle = cell.shift.vehicle_id ? `Xe ${cell.shift.vehicle_id}` : 'Chưa gán xe';
      const hours = cell.shift.start_label && cell.shift.end_label
        ? `${cell.shift.start_label} – ${cell.shift.end_label}`
        : shiftDef.time;
      return `${who} — ${when}\n${hours} · ${vehicle}`;
    }
    return `${who} — ${when}\nCòn trống · chọn để xếp ca`;
  }

  // ------------------------------------------------------------------
  // Ma trận tuần
  // ------------------------------------------------------------------

  /**
   * Một ô ca. Là <button> chứ không phải <div>: nó bấm được, nên phải tới được
   * bằng bàn phím và có trạng thái focus.
   */
  function shiftCell(person, day, shiftDef, cell) {
    const state = cellState(cell);
    const tone = STATE[state];
    const locked = state === 'locked';
    const handler = locked
      ? `DriverRosterActions.openTrip('${escAttr(cell.trip.trip_id)}', '${escAttr(person.id)}')`
      : cell && cell.shift
        ? `DriverRosterActions.openShift('${escAttr(cell.shift.id)}')`
        : `DriverRosterActions.assign('${escAttr(person.id)}', '${escAttr(day.key)}', '${escAttr(shiftDef.key)}')`;
    return `<button type="button" class="dr-cell dr-cell--${state}"
      style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
      title="${esc(cellTooltip(person, day, shiftDef, cell))}"
      aria-label="${esc(`${person.name || person.id}, ${day.label}, ${shiftDef.label}: ${tone.label}`)}"
      onclick="${handler}"><span class="dr-cell-letter">${shiftDef.letter}</span>${
        locked ? '<i class="fa-solid fa-lock dr-cell-mark" aria-hidden="true"></i>' : ''
      }</button>`;
  }

  /** Ba ô ca của một người trong một ngày. */
  function dayGroup(person, day, cells) {
    return `<div class="dr-day-group">${
      SHIFTS.map(shiftDef => shiftCell(person, day, shiftDef, cells[shiftDef.key])).join('')
    }</div>`;
  }

  /**
   * Ma trận NGƯỜI × NGÀY.
   *
   * Cột đầu dính (sticky) và phần lưới cuộn ngang trong khung của nó, nên thêm
   * người hay đổi sang màn hẹp đều không làm trang cuộn ngang.
   */
  function weekMatrix(data, options) {
    const days = (data && data.days) || [];
    const all = (data && data.people) || [];
    const selectedDay = (options && options.selectedDay) || '';

    if (!days.length) return emptyState('Chưa xác định được tuần cần xếp ca.');
    if (!all.length) {
      return emptyState('Không có nhân sự nào khớp bộ lọc. Xóa từ khóa tìm kiếm để xem toàn bộ đội.');
    }

    // Mỗi người chiếm 21 ô (7 ngày × 3 ca), nên 400 người là 8.400 nút và
    // khoảng 3,3 MB HTML trong một lần innerHTML.
    const limit = Number((options && options.limit) || PERSON_PAGE_SIZE);
    const people = all.slice(0, Math.max(1, limit));
    const hidden = all.length - people.length;

    const header = `
      <div class="dr-row dr-row--head">
        <div class="dr-name dr-name--head">Nhân sự</div>
        ${days.map(day => {
          const load = dayLoad(people, day.key);
          const level = load.assigned === 0 ? 'free' : load.assigned >= load.capacity ? 'assigned' : 'absence';
          return `<div class="dr-col-head${day.key === selectedDay ? ' is-selected' : ''}">
            <button type="button" class="dr-col-head-btn"
                    onclick="DriverRosterActions.selectDay('${escAttr(day.key)}')"
                    title="${esc(`${day.label}: ${load.assigned} ca đã xếp, ${load.absence} nghỉ, ${load.locked} khóa lịch, còn ${load.capacity - load.assigned} chỗ`)}">
              <b>${esc(day.label)}</b>
              <span class="dr-col-load" style="--dr-tone:${STATE[level].color};">
                <span class="dr-col-load-fill" style="width:${load.capacity ? Math.round(load.assigned * 100 / load.capacity) : 0}%;"></span>
              </span>
              <small>${load.assigned}/${load.capacity} ca</small>
            </button>
          </div>`;
        }).join('')}
        <div class="dr-total dr-total--head">Tuần</div>
      </div>`;

    const rows = people.map(person => {
      const weekTotal = days.reduce((sum, day) => {
        const cells = personCells(person, day.key);
        return sum + SHIFTS.filter(s => cellState(cells[s.key]) === 'assigned').length;
      }, 0);
      const roleLine = [person.role, person.license].filter(Boolean).join(' · ');
      return `
        <div class="dr-row">
          <div class="dr-name">
            <b>${esc(person.name || person.id)}</b>
            <small>${esc(person.id)}${roleLine ? ` · ${esc(roleLine)}` : ''}</small>
          </div>
          ${days.map(day => `<div class="dr-col${day.key === selectedDay ? ' is-selected' : ''}">${
            dayGroup(person, day, personCells(person, day.key))
          }</div>`).join('')}
          <div class="dr-total"><b>${weekTotal}</b><small>ca</small></div>
        </div>`;
    }).join('');

    const footer = hidden > 0
      ? `<div class="dr-page">
          <span>Đang xem <b>${people.length}</b> trên <b>${all.length}</b> nhân sự</span>
          <button type="button" onclick="DriverRosterActions.showMorePeople()">
            <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
            Xem thêm ${Math.min(hidden, PERSON_PAGE_SIZE)} người
          </button>
        </div>`
      : `<div class="dr-page"><span>Đang xem đủ <b>${all.length}</b> nhân sự</span></div>`;

    return `<div class="dr-matrix" style="--dr-days:${days.length};" role="group" aria-label="Bảng xếp ca theo tuần">${header}${rows}</div>${footer}`;
  }

  /** Các ô ca của một người trong một ngày, khóa theo loại ca. */
  function personCells(person, dayKey) {
    const day = (person.days || []).find(item => item.key === dayKey) || {};
    const cells = {};
    SHIFTS.forEach(shiftDef => {
      const shift = (day.shifts || []).find(item => item.type === shiftDef.key) || null;
      const trip = (day.trips || []).find(item => !item.shift_type || item.shift_type === shiftDef.key) || null;
      cells[shiftDef.key] = { shift, trip: shift ? null : trip };
    });
    return cells;
  }

  /** Tổng hợp một ngày: đã xếp, nghỉ, khóa lịch, và tổng chỗ có thể xếp. */
  function dayLoad(people, dayKey) {
    let assigned = 0;
    let absence = 0;
    let locked = 0;
    people.forEach(person => {
      const cells = personCells(person, dayKey);
      SHIFTS.forEach(shiftDef => {
        const state = cellState(cells[shiftDef.key]);
        if (state === 'assigned') assigned += 1;
        else if (state === 'absence') absence += 1;
        else if (state === 'locked') locked += 1;
      });
    });
    return { assigned, absence, locked, capacity: people.length * SHIFTS.length };
  }

  // ------------------------------------------------------------------
  // Chú giải
  // ------------------------------------------------------------------

  function legend() {
    const order = ['assigned', 'absence', 'locked', 'free'];
    return `
      <ul class="dr-legend">
        ${order.map(key => {
          const tone = STATE[key];
          return `<li><span class="dr-legend-swatch dr-cell--${key}" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};" aria-hidden="true"></span>
            <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}</li>`;
        }).join('')}
        <li class="dr-legend-note">S = sáng · C = chiều · Đ = đêm</li>
      </ul>`;
  }

  // ------------------------------------------------------------------
  // Chi tiết một ngày — hiện NGAY TRONG TRANG, không dùng hộp thoại
  // ------------------------------------------------------------------

  /**
   * Bảng chi tiết một ngày. Giữ lại vì có lúc cần đọc kỹ giờ giấc và xe của
   * từng người, nhưng đặt ngay trong trang thay vì trong hộp thoại che màn hình.
   */
  function dayDetail(data, dayKey) {
    const days = (data && data.days) || [];
    const people = (data && data.people) || [];
    const day = days.find(item => item.key === dayKey);
    if (!day) return emptyState('Chọn một ngày trên bảng tuần để xem chi tiết.');
    if (!people.length) return emptyState('Không có nhân sự nào khớp bộ lọc.');

    const rows = people.map(person => {
      const cells = personCells(person, dayKey);
      const cellHtml = SHIFTS.map(shiftDef => {
        const cell = cells[shiftDef.key];
        const state = cellState(cell);
        const tone = STATE[state];
        if (state === 'free') {
          return `<td><button type="button" class="dr-detail-free"
            onclick="DriverRosterActions.assign('${escAttr(person.id)}', '${escAttr(dayKey)}', '${escAttr(shiftDef.key)}')">
            <i class="fa-solid fa-plus" aria-hidden="true"></i> Xếp ca</button></td>`;
        }
        if (state === 'locked') {
          return `<td><span class="dr-detail-chip" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};">
            <i class="fa-solid fa-lock" aria-hidden="true"></i>
            <b>${esc(cell.trip.trip_id)}</b>
            <small>${esc(cell.trip.vehicle_id ? `Xe ${cell.trip.vehicle_id}` : cell.trip.role || 'Chuyến')}</small>
          </span></td>`;
        }
        const kind = cell.shift.kind || 'work';
        const primary = kind === 'work'
          ? `${cell.shift.start_label || ''} – ${cell.shift.end_label || ''}`.trim()
          : (ABSENCE_LABELS[kind] || kind);
        const secondary = kind === 'work'
          ? (cell.shift.vehicle_id ? `Xe ${cell.shift.vehicle_id}` : 'Chưa gán xe')
          : 'Không nhận ca';
        return `<td><button type="button" class="dr-detail-chip dr-detail-chip--action"
          style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
          onclick="DriverRosterActions.openShift('${escAttr(cell.shift.id)}')">
          <i class="fa-solid ${tone.icon}" aria-hidden="true"></i>
          <b>${esc(primary)}</b><small>${esc(secondary)}</small>
        </button></td>`;
      }).join('');
      const roleLine = [person.role, person.license].filter(Boolean).join(' · ');
      return `<tr>
        <th scope="row"><b>${esc(person.name || person.id)}</b><small>${esc(person.id)}${roleLine ? ` · ${esc(roleLine)}` : ''}</small></th>
        ${cellHtml}
      </tr>`;
    }).join('');

    return `
      <div class="dr-detail">
        <div class="dr-detail-head">
          <h4><i class="fa-solid fa-calendar-day" aria-hidden="true"></i> ${esc(day.label)}</h4>
          <p>${people.length} nhân sự · ba ca và các chuyến đã khóa lịch</p>
        </div>
        <div class="dr-detail-scroll">
          <table class="dr-detail-table">
            <thead>
              <tr>
                <th scope="col">Nhân sự</th>
                ${SHIFTS.map(s => `<th scope="col">${esc(s.label)}<small>${esc(s.time)}</small></th>`).join('')}
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }

  function emptyState(message) {
    return `<p class="dr-empty">${esc(message)}</p>`;
  }

  // ------------------------------------------------------------------
  // Lịch xe — ma trận XE × NGÀY
  // ------------------------------------------------------------------

  /**
   * Trạng thái xe trong một ngày.
   *
   * Ở đây màu ĐỎ là hợp lý, khác với "khóa lịch" ở bảng ca: xung đột lịch là
   * một lỗi thật cần người xử lý, không phải một sự thật phải chấp nhận.
   *
   * "Rảnh" cố tình dùng nét đứt trung tính chứ không tô xanh: xe rảnh là năng
   * lực chưa dùng, không phải thành tích — tô xanh cả tuần sẽ làm bảng trông
   * như mọi thứ đều tốt trong khi thật ra cả đội đang không chạy.
   */
  const VEHICLE_STATE = {
    available: { color: '#94a3b8', soft: '#ffffff', icon: 'fa-circle-check', label: 'Rảnh' },
    busy: { color: '#1d4ed8', soft: '#eff6ff', icon: 'fa-truck-fast', label: 'Đang có lịch' },
    maintenance: { color: '#d97706', soft: '#fffbeb', icon: 'fa-screwdriver-wrench', label: 'Bảo dưỡng / sửa chữa' },
    conflict: { color: '#b91c1c', soft: '#fef2f2', icon: 'fa-triangle-exclamation', label: 'Xung đột lịch' },
  };

  /** Dòng chữ ngắn mô tả ngày của một xe. */
  function vehicleDayHint(day) {
    if (!day) return '—';
    if (day.maintenances && day.maintenances.length) {
      return day.maintenances.map(item => item.label).filter(Boolean).join(', ') || 'Bảo dưỡng';
    }
    if (day.trip_ids && day.trip_ids.length) return day.trip_ids.join(', ');
    if (day.shifts && day.shifts.length) return `${day.shifts.length} ca dự kiến`;
    return '—';
  }

  function vehicleCell(vehicle, day, dayData) {
    const status = (dayData && dayData.status) || 'available';
    const tone = VEHICLE_STATE[status] || VEHICLE_STATE.available;
    const hint = vehicleDayHint(dayData);
    const drivers = dayData && dayData.driver_ids && dayData.driver_ids.length
      ? dayData.driver_ids.filter(Boolean).join(', ')
      : '';
    const tooltip = [
      `${vehicle.label || vehicle.vehicle_id} — ${day.label}`,
      tone.label,
      hint !== '—' ? hint : null,
      drivers ? `Tài xế: ${drivers}` : null,
    ].filter(Boolean).join('\n');
    return `<button type="button" class="dr-vcell dr-vcell--${status}"
      style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
      title="${esc(tooltip)}"
      aria-label="${esc(`${vehicle.label || vehicle.vehicle_id}, ${day.label}: ${tone.label}`)}"
      onclick="DriverRosterActions.openVehicle('${escAttr(vehicle.vehicle_id)}', '${escAttr(day.key)}')">
      <i class="fa-solid ${tone.icon}" aria-hidden="true"></i>
      <span class="dr-vcell-hint">${esc(hint)}</span>
    </button>`;
  }

  /**
   * Ma trận XE × NGÀY.
   *
   * Cùng lý do như bảng xếp ca: dải 7 ngày cũ chỉ hiện số tổng ("3 rảnh · 0
   * bận") nên không biết XE NÀO rảnh ngày nào, và chi tiết thì nằm trong hộp
   * thoại che kín màn hình.
   */
  function vehicleMatrix(data, options) {
    const days = (data && data.days) || [];
    const all = (data && data.vehicles) || [];
    const selectedDay = (options && options.selectedDay) || '';

    if (!days.length) return emptyState('Chưa xác định được tuần cần xem.');
    if (!all.length) {
      return emptyState('Chưa có xe nào khớp bộ lọc. Xóa từ khóa để xem toàn bộ đội xe.');
    }

    // Chỉ dựng một trang xe mỗi lần. Ở 500 xe, dựng hết là 1,7 MB HTML và
    // 3.500 nút trong một lần innerHTML, và mỗi lần gõ tìm kiếm lại dựng lại
    // toàn bộ.
    const limit = Number((options && options.limit) || VEHICLE_PAGE_SIZE);
    const vehicles = all.slice(0, Math.max(1, limit));
    const hidden = all.length - vehicles.length;

    const header = `
      <div class="dr-row dr-row--head">
        <div class="dr-name dr-name--head">Phương tiện</div>
        ${days.map(day => {
          const load = vehicleDayLoad(vehicles, day.key);
          // Có xung đột thì đó là thứ cần thấy trước, nên nó quyết định màu.
          const level = load.conflict ? 'conflict' : load.maintenance ? 'maintenance' : load.busy ? 'busy' : 'available';
          const used = load.busy + load.maintenance + load.conflict;
          return `<div class="dr-col-head${day.key === selectedDay ? ' is-selected' : ''}">
            <button type="button" class="dr-col-head-btn"
                    onclick="DriverRosterActions.selectVehicleDay('${escAttr(day.key)}')"
                    title="${esc(`${day.label}: ${load.available} rảnh, ${load.busy} đang có lịch, ${load.maintenance} bảo dưỡng, ${load.conflict} xung đột`)}">
              <b>${esc(day.label)}</b>
              <span class="dr-col-load" style="--dr-tone:${VEHICLE_STATE[level].color};">
                <span class="dr-col-load-fill" style="width:${vehicles.length ? Math.round(used * 100 / vehicles.length) : 0}%;"></span>
              </span>
              <small>${used}/${vehicles.length} xe dùng</small>
            </button>
          </div>`;
        }).join('')}
        <div class="dr-total dr-total--head">Rảnh</div>
      </div>`;

    const rows = vehicles.map(vehicle => {
      const freeDays = days.filter(day => {
        const dayData = (vehicle.days || []).find(item => item.key === day.key);
        return !dayData || (dayData.status || 'available') === 'available';
      }).length;
      const typeLine = vehicle.type || 'Chưa cấu hình loại xe';
      return `
        <div class="dr-row">
          <div class="dr-name">
            <b>${esc(vehicle.label || vehicle.vehicle_id)}</b>
            <small>${esc(vehicle.vehicle_id)} · ${esc(typeLine)}</small>
          </div>
          ${days.map(day => `<div class="dr-col dr-col--wide${day.key === selectedDay ? ' is-selected' : ''}">${
            vehicleCell(vehicle, day, (vehicle.days || []).find(item => item.key === day.key))
          }</div>`).join('')}
          <div class="dr-total"><b>${freeDays}</b><small>ngày</small></div>
        </div>`;
    }).join('');

    const footer = hidden > 0
      ? `<div class="dr-page">
          <span>Đang xem <b>${vehicles.length}</b> trên <b>${all.length}</b> xe</span>
          <button type="button" onclick="DriverRosterActions.showMoreVehicles()">
            <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
            Xem thêm ${Math.min(hidden, VEHICLE_PAGE_SIZE)} xe
          </button>
        </div>`
      : `<div class="dr-page"><span>Đang xem đủ <b>${all.length}</b> xe</span></div>`;

    return `<div class="dr-matrix dr-matrix--vehicles" style="--dr-days:${days.length};" role="group" aria-label="Lịch xe theo tuần">${header}${rows}</div>${footer}`;
  }

  /** Tổng hợp một ngày của cả đội xe. */
  function vehicleDayLoad(vehicles, dayKey) {
    const load = { available: 0, busy: 0, maintenance: 0, conflict: 0 };
    vehicles.forEach(vehicle => {
      const dayData = (vehicle.days || []).find(item => item.key === dayKey);
      const status = (dayData && dayData.status) || 'available';
      if (load[status] === undefined) load.available += 1;
      else load[status] += 1;
    });
    return load;
  }

  /* ======================================================================
     Đội tài xế lớn: cùng lý do như đội xe
     ----------------------------------------------------------------------
     Với 400 tài xế, ma trận người × ngày × 3 ca sinh ra khoảng 3,3 MB HTML và
     8.400 nút bấm — nặng hơn cả bảng xe, vì mỗi ngày có ba ô thay vì một.

     Và câu hỏi thật của người xếp ca không phải "cho tôi xem 400 người", mà là
     "ca đêm thứ Năm đã có ai chưa" và "ai chưa được xếp ca nào tuần này".
     ====================================================================== */

  const PERSON_PAGE_SIZE = 50;

  /**
   * Số người trực từng ca, từng ngày.
   *
   * Đây là thứ trả lời ngay được câu "ca nào đang trống người" mà không cần
   * cuộn qua 400 dòng.
   */
  function shiftCoverage(people, dayKey) {
    const counts = {};
    SHIFTS.forEach(shiftDef => { counts[shiftDef.key] = 0; });
    people.forEach(person => {
      const cells = personCells(person, dayKey);
      SHIFTS.forEach(shiftDef => {
        const state = cellState(cells[shiftDef.key]);
        // Nghỉ phép không tính là có người trực.
        if (state === 'assigned' || state === 'locked') counts[shiftDef.key] += 1;
      });
    });
    return counts;
  }

  /** Băng phủ ca 7 ngày: mỗi ngày ba con số S / C / Đ. */
  function crewCoverageStrip(data, options) {
    const days = (data && data.days) || [];
    const people = (data && data.people) || [];
    const selectedDay = (options && options.selectedDay) || '';
    if (!days.length) return '';

    return `
      <div class="dr-capacity" role="group" aria-label="Số người trực theo ca">
        ${days.map(day => {
          const counts = shiftCoverage(people, day.key);
          const empty = SHIFTS.filter(shiftDef => !counts[shiftDef.key]);
          const total = SHIFTS.reduce((sum, shiftDef) => sum + counts[shiftDef.key], 0);
          const tooltip = SHIFTS.map(shiftDef => `${shiftDef.label}: ${counts[shiftDef.key]} người`).join(', ');
          return `<button type="button" class="dr-cap${day.key === selectedDay ? ' is-selected' : ''}"
                  aria-pressed="${day.key === selectedDay}"
                  title="${esc(`${day.label} — ${tooltip}`)}"
                  onclick="DriverRosterActions.selectDay('${escAttr(day.key)}')">
            <b>${esc(day.label)}</b>
            <span class="dr-shift-counts">
              ${SHIFTS.map(shiftDef => `<span class="dr-shift-count${counts[shiftDef.key] ? '' : ' is-empty'}"
                  title="${esc(`${shiftDef.label} (${shiftDef.time}): ${counts[shiftDef.key]} người`)}">
                <em>${esc(shiftDef.letter)}</em>
                <b>${counts[shiftDef.key]}</b>
              </span>`).join('')}
            </span>
            <strong>${total}</strong>
            <small>lượt trực / ${people.length} người</small>
            ${empty.length ? `<em class="dr-cap-flag"><i class="fa-solid fa-user-slash" aria-hidden="true"></i> Trống ${empty.map(item => item.letter).join(', ')}</em>` : ''}
          </button>`;
        }).join('')}
      </div>`;
  }

  /**
   * Những chỗ hổng thật sự cần người xếp ca xử lý.
   *
   * Ca không có ai trực là lỗ hổng vận hành — nặng hơn nhiều so với một người
   * rảnh cả tuần, nên nó lên trước.
   */
  function crewGaps(data) {
    const days = (data && data.days) || [];
    const people = (data && data.people) || [];
    const rows = [];

    days.forEach(day => {
      const counts = shiftCoverage(people, day.key);
      SHIFTS.forEach(shiftDef => {
        if (counts[shiftDef.key]) return;
        rows.push({
          kind: 'uncovered',
          key: day.key,
          shift: shiftDef.key,
          dayLabel: day.label,
          label: `${shiftDef.label} ${day.label}`,
          hint: `${shiftDef.time} — chưa có ai trực`,
        });
      });
    });

    // Người không có ca nào cả tuần: năng lực chưa dùng, đáng nhắc nhưng không
    // khẩn cấp bằng một ca trống.
    people.forEach(person => {
      const busy = days.some(day => {
        const cells = personCells(person, day.key);
        return SHIFTS.some(shiftDef => {
          const state = cellState(cells[shiftDef.key]);
          return state === 'assigned' || state === 'locked';
        });
      });
      if (busy) return;
      rows.push({
        kind: 'idle',
        key: '',
        person_id: person.id,
        label: person.name || person.id,
        hint: `${person.role || 'Nhân sự'} — chưa có ca nào tuần này`,
      });
    });

    return rows;
  }

  function crewGapList(data, options) {
    const rows = crewGaps(data);
    const expanded = Boolean(options && options.expanded);
    if (!rows.length) {
      return `<section class="dr-panel dr-panel--clear">
        <h4><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Tuần này đã kín ca</h4>
        <p>Mọi ca đều có người trực và không ai bị bỏ trống cả tuần.</p>
      </section>`;
    }

    const uncovered = rows.filter(row => row.kind === 'uncovered').length;
    const shown = expanded ? rows : rows.slice(0, EXCEPTION_PREVIEW);
    return `<section class="dr-panel dr-panel--alert">
      <h4>
        <i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
        Cần xếp <span class="dr-panel-count">${rows.length}</span>
        ${uncovered ? `<small>trong đó ${uncovered} ca chưa có ai trực</small>` : ''}
      </h4>
      <ul class="dr-exceptions">
        ${shown.map(row => {
          const uncoveredRow = row.kind === 'uncovered';
          const tone = uncoveredRow ? '#b91c1c' : '#94a3b8';
          const icon = uncoveredRow ? 'fa-user-slash' : 'fa-user-clock';
          const action = uncoveredRow
            ? `DriverRosterActions.selectDay('${escAttr(row.key)}')`
            : `DriverRosterActions.focusPerson('${escAttr(row.person_id)}')`;
          return `<li>
            <button type="button" class="dr-exception" style="--dr-tone:${tone};" onclick="${action}">
              <i class="fa-solid ${icon}" aria-hidden="true"></i>
              <span class="dr-exception-text">
                <b>${esc(row.label)}</b>
                <small>${esc(row.hint)}</small>
              </span>
              <i class="fa-solid fa-chevron-right dr-exception-go" aria-hidden="true"></i>
            </button>
          </li>`;
        }).join('')}
      </ul>
      ${rows.length > EXCEPTION_PREVIEW ? `<button type="button" class="dr-more" onclick="DriverRosterActions.toggleGaps()">
        ${expanded ? 'Thu gọn' : `Xem tất cả ${rows.length} dòng`}
      </button>` : ''}
    </section>`;
  }

  /* ======================================================================
     Đội xe lớn: tình hình trước, việc cần xử lý sau, chi tiết sau cùng
     ----------------------------------------------------------------------
     Ma trận xe × ngày rất hợp lý với đội vài chục xe, nhưng ở 500 xe nó sinh
     ra khoảng 1,7 MB HTML và 3.500 nút bấm trong một lần innerHTML — và mỗi
     lần gõ vào ô tìm kiếm lại dựng lại toàn bộ.

     Nặng hơn cả tốc độ là cách nghĩ: với 500 xe thì không ai cuộn hết danh
     sách. Câu hỏi thật của người điều phối là "thứ Năm còn bao nhiêu xe rảnh"
     và "tuần này có xung đột nào không" — tức bài toán LỌC và BẮT NGOẠI LỆ,
     không phải duyệt hết. Ma trận cũ chôn đúng 5 xe có vấn đề giữa 495 xe
     bình thường.
     ====================================================================== */

  /** Số xe tối đa dựng một lần. Còn lại tải thêm theo yêu cầu. */
  const VEHICLE_PAGE_SIZE = 50;

  /** Số dòng ngoại lệ hiện sẵn trước khi phải bấm "xem tất cả". */
  const EXCEPTION_PREVIEW = 6;

  /**
   * Băng năng lực 7 ngày: mỗi ngày một cột, thanh xếp chồng theo trạng thái.
   *
   * Đây là thứ trả lời được ngay câu hỏi hay gặp nhất mà không cần cuộn dòng
   * nào: ngày nào đội xe căng, ngày nào còn dư.
   */
  function vehicleCapacityStrip(data, options) {
    const days = (data && data.days) || [];
    const vehicles = (data && data.vehicles) || [];
    const selectedDay = (options && options.selectedDay) || '';
    if (!days.length) return '';

    const order = ['busy', 'maintenance', 'conflict', 'available'];
    return `
      <div class="dr-capacity" role="group" aria-label="Năng lực đội xe theo ngày">
        ${days.map(day => {
          const load = vehicleDayLoad(vehicles, day.key);
          const total = vehicles.length || 1;
          const used = load.busy + load.maintenance + load.conflict;
          const tooltip = `${day.label}: ${load.available} rảnh, ${load.busy} đang có lịch, ${load.maintenance} bảo dưỡng, ${load.conflict} xung đột`;
          return `<button type="button" class="dr-cap${day.key === selectedDay ? ' is-selected' : ''}"
                  aria-pressed="${day.key === selectedDay}"
                  title="${esc(tooltip)}"
                  onclick="DriverRosterActions.selectVehicleDay('${escAttr(day.key)}')">
            <b>${esc(day.label)}</b>
            <span class="dr-cap-bar">
              ${order.map(key => {
                const value = load[key];
                if (!value) return '';
                const tone = VEHICLE_STATE[key];
                return `<span class="dr-cap-seg" style="flex:${value}; background:${tone.color};"
                         title="${esc(`${value} xe — ${tone.label}`)}"></span>`;
              }).join('')}
            </span>
            <strong>${load.available}</strong>
            <small>xe rảnh / ${vehicles.length}</small>
            ${load.conflict ? `<em class="dr-cap-flag"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> ${load.conflict} xung đột</em>` : ''}
            ${!load.conflict && load.maintenance ? `<em class="dr-cap-flag dr-cap-flag--soft"><i class="fa-solid fa-screwdriver-wrench" aria-hidden="true"></i> ${load.maintenance} bảo dưỡng</em>` : ''}
            <span class="dr-cap-used">${used}/${total} đang dùng</span>
          </button>`;
        }).join('')}
      </div>`;
  }

  /**
   * Những dòng thật sự cần người xử lý, xếp việc nặng lên trước.
   *
   * Trả về dữ liệu thuần để kiểm chứng được phép sắp xếp bằng Node — thứ tự
   * ở đây quyết định người dùng nhìn thấy gì đầu tiên.
   */
  function vehicleExceptions(data) {
    const days = (data && data.days) || [];
    const vehicles = (data && data.vehicles) || [];
    const labelOf = key => (days.find(day => day.key === key) || {}).label || key;
    const rows = [];
    vehicles.forEach(vehicle => {
      (vehicle.days || []).forEach(day => {
        const status = (day && day.status) || 'available';
        if (status !== 'conflict' && status !== 'maintenance') return;
        rows.push({
          vehicle_id: vehicle.vehicle_id,
          label: vehicle.label || vehicle.vehicle_id,
          type: vehicle.type || '',
          key: day.key,
          dayLabel: labelOf(day.key),
          status,
          hint: vehicleDayHint(day),
        });
      });
    });
    // Xung đột lịch là lỗi phải sửa ngay; bảo dưỡng chỉ là việc đã biết trước.
    const weight = { conflict: 0, maintenance: 1 };
    return rows.sort((a, b) =>
      (weight[a.status] - weight[b.status])
      || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0)
      || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0)
    );
  }

  function vehicleExceptionList(data, options) {
    const rows = vehicleExceptions(data);
    const expanded = Boolean(options && options.expanded);
    if (!rows.length) {
      return `<section class="dr-panel dr-panel--clear">
        <h4><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Không có việc cần xử lý</h4>
        <p>Tuần này không có xung đột lịch hay lịch bảo dưỡng nào trong đội xe đang lọc.</p>
      </section>`;
    }

    const shown = expanded ? rows : rows.slice(0, EXCEPTION_PREVIEW);
    const conflicts = rows.filter(row => row.status === 'conflict').length;
    return `<section class="dr-panel dr-panel--alert">
      <h4>
        <i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
        Cần xử lý <span class="dr-panel-count">${rows.length}</span>
        ${conflicts ? `<small>trong đó ${conflicts} xung đột lịch</small>` : ''}
      </h4>
      <ul class="dr-exceptions">
        ${shown.map(row => {
          const tone = VEHICLE_STATE[row.status];
          return `<li>
            <button type="button" class="dr-exception" style="--dr-tone:${tone.color};"
                    onclick="DriverRosterActions.openVehicle('${escAttr(row.vehicle_id)}', '${escAttr(row.key)}')">
              <i class="fa-solid ${tone.icon}" aria-hidden="true"></i>
              <span class="dr-exception-text">
                <b>${esc(row.label)}</b>
                <small>${esc(row.dayLabel)} · ${esc(tone.label)}${row.hint !== '—' ? ` · ${esc(row.hint)}` : ''}</small>
              </span>
              <i class="fa-solid fa-chevron-right dr-exception-go" aria-hidden="true"></i>
            </button>
          </li>`;
        }).join('')}
      </ul>
      ${rows.length > EXCEPTION_PREVIEW ? `<button type="button" class="dr-more" onclick="DriverRosterActions.toggleExceptions()">
        ${expanded ? 'Thu gọn' : `Xem tất cả ${rows.length} dòng`}
      </button>` : ''}
    </section>`;
  }

  function vehicleLegend() {
    const order = ['available', 'busy', 'maintenance', 'conflict'];
    return `
      <ul class="dr-legend">
        ${order.map(key => {
          const tone = VEHICLE_STATE[key];
          return `<li><span class="dr-legend-swatch dr-vcell--${key}" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};" aria-hidden="true"></span>
            <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}</li>`;
        }).join('')}
      </ul>`;
  }

  /**
   * Dải lọc nhanh phía trên ma trận.
   *
   * Vì sao cần: ở quy mô thật một bãi có hàng trăm tài xế, nên ma trận luôn dài
   * hơn màn hình và người xếp ca phải cuộn để tìm ra ai đang thiếu lịch. Ba
   * nhóm dưới đây là ba câu hỏi họ thật sự hỏi, nên đặt thành nút bấm được thay
   * vì để họ tự dò.
   *
   * Mỗi nhóm phải có một ĐỊNH NGHĨA đo được, viết ngay trong nhãn phụ, chứ
   * không để người dùng đoán "vượt giờ" là vượt bao nhiêu:
   *   · chưa xếp  — cả tuần không có ca làm việc nào
   *   · vượt giờ  — tổng giờ ca làm việc trong tuần trên 48 giờ
   *   · có nghỉ   — có ít nhất một ngày nghỉ / ốm / off trong tuần
   */
  function filterChips(nhom, dangChon, hamGoi) {
    const ds = [
      ['all', 'Tất cả', '', ''],
      ['need', 'Chưa xếp', 'cả tuần không có ca nào', 'r'],
      ['over', 'Vượt giờ', 'trên 48 giờ/tuần', 'a'],
      ['leave', 'Có nghỉ', 'nghỉ / ốm / off trong tuần', ''],
    ];
    return `<div class="dr-chips" role="group" aria-label="Lọc nhanh nhân sự">
      ${ds.map(([ma, ten, mota, lop]) => {
        const n = Number(nhom[ma] || 0);
        // Nhóm rỗng vẫn hiện, chỉ mờ và không bấm được: ẩn hẳn thì dải nút nhảy
        // chỗ mỗi lần đổi tuần, và người dùng mất mốc để so.
        const tat = ma !== 'all' && n === 0;
        return `<button type="button"
          class="dr-chip${lop ? ' dr-chip--' + lop : ''}${dangChon === ma ? ' is-active' : ''}${tat ? ' is-empty' : ''}"
          ${tat ? 'disabled' : ''} title="${esc(mota || 'Toàn bộ nhân sự')}"
          onclick="${esc(hamGoi)}('${esc(ma)}')">${esc(ten)} <b>${n}</b></button>`;
      }).join('')}
    </div>`;
  }

  return {
    SHIFTS,
    STATE,
    VEHICLE_STATE,
    ABSENCE_LABELS,
    filterChips,
    cellState,
    personCells,
    dayLoad,
    weekMatrix,
    dayDetail,
    legend,
    PERSON_PAGE_SIZE,
    VEHICLE_PAGE_SIZE,
    shiftCoverage,
    crewCoverageStrip,
    crewGaps,
    crewGapList,
    vehicleDayHint,
    vehicleDayLoad,
    vehicleMatrix,
    vehicleLegend,
    vehicleCapacityStrip,
    vehicleExceptions,
    vehicleExceptionList,
  };
});
