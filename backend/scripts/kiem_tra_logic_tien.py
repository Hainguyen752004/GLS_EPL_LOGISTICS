"""Kiem so hoc cua luong tien, thay vi tin vao viec luong chay xong.

Chay xong khong co nghia la tinh dung. Nhung dieu duoi day phai dung, va neu
sai thi la sai o logic backend chu khong phai o so lieu demo.
"""
import os
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
fails = []
checks = 0


def check(name, ok, detail=''):
    global checks
    checks += 1
    print('%-4s %-58s %s' % ('OK' if ok else 'SAI', name, detail))
    if not ok:
        fails.append(name)


with engine.connect() as c:
    def rows(sql, **kw):
        return list(c.execute(text(sql), kw))

    def tables():
        return {r[0] for r in c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))}

    have = tables()

    # ---------------------------------------------------------------- 1
    # So cai phai CAN: tong No == tong Co, tren toan so va tren tung but toan.
    if 'journal_lines' in have:
        total = rows("SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM journal_lines")[0]
        check('So cai can tren toan bo so', Decimal(total[0]) == Decimal(total[1]),
              'No=%s Co=%s' % (total[0], total[1]))

        unbalanced = rows("""
            SELECT batch_id, SUM(debit) d, SUM(credit) k
            FROM journal_lines GROUP BY batch_id
            HAVING SUM(debit) <> SUM(credit)
        """)
        check('Moi but toan deu can', not unbalanced,
              'lech: %s' % [(r[0], str(r[1]), str(r[2])) for r in unbalanced[:3]])

        neg = rows("SELECT COUNT(*) FROM journal_lines WHERE debit < 0 OR credit < 0")[0][0]
        check('Khong co dong No/Co am', neg == 0, '%s dong am' % neg)

        both = rows("SELECT COUNT(*) FROM journal_lines WHERE debit <> 0 AND credit <> 0")[0][0]
        check('Mot dong khong vua No vua Co', both == 0, '%s dong' % both)

    # ---------------------------------------------------------------- 2
    # Chi phi thuc te: tong phai bang tong cac dong hang muc.
    if 'freight_actual_costs' in have and 'freight_charge_items' in have:
        bad = rows("""
            SELECT fc.id, fc.total_amount, COALESCE(SUM(i.total_amount + i.rounding_adjustment), 0)
            FROM freight_actual_costs fc
            LEFT JOIN freight_charge_items i ON i.cost_id = fc.id
            GROUP BY fc.id, fc.total_amount
            HAVING fc.total_amount <> COALESCE(SUM(i.total_amount + i.rounding_adjustment), 0)
        """)
        check('Chi phi thuc te = tong cac dong hang muc', not bad,
              'lech: %s' % [(r[0], str(r[1]), str(r[2])) for r in bad[:3]])

        bad2 = rows("""
            SELECT id, subtotal_amount, tax_amount, total_amount
            FROM freight_actual_costs
            WHERE subtotal_amount + tax_amount <> total_amount
        """)
        check('Tong = Tam tinh + Thue', not bad2,
              'lech: %s' % [(r[0], str(r[1]), str(r[2]), str(r[3])) for r in bad2[:3]])

        bad3 = rows("""
            SELECT id, net_amount, tax_amount, total_amount FROM freight_charge_items
            WHERE net_amount + tax_amount <> total_amount
        """)
        check('Tung dong: Net + Thue = Tong', not bad3,
              'lech: %s' % [(r[0], str(r[1]), str(r[2]), str(r[3])) for r in bad3[:3]])

    # ---------------------------------------------------------------- 3
    # Tien te: moi ban ghi tien phai co ma tien te va ty gia da chot.
    for table, col in (('freight_actual_costs', 'currency_code'), ('ap_invoices', 'currency_code')):
        if table in have:
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"), {'t': table})}
            if col in cols:
                missing = rows(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL OR {col} = ''")[0][0]
                check(f'{table}: khong ban ghi nao thieu ma tien te', missing == 0, '%s thieu' % missing)
            if 'exchange_rate_snapshot' in cols:
                miss = rows(f"SELECT COUNT(*) FROM {table} WHERE exchange_rate_snapshot IS NULL")[0][0]
                check(f'{table}: ty gia duoc chot lai tai thoi diem ghi', miss == 0, '%s thieu' % miss)

    # ---------------------------------------------------------------- 4
    # Kieu du lieu tien: phai la NUMERIC, khong duoc la float nhi phan.
    money_like = rows("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='public'
          AND (column_name LIKE '%amount%' OR column_name LIKE '%cost%'
               OR column_name LIKE '%price%' OR column_name LIKE '%_fee%')
          AND data_type IN ('double precision','real')
    """)
    check('Khong con cot tien nao la so thuc nhi phan', not money_like,
          'con: %s' % [(r[0], r[1]) for r in money_like[:6]])

    # ---------------------------------------------------------------- 5
    # AR: hoa don da hach toan phai co but toan so cai tuong ung.
    if 'ar_invoices' in have:
        posted = rows("SELECT COUNT(*) FROM ar_invoices WHERE canonical_status = 'posted'")[0][0]
        check('Co hoa don AR da hach toan', posted > 0, '%s hoa don posted' % posted)
        bad = rows("SELECT id, amount, vat_amount, total FROM ar_invoices WHERE amount + vat_amount <> total")
        check('Hoa don AR: Tien hang + VAT = Tong', not bad,
              'lech: %s' % [(r[0], str(r[1]), str(r[2]), str(r[3])) for r in bad[:3]])
    if 'journal_lines' in have:
        batches = rows("SELECT COUNT(DISTINCT batch_id) FROM journal_lines")[0][0]
        check('Co but toan so cai', batches > 0, '%s but toan' % batches)
        # Doi ung: cot chuc nang cung phai can, khong chi cot nguyen te.
        fx = rows("SELECT COALESCE(SUM(functional_debit),0), COALESCE(SUM(functional_credit),0) FROM journal_lines")[0]
        check('So cai can ca o dong tien chuc nang', Decimal(fx[0]) == Decimal(fx[1]),
              'No=%s Co=%s' % (fx[0], fx[1]))

print()
print('=' * 78)
print('%d kiem tra, %d sai' % (checks, len(fails)))
for f in fails:
    print('  SAI:', f)
engine.dispose()
sys.exit(1 if fails else 0)
