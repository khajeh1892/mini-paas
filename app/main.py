from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, sqlite3, string, random

DB_PATH = os.getenv("DB_PATH", "/data/db.sqlite3")

app = FastAPI(title="Mini PaaS Demo (URL Shortener)")

class CreateReq(BaseModel):
    url: str

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS links(
        code TEXT PRIMARY KEY,
        url  TEXT NOT NULL
      )
    """)
    con.commit()
    con.close()

def gen_code(n=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(n))

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/create")
def create(req: CreateReq):
    code = gen_code()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # تلاش تا وقتی کد تکراری نشه
    for _ in range(5):
        try:
            cur.execute("INSERT INTO links(code,url) VALUES(?,?)", (code, req.url))
            con.commit()
            con.close()
            return {"code": code, "short": f"/{code}"}
        except sqlite3.IntegrityError:
            code = gen_code()
    con.close()
    raise HTTPException(500, "Could not create code")

@app.get("/{code}")
def resolve(code: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT url FROM links WHERE code=?", (code,))
    row = cur.fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "Not found")
    return {"url": row[0]}
