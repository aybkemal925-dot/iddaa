"""
ucl_pipeline.py - UCL/UEFA/UNL eksik maç tespiti

1. output/iddaagecmismaclar_clean.xlsx oku (yoksa ham dosyayı kullan)
2. UCL/UEL/UNL/Konferans maçlarını filtrele
3. FootballData.co.uk'ten CSV'leri indir
4. Mevcut Excel'deki maçlarla karşılaştır
5. Eksik maçları output/eksik_ucl_maclar.csv olarak kaydet
"""

import os
import sys
import requests
import pandas as pd
import io
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
CLEAN_FILE = os.path.join(BASE_DIR, 'output', 'iddaagecmismaclar_clean.xlsx')
RAW_FILE = os.path.join(BASE_DIR, 'output', 'iddaagecmismaclar.xlsx')
OUTPUT_CSV = os.path.join(BASE_DIR, 'output', 'eksik_ucl_maclar.csv')

# FootballData.co.uk CSV URL'leri
FDUK_URLS = {
    'UCL': 'https://www.football-data.co.uk/new/UCL.csv',
    'UEL': 'https://www.football-data.co.uk/new/UEL.csv',
    'UECL': 'https://www.football-data.co.uk/new/UECL.csv',  # UEFA Conference League
    'UNL': 'https://www.football-data.co.uk/new/UNL.csv',    # UEFA Nations League
}

# Excel'deki lig isimlerinde arama yapılacak keyword'ler (encoding bozuk unicode)
# Türkçe karakter bozulması: Ş→?, ı→? vs.
LIG_KEYWORDS = {
    'UCL': ['ampiyonlar Ligi', 'Champions League', 'UCL'],
    'UEL': ['Avrupa Ligi', 'Europa League', 'UEL'],
    'UECL': ['Konferans', 'Conference'],
    'UNL': ['Uluslar Ligi', 'Nations League', 'UNL'],
}

# Dışlama keyword'leri (CAF, AFC gibi yanlış eşleşmeleri önle)
EXCLUDE_KEYWORDS = ['CAF', 'AFC', 'CONCACAF', 'Arjantin', 'Afrika', 'Kad']


def normalize_team_name(name):
    """Takım isimlerini normalize et (küçük harf, boşluk trim)."""
    if pd.isna(name):
        return ''
    return str(name).strip().lower()


def normalize_date(val):
    """Tarih değerini normalize et (YYYY-MM-DD formatına çevir)."""
    if pd.isna(val):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    # DD/MM/YYYY formatını dene
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


def download_csv(url, tournament_name):
    """FootballData.co.uk'ten CSV indir."""
    print(f"  İndiriliyor: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(url, timeout=30, headers=headers)
        r.raise_for_status()
        # encoding dene
        try:
            content = r.content.decode('utf-8')
        except UnicodeDecodeError:
            content = r.content.decode('latin-1', errors='ignore')

        df = pd.read_csv(io.StringIO(content))
        print(f"  {tournament_name}: {len(df)} satır indirildi, sütunlar: {list(df.columns[:8])}")
        return df
    except requests.exceptions.HTTPError as e:
        print(f"  HATA: {tournament_name} indirilemedi - {e}")
        return None
    except Exception as e:
        print(f"  HATA: {tournament_name} - {e}")
        return None


def filter_lig(df, tournament):
    """Excel'deki maçları lig keyword'lerine göre filtrele."""
    include_kw = LIG_KEYWORDS.get(tournament, [])
    mask = pd.Series([False] * len(df), index=df.index)

    for kw in include_kw:
        mask = mask | df['Lig'].fillna('').str.contains(kw, case=False, na=False)

    # Hariç tutulacakları çıkar
    for excl in EXCLUDE_KEYWORDS:
        mask = mask & ~df['Lig'].fillna('').str.contains(excl, case=False, na=False)

    return df[mask].copy()


def build_match_key(home, away, date):
    """Maç anahtarı oluştur (karşılaştırma için)."""
    return f"{normalize_team_name(home)}|{normalize_team_name(away)}|{normalize_date(date)}"


def find_fduk_columns(fduk_df):
    """FootballData.co.uk CSV'sindeki ev sahibi, deplasman ve tarih sütunlarını bul."""
    col_map = {}

    # Ev sahibi sütunu
    for candidate in ['HomeTeam', 'Home', 'HTeam', 'home_team']:
        if candidate in fduk_df.columns:
            col_map['home'] = candidate
            break

    # Deplasman sütunu
    for candidate in ['AwayTeam', 'Away', 'ATeam', 'away_team']:
        if candidate in fduk_df.columns:
            col_map['away'] = candidate
            break

    # Tarih sütunu
    for candidate in ['Date', 'date', 'Datetime']:
        if candidate in fduk_df.columns:
            col_map['date'] = candidate
            break

    # Sezon sütunu
    for candidate in ['Season', 'season', 'Seas']:
        if candidate in fduk_df.columns:
            col_map['season'] = candidate
            break

    return col_map


def compare_matches(excel_df, fduk_df, tournament, col_map):
    """
    FootballData.co.uk maçlarını Excel'deki maçlarla karşılaştır.
    Excel'de olmayan maçları döndür.
    """
    if fduk_df is None or len(fduk_df) == 0:
        return pd.DataFrame()

    if 'home' not in col_map or 'away' not in col_map or 'date' not in col_map:
        print(f"  UYARI: {tournament} için gerekli sütunlar bulunamadı: {list(fduk_df.columns[:10])}")
        return pd.DataFrame()

    # Excel maç anahtarlarını oluştur
    excel_keys = set()
    for _, row in excel_df.iterrows():
        key = build_match_key(row['Ev Sahibi'], row['Deplasman'], row['Tarih'])
        excel_keys.add(key)

    # FD.co.uk maçlarını kontrol et
    missing_rows = []
    for _, row in fduk_df.iterrows():
        key = build_match_key(
            row.get(col_map['home'], ''),
            row.get(col_map['away'], ''),
            row.get(col_map['date'], '')
        )
        if key and key not in excel_keys:
            missing_rows.append({
                'Tournament': tournament,
                'Ev Sahibi': row.get(col_map['home'], ''),
                'Deplasman': row.get(col_map['away'], ''),
                'Tarih': row.get(col_map['date'], ''),
                'Sezon': row.get(col_map.get('season', ''), '') if 'season' in col_map else '',
                'Kaynak': 'football-data.co.uk',
                'Match_Key': key,
            })

    return pd.DataFrame(missing_rows)


def main():
    print("=" * 60)
    print("UCL/UEFA Eksik Maç Tespiti Pipeline")
    print("=" * 60)

    # 1. Excel oku
    excel_path = CLEAN_FILE if os.path.exists(CLEAN_FILE) else RAW_FILE
    print(f"\n[1] Excel okunuyor: {excel_path}")
    df = pd.read_excel(excel_path, header=1 if excel_path == RAW_FILE else 0)
    print(f"    Toplam satır: {len(df):,}")

    # Tarih sütununu string'e normalize et
    df['_tarih_norm'] = df['Tarih'].apply(normalize_date)

    # 2. Her turnuva için filtrele
    print(f"\n[2] Turnuvaya göre filtreleme...")
    tournament_dfs = {}
    for t in ['UCL', 'UEL', 'UECL', 'UNL']:
        filtered = filter_lig(df, t)
        tournament_dfs[t] = filtered
        print(f"    {t}: {len(filtered)} maç bulundu")
        if len(filtered) > 0:
            ligs = filtered['Lig'].unique()
            for l in ligs:
                print(f"      - {repr(l)}")

    # 3. FootballData.co.uk'ten CSV'leri indir
    print(f"\n[3] FootballData.co.uk'ten veriler indiriliyor...")
    fduk_data = {}
    for tournament, url in FDUK_URLS.items():
        fduk_data[tournament] = download_csv(url, tournament)

    # 4. Karşılaştır
    print(f"\n[4] Eksik maçlar tespit ediliyor...")
    all_missing = []

    for tournament in ['UCL', 'UEL', 'UECL', 'UNL']:
        excel_tournament_df = tournament_dfs.get(tournament, pd.DataFrame())
        fduk_df = fduk_data.get(tournament)

        if fduk_df is None:
            print(f"  {tournament}: FootballData verisi yok, atlanıyor")
            continue

        col_map = find_fduk_columns(fduk_df)
        missing_df = compare_matches(excel_tournament_df, fduk_df, tournament, col_map)

        print(f"  {tournament}: {len(missing_df)} eksik maç bulundu")
        if not missing_df.empty:
            all_missing.append(missing_df)

    # 5. Sonuçları kaydet
    print(f"\n[5] Eksik maçlar kaydediliyor: {OUTPUT_CSV}")
    if all_missing:
        result_df = pd.concat(all_missing, ignore_index=True)
        result_df = result_df.drop(columns=['Match_Key'], errors='ignore')
        result_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"    Toplam eksik maç: {len(result_df)}")
        print(f"    Dosya kaydedildi: {OUTPUT_CSV}")

        # Turnuva bazında özet
        print(f"\n    Turnuva bazında özet:")
        for t, count in result_df.groupby('Tournament').size().items():
            print(f"      {t}: {count} eksik maç")
    else:
        # Boş CSV kaydet
        empty_df = pd.DataFrame(columns=['Tournament', 'Ev Sahibi', 'Deplasman', 'Tarih', 'Sezon', 'Kaynak'])
        empty_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print("    Eksik maç bulunamadı. Boş CSV kaydedildi.")

    print("\n" + "=" * 60)
    print("Pipeline tamamlandı.")
    print("=" * 60)


if __name__ == '__main__':
    main()
