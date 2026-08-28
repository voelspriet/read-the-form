#!/usr/bin/env python3
"""Point a camera at an FAA Service Difficulty Report and get English back.

The division of labour is the whole point. GLM-5.3-Flash reads the image and is
allowed to do one thing: transcribe the characters it can see, box by box. It is
never asked what a code means. Meaning comes from the FAA's own published lookup
tables, applied here in code.

That split is deliberate. Asked to interpret, a model will produce a plausible
expansion for a code it has never seen and will not flag the guess. On a public
safety record that is not a small error, it is a fabricated fact wearing the
formatting of a real one. So: the model reads, the tables decide, and anything
the tables do not cover stays on screen as the raw code.
"""
import base64, json, os, re, io
import requests
from flask import Flask, jsonify, request, send_from_directory

ZAI_URL = "https://api.z.ai/api/paas/v4/chat/completions"
MODEL = "glm-5.3-flash"
SDR = "https://aircraftdefects.com"          # the corpus and the FAA code tables
HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder="static")

# The nine coded boxes on the form, in the order the FAA prints them, mapped to
# the lookup table that defines each one.
FIELDS = [
    ("operator_designator",   "a", "Operator Designator",     "operator"),
    ("operator_type",         "b", "Operator Type",           "operator_type"),
    ("jasc_ata_code",         "c", "JASC/ATA Code",           "jasc"),
    ("stage_of_operation",    "d", "Stage of Operation",      "stage"),
    ("how_discovered",        "e", "How Discovered",          "discovered"),
    ("nature_of_condition",   "f", "Nature of Condition",     "nature"),
    ("precautionary",         "g", "Precautionary Procedures","precaution"),
    ("faa_region",            "h", "FAA Region",              "region"),
    ("district_office",       "i", "District Office",         "district"),
    ("flight_number",         "j", "Flight Number",           None),
]

READ_PROMPT = """You are reading a photograph of an FAA Service Difficulty Report form.

Transcribe ONLY what is written in each box. Copy the characters exactly as they
appear, including letters, digits and spacing.

Do NOT expand, translate, interpret or guess the meaning of any code. Do not say
what an airline code stands for. Do not say what a zone number refers to. If a
box is empty, unreadable or absent from the form, return null for it.

Return strict JSON only, no prose and no code fences, with exactly these keys:
{"operator_designator":null,"operator_type":null,"jasc_ata_code":null,
 "stage_of_operation":null,"how_discovered":null,"nature_of_condition":null,
 "precautionary":null,"faa_region":null,"district_office":null,
 "flight_number":null,"free_text":null}

free_text is any narrative description of the defect written on the form, copied
verbatim, or null if there is none."""

_TABLES = None


def tables():
    """The FAA's own code tables, taken from the tool that already carries them."""
    global _TABLES
    if _TABLES is None:
        r = requests.get(SDR + "/api/glossary", timeout=30)
        r.raise_for_status()
        _TABLES = r.json().get("codes", {})
    return _TABLES


def decode(table_name, code):
    """One code to one meaning, or an honest miss. Never an invention."""
    if not code or not table_name:
        return None
    t = tables().get(table_name) or {}
    v = t.get(str(code).strip().upper()) or t.get(str(code).strip())
    if v is None:
        return None
    if isinstance(v, dict):
        return {"label": v.get("label") or v.get("faa"), "faa": v.get("faa"),
                "note": v.get("note")}
    return {"label": v, "faa": v, "note": None}


def read_form(image_b64, mime):
    key = os.environ.get("ZAI_API_KEY", "").strip()
    if not key or "paste" in key.lower():
        raise RuntimeError("No z.ai API key yet. Put a real one in .env as ZAI_API_KEY, "
                           "then restart. Get one at https://z.ai")
    body = {
        "model": MODEL,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": READ_PROMPT},
            {"type": "image_url",
             "image_url": {"url": "data:%s;base64,%s" % (mime, image_b64)}},
        ]}],
    }
    r = requests.post(ZAI_URL, json=body, timeout=180,
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError("z.ai %s: %s" % (r.status_code, r.text[:300]))
    txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)          # models like to wrap JSON in prose
    if not m:
        raise RuntimeError("model returned no JSON: " + txt[:300])
    return json.loads(m.group(0))


@app.post("/api/read")
def api_read():
    f = request.files.get("image")
    if not f:
        return jsonify(error="no image"), 400
    raw = f.read()
    if len(raw) > 12 * 1024 * 1024:
        return jsonify(error="image over 12 MB"), 400
    mime = f.mimetype or "image/jpeg"
    try:
        seen = read_form(base64.b64encode(raw).decode(), mime)
    except Exception as e:
        return jsonify(error=str(e)[:400]), 502

    out, unresolved = [], []
    for key, letter, label, table in FIELDS:
        code = seen.get(key)
        code = None if code in ("", "null") else code
        meaning = decode(table, code) if code else None
        if code and table and not meaning:
            unresolved.append({"field": label, "code": code})
        out.append({"key": key, "letter": letter, "field": label,
                    "code": code, "meaning": meaning,
                    "decodable": bool(table)})
    return jsonify(fields=out, free_text=seen.get("free_text"),
                   unresolved=unresolved, model=MODEL)


@app.post("/api/similar")
def api_similar():
    """What else in the file looks like this. The corpus answers, not the model."""
    d = request.get_json(force=True, silent=True) or {}
    params = {}
    if d.get("jasc_ata_code"):      params["jasc"] = d["jasc_ata_code"]
    if d.get("operator_designator"):params["operator"] = d["operator_designator"]
    if d.get("nature_of_condition"):params["nature"] = d["nature_of_condition"]
    if not params:
        return jsonify(error="nothing to search on"), 400
    params["limit"] = 8
    try:
        r = requests.get(SDR + "/api/search", params=params, timeout=45)
        return jsonify(query=params, status=r.status_code, result=r.json())
    except Exception as e:
        return jsonify(error=str(e)[:300]), 502


@app.get("/api/health")
def health():
    k = (os.environ.get("ZAI_API_KEY") or "").strip()
    real = bool(k) and "paste" not in k.lower()
    return jsonify(model=MODEL, key_set=real,
                   key_hint=("placeholder still in .env" if k and not real else
                             ("set" if real else "missing")),
                   tables=sorted(tables().keys()))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, ".env"))
    except ImportError:
        pass
    app.run(host="127.0.0.1", port=8210, debug=True)
