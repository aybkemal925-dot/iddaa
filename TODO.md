# İddaaPro TODO Listesi

## ✅ Tamamlananlar
- [x] 12+ market verisi ekleme
- [x] Hakem/MBS kaldırma
- [x] Tarih/Saat/Lig bilgisi ekleme
- [x] Maç linkini Excel'den kaldırma

---

## 📋 Yapılacaklar

### 1️⃣ Performans İyileştirmesi (20 Yıllık Veri Optimizasyonu)
**Dosya:** `iddaapro.py`

**Görevler:**
- [ ] Page load timeout'ları azalt (30s → 15s)
- [ ] Implicit wait ekle (driver seviyesinde)
- [ ] time.sleep() sürelerini optimize et (1.5s → 0.5s gibi)
- [ ] Popup kontrollerini azalt (2 kez → 1 kez)
- [ ] Paralel tarih işleme ekle (opsiyonel - multiprocessing)
- [ ] Başarısız maçları skip et, retry mekanizması kaldır
- [ ] WebDriverWait timeout'larını düşür (20s → 10s)
- [ ] Element bulma stratejilerini optimize et (CSS selector öncelik)
- [ ] Console log seviyesini azalt (sadece hata logları)

**Beklenen Sonuç:** 
- Mevcut: ~5-10 saniye/maç → Hedef: ~2-3 saniye/maç

---

### 2️⃣ BAT Dosyası Oluşturma
**Dosya:** `iddaapro.bat`

**Görevler:**
- [ ] `iddaapro.bat` dosyası oluştur
- [ ] Python yolu otomatik bul (`py` komutu kullan)
- [ ] CMD penceresini açık tut (`pause` ekle)
- [ ] Hata mesajlarını göster
- [ ] Başlangıç mesajı ekle

**İçerik Taslağı:**
```batch
@echo off
title IddaaPro - Veri Cekici
echo =====================================
echo    IddaaPro Baslatiliyor...
echo =====================================
echo.
py iddaapro.py
if %errorlevel% neq 0 (
    echo.
    echo HATA: Program beklenmedik sekilde sonlandi!
    pause
)
```

---

### 3️⃣ BAT Dosyasına İkon Ekleme
**Dosya:** İkon dosyası + exe converter

**Görevler:**
- [ ] 256x256 veya 128x128 iddaa temalı ikon oluştur/indir
- [ ] İkon dosyasını `.ico` formatına çevir
- [ ] Bat2Exe veya benzeri araç kullanarak BAT → EXE dönüşümü yap
- [ ] İkonu EXE'ye gömme

**Alternatif Yöntem:**
- [ ] Python GUI'yi `pyinstaller` ile derle
- [ ] `--icon=iddaa_icon.ico` parametresi ile ikon ekle

**Komut:**
```bash
pyinstaller --onefile --windowed --icon=iddaa_icon.ico iddaapro.py
```

---

### 4️⃣ GUI Tasarımı: Sarı-Yeşil-Beyaz Tema
**Dosya:** `iddaapro.py` (GUI section)

**Renk Paleti (İddaa.com benzeri):**
```python
CLR_BG      = "#FFFFFF"      # Beyaz arka plan
CLR_HEADER  = "#FFD600"      # Sarı header
CLR_BTN_G   = "#00A650"      # Yeşil buton (ana)
CLR_BTN_Y   = "#FFD600"      # Sarı buton (ikincil)
CLR_BTN_O   = "#FF8C00"      # Turuncu (uyarı)
CLR_BTN_R   = "#D32F2F"      # Kırmızı (iptal)
CLR_BTN_TXT = "#FFFFFF"      # Beyaz yazı
CLR_GRID_H  = "#FFF9C4"      # Açık sarı (tablo header)
CLR_HOVER   = "#FFEB3B"      # Hover sarısı
```

**Görevler:**
- [ ] Renk sabitlerini güncelle
- [ ] Header bandını sarı yap (#FFD600)
- [ ] Ana butonları yeşil yap (#00A650)
- [ ] İptal butonu kırmızı (#D32F2F)
- [ ] Arka planı beyaz yap (#FFFFFF)
- [ ] Treeview header'ı açık sarı (#FFF9C4)

---

### 5️⃣ Hover Efektleri Ekleme
**Dosya:** `iddaapro.py` (GUI section)

**Görevler:**
- [ ] Butonlara `<Enter>` ve `<Leave>` event'leri ekle
- [ ] Hover'da renk değiştirme (yeşil → açık yeşil)
- [ ] Hover'da cursor değişimi (`hand2`)
- [ ] Treeview satırlarına hover ekle
- [ ] Hafif gölge efekti (border değişimi)

**Örnek Kod:**
```python
def _btn_hover_enter(self, event, btn, hover_color):
    btn.configure(bg=hover_color)

def _btn_hover_leave(self, event, btn, normal_color):
    btn.configure(bg=normal_color)

# Kullanım:
btn.bind("<Enter>", lambda e: self._btn_hover_enter(e, btn, "#4CAF50"))
btn.bind("<Leave>", lambda e: self._btn_hover_leave(e, btn, "#00A650"))
```

---

### 6️⃣ Kartları Dengeleme
**Dosya:** `iddaapro.py` (GUI section)

**Görevler:**
- [ ] LabelFrame'leri eşit genişlikte yap
- [ ] Grid layout yerine uniform column kullan
- [ ] Her kartın min-max genişliği belirle
- [ ] Padding/margin değerlerini eşitle
- [ ] Kartlar arası boşlukları düzenle (6-8px)
- [ ] Responsive tasarım (pencere resize'da düzen bozulmasın)

**Layout Düzeni:**
```
[ Veri Çekme (300px) ] [ 2 Tarih Arası (250px) ] [ Excel Aktar (200px) ]
```

---

### 7️⃣ Premium Görünüm
**Dosya:** `iddaapro.py` (GUI section)

**Görevler:**
- [ ] Modern font kullan (`Segoe UI`, `Arial`, `Helvetica`)
- [ ] Rounded corners ekle (tkinter'da simüle et - border tricks)
- [ ] Gölge efekti (Frame'lere `highlightthickness` + renk)
- [ ] Gradient arka plan (Canvas kullanarak - opsiyonel)
- [ ] İkonlu butonlar (emoji veya unicode symbols)
- [ ] Animasyonlu progressbar (renk değişimi)
- [ ] Status bar'a ikon ekle (✓, ⚠, ⏳)
- [ ] Treeview satırlarına zebra çizgi (alternatif renk)

**Ek Fikirler:**
- [ ] Başlık bandına logo ekle (PhotoImage)
- [ ] Butonlara ikon ekle: 
  - ▶ Çek
  - ⏹ İptal
  - 🔄 Yenile
  - 📥 Aktar
- [ ] Tooltip ekle (buton üzerine gelince açıklama)

---

## 🎯 Öncelik Sırası

1. **Yüksek Öncelik:**
   - Performans optimizasyonu (20 yıllık veri için kritik)
   - BAT dosyası oluşturma (kullanım kolaylığı)

2. **Orta Öncelik:**
   - Sarı-yeşil-beyaz tema (görsel iyileştirme)
   - Kartları dengeleme (düzen)

3. **Düşük Öncelik:**
   - Hover efektleri (detay)
   - Premium görünüm (ekstra detaylar)
   - İkon ekleme (BAT için)

---

## 📝 Notlar

- Her görev için ayrı commit yap
- Test et, sonra devam et
- Performans değişikliklerini önce küçük veri setiyle dene (1 haftalık)
- GUI değişikliklerini canlı test et (pencereyi açık tut)
- BAT dosyası için geckodriver.exe'nin aynı klasörde olduğundan emin ol

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Performans optimizasyonu için:
"iddaapro.py dosyasında time.sleep() sürelerini 0.5'e düşür"

# 2. BAT dosyası için:
"iddaapro.bat dosyası oluştur, içine py iddaapro.py yaz"

# 3. Tema değişikliği için:
"CLR_HEADER = '#FFD600' ve CLR_BTN_G = '#00A650' yap"
```
