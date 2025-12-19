from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sqlite3
import string
import random

# Default to a writable path; platform ENV might override it, so we handle failures safely.
DB_PATH = os.getenv("DB_PATH", "/tmp/db.sqlite3")

app = FastAPI(title="Mini PaaS Demo (URL Shortener)")

class CreateReq(BaseModel):
    url: str

DB_READY = False
DB_ERROR = ""

def init_db() -> None:
    global DB_READY, DB_ERROR

    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS links(
                code TEXT PRIMARY KEY,
                url  TEXT NOT NULL
            )
            """
        )
        con.commit()
        con.close()
        DB_READY = True
        DB_ERROR = ""
    except Exception as e:
        # Do NOT crash the app on PaaS. Keep the service up.
        DB_READY = False
        DB_ERROR = f"{type(e).__name__}: {e}"

def gen_code(n: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(n))

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health():
    # Health must be OK so the platform stops restarting the container
    return {"ok": True, "db_ready": DB_READY, "db_path": DB_PATH, "db_error": DB_ERROR}

@app.post("/create")
def create(req: CreateReq):
    if not DB_READY:
        # optional: still accept but explain
        raise HTTPException(status_code=503, detail=f"DB not ready: {DB_ERROR}")

    code = gen_code()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for _ in range(10):
        try:
            cur.execute("INSERT INTO links(code, url) VALUES(?, ?)", (code, req.url))
            con.commit()
            con.close()
            return {"code": code, "short": f"/{code}"}
        except sqlite3.IntegrityError:
            code = gen_code()

    con.close()
    raise HTTPException(status_code=500, detail="Could not create code")

@app.get("/{code}")
def resolve(code: str):
    if not DB_READY:
        raise HTTPException(status_code=503, detail=f"DB not ready: {DB_ERROR}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT url FROM links WHERE code = ?", (code,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"url": row[0]}
