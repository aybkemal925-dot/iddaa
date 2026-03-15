"""
arsiv.mackolik.com/Genis-Iddaa-Programi sayfasındaki
"Ligler" dropdown'undan tüm ligleri çeker → ligler.txt'e yazar.

Kullanım: python ligleri_listele.py
"""
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = Path(__file__).resolve().parent
URL      = "https://arsiv.mackolik.com/Genis-Iddaa-Programi"

def build_driver():
    opts = FirefoxOptions()
    opts.add_argument("-headless")
    opts.page_load_strategy = "eager"
    gd  = BASE_DIR / "geckodriver.exe"
    svc = FirefoxService(executable_path=str(gd)) if gd.exists() else None
    drv = webdriver.Firefox(service=svc, options=opts) if svc else webdriver.Firefox(options=opts)
    drv.set_page_load_timeout(20)
    drv.implicitly_wait(5)
    return drv

def main():
    print("Tarayıcı açılıyor...")
    driver = build_driver()

    try:
        driver.get(URL)
        print(f"Sayfa yüklendi: {URL}")
        time.sleep(4)  # JS render için bekle

        ligler = set()
        import re

        src = driver.page_source

        # ── Yöntem 1: changeSubGroup çağrısı yapan tüm link/span'ları bul ──
        # onclick="changeSubGroup(123)" → bunlar lig linkleri
        els = driver.find_elements(By.XPATH, "//*[contains(@onclick,'changeSubGroup')]")
        for el in els:
            txt = el.text.strip()
            if txt and len(txt) > 2:
                ligler.add(txt)
        if ligler:
            print(f"changeSubGroup linklerinden {len(ligler)} lig bulundu.")

        # ── Yöntem 2: HTML'de changeSubGroup pattern'ından metin çek ────────
        if not ligler:
            # changeSubGroup(123)>Türkiye Süper Lig</a> gibi pattern
            found = re.findall(
                r"changeSubGroup\(\d+\)[^>]*>([^<]{3,80})<",
                src
            )
            for f in found:
                f = f.strip()
                if f:
                    ligler.add(f)
            if ligler:
                print(f"HTML regex'den {len(ligler)} lig bulundu.")

        # ── Yöntem 3: Tablo "Lig" sütunundan ────────────────────────────────
        if not ligler:
            print("Tablo 'Lig' sütunundan çekiliyor...")
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table tr td"))
                )
                rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
                # Header'dan Lig sütun indexini bul
                headers = rows[0].find_elements(By.TAG_NAME, "td") or \
                          rows[0].find_elements(By.TAG_NAME, "th")
                lig_idx = next(
                    (i for i, h in enumerate(headers) if "lig" in h.text.lower()), None
                )
                if lig_idx is not None:
                    for row in rows[1:]:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) > lig_idx:
                            val = cells[lig_idx].text.strip()
                            if val:
                                ligler.add(val)
                    print(f"Tablodan {len(ligler)} lig bulundu.")
            except Exception as e:
                print(f"Tablo okunamadı: {e}")

        # ── Yöntem 4: Debug — sayfa kaynağını kaydet ─────────────────────────
        if not ligler:
            dbg = Path(__file__).parent / "debug_ligler.html"
            dbg.write_text(src, encoding="utf-8")
            print(f"Hiç lig bulunamadı. Sayfa kaynağı kaydedildi: {dbg}")
            print("debug_ligler.html dosyasını açıp 'Ligler' kelimesini arayın.")

    finally:
        driver.quit()
        print("Tarayıcı kapatıldı.")

    if not ligler:
        print("\nHiç lig bulunamadı. Sayfa yapısı değişmiş olabilir.")
        return

    sorted_ligler = sorted(ligler, key=str.lower)

    out = BASE_DIR / "ligler.txt"
    out.write_text("\n".join(sorted_ligler), encoding="utf-8")

    print(f"\n{'─'*50}")
    print(f"Toplam {len(sorted_ligler)} lig bulundu:\n")
    for lig in sorted_ligler:
        print(f"  {lig}")
    print(f"\n→ Kaydedildi: {out}")


if __name__ == "__main__":
    main()
