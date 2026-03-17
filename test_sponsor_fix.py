#!/usr/bin/env python3
"""Sponsor kelime temizligi ve lig esleme testi.

Mackolik'ten yillar icerisinde gelen farkli lig isimlerinin
ayni lig olarak eslesip eslesmedigini dogrular.
"""
import sys
sys.path.insert(0, '.')

from scraper_cli import _fold_lig, lig_key, lig_filtreli_key, _league_tier, _SPONSOR_WORDS

PASSED = 0
FAILED = 0

def check(desc, got, expected):
    global PASSED, FAILED
    if got == expected:
        PASSED += 1
        print(f"  OK: {desc}")
    else:
        FAILED += 1
        print(f"  FAIL: {desc}")
        print(f"        got={got!r}  expected={expected!r}")

# ── 1. _fold_lig sponsor temizleme testleri ──
print("=== _fold_lig sponsor temizleme ===")

# Turkiye - yillar icerisinde degisen isimler
check("Trendyol Super Lig -> super lig",
      _fold_lig("Trendyol Süper Lig"), "super lig")
check("Spor Toto Super Lig -> super lig",
      _fold_lig("Spor Toto Süper Lig"), "super lig")
check("Misli Super Lig -> super lig",
      _fold_lig("Misli Süper Lig"), "super lig")
check("Turkcell Super Lig -> super lig",
      _fold_lig("Turkcell Süper Lig"), "super lig")
check("Süper Lig (sponsor yok) -> super lig",
      _fold_lig("Süper Lig"), "super lig")

# Turkiye 1. Lig
check("Trendyol 1. Lig -> 1 lig",
      _fold_lig("Trendyol 1. Lig"), "1 lig")
check("Spor Toto 1. Lig -> 1 lig",
      _fold_lig("Spor Toto 1. Lig"), "1 lig")
check("TFF 1. Lig -> 1 lig",
      _fold_lig("TFF 1. Lig"), "1 lig")
check("PTT 1. Lig -> 1 lig",
      _fold_lig("PTT 1. Lig"), "1 lig")
check("Bank Asya 1. Lig -> 1 lig",
      _fold_lig("Bank Asya 1. Lig"), "1 lig")

# Italya - Serie A TIM
check("Serie A TIM -> serie a",
      _fold_lig("Serie A TIM"), "serie a")
check("Serie A -> serie a",
      _fold_lig("Serie A"), "serie a")
check("Serie B -> serie b",
      _fold_lig("Serie B"), "serie b")

# Fransa - Ligue 1 Uber Eats
check("Ligue 1 Uber Eats -> lig 1",
      _fold_lig("Ligue 1 Uber Eats"), "lig 1")
check("Ligue 1 -> lig 1",
      _fold_lig("Ligue 1"), "lig 1")

# Almanya - sponsor ismi yok ama kontrol
check("Bundesliga -> bundesliga",
      _fold_lig("Bundesliga"), "bundesliga")
check("2. Bundesliga -> 2 bundesliga",
      _fold_lig("2. Bundesliga"), "2 bundesliga")

# Ingiltere - Premier League
check("Premier League -> premier lig",
      _fold_lig("Premier League"), "premier lig")
check("Premier Lig -> premier lig",
      _fold_lig("Premier Lig"), "premier lig")

# Ulke + lig birlesimleri
check("Turkiye country fold", _fold_lig("Turkey"), "turkiye")
check("England country fold", _fold_lig("England"), "ingiltere")

# Bos string korunmasi
check("Bos string -> bos", _fold_lig(""), "")

# ── 2. lig_key testleri ──
print("\n=== lig_key testleri ===")

# LEAGUE_LIST'ten uretilen key'ler
turkey_super = lig_key("TÜRKİYE", "Süper Lig")
check("TURKIYE Super Lig key", turkey_super, "turkiye super lig")

turkey_first = lig_key("TÜRKİYE", "1. Lig")
check("TURKIYE 1. Lig key", turkey_first, "turkiye 1 lig")

italy_a = lig_key("İTALYA", "Serie A")
check("ITALYA Serie A key", italy_a, "italya serie a")

france_1 = lig_key("FRANSA", "Ligue 1")
check("FRANSA Ligue 1 key", france_1, "fransa lig 1")

eng_prem = lig_key("İNGİLTERE", "Premier Lig")
check("INGILTERE Premier Lig key", eng_prem, "ingiltere premier lig")

# ── 3. lig_filtreli_key - tarihsel isimlerle eslestirme ──
print("\n=== lig_filtreli_key eslestirme testleri ===")

# Turkiye Super Lig - farkli sponsor isimleriyle
sel = {turkey_super}
check("Spor Toto Super Lig -> Turkiye Super Lig match",
      lig_filtreli_key("turkiye Spor Toto Süper Lig", sel), True)
check("Trendyol Super Lig -> Turkiye Super Lig match",
      lig_filtreli_key("turkiye Trendyol Süper Lig", sel), True)
check("Turkcell Super Lig -> Turkiye Super Lig match",
      lig_filtreli_key("turkiye Turkcell Süper Lig", sel), True)
check("Misli Super Lig -> Turkiye Super Lig match",
      lig_filtreli_key("turkiye Misli Süper Lig", sel), True)
check("Sadece Super Lig -> Turkiye Super Lig match",
      lig_filtreli_key("turkiye Süper Lig", sel), True)

# Turkiye 1. Lig - farkli sponsor isimleriyle
sel1 = {turkey_first}
check("TFF 1. Lig -> Turkiye 1. Lig match",
      lig_filtreli_key("turkiye TFF 1. Lig", sel1), True)
check("Bank Asya 1. Lig -> Turkiye 1. Lig match",
      lig_filtreli_key("turkiye Bank Asya 1. Lig", sel1), True)
check("PTT 1. Lig -> Turkiye 1. Lig match",
      lig_filtreli_key("turkiye PTT 1. Lig", sel1), True)

# Yanlis eslestirme - farkli lig seviyesi
check("Turkiye 2. Lig != Super Lig",
      lig_filtreli_key("turkiye 2. Lig", sel), False)
check("Turkiye Super Lig != 1. Lig",
      lig_filtreli_key("turkiye Süper Lig", sel1), False)

# Italya - Serie A TIM
sel_it = {italy_a}
check("Serie A TIM -> Italya Serie A match",
      lig_filtreli_key("italya Serie A TIM", sel_it), True)
check("Serie A -> Italya Serie A match",
      lig_filtreli_key("italya Serie A", sel_it), True)

# Fransa - Ligue 1 Uber Eats
sel_fr = {france_1}
check("Ligue 1 Uber Eats -> Fransa Ligue 1 match",
      lig_filtreli_key("fransa Ligue 1 Uber Eats", sel_fr), True)
check("Ligue 1 -> Fransa Ligue 1 match",
      lig_filtreli_key("fransa Ligue 1", sel_fr), True)

# Ingiltere
sel_eng = {eng_prem}
check("England Premier League -> Ingiltere Premier Lig match",
      lig_filtreli_key("england Premier League", sel_eng), True)

# ── 4. _league_tier testleri ──
print("\n=== _league_tier testleri ===")
check("turkiye super lig -> tier 1", _league_tier("turkiye", "super lig"), 1)
check("turkiye 1 lig -> tier 2", _league_tier("turkiye", "1 lig"), 2)
check("ingiltere premier lig -> tier 1", _league_tier("ingiltere", "premier lig"), 1)
check("ingiltere championship -> tier 2", _league_tier("ingiltere", "championship"), 2)
check("italya serie a -> tier 1", _league_tier("italya", "serie a"), 1)
check("italya serie b -> tier 2", _league_tier("italya", "serie b"), 2)

# ── Sonuc ──
print(f"\n{'='*50}")
print(f"PASSED: {PASSED}  FAILED: {FAILED}")
if FAILED > 0:
    print("BAZI TESTLER BASARISIZ!")
    sys.exit(1)
else:
    print("TUM TESTLER BASARILI!")
    sys.exit(0)
