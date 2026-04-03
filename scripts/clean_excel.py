"""
clean_excel.py - Excel temizleme scripti

1. NaN satırları (194 adet boş satır) siler
2. Duplikat satırları akıllıca temizler:
   - Aynı (Ev Sahibi, Deplasman, Tarih, Saat) grubunda:
     a) MS Skor dolu olanı tercih et (boş veya "-" olanı at)
     b) IY Skor dolu olanı tercih et
     c) İkisi de doluysa: daha fazla dolu sütunu olan satırı tut
     d) Fallback: keep="first"
3. Temizlenen Excel'i output/iddaagecmismaclar_clean.xlsx olarak kaydeder
"""

import pandas as pd
import numpy as np
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'output', 'iddaagecmismaclar.xlsx')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'output', 'iddaagecmismaclar_clean.xlsx')

DUP_KEYS = ['Ev Sahibi', 'Deplasman', 'Tarih', 'Saat']


def is_score_valid(val):
    """Skor değerinin dolu ve geçerli olup olmadığını kontrol eder."""
    if pd.isna(val):
        return False
    s = str(val).strip()
    if s in ('', '-', 'nan', 'None'):
        return False
    return True


def count_filled(row):
    """Satırdaki dolu (non-NaN, non-empty) sütun sayısını döner."""
    count = 0
    for v in row:
        if pd.notna(v) and str(v).strip() not in ('', '-', 'nan', 'None'):
            count += 1
    return count


def pick_best_row(group_df):
    """
    Bir duplikat grubundan en iyi satırı seçer.
    Öncelik: MS Skor dolu > IY Skor dolu > en fazla dolu sütun > ilk satır
    """
    if len(group_df) == 1:
        return group_df.index[0]

    # MS Skor kontrolü
    ms_col = 'MS Skor'
    if ms_col in group_df.columns:
        ms_valid = group_df[ms_col].apply(is_score_valid)
        if ms_valid.sum() == 1:
            return group_df[ms_valid].index[0]
        elif ms_valid.sum() > 1:
            group_df = group_df[ms_valid]

    # IY Skor kontrolü
    iy_col = 'IY Skor'
    if iy_col in group_df.columns:
        iy_valid = group_df[iy_col].apply(is_score_valid)
        if iy_valid.sum() == 1:
            return group_df[iy_valid].index[0]
        elif iy_valid.sum() > 1:
            group_df = group_df[iy_valid]

    # En fazla dolu sütun
    filled_counts = group_df.apply(count_filled, axis=1)
    return filled_counts.idxmax()


def main():
    print("=" * 60)
    print("Excel Temizleme Scripti")
    print("=" * 60)

    # 1. Excel oku
    print(f"\n[1] Excel okunuyor: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE, header=1)
    original_count = len(df)
    print(f"    Toplam satır: {original_count:,}")
    print(f"    Toplam sütun: {len(df.columns)}")

    # 2. NaN satırları sil (Ev Sahibi = NaN)
    print(f"\n[2] Boş satırlar temizleniyor...")
    nan_mask = df['Ev Sahibi'].isna()
    nan_count = nan_mask.sum()
    df = df[~nan_mask].reset_index(drop=True)
    print(f"    Silinen boş satır: {nan_count}")
    print(f"    Kalan satır: {len(df):,}")

    # 3. Duplikat temizleme
    print(f"\n[3] Duplikatlar temizleniyor...")

    # Duplikat gruplarını bul
    dup_mask = df.duplicated(subset=DUP_KEYS, keep=False)
    dup_df = df[dup_mask]
    dup_groups = dup_df.groupby(DUP_KEYS, dropna=False)

    print(f"    Duplikat grup sayısı: {len(dup_groups)}")
    print(f"    Duplikat toplam satır: {len(dup_df)}")

    keep_indices = set()
    removed_details = []

    for keys, group in dup_groups:
        best_idx = pick_best_row(group)
        removed = group.index[group.index != best_idx].tolist()
        keep_indices.add(best_idx)

        # Rapor için
        ev, dep, tarih, saat = keys
        for rem_idx in removed:
            removed_details.append({
                'index': rem_idx,
                'Ev Sahibi': ev,
                'Deplasman': dep,
                'Tarih': tarih,
                'Saat': saat,
                'MS Skor': df.loc[rem_idx, 'MS Skor'] if 'MS Skor' in df.columns else 'N/A',
            })

    # Duplikat olmayan satırlar + seçilen best satırlar
    non_dup_indices = set(df[~dup_mask].index.tolist())
    final_indices = sorted(non_dup_indices | keep_indices)
    df_clean = df.loc[final_indices].reset_index(drop=True)

    dup_removed_count = len(dup_df) - len(keep_indices)
    print(f"    Silinen duplikat satır: {dup_removed_count}")

    if removed_details:
        print(f"\n    Silinen duplikat satırların detayı:")
        for d in removed_details:
            print(f"      - [{d['index']}] {d['Ev Sahibi']} vs {d['Deplasman']} | {d['Tarih']} {d['Saat']} | MS Skor: {d['MS Skor']}")

    # 4. Kaydet
    print(f"\n[4] Temiz Excel kaydediliyor: {OUTPUT_FILE}")
    df_clean.to_excel(OUTPUT_FILE, index=False)
    print(f"    Dosya kaydedildi.")

    # 5. Rapor
    total_removed = original_count - len(df_clean)
    print(f"\n{'=' * 60}")
    print(f"RAPOR:")
    print(f"  Orijinal satır sayısı : {original_count:,}")
    print(f"  Silinen boş satır     : {nan_count}")
    print(f"  Silinen duplikat      : {dup_removed_count}")
    print(f"  Toplam silinen        : {total_removed}")
    print(f"  Kalan satır sayısı    : {len(df_clean):,}")
    print(f"  Çıktı dosyası         : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    main()
