"""
scrape_uefa.py - Mackolik'ten UEFA maclarini cekip Excel'e ekler

Kullanim:
    python scripts/scrape_uefa.py --start 2020-01-01 --end 2021-06-30
    python scripts/scrape_uefa.py --start 2020-01-01 --end 2021-06-30 --resume
    python scripts/scrape_uefa.py --dry-run

GitHub Actions icin:
- --output  : cikti excel dosyasi (varsayilan: output/iddaa_uefa_START_END.xlsx)
- --resume  : progress.json'dan kaldigi yerden devam
- --max-hours N : N saat sonra kaydet ve cik (Actions timeout icin)
"""
from __future__ import annotations
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import datetime as dt
import json
import time
import unicodedata
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iddaapro import scrape_match_fast

# ── Sabitler ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
BASE_URL  = "https://www.mackolik.com"
API_URL   = "https://www.mackolik.com/perform/p0/ajax/components/competition/livescores/json?"

_SESSION = requests.Session()
_SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
})

UEFA_COMP_KEYWORDS = [
    "sampiyonlar ligi", "champions league",
    "avrupa ligi", "europa league",
    "konferans ligi", "conference league",
    "uluslar ligi", "nations league",
]
UEFA_EXCLUDE = [
    "caf", "afc", "concacaf", "kadin", "women", "arjantin",
    "afrika", "u21", "u23", "u19", "u18", "u17",
    "kupasi", "cup",
]

EXCEL_HEADERS = [
    "Ev Sahibi", "Deplasman", "Tarih", "Saat", "Lig",
    "MS Kodu", "IY Skor", "MS Skor",
    "MS1", "MS0", "MS2",
    "CS 1X", "CS 12", "CS X2",
    "IY1", "IY0", "IY2",
    "AU 0.5 Alt", "AU 0.5 Ust",
    "AU 1.5 Alt", "AU 1.5 Ust",
    "AU 2.5 Alt", "AU 2.5 Ust",
    "AU 3.5 Alt", "AU 3.5 Ust",
    "AU 4.5 Alt", "AU 4.5 Ust",
    "KG Var", "KG Yok",
    "HND1", "HNDX", "HND2",
    "HND2-1", "HND2-X", "HND2-2",
    "IY AU 0.5 Alt", "IY AU 0.5 Ust",
    "IY AU 1.5 Alt", "IY AU 1.5 Ust",
    "IY/MS 1/1", "IY/MS 1/X", "IY/MS 1/2",
    "IY/MS X/1", "IY/MS X/X", "IY/MS X/2",
    "IY/MS 2/1", "IY/MS 2/X", "IY/MS 2/2",
    "TG 0-1", "TG 2-3", "TG 4-5", "TG 6+",
    "T1 1.5 Ust", "T1 2.5 Ust",
    "T2 1.5 Ust", "T2 2.5 Ust",
]

KEY_TO_COL = {
    "ev_sahibi": "Ev Sahibi", "konuk_ekip": "Deplasman",
    "mac_tarihi": "Tarih", "mac_saati": "Saat", "lig": "Lig",
    "ms_kodu": "MS Kodu", "ilk_yari_skor": "IY Skor", "mac_skoru": "MS Skor",
    "ms1": "MS1", "ms0": "MS0", "ms2": "MS2",
    "cs_1x": "CS 1X", "cs_12": "CS 12", "cs_x2": "CS X2",
    "iy1": "IY1", "iy0": "IY0", "iy2": "IY2",
    "au_0_5_alt": "AU 0.5 Alt", "au_0_5_ust": "AU 0.5 Ust",
    "au_1_5_alt": "AU 1.5 Alt", "au_1_5_ust": "AU 1.5 Ust",
    "au_2_5_alt": "AU 2.5 Alt", "au_2_5_ust": "AU 2.5 Ust",
    "au_3_5_alt": "AU 3.5 Alt", "au_3_5_ust": "AU 3.5 Ust",
    "au_4_5_alt": "AU 4.5 Alt", "au_4_5_ust": "AU 4.5 Ust",
    "kg_var": "KG Var", "kg_yok": "KG Yok",
    "hnd_1": "HND1", "hnd_x": "HNDX", "hnd_2": "HND2",
    "hnd2_1": "HND2-1", "hnd2_x": "HND2-X", "hnd2_2": "HND2-2",
    "iy_au_05_alt": "IY AU 0.5 Alt", "iy_au_05_ust": "IY AU 0.5 Ust",
    "iy_au_15_alt": "IY AU 1.5 Alt", "iy_au_15_ust": "IY AU 1.5 Ust",
    "iy_ms_1_1": "IY/MS 1/1", "iy_ms_1_x": "IY/MS 1/X", "iy_ms_1_2": "IY/MS 1/2",
    "iy_ms_x_1": "IY/MS X/1", "iy_ms_x_x": "IY/MS X/X", "iy_ms_x_2": "IY/MS X/2",
    "iy_ms_2_1": "IY/MS 2/1", "iy_ms_2_x": "IY/MS 2/X", "iy_ms_2_2": "IY/MS 2/2",
    "tg_0_1": "TG 0-1", "tg_2_3": "TG 2-3", "tg_4_5": "TG 4-5", "tg_6p": "TG 6+",
    "t1_1_5_ust": "T1 1.5 Ust", "t1_2_5_ust": "T1 2.5 Ust",
    "t2_1_5_ust": "T2 1.5 Ust", "t2_2_5_ust": "T2 2.5 Ust",
}
COL_TO_KEY = {v: k for k, v in KEY_TO_COL.items()}


def _fold(s: str) -> str:
    if not s:
        return ""
    s = s.replace("I", "i").replace("\u0130", "i")
    s = s.lower()
    for old, new in [("\u015f","s"),("\u011f","g"),("\u00fc","u"),("\u00f6","o"),
                     ("\u00e7","c"),("\u0131","i"),("\u015e","s"),("\u011e","g"),
                     ("\u00dc","u"),("\u00d6","o"),("\u00c7","c")]:
        s = s.replace(old, new)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split())


def is_uefa(comp_name: str, area_name: str) -> bool:
    cn = _fold(comp_name)
    an = _fold(area_name)
    if an not in ("avrupa", "europe", "uefa"):
        return False
    if any(ex in cn for ex in UEFA_EXCLUDE):
        return False
    return any(kw in cn for kw in UEFA_COMP_KEYWORDS)


def fetch_day(target_date: dt.date, max_retries: int = 4) -> list[dict]:
    params = {"sports[]": "Soccer", "matchDate": target_date.strftime("%Y-%m-%d")}
    data = {}
    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(API_URL, params=params, timeout=15)
            resp.raise_for_status()
            jr = resp.json()
            data = jr.get("data", {})
            if not data or (not data.get("matches") and jr.get("matches")):
                data = jr
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
            else:
                print(f"  [API] {target_date} basarisiz: {e}")
                return []

    matches_raw  = data.get("matches", {})
    competitions = data.get("competitions", {})
    if isinstance(matches_raw, list):
        matches_raw = {str(i): m for i, m in enumerate(matches_raw) if isinstance(m, dict)}
    if isinstance(competitions, list):
        competitions = {str(c.get("id", i)): c for i, c in enumerate(competitions) if isinstance(c, dict)}

    def _slug(name):
        s = name.lower()
        for old, new in [("\u0131","i"),("\u015f","s"),("\u011f","g"),("\u00e7","c"),
                         ("\u00fc","u"),("\u00f6","o"),(" ","-"),(".","-"),("'",""),("\"","")]:
            s = s.replace(old, new)
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return re.sub(r'-{2,}', '-', s).strip('-')

    results = []
    for mid, m in matches_raw.items():
        iddaa_code = str(m.get("iddaaCode", "") or "")
        if not iddaa_code or iddaa_code == "None":
            continue
        home = m.get("homeTeam", {}).get("name", "")
        away = m.get("awayTeam", {}).get("name", "")
        if not home or not away:
            continue
        comp_id = m.get("competitionId")
        comp    = competitions.get(str(comp_id)) or competitions.get(comp_id) or {}
        area_obj  = comp.get("country") or comp.get("area") or {}
        area_name = area_obj.get("name", "")
        comp_name = comp.get("name", "")
        if not is_uefa(comp_name, area_name):
            continue

        score_h = m.get("score", {}).get("home", "")
        score_a = m.get("score", {}).get("away", "")
        mac_skoru = f"{score_h}-{score_a}" if score_h != "" and score_a != "" else ""
        try:
            ht = m.get("score", {}).get("ht", {})
            home_ht = str(ht.get('home', '')).strip() if isinstance(ht, dict) else ''
            away_ht = str(ht.get('away', '')).strip() if isinstance(ht, dict) else ''
            iy_skor = f"{home_ht}-{away_ht}" if (home_ht or away_ht) else ""
        except Exception:
            iy_skor = ""

        mst_utc    = m.get("mstUtc")
        mac_saati  = ""
        mac_tarihi = target_date.strftime("%d.%m.%Y")
        if mst_utc:
            try:
                utc_dt = dt.datetime.fromtimestamp(mst_utc / 1000, tz=dt.timezone.utc)
                ist_dt = utc_dt + dt.timedelta(hours=3)
                mac_saati  = ist_dt.strftime("%H:%M")
                mac_tarihi = ist_dt.strftime("%d.%m.%Y")
            except Exception:
                pass

        api_slug = m.get("slug") or m.get("url") or ""
        if api_slug and "/mac/" in api_slug:
            iddaa_link = urljoin(BASE_URL, api_slug.rstrip("/") + "/iddaa")
            if "/iddaa/iddaa" in iddaa_link:
                iddaa_link = iddaa_link.replace("/iddaa/iddaa", "/iddaa")
        else:
            iddaa_link = f"{BASE_URL}/mac/{_slug(home)}-vs-{_slug(away)}/iddaa/{mid}"

        results.append({
            "ev_sahibi": home, "konuk_ekip": away,
            "mac_saati": mac_saati, "mac_tarihi": mac_tarihi,
            "ilk_yari_skor": iy_skor, "mac_skoru": mac_skoru,
            "iddaa_link": iddaa_link, "lig": comp_name,
            "lig_key": _fold(area_name) + " " + _fold(comp_name),
            "ms_kodu": iddaa_code,
        })
    return results


def make_key(ev: str, dep: str, tarih: str) -> str:
    return f"{str(ev).strip().lower()}|{str(dep).strip().lower()}|{str(tarih).strip()}"


def save_excel(rows: list[dict], path: Path) -> None:
    """Yeni Excel olustur veya mevcuta ekle."""
    if path.exists():
        wb = load_workbook(path)
        ws = wb.active
        header = [c.value for c in ws[1]]
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "UEFA Oranlari"
        header = EXCEL_HEADERS
        ws.append(header)
        hfill = PatternFill("solid", fgColor="1A5276")
        hfont = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = hfill
            cell.font = hfont
            cell.alignment = Alignment(horizontal="center")

    for row_dict in rows:
        excel_row = []
        for col_name in header:
            key = COL_TO_KEY.get(col_name)
            val = row_dict.get(key, "") if key else ""
            excel_row.append(val if val != "" else None)
        ws.append(excel_row)

    for col in ws.columns:
        w = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(w + 2, 35)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def load_progress(progress_file: Path) -> dict:
    if progress_file.exists():
        try:
            return json.loads(progress_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_progress(progress_file: Path, data: dict) -> None:
    progress_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="UEFA maclarini cek")
    parser.add_argument("--start",     default="2017-08-01")
    parser.add_argument("--end",       default="2026-03-31")
    parser.add_argument("--output",    default=None,  help="Cikti xlsx (varsayilan: output/iddaa_uefa_START_END.xlsx)")
    parser.add_argument("--progress",  default="progress_uefa.json")
    parser.add_argument("--workers",   type=int, default=4)
    parser.add_argument("--max-hours", type=float, default=5.5, help="Maksimum calisma suresi (saat)")
    parser.add_argument("--resume",    action="store_true")
    parser.add_argument("--dry-run",   action="store_true")
    args = parser.parse_args()

    start_date = dt.date.fromisoformat(args.start)
    end_date   = dt.date.fromisoformat(args.end)
    total_days = (end_date - start_date).days + 1

    # Cikti dosyasi
    if args.output:
        output_path = Path(args.output)
    else:
        slug = f"{args.start.replace('-','')}_{args.end.replace('-','')}"
        output_path = BASE_DIR / "output" / f"iddaa_uefa_{slug}.xlsx"

    progress_file = BASE_DIR / args.progress
    deadline = dt.datetime.now() + dt.timedelta(hours=args.max_hours)

    print("=" * 60)
    print("UEFA Mac Scraper")
    print(f"Aralik  : {start_date} - {end_date} ({total_days} gun)")
    print(f"Cikti   : {output_path}")
    print(f"Max sure: {args.max_hours} saat")
    print("=" * 60)

    # Progress yukle
    progress = load_progress(progress_file) if args.resume else {}
    last_done_date = progress.get("last_done_date")
    existing_keys  = set(progress.get("existing_keys", []))

    # Mevcut Excel'deki key'leri yukle (resume degilse veya bos ise)
    if not existing_keys and output_path.exists():
        print(f"[1] Mevcut Excel okunuyor: {output_path}")
        df = pd.read_excel(output_path)
        print(f"    {len(df):,} satir")
        for _, row in df.iterrows():
            existing_keys.add(make_key(
                row.get("Ev Sahibi", ""),
                row.get("Deplasman", ""),
                row.get("Tarih", ""),
            ))
        print(f"    {len(existing_keys):,} dedup key yuklendi")

    # Kaldigi yerden devam
    effective_start = start_date
    if last_done_date and args.resume:
        effective_start = dt.date.fromisoformat(last_done_date) + dt.timedelta(days=1)
        print(f"[RESUME] {last_done_date} tarihinden devam ediliyor")

    # Gunleri tara
    print(f"\n[2] Gunler taranıyor...")
    all_summaries: list[tuple[dt.date, dict]] = []
    found = 0
    skipped = 0
    batch_rows: list[dict] = []
    BATCH_SIZE = 200  # Her 200 maci kaydet

    start_time = dt.datetime.now()

    for i, day in enumerate(date_range(effective_start, end_date), 1):
        # Zaman kontrolu
        if dt.datetime.now() >= deadline:
            print(f"\n[!] Zaman doldu ({args.max_hours} saat). Kaydedilip cikiliyor...")
            break

        matches = fetch_day(day)
        new_for_day = []
        for s in matches:
            k = make_key(s.get("ev_sahibi",""), s.get("konuk_ekip",""), s.get("mac_tarihi", day.strftime("%d.%m.%Y")))
            if k in existing_keys:
                skipped += 1
                continue
            new_for_day.append((day, s))
            existing_keys.add(k)
            found += 1

        all_summaries.extend(new_for_day)

        if i % 30 == 0:
            elapsed = (dt.datetime.now() - start_time).seconds // 60
            print(f"  {i} gun -- {found} yeni mac, {skipped} var, {elapsed}dk gecti")

        time.sleep(0.15)

        # Batch olarak oran cek ve kaydet
        if len(all_summaries) >= BATCH_SIZE or (i == total_days and all_summaries):
            if not args.dry_run:
                _process_batch(all_summaries, output_path, args.workers)
            all_summaries = []
            # Progress kaydet
            progress["last_done_date"] = day.isoformat()
            progress["existing_keys"] = list(existing_keys)
            save_progress(progress_file, progress)

    # Kalan batch
    if all_summaries and not args.dry_run:
        _process_batch(all_summaries, output_path, args.workers)

    # Son progress kaydet
    progress["last_done_date"] = end_date.isoformat()
    progress["existing_keys"] = list(existing_keys)
    save_progress(progress_file, progress)

    print(f"\n{'='*60}")
    print(f"OZET:")
    print(f"  Bulunan UEFA maci : {found}")
    print(f"  Zaten var         : {skipped}")
    print(f"  Cikti             : {output_path}")
    print("=" * 60)


def _process_batch(summaries: list[tuple[dt.date, dict]], output_path: Path, workers: int) -> None:
    """Bir batch macin oranlarini cek ve Excel'e ekle."""
    print(f"  --> {len(summaries)} mac orani cekiliyor...")
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(scrape_match_fast, s, day): (day, s)
            for day, s in summaries
        }
        for future in as_completed(future_map):
            day, s = future_map[future]
            try:
                row = future.result()
                if row:
                    if not row.get("lig"):
                        row["lig"] = s.get("lig", "")
                    rows.append(row)
                else:
                    rows.append(dict(s))
            except Exception:
                rows.append(dict(s))

    save_excel(rows, output_path)
    print(f"  --> {len(rows)} satir kaydedildi: {output_path}")


if __name__ == "__main__":
    main()
