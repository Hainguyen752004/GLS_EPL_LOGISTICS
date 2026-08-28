import json
import sqlite3

import pytest


def make_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE customers(id TEXT PRIMARY KEY);
        CREATE TABLE quotations(id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(id));
        CREATE TABLE quotation_details(id INTEGER PRIMARY KEY, quotation_id TEXT REFERENCES quotations(id));
        CREATE TABLE sales_orders(id TEXT PRIMARY KEY, quotation_id TEXT REFERENCES quotations(id));
        CREATE TABLE delivery_orders(id TEXT PRIMARY KEY, so_id TEXT REFERENCES sales_orders(id), vehicle_id TEXT, driver_id TEXT);
        CREATE TABLE pod(do_id TEXT PRIMARY KEY REFERENCES delivery_orders(id));
        CREATE TABLE vehicles(id TEXT PRIMARY KEY, status TEXT);
        CREATE TABLE drivers(id TEXT PRIMARY KEY, status TEXT);
        CREATE TABLE audit_logs(id INTEGER PRIMARY KEY, table_name TEXT, record_id TEXT);
        INSERT INTO customers VALUES ('C1');
        INSERT INTO quotations VALUES ('QT-2026-001','C1'),('QT-2026-021','C1'),('bad','C1');
        INSERT INTO quotation_details VALUES (1,'QT-2026-021'),(2,NULL);
        INSERT INTO sales_orders VALUES ('SO-1','QT-2026-021');
        INSERT INTO delivery_orders VALUES ('DO-1','SO-1','V1','D1');
        INSERT INTO pod VALUES ('DO-1');
        INSERT INTO vehicles VALUES ('V1','Busy');
        INSERT INTO drivers VALUES ('D1','Busy');
        INSERT INTO audit_logs VALUES (1,'quotations','QT-2026-021');
        """
    )
    con.commit()
    con.close()


def test_dry_run_is_stable_and_enumerates_plan(tmp_path):
    from data_cleanup import build_manifest

    db = tmp_path / "db.sqlite3"
    make_db(db)
    first = build_manifest(f"sqlite:///{db}", keep_root_max=20)
    second = build_manifest(f"sqlite:///{db}", keep_root_max=20)
    assert first == second
    assert first["kept"]["quotations"] == ["QT-2026-001"]
    assert first["deleted"]["quotations"] == ["QT-2026-021"]
    assert first["deleted"]["pod"] == ["DO-1"]
    assert first["deleted"]["audit_logs"] == [1]
    assert first["quarantined"]["quotations"] == ["bad"]
    assert first["quarantined"]["quotation_details"] == [2]
    assert first["counts"]["quotations"] == {"before": 3, "after": 1}
    assert "customers" not in first["deleted"]
    assert first["counts"]["customers"] == {"before": 1, "after": 1}


def test_apply_requires_matching_approved_manifest_and_rolls_back(tmp_path):
    from data_cleanup import apply_manifest, build_manifest, write_manifest

    db = tmp_path / "db.sqlite3"
    make_db(db)
    manifest = tmp_path / "manifest.json"
    plan = build_manifest(f"sqlite:///{db}")
    digest = write_manifest(plan, manifest)
    with pytest.raises(RuntimeError, match="approved SHA256"):
        apply_manifest(f"sqlite:///{db}", manifest, "wrong", tmp_path / "backups")
    apply_manifest(f"sqlite:///{db}", manifest, digest, tmp_path / "backups")
    with sqlite3.connect(db) as con:
        assert con.execute("select id from quotations").fetchall() == [("QT-2026-001",)]
        assert con.execute("select status from vehicles").fetchone() == ("Sẵn sàng",)


def test_restore_verifies_backup_then_replaces_database(tmp_path):
    from data_cleanup import apply_manifest, build_manifest, restore_backup, write_manifest

    db = tmp_path / "db.sqlite3"
    make_db(db)
    manifest = tmp_path / "manifest.json"
    digest = write_manifest(build_manifest(f"sqlite:///{db}"), manifest)
    backup = apply_manifest(f"sqlite:///{db}", manifest, digest, tmp_path / "backups")
    restore_backup(f"sqlite:///{db}", backup)
    with sqlite3.connect(db) as con:
        assert con.execute("select count(*) from quotations").fetchone()[0] == 3


def test_injected_apply_failure_leaves_no_partial_writes(tmp_path):
    from data_cleanup import apply_manifest, build_manifest, write_manifest
    db = tmp_path / "db.sqlite3"
    make_db(db)
    manifest = tmp_path / "manifest.json"
    digest = write_manifest(build_manifest(f"sqlite:///{db}"), manifest)
    with pytest.raises(RuntimeError, match="injected"):
        apply_manifest(f"sqlite:///{db}", manifest, digest, tmp_path / "backups",
                       failure_hook=lambda _con: (_ for _ in ()).throw(RuntimeError("injected")))
    with sqlite3.connect(db) as con:
        assert con.execute("select count(*) from quotations").fetchone()[0] == 3


def test_orphan_descendants_are_quarantined_as_a_fixed_point(tmp_path):
    from data_cleanup import build_manifest
    db = tmp_path / "db.sqlite3"
    make_db(db)
    with sqlite3.connect(db) as con:
        con.execute("pragma foreign_keys=off")
        con.execute("insert into sales_orders values ('SO-ORPHAN','missing')")
        con.execute("insert into delivery_orders values ('DO-ORPHAN','SO-ORPHAN',NULL,NULL)")
    plan = build_manifest(f"sqlite:///{db}")
    assert plan["quarantined"]["sales_orders"] == ["SO-ORPHAN"]
    assert plan["quarantined"]["delivery_orders"] == ["DO-ORPHAN"]


def test_postgres_requires_distinct_verification_database(monkeypatch, tmp_path):
    from data_cleanup import postgres_backup
    monkeypatch.setenv("PG_DUMP_PATH", "pg_dump")
    monkeypatch.setenv("PG_RESTORE_PATH", "pg_restore")
    monkeypatch.setenv("PG_VERIFY_DATABASE_URL", "postgresql://db/prod")
    with pytest.raises(RuntimeError, match="distinct disposable"):
        postgres_backup("postgresql://db/prod", tmp_path / "x.dump", runner=lambda *a, **k: None)


def test_restore_recovers_original_when_atomic_swap_is_interrupted(tmp_path):
    from data_cleanup import apply_manifest, build_manifest, restore_backup, write_manifest
    db = tmp_path / "db.sqlite3"; make_db(db)
    manifest = tmp_path / "manifest.json"; digest = write_manifest(build_manifest(f"sqlite:///{db}"), manifest)
    backup = apply_manifest(f"sqlite:///{db}", manifest, digest, tmp_path / "backups")
    with pytest.raises(RuntimeError, match="swap"):
        restore_backup(f"sqlite:///{db}", backup, failure_hook=lambda: (_ for _ in ()).throw(RuntimeError("swap")))
    with sqlite3.connect(db) as con:
        assert con.execute("select count(*) from quotations").fetchone()[0] == 1


def test_composite_fk_uses_complete_tuple_and_does_not_overdelete(tmp_path):
    from data_cleanup import apply_manifest, build_manifest, write_manifest
    db=tmp_path/"composite.sqlite3"
    with sqlite3.connect(db) as con:
        con.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE quotations(id TEXT PRIMARY KEY);
        CREATE TABLE pairs(a TEXT,b INTEGER,quotation_id TEXT REFERENCES quotations(id),PRIMARY KEY(a,b));
        CREATE TABLE pair_notes(id INTEGER PRIMARY KEY,a TEXT,b INTEGER,FOREIGN KEY(a,b) REFERENCES pairs(a,b));
        INSERT INTO quotations VALUES('QT-2026-001'),('QT-2026-021');
        INSERT INTO pairs VALUES('A',1,'QT-2026-021'),('A',2,'QT-2026-001');
        INSERT INTO pair_notes VALUES(1,'A',1),(2,'A',2);
        """)
    plan=build_manifest(f"sqlite:///{db}")
    assert plan["deleted"]["pairs"] == [["A",1]]
    assert plan["deleted"]["pair_notes"] == [1]
    mf=tmp_path/"m.json"; digest=write_manifest(plan,mf)
    apply_manifest(f"sqlite:///{db}",mf,digest,tmp_path/"backups")
    with sqlite3.connect(db) as con:
        assert con.execute("select a,b from pairs").fetchall()==[("A",2)]
        assert con.execute("select id from pair_notes").fetchall()==[(2,)]
