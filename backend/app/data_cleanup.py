"""Safe manifest-driven cleanup; never imports the application's default database."""
import argparse, gc, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_RE = re.compile(r"^QT-(\d{4})-(\d{3})$")
MASTER = {"customers","vehicles","drivers","routes","locations","vehicle_types","items","uoms","cost_formulas","price_lists","currencies","users","roles","chart_of_accounts","account_mappings","accounting_periods"}
BUSINESS = {"quotations","quotation_details","delivery_orders","delivery_order_details","shipment_costs","vehicle_tracking","pod","ar_invoices","gl_transactions","incidents","audit_logs","journal_batches","journal_lines"}
LOGICAL_RELATIONS = {"incidents": ("do_id", "delivery_orders")}

def _path(url):
    if not url.startswith("sqlite:///"): raise ValueError("not a SQLite database URL")
    return Path(url[10:])

def _bytes(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
def manifest_sha256(v): return hashlib.sha256(_bytes(v)).hexdigest()
def write_manifest(v,path):
    data=_bytes(v); Path(path).write_bytes(data); return hashlib.sha256(data).hexdigest()

def _schema(c):
    out={}
    for (t,) in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"):
        cols=c.execute(f'pragma table_info("{t}")').fetchall()
        raw=list(c.execute(f'pragma foreign_key_list("{t}")')); groups={}
        for x in raw:groups.setdefault(x[0],[]).append(x)
        fks=[]
        for rows in groups.values():
            rows=sorted(rows,key=lambda x:x[1]); fks.append((tuple(x[3] for x in rows),rows[0][2],tuple(x[4] for x in rows)))
        out[t]={"pk":[x[1] for x in sorted(cols,key=lambda x:x[5]) if x[5]],"columns":[x[1] for x in cols],"fks":fks}
    return out

def _ids(c,t,pk,w="1=1",p=()):
    keys=[pk] if isinstance(pk,str) else pk; names=','.join(f'"{x}"' for x in keys)
    return [x[0] if len(keys)==1 else tuple(x) for x in c.execute(f'select {names} from "{t}" where {w} order by {names}',p)]

def _key_predicate(columns,values):
    clauses=[]; params=[]
    for value in values:
        parts=value if isinstance(value,(tuple,list)) else (value,)
        clauses.append('('+' and '.join(f'"{x}"=?' for x in columns)+')'); params.extend(parts)
    return ' or '.join(clauses) or '0',tuple(params)

def _ids_matching(c,t,pk,columns,values,batch_size=400):
    found=set(); values=list(values)
    for start in range(0,len(values),batch_size):
        where,params=_key_predicate(columns,values[start:start+batch_size])
        found.update(_ids(c,t,pk,where,params))
    return found

def _delete_matching(c,t,pk,values,batch_size=400):
    values=list(values)
    for start in range(0,len(values),batch_size):
        where,params=_key_predicate(pk,values[start:start+batch_size])
        c.execute(f'delete from "{t}" where {where}',params)

def build_manifest(database_url,keep_root_max=20,_connection=None):
    if not 1<=keep_root_max<=999: raise ValueError("keep_root_max must be between 1 and 999")
    owned=_connection is None; c=_connection or sqlite3.connect(_path(database_url))
    try:
        s=_schema(c); pk=s["quotations"]["pk"]; roots=_ids(c,"quotations",pk)
        keep=[]; delete=[]; bad=[]
        for x in roots:
            m=ROOT_RE.fullmatch(str(x))
            (bad if not m else keep if int(m.group(2))<=keep_root_max else delete).append(x)
        selected={"quotations":set(delete+bad)}; quarantine={"quotations":sorted(bad)} if bad else {}
        changed=True
        while changed:
            changed=False
            for t,m in s.items():
                if t in MASTER or not m["pk"]: continue
                found=set(selected.get(t,set()))
                for cols,parent,_ in m["fks"]:
                    vals=selected.get(parent,set())
                    if vals:
                        found.update(_ids_matching(c,t,m["pk"],cols,sorted(vals,key=str)))
                if found!=selected.get(t,set()): selected[t]=found; changed=True
            for t,(col,parent) in LOGICAL_RELATIONS.items():
                if t in s and s[t]["pk"] and selected.get(parent):
                    vals=selected[parent]; q=",".join("?"*len(vals)); found=set(selected.get(t,set()))
                    found.update(_ids(c,t,s[t]["pk"][0],f'"{col}" in ({q})',tuple(sorted(vals,key=str))))
                    if found!=selected.get(t,set()):selected[t]=found; changed=True
        # Null/dangling transaction references are quarantine candidates. Master Data
        # itself is preserved; business rows pointing at missing Master Data are
        # quarantined so operators can recreate the master record or remove the row.
        for t,m in sorted(s.items()):
            if t in MASTER or t=="quotations" or not m["pk"]: continue
            orphan=set()
            for cols,parent,parent_cols in m["fks"]:
                if parent not in MASTER or t in BUSINESS:
                    nulls=' or '.join(f'"{x}" is null' for x in cols); joins=' and '.join(f'p."{pc}"="{t}"."{cc}"' for cc,pc in zip(cols,parent_cols))
                    orphan.update(_ids(c,t,m["pk"],f'({nulls}) or not exists(select 1 from "{parent}" p where {joins})'))
            orphan-=selected.get(t,set())
            if orphan: quarantine[t]=sorted(orphan,key=str); selected.setdefault(t,set()).update(orphan)
        changed=True
        while changed:
            changed=False
            for t,m in sorted(s.items()):
                if t in MASTER or not m["pk"]:continue
                found=set(quarantine.get(t,[]))
                for cols,parent,_ in m["fks"]:
                    vals=set(quarantine.get(parent,[]))
                    if vals:
                        found.update(_ids_matching(c,t,m["pk"],cols,sorted(vals,key=str)))
                if found!=set(quarantine.get(t,[])):
                    quarantine[t]=sorted(found,key=str); selected.setdefault(t,set()).update(found); changed=True
        if "audit_logs" in s and {"table_name","record_id"}<=set(s["audit_logs"]["columns"]):
            vals=set()
            for t,ids in selected.items():
                if ids:
                    q=",".join("?"*len(ids)); vals.update(_ids(c,"audit_logs",s["audit_logs"]["pk"][0],f'table_name=? and record_id in ({q})',(t,*sorted(ids,key=str))))
            if vals:selected["audit_logs"]=vals
        deleted={}
        for t,ids in selected.items():
            normal=ids-set(quarantine.get(t,[]))
            if normal:deleted[t]=sorted(normal,key=str)
        repaired={}
        doomed=selected.get("delivery_orders",set())
        if "delivery_orders" in s:
            for resource,col in (("vehicles","vehicle_id"),("drivers","driver_id")):
                if resource not in s or col not in s["delivery_orders"]["columns"]:continue
                release=[]
                for (rid,) in c.execute(f'select distinct "{col}" from delivery_orders where "{col}" is not null'):
                    q=",".join("?"*len(doomed)) or "null"
                    if not c.execute(f'select count(*) from delivery_orders where "{col}"=? and id not in ({q})',(rid,*sorted(doomed,key=str))).fetchone()[0]:release.append(rid)
                if release:repaired[resource]=sorted(release,key=str)
        counts={}
        for t in sorted(s):
            before=c.execute(f'select count(*) from "{t}"').fetchone()[0]; counts[t]={"before":before,"after":before-len(selected.get(t,set()))}
        repaired={k:v for k,v in repaired.items() if v}
        quarantine={k:v for k,v in quarantine.items() if v}
        deleted={k:v for k,v in deleted.items() if v}
        result={"format":1,"database":"sqlite","keep_root_max":keep_root_max,"kept":{"quotations":sorted(keep)},"repaired":dict(sorted(repaired.items())),"quarantined":dict(sorted(quarantine.items())),"deleted":dict(sorted(deleted.items())),"counts":counts}
        return json.loads(json.dumps(result,ensure_ascii=False))
    finally:
        if owned:c.close()

def _backup(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(src) as a,sqlite3.connect(dst) as b:
        a.backup(b)
        cur=b.execute("pragma integrity_check")
        try:
            if cur.fetchone()[0]!="ok":raise RuntimeError("backup integrity check failed")
        finally:
            cur.close()

def _fk_rows(connection):
    rows=connection.execute("pragma foreign_key_check").fetchall()
    return [tuple(row) for row in rows]

def _verify_backup_restore(backup,expected_fk_rows=None):
    probe=Path(str(backup)+".verify.tmp")
    try:
        shutil.copy2(backup,probe)
        c=sqlite3.connect(probe)
        try:
            cur=c.execute("pragma integrity_check")
            try:
                if cur.fetchone()[0]!="ok":raise RuntimeError("backup restore integrity check failed")
            finally:
                cur.close()
            cur=c.execute("pragma foreign_key_check")
            try:
                actual=[tuple(row) for row in cur.fetchall()]
                if expected_fk_rows is not None:
                    if sorted(actual)!=sorted(expected_fk_rows):raise RuntimeError("backup restore foreign key check changed source state")
                elif actual:
                    raise RuntimeError("backup restore foreign key check failed")
            finally:
                cur.close()
        finally:
            c.close(); gc.collect()
    finally:
        for _ in range(5):
            try:
                if probe.exists():probe.unlink()
                break
            except PermissionError:
                time.sleep(0.05); gc.collect()
        else:
            probe.unlink()

def apply_manifest(database_url,manifest_path,approved_sha256,backup_dir,failure_hook=None):
    raw=Path(manifest_path).read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    if not approved_sha256 or digest.lower()!=approved_sha256.lower():raise RuntimeError("approved SHA256 does not match manifest")
    plan=json.loads(raw.decode()); path=_path(database_url); c=sqlite3.connect(path)
    try:
        c.execute("pragma foreign_keys=on"); c.execute("begin immediate")
        fresh=build_manifest(database_url,plan["keep_root_max"],c)
        if fresh!=plan:raise RuntimeError("database drift detected; regenerate and re-approve manifest")
        source_fk=_fk_rows(c)
        backup=Path(backup_dir)/f"{path.stem}-{time.strftime('%Y%m%dT%H%M%S')}-{digest[:12]}.sqlite3"; _backup(path,backup); _verify_backup_restore(backup,source_fk)
        s=_schema(c)
        try:
            remove={k:{tuple(x) if isinstance(x,list) else x for x in v} for k,v in plan["deleted"].items()}
            for k,v in plan["quarantined"].items():remove.setdefault(k,set()).update(tuple(x) if isinstance(x,list) else x for x in v)
            remaining=set(remove); order=[]
            while remaining:
                leaves=sorted(t for t in remaining if not any(f[1]==t for child in remaining for f in s.get(child,{}).get("fks",[]))) or [sorted(remaining)[0]]
                order+=leaves; remaining-=set(leaves)
            for t in order:
                vals=sorted(remove[t],key=str)
                if vals and t in s:
                    _delete_matching(c,t,s[t]["pk"],vals)
            for t,vals in plan["repaired"].items():
                if vals:
                    q=",".join("?"*len(vals)); status="Sẵn sàng" if t=="vehicles" else "🟢 Rảnh (Sẵn sàng)"; c.execute(f'update "{t}" set status=? where "{s[t]["pk"][0]}" in ({q})',(status,*vals))
            if failure_hook:failure_hook(c)
            after_fk=_fk_rows(c)
            if len(after_fk)>len(source_fk):raise RuntimeError("foreign key check regressed")
            c.commit()
        except Exception:c.rollback();raise
    finally:c.close()
    write_manifest({"source_manifest_sha256":digest,"records":plan["quarantined"]},Path(manifest_path).with_suffix(Path(manifest_path).suffix+".quarantine.json"))
    return backup

def restore_backup(database_url,backup_path,failure_hook=None):
    target=_path(database_url); backup=Path(backup_path)
    if not backup.is_file():raise RuntimeError("backup does not exist")
    temp=target.with_name(target.name+".restore.tmp")
    try:
        shutil.copy2(backup,temp)
        c=sqlite3.connect(temp)
        try:
            cursor=c.execute("pragma integrity_check"); result=cursor.fetchone()[0]; cursor.close()
            if result!="ok":raise RuntimeError("restore integrity check failed")
        finally:
            c.close()
        previous=target.with_name(target.name+".restore.previous")
        try:
            os.chmod(target,0o666); os.chmod(temp,0o666)
            os.replace(target,previous)
            if failure_hook:failure_hook()
            os.replace(temp,target)
            previous.unlink(missing_ok=True)
        except Exception:
            if previous.exists():os.replace(previous,target)
            raise
    finally:
        if temp.exists():temp.unlink(missing_ok=True)

def postgres_backup(database_url,backup_path,runner=subprocess.run):
    dump,restore,verify=(os.getenv(x) for x in ("PG_DUMP_PATH","PG_RESTORE_PATH","PG_VERIFY_DATABASE_URL"))
    if not all((dump,restore,verify)):raise RuntimeError("PostgreSQL cleanup requires PG_DUMP_PATH, PG_RESTORE_PATH, and PG_VERIFY_DATABASE_URL")
    if verify==database_url:raise RuntimeError("verification database must be a distinct disposable database")
    for tool in (dump,restore):
        if not ((Path(tool).is_file() and os.access(tool,os.X_OK)) or shutil.which(tool)):raise RuntimeError(f"PostgreSQL tool is not executable: {tool}")
    runner([dump,"--format=custom","--file",str(backup_path),database_url],check=True)
    runner([restore,"--list",str(backup_path)],check=True,capture_output=True,text=True)
    runner([restore,"--clean","--if-exists","--dbname",verify,str(backup_path)],check=True)
    runner([restore,"--list",str(backup_path)],check=True,capture_output=True,text=True)

def postgres_restore(database_url,backup_path,runner=subprocess.run):
    restore=os.getenv("PG_RESTORE_PATH")
    if not restore or not ((Path(restore).is_file() and os.access(restore,os.X_OK)) or shutil.which(restore)):
        raise RuntimeError("PG_RESTORE_PATH must name an executable")
    runner([restore,"--list",str(backup_path)],check=True,capture_output=True,text=True)
    runner([restore,"--clean","--if-exists","--dbname",database_url,str(backup_path)],check=True)
    runner([restore,"--list",str(backup_path)],check=True,capture_output=True,text=True)

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("dry-run","apply","restore")); p.add_argument("--database-url",required=True); p.add_argument("--keep-root-max",type=int,default=20); p.add_argument("--manifest",required=True); p.add_argument("--backup-dir",required=True); p.add_argument("--approved-sha256",default=os.getenv("CLEANUP_APPROVED_SHA256")); a=p.parse_args(argv)
    postgres=a.database_url.startswith(("postgresql:","postgres:"))
    if postgres and a.command in ("dry-run","apply"):
        raise RuntimeError("PostgreSQL manifest/apply is not supported; no database was changed")
    if a.command=="dry-run":
        plan=build_manifest(a.database_url,a.keep_root_max); print(json.dumps({"manifest_sha256":write_manifest(plan,a.manifest),**plan},ensure_ascii=False,sort_keys=True))
    elif a.command=="apply":print(apply_manifest(a.database_url,a.manifest,a.approved_sha256,a.backup_dir))
    elif postgres:postgres_restore(a.database_url,a.manifest)
    else:restore_backup(a.database_url,a.manifest)
if __name__=="__main__":main()
