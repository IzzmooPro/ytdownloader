# YouTube İndirici v1.2.1

Bu sürüm, 1.2.0 ile gelen yenilikleri ve ardından yapılan kapsamlı bir hata
taramasının düzeltmelerini içerir. Tüm düzeltmeler Windows'ta denenmiştir.

## 1.2.0 ile Gelenler

- **Kalıcı kuyruk:** Program kapanırken bitmemiş indirmeler kaydedilir; açılışta
  geri yükleme önerilir ve indirmeler kaldığı yerden devam eder.
- **Uyku engelleme:** İndirme sürerken bilgisayar uykuya geçmez.
- **Sistem tepsisi:** Pencere kapatılınca indirmeler tepside sürer.
- **Tek pencere:** Program ikinci kez açılınca mevcut pencere öne gelir.
- **Sürükle-bırak:** Tarayıcıdan link sürükleyerek video eklenebilir.
- **7 dil:** Arayüzün tamamı Türkçe, İngilizce, İspanyolca, Fransızca,
  Almanca, Japonca ve Portekizce.
- **Otomatik tema:** Windows'un koyu/açık ayarını takip eder.
- Aynı başlıklı farklı videolar artık birbirinin üzerine yazılmaz
  (dosya adında video kimliği bulunur).

## İndirme

- **MP4 uyumluluğu:** 1080p ve altında H.264 tercih edilir; dosyalar her TV,
  telefon ve oynatıcıda açılır. 1440p/4K seçenekleri korunur.
- **Doğru ilerleme:** Uzun videolarda ilerleme çubuğu baştan %100'de
  takılıyordu; artık gerçek yüzdeyi ve "… kaldı" süresini gösterir.
- **Daha dayanıklı:** Bağlantı kopması, zaman aşımı ve YouTube'un 403 hatası
  otomatik yeniden denenir; inmiş kısım kaybolmaz.
- **İlk kurulum:** FFmpeg ilk açılışta kurulduğunda MP3 dönüştürme program
  yeniden başlatılana kadar başarısız oluyordu; düzeltildi.
- **İndirme motoru güncellemesi:** yt-dlp arka planda günde bir kontrol edilir
  ve yeni sürüm bir sonraki açılışta devreye girer. YouTube değişikliklerinde
  program güncellemesi beklemek gerekmez.

## Linkler ve Playlist

- Telefondan paylaşılan (`m.youtube.com`), canlı yayın (`/live/`) ve embed
  linkleri kabul edilir.
- Playlist linki (`youtube.com/playlist?list=...`) yapıştırılınca doğrudan
  seçim penceresi açılır.
- Erişilemeyen playlist'lerde nedeni açıklayan mesaj gösterilir.
- Listede olan bir video tekrar eklenince "Video zaten listede" denir
  ("Geçersiz URL" yerine).

## Hata Düzeltmeleri

- Dönüştürme sırasında "Duraklat"a basılınca kart sonsuza kadar takılı
  kalıyordu.
- İptal edilen indirmelerin yarım dosyaları (`.part`) klasörde kalıyordu.
- Kart silinince ya da liste temizlenince yanlışlıkla "İndirme Hatası"
  bildirimi çıkıyordu.
- Karttan klasör seçmek araya giren ayar değişikliklerini geri alabiliyordu.
- "Simge durumunda başlat" ayarı çalışmıyordu.
- Bildirimlerde ikonlar iki kez görünüyordu.

## Güvenlik

- FFmpeg indirmeleri kurulmadan önce SHA-256 ile doğrulanır.
- İndirme motoru güncellemeleri resmi sürümün SHA-256 listesiyle doğrulanır.
- SSL hatasında sertifika doğrulamasını kapatan geri dönüş kaldırıldı.
