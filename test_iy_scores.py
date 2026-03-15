#!/usr/bin/env python3
"""
Test script: API'den İlk Yarı Skorlarının çekilip çekilmediğini kontrol et
"""
import datetime as dt
import json
from iddaapro import fetch_matches_api

# Bugün ve dün için test et
today = dt.date.today()
yesterday = today - dt.timedelta(days=1)

print("=" * 70)
print(f"TEST: İlk Yarı Skorları (IY MS) Kontrol")
print("=" * 70)

for target_date in [yesterday]:
    print(f"\n📅 Tarih: {target_date.strftime('%d.%m.%Y')}")
    print("-" * 70)
    
    matches = fetch_matches_api(target_date)
    print(f"   Toplam maç: {len(matches)}")
    
    if not matches:
        print("   ⚠️  Hiç maç bulunamadı!")
        continue
    
    # İlk 5 maçı göster
    for i, m in enumerate(matches[:5], 1):
        home = m.get("ev_sahibi", "?")
        away = m.get("konuk_ekip", "?")
        iy = m.get("ilk_yari_skor", "")
        ms = m.get("mac_skoru", "")
        
        iy_status = "✅" if iy else "❌ BOŞ"
        ms_status = "✅" if ms else "⚠️  BOŞ"
        
        print(f"   {i}. {home:15} vs {away:15}")
        print(f"      IY:  {iy_status} '{iy}'")
        print(f"      MS:  {ms_status} '{ms}'")

print("\n" + "=" * 70)
print("Test tamamlandı!")
print("=" * 70)
