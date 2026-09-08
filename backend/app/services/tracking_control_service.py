"""Read-only control tower: actual positions are separate from trip plans."""

import json
import math
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, or_
from services import gps_simulation
from services import toa_do_diem
from services import duong_bo as dich_vu_duong_bo
from models import (Customer, DeliveryOrder, DeliveryPODRecord, DeliveryPODDocument, Driver, FreightOrder, Incident,
                    Route, TransportEvent, TransportTrip, TransportTripLeg,
                    TripDeliveryOrder, VehicleTracking)


def utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def iso(value):
    return utc(value).isoformat() if value else None


def coordinates(lat, lng):
    return (lat is not None and lng is not None
            and math.isfinite(lat) and math.isfinite(lng)
            and -90 <= lat <= 90 and -180 <= lng <= 180)


# Bang toa do da chuyen sang `services/toa_do_diem.py` de man "Tuyen duong"
# dung CHUNG mot nguon. Truoc day bang nay chi song trong tep nay, nen man
# Tuyen duong phai di hoi Nominatim qua Internet va o ban do trang tron khi may
# khong co mang — trong khi he thong da biet toa do cua dung nhung diem do.
REFERENCE_POINTS = toa_do_diem.DIEM_THAM_CHIEU


normalize_location = toa_do_diem.chuan_hoa


reference_coordinates = toa_do_diem.toa_do


#: Chuoi moc chinh cua mot chuyen, dung bang `MAIN_SEQUENCE` cua
#: `tms_execution_service` — khai LAI o day thi hai ban sao se troi khoi nhau,
#: nen doc thang tu do.
from services.tms_execution_service import MAIN_SEQUENCE as _CHUOI

CHUOI_MOC = [
    {'ma': 'check_in', 'ten': 'Check-in điểm lấy hàng'},
    {'ma': 'pickup', 'ten': 'Lấy hàng'},
    {'ma': 'departure', 'ten': 'Xuất bến'},
    {'ma': 'arrival', 'ten': 'Đến điểm giao'},
    {'ma': 'unloading', 'ten': 'Dỡ hàng'},
    {'ma': 'delivered', 'ten': 'Giao xong'},
]
assert [m['ma'] for m in CHUOI_MOC] == list(_CHUOI), (
    'CHUOI_MOC phai khop MAIN_SEQUENCE cua tms_execution_service')


def moc_ke_tiep(danh_sach_su_kien):
    """Moc chinh KE TIEP can ghi, hoac `None` khi da di het chuoi.

    Doc tu cac su kien DA GHI, khong tu trang thai don: chuoi moc la thu duoc
    `record_event` thi hanh, nen dem theo chuoi do moi khop voi cai may chu se
    nhan.
    """
    da_ghi = {e['type'] for e in danh_sach_su_kien}
    for moc in CHUOI_MOC:
        if moc['ma'] not in da_ghi:
            return moc
    return None


def eta_du_bao(trip):
    """Gio du kien den, neo vao gio xuat ben THUC TE.

    `actual_departure_at` + (thoi luong ke hoach). Mot chuyen roi ben muon mot
    gio thi ETA muon mot gio — con lay thang `planned_arrival_at` thi con so do
    bang dung han giao va do lech luon bang 0, tuc no khong noi gi ca.
    """
    ke_hoach_di = getattr(trip, 'planned_departure_at', None)
    ke_hoach_den = getattr(trip, 'planned_arrival_at', None)
    if not ke_hoach_den:
        return None
    thuc_di = getattr(trip, 'actual_departure_at', None)
    if not (thuc_di and ke_hoach_di):
        return ke_hoach_den
    return utc(ke_hoach_den) + (utc(thuc_di) - utc(ke_hoach_di))


def route_segments(route):
    """Cac chang cua mot tuyen, doc tu `segments_json`.

    Gom vao mot ham thay vi lap lai khoi `try/except` trong vong lap: khoi do
    can o HAI cho (tinh vi tri mo phong, va tra ve cho giao dien ve tuyen), va
    hai ban sao thi de troi khoi nhau.
    """
    if not route:
        return []
    try:
        rows = json.loads(route.segments_json or '[]')
    except (ValueError, TypeError):
        return []
    return rows if isinstance(rows, list) else []


def enrich_route_segments(segments):
    enriched = []
    for segment in segments if isinstance(segments, list) else []:
        if not isinstance(segment, dict):
            continue
        row = dict(segment)
        origin = row.get('from') or row.get('origin')
        destination = row.get('to') or row.get('destination')
        origin_point = reference_coordinates(origin)
        destination_point = reference_coordinates(destination)
        if origin_point and row.get('origin_lat') is None and row.get('from_lat') is None:
            row['origin_lat'], row['origin_lng'] = origin_point
            row['from_lat'], row['from_lng'] = origin_point
        if destination_point and row.get('destination_lat') is None and row.get('to_lat') is None:
            row['destination_lat'], row['destination_lng'] = destination_point
            row['to_lat'], row['to_lng'] = destination_point
        enriched.append(row)
    return enriched


def control_tower(db, now=None):
    now = utc(now or datetime.now(timezone.utc))
    active = db.query(TransportTrip).filter(
        TransportTrip.status.in_(['dispatched', 'in_transit'])).all()
    trips = {trip.id: trip for trip in active}
    links = db.query(TripDeliveryOrder).filter(TripDeliveryOrder.trip_id.in_(trips)).all()
    by_do = defaultdict(list)
    for link in links:
        by_do[link.do_id].append(trips[link.trip_id])
    orders = db.query(DeliveryOrder).filter(DeliveryOrder.canonical_status != 'cancelled', or_(
        DeliveryOrder.canonical_status.in_(['in_transit', 'arrived']),
        DeliveryOrder.id.in_(by_do),
    )).order_by(DeliveryOrder.id).all()
    ids = [order.id for order in orders]
    tracks = {row.do_id: row for row in db.query(VehicleTracking).filter(VehicleTracking.do_id.in_(ids))}
    # Nap MOT luot, khong truy van trong vong lap: o quy mo hang tram chuyen dang
    # chay thi mot truy van moi dong la mot man hinh khong mo duoc.
    fo_ids = {t.freight_order_id for t in active if t.freight_order_id}
    freight_orders = {row.id: row for row in
                      db.query(FreightOrder).filter(FreightOrder.id.in_(fo_ids))} if fo_ids else {}
    customers = {row.id: row for row in db.query(Customer).filter(Customer.id.in_([o.customer_id for o in orders]))}
    routes = {row.id: row for row in db.query(Route).filter(Route.id.in_([o.route_id for o in orders]))}
    driver_ids = {o.driver_id for o in orders} | {t.driver_id for t in active} | {t.co_driver_id for t in active}
    drivers = {row.id: row for row in db.query(Driver).filter(Driver.id.in_(driver_ids))}
    incidents = defaultdict(list)
    for row in db.query(Incident).filter(Incident.do_id.in_(ids)).order_by(Incident.id.desc()):
        incidents[row.do_id].append({key: getattr(row, key) for key in
            ('id', 'vehicle_id', 'incident_type', 'status', 'severity', 'location', 'description', 'reported_at')})
    pods = defaultdict(list)
    for row in db.query(DeliveryPODRecord).filter(DeliveryPODRecord.do_id.in_(ids)):
        pods[row.do_id].append(row)
    documents = defaultdict(list)
    pod_ids = [p.id for rows in pods.values() for p in rows]
    # Do not fetch binary document content for a fleet overview.
    for row in db.query(DeliveryPODDocument.id, DeliveryPODDocument.pod_record_id,
                        DeliveryPODDocument.file_name).filter(DeliveryPODDocument.pod_record_id.in_(pod_ids)):
        documents[row.pod_record_id].append({'id': row.id, 'file_name': row.file_name})
    legs = defaultdict(list)
    for row in db.query(TransportTripLeg).filter(TransportTripLeg.trip_id.in_(trips)).order_by(TransportTripLeg.sequence_no):
        legs[row.trip_id].append(row)
    events = defaultdict(list)
    event_positions = {}
    su_kien = db.query(TransportEvent).filter(TransportEvent.trip_id.in_(trips)).order_by(TransportEvent.event_time).all()
    # So ANH / chung tu cua tung su kien, nap MOT luot.
    #
    # Ban mau ve o anh nho duoi moc "lay hang" ("2 anh"). Khong co con so nay thi
    # khong biet moc nao co bang chung — ma do dung la thu phan biet mot moc co
    # anh chup thung hang voi mot moc chi co dong chu.
    so_tai_lieu = defaultdict(int)
    if su_kien:
        from models import TransportEventDocument
        for ma, dem in db.query(
            TransportEventDocument.event_id, func.count(TransportEventDocument.id)
        ).filter(TransportEventDocument.event_id.in_([r.id for r in su_kien])
                 ).group_by(TransportEventDocument.event_id):
            so_tai_lieu[ma] = dem
    for row in su_kien:
        if coordinates(row.lat, row.lng):
            event_positions[row.trip_id] = row
        events[row.trip_id].append({
            'id': row.id, 'type': row.event_type, 'time': iso(row.event_time),
            'location': row.location_text, 'source': row.source, 'note': row.note,
            'lat': row.lat, 'lng': row.lng, 'speed_kmh': row.speed_kmh,
            'document_count': so_tai_lieu.get(row.id, 0),
        })
    items = []
    for order in orders:
        # Keep each active trip separately: one DO can be allocated to several trucks.
        for trip in sorted(by_do[order.id], key=lambda t: t.id) or [None]:
            vehicle_id = trip.vehicle_id if trip else order.vehicle_id
            driver_id = trip.driver_id if trip else order.driver_id
            driver = drivers.get(driver_id)
            customer = customers.get(order.customer_id)
            route = routes.get(order.route_id)
            track = tracks.get(order.id)
            valid = bool(track and coordinates(track.lat, track.lng)
                         and (not vehicle_id or track.vehicle_id == vehicle_id)
                         and len(by_do[order.id]) <= 1)
            if valid and trip and trip.actual_departure_at:
                valid = bool(track.last_update and utc(track.last_update) >= utc(trip.actual_departure_at))
            point = event_positions.get(trip.id) if trip else None
            if point:
                lat, lng, speed, observed_at = point.lat, point.lng, point.speed_kmh, point.event_time
                valid = True
            else:
                lat, lng, speed, observed_at = (track.lat, track.lng, track.speed_kmh, track.last_update) if valid else (None, None, None, None)
            age = (now - utc(observed_at)).total_seconds() if valid and observed_at else None
            gps_status = 'missing' if not valid else 'fresh' if age is not None and 0 <= age <= 900 else 'stale'

            # VI TRI MO PHONG, khi khong co vi tri THAT con moi.
            #
            # Bo du lieu mau ghi mot moc GPS luc NAP, nen sau muoi lam phut ngoi
            # xem la ca hai xe deu thanh "GPS cu" va hai diem tren ban do dung
            # yen mot cho — do duoc tren man hinh that. Voi mot ban demo thi do
            # la mot man hinh chet, va nap lai du lieu khong sua duoc: bao nhieu
            # lan nap cung se cu di sau muoi lam phut.
            #
            # Nen khi thiet bi khong gui gi con moi, TINH vi tri tai luc doc: xe
            # di duoc bao nhieu phan tuyen thi dat diem o dung cho do tren duong
            # gap khuc cua tuyen. Xem `services/gps_simulation.py`.
            #
            # Vi tri THAT luon duoc uu tien; mo phong chi lap vao cho trong. Va
            # no duoc danh dau `simulated` chu khong phai `fresh` — mot diem mo
            # phong ma man hinh bao la GPS thiet bi thi nguoi truc se tin vao mot
            # vi tri khong ai do duoc.
            # HINH DUONG BO THAT cua tuyen, da luu san o bang `routes`. Doc chu
            # khong lay moi: mot loi goi ra ngoai giua vong lap dung nay se lam
            # ca man Theo doi cho hang chuc giay.
            hinh_bo = dich_vu_duong_bo.hinh_da_luu(route)
            diem_duong_bo = hinh_bo.get('diem') if hinh_bo else None

            simulated = None
            if gps_status != 'fresh' and trip and trip.status in ('dispatched', 'in_transit'):
                simulated = gps_simulation.vi_tri_mo_phong(
                    trip, enrich_route_segments(route_segments(route)), now,
                    tong_km=(hinh_bo.get('km') if hinh_bo else None) or (route.distance_km if route else None),
                    trang_thai_don=order.canonical_status,
                    # Xe chay tren DUONG BO that, khong tren duong thang noi cac
                    # tram — mot duong thang tu Long An sang Cai Mep di xuyen
                    # qua song, va cai xe mo phong dung giua song.
                    duong_bo=diem_duong_bo,
                )
            if simulated:
                lat, lng = simulated['lat'], simulated['lng']
                speed = simulated['speed_kmh']
                observed_at = simulated['quan_sat_luc']
                age = 0
                gps_status = 'simulated'

            due = utc(order.delivery_window_end or order.planned_arrival_at)
            order_incidents = [inc for inc in incidents[order.id] if not inc['vehicle_id'] or inc['vehicle_id'] == vehicle_id]
            open_incidents = [inc for inc in order_incidents if str(inc['status']).lower() not in ('resolved', 'closed', 'cancelled')]
            selected_pods = [p for p in pods[order.id] if p.trip_id == (trip.id if trip else None)]
            trip_legs = legs[trip.id] if trip else []
            segments = route_segments(route)
            overdue = bool(due and due < now and order.canonical_status not in ('delivered', 'cancelled'))
            items.append({
                'key': f'{trip.id if trip else "legacy"}:{order.id}',
                'trip_id': trip.id if trip else None, 'trip_status': trip.status if trip else None,
                # Ma va phien ban LENH VAN CHUYEN. Duong ghi su kien van tai doi
                # `expected_version` cua lenh nay, khong phai cua chuyen — gui sai
                # thi tra ve VERSION_CONFLICT va nguoi dung khong hieu vi sao.
                'freight_order_id': trip.freight_order_id if trip else None,
                'freight_order_version': (
                    freight_orders[trip.freight_order_id].version
                    if trip and trip.freight_order_id in freight_orders else None),
                'freight_order_status': (
                    freight_orders[trip.freight_order_id].status
                    if trip and trip.freight_order_id in freight_orders else None),
                'do_id': order.id, 'status': order.canonical_status,
                'customer_name': customer.name if customer else order.customer_id,
                'vehicle_id': vehicle_id, 'driver_id': driver_id,
                'driver_name': driver.name if driver else driver_id,
                'driver_phone': driver.phone if driver else None,
                'co_driver_name': (drivers[trip.co_driver_id].name if trip and trip.co_driver_id in drivers else None) if trip else order.co_driver,
                'route_name': route.name if route else order.route_id,
                'origin': order.origin, 'destination': order.destination,
                'route_segments': enrich_route_segments(segments),
                'route_distance_km': route.distance_km if route else None,
                # Hinh duong bo that de giao dien VE dung tuyen, thay vi tu di
                # lay tu trinh duyet roi ve duong thang khi khong lay duoc.
                'duong_bo': diem_duong_bo,
                'km_duong_bo': hinh_bo.get('km') if hinh_bo else None,
                'delivery_due': iso(due), 'planned_arrival_at': iso(trip.planned_arrival_at if trip else order.planned_arrival_at),
                'planned_return_at': iso(trip.planned_return_at if trip else order.planned_return_at),
                # MOC KE TIEP can ghi, tinh tu chuoi moc chinh cua lenh van chuyen.
                #
                # Giao dien can biet moc nao la moc tiep theo de ve dung mot nut
                # "ghi moc" — doan o tang giao dien thi no phai lap lai chuoi
                # `MAIN_SEQUENCE`, va hai ban sao se troi khoi nhau.
                'next_milestone': moc_ke_tiep(events[trip.id] if trip else []),
                'milestones': CHUOI_MOC,
                # ETA suy tu GIO XUAT BEN THUC TE cong thoi luong ke hoach.
                #
                # Truoc day o nay luon la `None`, va giao dien ghi "Chua co nguon
                # du bao". Lay thang gio ke hoach lam du bao thi con so vo nghia:
                # no bang dung han giao nen do lech luon bang 0. Neo vao gio xuat
                # ben THUC TE thi mot chuyen roi ben muon mot gio se hien ETA
                # muon mot gio — do la thong tin that.
                'predicted_eta': iso(eta_du_bao(trip)) if trip else None,
                'deviation_km': None, 'overdue': overdue,
                'awaiting_pod': order.canonical_status == 'arrived',
                'gps': {'status': gps_status, 'lat': lat,
                        'lng': lng, 'speed_kmh': speed,
                        'last_update': iso(observed_at),
                        'age_seconds': max(0, age) if age is not None else None,
                        # `simulated` de giao dien danh dau RIENG. Thieu co nay
                        # thi mot diem tinh ra hien y het mot diem thiet bi gui.
                        'simulated': bool(simulated),
                        # Don DA DEN NOI thi tien do la 100% va con lai 0 km, ke ca
                        # khi khong chay mo phong (vi da co vi tri that con moi).
                        # Bo trong thi o "Da di / Con" tren ho so chuyen rong tron
                        # cho dung nhung chuyen DA di het duong — doc ra nhu he
                        # thong khong biet gi ve chuyen vua ve toi.
                        'progress_percent': (
                            100.0 if order.canonical_status in ('arrived', 'delivered')
                            else (simulated['phan_tram'] if simulated else None)),
                        'remaining_km': (
                            0.0 if order.canonical_status in ('arrived', 'delivered')
                            else (simulated['con_lai_km'] if simulated else None))},
                'incidents': order_incidents, 'open_incident_count': len(open_incidents),
                'pod_count': len(selected_pods),
                'pods': [{'id': p.id, 'receiver_name': p.receiver_name, 'location': p.location_text,
                          'time': iso(p.delivery_time), 'status': p.status, 'documents': documents[p.id]} for p in selected_pods],
                'events': events[trip.id] if trip else [],
                'legs': [{'id': leg.id, 'origin': leg.origin, 'destination': leg.destination,
                          'status': leg.status, 'type': leg.leg_type,
                          'planned_arrival_at': iso(leg.planned_arrival_at),
                          'actual_arrival_at': iso(leg.actual_arrival_at)} for leg in trip_legs],
            })
    return {'generated_at': iso(now), 'gps_stale_after_seconds': 900, 'items': items,
            'kpis': {'total': len(items),
                     'vehicles': len({i['vehicle_id'] for i in items if i['vehicle_id']}),
                     'overdue': sum(i['overdue'] for i in items),
                     # Mo phong KHONG tinh la mat tin hieu — no la mot vi tri tinh
                     # duoc, chi khong phai do thiet bi gui. Dem chung vao thi dai
                     # so lieu bao dong cho mot chuyen dang hien binh thuong tren
                     # ban do, va nguoi truc di goi tai xe khong can thiet.
                     'gps_unavailable': sum(i['gps']['status'] not in ('fresh', 'simulated') for i in items),
                     'gps_simulated': sum(i['gps']['status'] == 'simulated' for i in items),
                     'awaiting_pod': sum(i['awaiting_pod'] for i in items),
                     'incidents': sum(i['open_incident_count'] > 0 for i in items),
                     'returning': sum(i['status'] == 'delivered' for i in items)}}
