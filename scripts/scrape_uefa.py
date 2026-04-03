"""
scrape_uefa.py - Mackolik'ten UEFA maclarini cekip Excel'e ekler

Kullanim:
    python scripts/scrape_uefa.py
    python scripts/scrape_uefa.py --start 2022-01-01 --end 2022-12-31
    python scripts/scrape_uefa.py --workers 4
    python scripts/scrape_uefa.py --dry-run    # Sadece kac mac bulunacagini goster

Neler yapar:
1. iddaagecmismaclar_clean.xlsx'deki mevcut maclari okur
2. Belirtilen tarih araliginda Mackolik API'sinden UEFA maclarini ceker
   (Sampiyonlar Ligi, Avrupa Ligi, Konferans Ligi, Uluslar Ligi)
3. Zaten olan maclari atlar (ev_sahibi + deplasman + tarih key'i)
4. Yeni maclarin oranlarini ceker
5. Excel'e ekler
"""
from __future__ import annotations
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import datetime as dt
import time
import unicodedata
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from openpyxl import load_workbook

# iddaapro modulunu import et
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iddaapro import scrape_match_fast, _fold_lig

# ── Sabitler ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "output" / "iddaagecmismaclar_clean.xlsx"
BASE_URL   = "https://www.mackolik.com"
API_URL    = "https://www.mackolik.com/perform/p0/ajax/components/competition/livescores/json?"

# HTTP session
_SESSION = requests.Session()
_SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
})

# UEFA turnuva isimleri (normalized fold ile eslesmesi)
UEFA_COMP_KEYWORDS = [
    "sampiyonlar ligi",
    "champions league",
    "avrupa ligi",
    "europa league",
    "konferans ligi",
    "conference league",
    "uluslar ligi",
    "nations league",
]

# Dislanacaklar (CAF, AFC, CONCACAF, Kadin vb.)
UEFA_EXCLUDE_KEYWORDS = [
    "caf", "afc", "concacaf", "kadin", "women", "arjantin",
    "afrika", "u21", "u23", "u19", "u18", "u17",
    "kupasi", "cup",  # Uluslar Kupasi, Nations Cup degil Nations League istiyoruz
]

# Uluslar Ligi icin ozel: "Uluslar Ligi" gecmeli, "Uluslar Kupasi" gecmemeli
def _fold(s: str) -> str:
    """Turkce karakterleri normalize et, kucult."""
    if not s:
        return ""
    s = s.replace("I", "i").replace("i", "i")
    s = s.lower()
    s = (s.replace("s", "s").replace("g", "g").replace("u", "u")
          .replace("o", "o").replace("c", "c").replace("i", "i"))
    # Simdiyse Turkce ozel karakterler
    for old, new in [("\u015f","s"),("\u011f","g"),("\u00fc","u"),("\u00f6","o"),
                     ("\u00e7","c"),("\u0131","i"),("\u015e","s"),("\u011e","g"),
                     ("\u00dc","u"),("\u00d6","o"),("\u00c7","c"),("\u0130","i")]:
        s = s.replace(old, new)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split())


def is_uefa_competition(comp_name: str, area_name: str) -> bool:
    """Bu turnuva gercek bir UEFA turnuvasi mi?"""
    cn = _fold(comp_name)
    an = _fold(area_name)

    # Alan "Avrupa" veya "Europe" olmali (UEFA maclari)
    if an not in ("avrupa", "europe", "uefa"):
        return False

    # Dislanacak keyword var mi?
    if any(ex in cn for ex in UEFA_EXCLUDE_KEYWORDS):
        return False

    # UEFA keyword'lerinden biri gecmeli
    return any(kw in cn for kw in UEFA_COMP_KEYWORDS)


def fetch_uefa_matches_api(target_date: dt.date, max_retries: int = 4) -> list[dict]:
    """
    Mackolik JSON API'den bir gunun UEFA maclarini cek.
    fetch_matches_api()'nin aksine LEAGUE_LIST filtresi uygulamaz,
    sadece UEFA turnuvalarini filtreler.
    """
    params = {"sports[]": "Soccer", "matchDate": target_date.strftime("%Y-%m-%d")}
    data = {}

    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(API_URL, params=params, timeout=15)
            resp.raise_for_status()
            json_resp = resp.json()
            data = json_resp.get("data", {})
            if not data or (not data.get("matches") and json_resp.get("matches")):
                data = json_resp
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                time.sleep(wait)
            else:
                print(f"  [API] {target_date} tum denemeler basarisiz: {e}")
                return []

    matches_raw  = data.get("matches", {})
    competitions = data.get("competitions", {})

    if isinstance(matches_raw, list):
        matches_raw = {str(i): m for i, m in enumerate(matches_raw) if isinstance(m, dict)}
    if isinstance(competitions, list):
        competitions = {str(c.get("id", i)): c for i, c in enumerate(competitions) if isinstance(c, dict)}

    results = []

    def _slug(name):
        s = name.lower()
        for old, new in [("\u0131","i"),("\u015f","s"),("\u011f","g"),("\u00e7","c"),("\u00fc","u"),
                         ("\u00f6","o"),("\u00e2","a"),("\u00ee","i"),("\u00e9","e"),("\u00e8","e"),
                         ("\u00e3","a"),("\u00ed","i"),("\u00f3","o"),("\u00fa","u"),("\u00e1","a"),
                         ("\u00f1","n"),("\u00e4","a"),("\u00eb","e"),("\u00ef","i"),
                         (" ","-"),(".","-"),("'",""),("\"","")]:
            s = s.replace(old, new)
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = re.sub(r'-{2,}', '-', s).strip('-')
        return s

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

        # Sadece UEFA turnuvalarini al
        if not is_uefa_competition(comp_name, area_name):
            continue

        # Skor
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

        # UTC → Istanbul saati
        mst_utc   = m.get("mstUtc")
        mac_saati = ""
        mac_tarihi = target_date.strftime("%d.%m.%Y")
        if mst_utc:
            try:
                utc_dt = dt.datetime.fromtimestamp(mst_utc / 1000, tz=dt.timezone.utc)
                ist_dt = utc_dt + dt.timedelta(hours=3)
                mac_saati  = ist_dt.strftime("%H:%M")
                mac_tarihi = ist_dt.strftime("%d.%m.%Y")
            except Exception:
                pass

        # iddaa linki
        api_slug = m.get("slug") or m.get("url") or ""
        if api_slug and "/mac/" in api_slug:
            iddaa_link = urljoin(BASE_URL, api_slug.rstrip("/") + "/iddaa")
            if "/iddaa/iddaa" in iddaa_link:
                iddaa_link = iddaa_link.replace("/iddaa/iddaa", "/iddaa")
        else:
            iddaa_link = f"{BASE_URL}/mac/{_slug(home)}-vs-{_slug(away)}/iddaa/{mid}"

        results.append({
            "ev_sahibi":     home,
            "konuk_ekip":    away,
            "mac_saati":     mac_saati,
            "mac_tarihi":    mac_tarihi,
            "ilk_yari_skor": iy_skor,
            "mac_skoru":     mac_skoru,
            "iddaa_link":    iddaa_link,
            "lig":           comp_name,
            "lig_key":       _fold(area_name) + " " + _fold(comp_name),
            "ms_kodu":       iddaa_code,
        })

    return results


# ── Excel sütun → scraper key eslesimi ──────────────────────────────────────
KEY_TO_EXCEL_COL = {
    "ev_sahibi":      "Ev Sahibi",
    "konuk_ekip":     "Deplasman",
    "mac_tarihi":     "Tarih",
    "mac_saati":      "Saat",
    "lig":            "Lig",
    "ms_kodu":        "MS Kodu",
    "ilk_yari_skor":  "IY Skor",
    "mac_skoru":      "MS Skor",
    "ms1":            "MS1",
    "ms0":            "MS0",
    "ms2":            "MS2",
    "cs_1x":          "CS 1X",
    "cs_12":          "CS 12",
    "cs_x2":          "CS X2",
    "iy1":            "IY1",
    "iy0":            "IY0",
    "iy2":            "IY2",
    "au_0_5_alt":     "AU 0.5 Alt",
    "au_0_5_ust":     "AU 0.5 Ust",
    "au_1_5_alt":     "AU 1.5 Alt",
    "au_1_5_ust":     "AU 1.5 Ust",
    "au_2_5_alt":     "AU 2.5 Alt",
    "au_2_5_ust":     "AU 2.5 Ust",
    "au_3_5_alt":     "AU 3.5 Alt",
    "au_3_5_ust":     "AU 3.5 Ust",
    "au_4_5_alt":     "AU 4.5 Alt",
    "au_4_5_ust":     "AU 4.5 Ust",
    "kg_var":         "KG Var",
    "kg_yok":         "KG Yok",
    "hnd_1":          "HND1",
    "hnd_x":          "HNDX",
    "hnd_2":          "HND2",
    "hnd2_1":         "HND2-1",
    "hnd2_x":         "HND2-X",
    "hnd2_2":         "HND2-2",
    "iy_au_05_alt":   "IY AU 0.5 Alt",
    "iy_au_05_ust":   "IY AU 0.5 Ust",
    "iy_au_15_alt":   "IY AU 1.5 Alt",
    "iy_au_15_ust":   "IY AU 1.5 Ust",
    "iy_ms_1_1":      "IY/MS 1/1",
    "iy_ms_1_x":      "IY/MS 1/X",
    "iy_ms_1_2":      "IY/MS 1/2",
    "iy_ms_x_1":      "IY/MS X/1",
    "iy_ms_x_x":      "IY/MS X/X",
    "iy_ms_x_2":      "IY/MS X/2",
    "iy_ms_2_1":      "IY/MS 2/1",
    "iy_ms_2_x":      "IY/MS 2/X",
    "iy_ms_2_2":      "IY/MS 2/2",
    "tg_0_1":         "TG 0-1",
    "tg_2_3":         "TG 2-3",
    "tg_4_5":         "TG 4-5",
    "tg_6p":          "TG 6+",
    "t1_1_5_ust":     "T1 1.5 Ust",
    "t1_2_5_ust":     "T1 2.5 Ust",
    "t2_1_5_ust":     "T2 1.5 Ust",
    "t2_2_5_ust":     "T2 2.5 Ust",
}


def make_dedup_key(ev: str, dep: str, tarih: str) -> str:
    return f"{str(ev).strip().lower()}|{str(dep).strip().lower()}|{str(tarih).strip()}"


def load_existing_keys(excel_path: Path) -> set[str]:
    print(f"[1] Mevcut Excel okunuyor: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"    Toplam satir: {len(df):,}")
    keys = set()
    for _, row in df.iterrows():
        k = make_dedup_key(
            row.get("Ev Sahibi", ""),
            row.get("Deplasman", ""),
            row.get("Tarih", ""),
        )
        keys.add(k)
    print(f"    Dedup key sayisi: {len(keys):,}")
    return keys


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def append_rows_to_excel(excel_path: Path, new_rows: list[dict]) -> None:
    """Yeni satirlari mevcut Excel dosyasina ekle."""
    wb = load_workbook(excel_path)
    ws = wb.active
    header_row = [cell.value for cell in ws[1]]

    # Excel col name → scraper key ters map
    col_to_key = {v: k for k, v in KEY_TO_EXCEL_COL.items()}

    for row_dict in new_rows:
        excel_row = []
        for col_name in header_row:
            scraper_key = col_to_key.get(col_name)
            val = row_dict.get(scraper_key, "") if scraper_key else ""
            excel_row.append(val if val != "" else None)
        ws.append(excel_row)

    wb.save(excel_path)


def main():
    parser = argparse.ArgumentParser(description="UEFA maclarini cekip Excel'e ekle")
    parser.add_argument("--start",   default="2020-01-01", help="Baslangic tarihi YYYY-MM-DD")
    parser.add_argument("--end",     default="2025-12-31", help="Bitis tarihi YYYY-MM-DD")
    parser.add_argument("--workers", type=int, default=6,  help="Paralel thread sayisi (oran cekme)")
    parser.add_argument("--dry-run", action="store_true",  help="Sadece kac mac bulundugunu goster, kaydetme")
    parser.add_argument("--no-odds", action="store_true",  help="Oran cekme, sadece skor/temel veri")
    args = parser.parse_args()

    start_date = dt.date.fromisoformat(args.start)
    end_date   = dt.date.fromisoformat(args.end)
    total_days = (end_date - start_date).days + 1

    print("=" * 60)
    print("UEFA Mac Scraper")
    print(f"Tarih araligi : {start_date} - {end_date} ({total_days} gun)")
    print(f"Cikti         : {EXCEL_PATH}")
    print("=" * 60)

    # 1. Mevcut Excel key'leri yukle
    existing_keys = load_existing_keys(EXCEL_PATH)

    # 2. Tum gunleri tara
    print(f"\n[2] Tarih araligi taranıyor ({total_days} gun)...")
    all_summaries: list[tuple[dt.date, dict]] = []
    found_total = 0
    skipped_existing = 0

    for i, day in enumerate(date_range(start_date, end_date), 1):
        summaries = fetch_uefa_matches_api(day)
        for s in summaries:
            dedup_key = make_dedup_key(
                s.get("ev_sahibi", ""),
                s.get("konuk_ekip", ""),
                s.get("mac_tarihi", day.strftime("%d.%m.%Y")),
            )
            if dedup_key in existing_keys:
                skipped_existing += 1
                continue
            all_summaries.append((day, s))
            found_total += 1

        if i % 30 == 0 or i == total_days:
            print(f"  {i}/{total_days} gun -- {found_total} yeni UEFA maci, {skipped_existing} zaten var")

        time.sleep(0.15)

    print(f"\n  Toplam yeni UEFA maci : {found_total}")
    print(f"  Zaten Excel'de olan   : {skipped_existing}")

    if found_total == 0:
        print("\nEklenecek yeni mac yok. Cikiliyor.")
        return

    if args.dry_run:
        print("\n[DRY-RUN] Kaydetme yapilmadi.")
        print("Bulunan maclar (ilk 20):")
        for day, s in all_summaries[:20]:
            print(f"  {day} | {s.get('ev_sahibi')} vs {s.get('konuk_ekip')} | {s.get('lig','')}")
        if len(all_summaries) > 20:
            print(f"  ... ve {len(all_summaries) - 20} mac daha")
        return

    # 3. Oranlari cek
    if args.no_odds:
        print(f"\n[3] --no-odds aktif, oran cekilmiyor")
        scraped_rows = [dict(s) for _, s in all_summaries]
    else:
        print(f"\n[3] {found_total} macin oranlari cekiliyor ({args.workers} paralel)...")
        scraped_rows = []
        done = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_map = {
                executor.submit(scrape_match_fast, s, day): (day, s)
                for day, s in all_summaries
            }
            for future in as_completed(future_map):
                day, s = future_map[future]
                try:
                    row = future.result()
                    if row:
                        # lig adini API verisinden koru (scraper bos birakabilir)
                        if not row.get("lig"):
                            row["lig"] = s.get("lig", "")
                        scraped_rows.append(row)
                        done += 1
                    else:
                        # Oran cekilemese de temel veriyi kaydet
                        scraped_rows.append(dict(s))
                        failed += 1
                except Exception as e:
                    scraped_rows.append(dict(s))
                    failed += 1

                total_done = done + failed
                if total_done % 50 == 0 or total_done == found_total:
                    print(f"  {total_done}/{found_total} -- {done} basarili, {failed} basarisiz")

        print(f"\n  Oran cekme tamamlandi: {done} basarili, {failed} basarisiz")

    # 4. Excel'e ekle
    print(f"\n[4] {len(scraped_rows)} satir Excel'e ekleniyor...")
    append_rows_to_excel(EXCEL_PATH, scraped_rows)
    print(f"    Kaydedildi: {EXCEL_PATH}")

    print(f"\n{'=' * 60}")
    print(f"OZET:")
    print(f"  Taranan gun          : {total_days}")
    print(f"  Bulunan UEFA maci    : {found_total}")
    print(f"  Zaten Excel'de olan  : {skipped_existing}")
    print(f"  Eklenen satir        : {len(scraped_rows)}")
    print(f"  Cikti                : {EXCEL_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
