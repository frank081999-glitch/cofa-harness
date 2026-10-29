#!/usr/bin/env python3
"""표 데이터 첫 점검: 행·열·결측·형식 섞임·숫자 범위·키 후보·개인정보 의심 열.

    python3 profile.py data.csv [more.xlsx ...]
    python3 profile.py --selftest

csv/tsv/json/jsonl 은 표준 라이브러리로 읽는다. xlsx/parquet 은 pandas 가 있을 때만.
"""
import csv, json, re, sys, tempfile, os
from collections import Counter
from datetime import datetime

NA = {"", "na", "n/a", "null", "none", "nan", "-", "#n/a"}
PII_NAME = re.compile(r"이름|성명|name|e-?mail|메일|phone|전화|휴대|연락|주민|주소|address|계좌|account|생년|birth|\bip\b|사번", re.I)
PII_VAL = [re.compile(p) for p in (r"[\w.+-]+@[\w-]+\.[\w.]+", r"01[016789]-?\d{3,4}-?\d{4}", r"\d{6}-?[1-4]\d{6}")]
DATE_FMTS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")


def kind(v):
    s = v.replace(",", "")
    for t, f in (("int", int), ("float", float)):
        try:
            f(s)
            return t
        except ValueError:
            pass
    for fmt in DATE_FMTS:
        try:
            datetime.strptime(v, fmt)
            return "date:" + fmt
        except ValueError:
            pass
    return "bool" if v.lower() in {"true", "false", "y", "n", "yes", "no"} else "str"


def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls", ".parquet"):
        import pandas as pd  # 없으면 ImportError 그대로 — csv 로 바꿔서 다시 돌린다
        df = pd.read_parquet(path) if ext == ".parquet" else pd.read_excel(path)
        return [{k: "" if pd.isna(v) else str(v) for k, v in r.items()} for r in df.to_dict("records")]
    if ext in (".json", ".jsonl"):
        txt = open(path, encoding="utf-8-sig").read()
        data = [json.loads(l) for l in txt.splitlines() if l.strip()] if ext == ".jsonl" else json.loads(txt)
        if isinstance(data, dict):  # {"items": [...]} 꼴이면 가장 긴 목록을 표로 본다
            data = max((v for v in data.values() if isinstance(v, list)), key=len)
        return [{k: "" if v is None else (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)) for k, v in r.items()} for r in data]
    for enc in ("utf-8-sig", "cp949"):  # 국내 엑셀 출력 csv 는 cp949 가 흔하다
        try:
            txt = open(path, encoding=enc).read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"{path}: utf-8·cp949 둘 다 아님")
    try:
        dialect = csv.Sniffer().sniff(txt[:20000], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab if ext == ".tsv" else csv.excel
    print(f"  인코딩 {enc}, 구분자 {dialect.delimiter!r}")
    return list(csv.DictReader(txt.splitlines(), dialect=dialect))


def mask(v):
    return v[:1] + "*" * max(len(v) - 2, 1) + v[-1:] if len(v) > 2 else "**"


def profile(path):
    print(f"== {path}")
    rows = load(path)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    dup = len(rows) - len({tuple(r.get(c, "") for c in cols) for r in rows})
    print(f"  행 {len(rows)} · 열 {len(cols)} · 완전 중복 행 {dup}")
    out = {}
    for c in cols:
        vals = [str(r.get(c) or "").strip() for r in rows]
        present = [v for v in vals if v.lower() not in NA]
        kinds = Counter(kind(v) for v in present)
        uniq = len(set(present))
        pii = bool(PII_NAME.search(c)) or any(p.fullmatch(v) for v in present[:200] for p in PII_VAL)
        flags = []
        if len(kinds) > 1:
            flags.append("형식섞임")
        if present and uniq == len(vals):
            flags.append("키후보")
        if pii:
            flags.append("PII?")
        line = f"  - {c}: 결측 {len(vals) - len(present)}/{len(vals)} · 고유 {uniq} · 형식 {dict(kinds.most_common(3))}"
        nums = [float(v.replace(",", "")) for v in present if kind(v) in ("int", "float")]
        if nums:
            line += f" · 범위 {min(nums):g}~{max(nums):g} 평균 {sum(nums) / len(nums):g}"
        top = [(mask(v) if pii else v[:30], n) for v, n in Counter(present).most_common(3)]
        print(line + f" · 상위 {top}" + (f"  [{' '.join(flags)}]" if flags else ""))
        out[c] = flags
    return rows, out


def selftest():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.csv")
    with open(p, "w", encoding="cp949", newline="") as f:
        f.write("id,이름,금액,날짜,연락처\n1,홍길동,1000,2026-10-01,010-1234-5678\n2,김철수,x,2026/10/02,\n3,이영희,3000,NA,010-2222-3333\n3,이영희,3000,NA,010-2222-3333\n")
    rows, flags = profile(p)
    assert len(rows) == 4
    assert "PII?" in flags["이름"] and "PII?" in flags["연락처"]
    assert "형식섞임" in flags["금액"] and "형식섞임" in flags["날짜"]
    assert "키후보" not in flags["id"]  # 3 이 두 번 — 키가 아니다
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif not sys.argv[1:]:
        print(__doc__)
    else:
        for a in sys.argv[1:]:
            profile(a)
