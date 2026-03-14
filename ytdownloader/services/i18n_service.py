# -*- coding: utf-8 -*-
"""I18nService — 7 dil desteği ile çeviri servisi."""

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "tr": {
        # Menü
        "dosya": "Dosya", "araclar": "Araçlar", "ayarlar": "Ayarlar",
        "gecmis": "İndirme Geçmişi", "guncelleme_kontrol": "Güncelleme Kontrolü",
        "hakkinda": "Hakkında", "cikis": "Çıkış",
        "kullanim": "Kullanım",
        "indir_yoneticiye_gonder": "İndirme Yöneticisine Gönder",
        "listeyi_ac": "Listeyi Aç...", "listeyi_kaydet": "Listeyi Kaydet...",
        # Toolbar
        "yapistir": "Yapıştır", "hepsini_indir": "Hepsini İndir",
        "listeyi_temizle": "Listeyi Temizle",
        # Filtre
        "goster": "Göster:", "tumu": "Tümü",
        "indiriliyor": "İndiriliyor", "tamamlandi": "Tamamlandı",
        # Kart
        "yukleniyor": "Yükleniyor...", "klasor_sec": "Klasör Seç",
        "indirme_klasoru_sec": "İndirme Klasörü Seç",
        # Durum
        "bekliyor": "Bekliyor", "duraklatildi": "Duraklatıldı",
        "yeniden_deneniyor": "Yeniden Deneniyor", "hata": "Hata",
        # Status bar
        "toplam": "Toplam", "video": "video", "tamamlandi_s": "Tamamlandı",
        # Bildirim
        "indirme_tamamlandi": "İndirme Tamamlandı",
        "indirme_hatasi": "İndirme Hatası",
        "gecersiz_url": "Geçersiz URL",
        "pano_url_yok": "Pano'da geçerli YouTube URL bulunamadı.",
        "liste_yuklendi": "Liste Yüklendi",
        "url_eklendi": "{n} URL eklendi.",
        "gecerli_url_yok": "Geçerli URL bulunamadı.",
        "liste_kaydedildi": "Kaydedildi",
        "url_kaydedildi": "{n} URL kaydedildi.",
        "listede_video_yok": "Listede video yok.",
        "toplu_indirme": "Toplu İndirme",
        "video_baslatildi": "{n} video başlatıldı.",
        # Ayarlar
        "ayarlar_title": "Ayarlar", "genel": "Genel", "indirme": "İndirme",
        "dil_section": "DİL", "uygulama_dili": "Uygulama Dili",
        "dil_not": "Dil değişikliği bir sonraki başlatmada geçerli olur.",
        "tema_section": "TEMA", "renk_temasi": "Renk Teması",
        "koyu": "Koyu (Dark)", "acik": "Açık (Light)",
        "bildirim_section": "BİLDİRİMLER",
        "diger_section": "DİĞER",
        "bildirim_tamamlandi": "İndirme tamamlandığında bildirim göster",
        "bildirim_hata": "Hata durumunda bildirim göster",
        "indirme_konum_section": "İNDİRME KONUMU",
        "varsayilan_klasor": "Varsayılan Klasör",
        "klasor_secilmedi": "Seçilmedi — her seferinde sorulur",
        "sec": "Seç", "temizle": "Temizle",
        "format_section": "VARSAYILAN FORMAT",
        "format": "Format", "varsayilan_kalite": "Varsayılan Kalite",
        "performans_section": "PERFORMANS",
        "eszamanli_indirme": "Eşzamanlı İndirme",
        "eszamanli_not": "0 = Sınırsız, 1–5 = Eşzamanlı indirme limiti",
        "iptal": "İptal", "kaydet": "Kaydet", "kapat": "Kapat",
        # Hakkında
        "hakkinda_title": "Hakkında",
        "hakkinda_desc": (
            "YouTube İndirici, YouTube videolarını kolayca\n"
            "MP3 veya MP4 formatında indirmenizi sağlayan\n"
            "ücretsiz bir masaüstü uygulamasıdır.\n\n"
            "Yüksek kaliteli indirme için yt-dlp altyapısı\n"
            "ve FFmpeg entegrasyonu kullanılmaktadır.\n\n"
            "Toplu indirme, format seçimi, otomatik yeniden\n"
            "deneme ve bildirim desteği sunar."
        ),
    },
    "en": {
        "dosya": "File", "araclar": "Tools", "ayarlar": "Settings",
        "gecmis": "Download History", "guncelleme_kontrol": "Check for Updates",
        "hakkinda": "About", "cikis": "Exit",
        "kullanim": "Help",
        "indir_yoneticiye_gonder": "Send to Download Manager",
        "listeyi_ac": "Open List...", "listeyi_kaydet": "Save List...",
        "yapistir": "Paste", "hepsini_indir": "Download All",
        "listeyi_temizle": "Clear List",
        "goster": "Show:", "tumu": "All",
        "indiriliyor": "Downloading", "tamamlandi": "Completed",
        "yukleniyor": "Loading...", "klasor_sec": "Select Folder",
        "indirme_klasoru_sec": "Select Download Folder",
        "bekliyor": "Waiting", "duraklatildi": "Paused",
        "yeniden_deneniyor": "Retrying", "hata": "Error",
        "toplam": "Total", "video": "video", "tamamlandi_s": "Completed",
        "indirme_tamamlandi": "Download Completed",
        "indirme_hatasi": "Download Error",
        "gecersiz_url": "Invalid URL",
        "pano_url_yok": "No valid YouTube URL found in clipboard.",
        "liste_yuklendi": "List Loaded",
        "url_eklendi": "{n} URL added.",
        "gecerli_url_yok": "No valid URL found.",
        "liste_kaydedildi": "Saved",
        "url_kaydedildi": "{n} URL saved.",
        "listede_video_yok": "No videos in list.",
        "toplu_indirme": "Bulk Download",
        "video_baslatildi": "{n} video(s) started.",
        "ayarlar_title": "Settings", "genel": "General", "indirme": "Download",
        "dil_section": "LANGUAGE", "uygulama_dili": "Application Language",
        "dil_not": "Language change takes effect on next launch.",
        "tema_section": "THEME", "renk_temasi": "Color Theme",
        "koyu": "Dark", "acik": "Light",
        "bildirim_section": "NOTIFICATIONS",
        "diger_section": "OTHER",
        "diger_section": "OTHER",
        "bildirim_tamamlandi": "Show notification when download completes",
        "bildirim_hata": "Show notification on error",
        "indirme_konum_section": "DOWNLOAD LOCATION",
        "varsayilan_klasor": "Default Folder",
        "klasor_secilmedi": "Not selected — will ask each time",
        "sec": "Browse", "temizle": "Clear",
        "format_section": "DEFAULT FORMAT",
        "format": "Format", "varsayilan_kalite": "Default Quality",
        "performans_section": "PERFORMANCE",
        "eszamanli_indirme": "Concurrent Downloads",
        "eszamanli_not": "0 = Unlimited, 1–5 = Concurrent download limit",
        "iptal": "Cancel", "kaydet": "Save", "kapat": "Close",
        "hakkinda_title": "About",
        "hakkinda_desc": (
            "YouTube Downloader lets you easily download\n"
            "YouTube videos in MP3 or MP4 format.\n\n"
            "Powered by yt-dlp and FFmpeg for high-quality\n"
            "downloads with batch support, format selection,\n"
            "auto-retry and notification features."
        ),
    },
    "es": {
        "dosya": "Archivo", "araclar": "Herramientas", "ayarlar": "Configuración",
        "gecmis": "Historial de Descargas", "guncelleme_kontrol": "Buscar Actualizaciones",
        "hakkinda": "Acerca de", "cikis": "Salir",
        "listeyi_ac": "Abrir lista...", "listeyi_kaydet": "Guardar lista...",
        "yapistir": "Pegar", "hepsini_indir": "Descargar todo",
        "listeyi_temizle": "Limpiar lista",
        "goster": "Mostrar:", "tumu": "Todos",
        "indiriliyor": "Descargando", "tamamlandi": "Completado",
        "yukleniyor": "Cargando...", "klasor_sec": "Seleccionar carpeta",
        "indirme_klasoru_sec": "Seleccionar carpeta de descarga",
        "bekliyor": "Esperando", "duraklatildi": "Pausado",
        "yeniden_deneniyor": "Reintentando", "hata": "Error",
        "toplam": "Total", "video": "video", "tamamlandi_s": "Completado",
        "indirme_tamamlandi": "Descarga completada",
        "indirme_hatasi": "Error de descarga",
        "gecersiz_url": "URL inválida",
        "pano_url_yok": "No se encontró una URL válida de YouTube en el portapapeles.",
        "liste_yuklendi": "Lista cargada", "url_eklendi": "{n} URL añadidas.",
        "gecerli_url_yok": "No se encontró URL válida.",
        "liste_kaydedildi": "Guardado", "url_kaydedildi": "{n} URL guardadas.",
        "listede_video_yok": "No hay videos en la lista.",
        "toplu_indirme": "Descarga masiva", "video_baslatildi": "{n} video(s) iniciados.",
        "ayarlar_title": "Configuración", "genel": "General", "indirme": "Descarga",
        "dil_section": "IDIOMA", "uygulama_dili": "Idioma de la aplicación",
        "dil_not": "El cambio de idioma se aplica al próximo inicio.",
        "tema_section": "TEMA", "renk_temasi": "Tema de color",
        "koyu": "Oscuro", "acik": "Claro",
        "bildirim_section": "NOTIFICACIONES",
        "diger_section": "OTROS",
        "bildirim_tamamlandi": "Mostrar notificación al completar descarga",
        "bildirim_hata": "Mostrar notificación en caso de error",
        "indirme_konum_section": "UBICACIÓN DE DESCARGA",
        "varsayilan_klasor": "Carpeta predeterminada",
        "klasor_secilmedi": "No seleccionada — se preguntará cada vez",
        "sec": "Seleccionar", "temizle": "Limpiar",
        "format_section": "FORMATO PREDETERMINADO",
        "format": "Formato", "varsayilan_kalite": "Calidad predeterminada",
        "performans_section": "RENDIMIENTO",
        "eszamanli_indirme": "Descargas simultáneas",
        "eszamanli_not": "0 = Ilimitado, 1–5 = Límite de descargas simultáneas",
        "iptal": "Cancelar", "kaydet": "Guardar", "kapat": "Cerrar",
        "hakkinda_title": "Acerca de",
        "hakkinda_desc": "YouTube Downloader te permite descargar\nvideos de YouTube en formato MP3 o MP4.\n\nImpulsado por yt-dlp y FFmpeg.",
    },
    "fr": {
        "dosya": "Fichier", "araclar": "Outils", "ayarlar": "Paramètres",
        "gecmis": "Historique des Téléchargements", "guncelleme_kontrol": "Vérifier les Mises à Jour",
        "hakkinda": "À propos", "cikis": "Quitter",
        "listeyi_ac": "Ouvrir la liste...", "listeyi_kaydet": "Enregistrer la liste...",
        "yapistir": "Coller", "hepsini_indir": "Tout télécharger",
        "listeyi_temizle": "Effacer la liste",
        "goster": "Afficher:", "tumu": "Tous",
        "indiriliyor": "Téléchargement", "tamamlandi": "Terminé",
        "yukleniyor": "Chargement...", "klasor_sec": "Sélectionner dossier",
        "indirme_klasoru_sec": "Sélectionner le dossier de téléchargement",
        "bekliyor": "En attente", "duraklatildi": "En pause",
        "yeniden_deneniyor": "Nouvelle tentative", "hata": "Erreur",
        "toplam": "Total", "video": "vidéo", "tamamlandi_s": "Terminé",
        "indirme_tamamlandi": "Téléchargement terminé",
        "indirme_hatasi": "Erreur de téléchargement",
        "gecersiz_url": "URL invalide",
        "pano_url_yok": "Aucune URL YouTube valide dans le presse-papiers.",
        "liste_yuklendi": "Liste chargée", "url_eklendi": "{n} URL ajoutées.",
        "gecerli_url_yok": "Aucune URL valide trouvée.",
        "liste_kaydedildi": "Enregistré", "url_kaydedildi": "{n} URL enregistrées.",
        "listede_video_yok": "Aucune vidéo dans la liste.",
        "toplu_indirme": "Téléchargement groupé", "video_baslatildi": "{n} vidéo(s) démarrée(s).",
        "ayarlar_title": "Paramètres", "genel": "Général", "indirme": "Téléchargement",
        "dil_section": "LANGUE", "uygulama_dili": "Langue de l'application",
        "dil_not": "Le changement de langue prend effet au prochain démarrage.",
        "tema_section": "THÈME", "renk_temasi": "Thème de couleur",
        "koyu": "Sombre", "acik": "Clair",
        "bildirim_section": "NOTIFICATIONS",
        "diger_section": "OTHER",
        "bildirim_tamamlandi": "Afficher une notification à la fin du téléchargement",
        "bildirim_hata": "Afficher une notification en cas d'erreur",
        "indirme_konum_section": "EMPLACEMENT DE TÉLÉCHARGEMENT",
        "varsayilan_klasor": "Dossier par défaut",
        "klasor_secilmedi": "Non sélectionné — demandé à chaque fois",
        "sec": "Parcourir", "temizle": "Effacer",
        "format_section": "FORMAT PAR DÉFAUT",
        "format": "Format", "varsayilan_kalite": "Qualité par défaut",
        "performans_section": "PERFORMANCE",
        "eszamanli_indirme": "Téléchargements simultanés",
        "eszamanli_not": "0 = Illimité, 1–5 = Limite de téléchargements simultanés",
        "iptal": "Annuler", "kaydet": "Enregistrer", "kapat": "Fermer",
        "hakkinda_title": "À propos",
        "hakkinda_desc": "YouTube Downloader vous permet de télécharger\ndes vidéos YouTube en MP3 ou MP4.\n\nAlimenté par yt-dlp et FFmpeg.",
    },
    "de": {
        "dosya": "Datei", "araclar": "Werkzeuge", "ayarlar": "Einstellungen",
        "gecmis": "Download-Verlauf", "guncelleme_kontrol": "Nach Updates suchen",
        "hakkinda": "Über", "cikis": "Beenden",
        "listeyi_ac": "Liste öffnen...", "listeyi_kaydet": "Liste speichern...",
        "yapistir": "Einfügen", "hepsini_indir": "Alles herunterladen",
        "listeyi_temizle": "Liste leeren",
        "goster": "Anzeigen:", "tumu": "Alle",
        "indiriliyor": "Wird heruntergeladen", "tamamlandi": "Abgeschlossen",
        "yukleniyor": "Wird geladen...", "klasor_sec": "Ordner auswählen",
        "indirme_klasoru_sec": "Download-Ordner auswählen",
        "bekliyor": "Wartend", "duraklatildi": "Pausiert",
        "yeniden_deneniyor": "Erneut versuchen", "hata": "Fehler",
        "toplam": "Gesamt", "video": "Video", "tamamlandi_s": "Abgeschlossen",
        "indirme_tamamlandi": "Download abgeschlossen",
        "indirme_hatasi": "Download-Fehler",
        "gecersiz_url": "Ungültige URL",
        "pano_url_yok": "Keine gültige YouTube-URL in der Zwischenablage.",
        "liste_yuklendi": "Liste geladen", "url_eklendi": "{n} URL hinzugefügt.",
        "gecerli_url_yok": "Keine gültige URL gefunden.",
        "liste_kaydedildi": "Gespeichert", "url_kaydedildi": "{n} URL gespeichert.",
        "listede_video_yok": "Keine Videos in der Liste.",
        "toplu_indirme": "Massendownload", "video_baslatildi": "{n} Video(s) gestartet.",
        "ayarlar_title": "Einstellungen", "genel": "Allgemein", "indirme": "Download",
        "dil_section": "SPRACHE", "uygulama_dili": "Anwendungssprache",
        "dil_not": "Sprachänderung wird beim nächsten Start wirksam.",
        "tema_section": "DESIGN", "renk_temasi": "Farbdesign",
        "koyu": "Dunkel", "acik": "Hell",
        "bildirim_section": "BENACHRICHTIGUNGEN",
        "bildirim_tamamlandi": "Benachrichtigung beim Abschluss anzeigen",
        "bildirim_hata": "Benachrichtigung bei Fehler anzeigen",
        "indirme_konum_section": "DOWNLOAD-SPEICHERORT",
        "varsayilan_klasor": "Standardordner",
        "klasor_secilmedi": "Nicht ausgewählt — wird jedes Mal gefragt",
        "sec": "Durchsuchen", "temizle": "Leeren",
        "format_section": "STANDARDFORMAT",
        "format": "Format", "varsayilan_kalite": "Standardqualität",
        "performans_section": "LEISTUNG",
        "eszamanli_indirme": "Gleichzeitige Downloads",
        "eszamanli_not": "0 = Unbegrenzt, 1–5 = Limit für gleichzeitige Downloads",
        "iptal": "Abbrechen", "kaydet": "Speichern", "kapat": "Schließen",
        "hakkinda_title": "Über",
        "hakkinda_desc": "YouTube Downloader ermöglicht das einfache\nHerunterladen von YouTube-Videos als MP3 oder MP4.\n\nAngetrieben von yt-dlp und FFmpeg.",
    },
    "ja": {
        "dosya": "ファイル", "araclar": "ツール", "ayarlar": "設定",
        "gecmis": "ダウンロード履歴", "guncelleme_kontrol": "アップデートを確認",
        "hakkinda": "について", "cikis": "終了",
        "listeyi_ac": "リストを開く...", "listeyi_kaydet": "リストを保存...",
        "yapistir": "貼り付け", "hepsini_indir": "すべてダウンロード",
        "listeyi_temizle": "リストをクリア",
        "goster": "表示:", "tumu": "すべて",
        "indiriliyor": "ダウンロード中", "tamamlandi": "完了",
        "yukleniyor": "読み込み中...", "klasor_sec": "フォルダを選択",
        "indirme_klasoru_sec": "ダウンロードフォルダを選択",
        "bekliyor": "待機中", "duraklatildi": "一時停止",
        "yeniden_deneniyor": "再試行中", "hata": "エラー",
        "toplam": "合計", "video": "動画", "tamamlandi_s": "完了",
        "indirme_tamamlandi": "ダウンロード完了",
        "indirme_hatasi": "ダウンロードエラー",
        "gecersiz_url": "無効なURL",
        "pano_url_yok": "クリップボードに有効なYouTube URLが見つかりません。",
        "liste_yuklendi": "リスト読み込み完了", "url_eklendi": "{n}件のURLを追加しました。",
        "gecerli_url_yok": "有効なURLが見つかりません。",
        "liste_kaydedildi": "保存完了", "url_kaydedildi": "{n}件のURLを保存しました。",
        "listede_video_yok": "リストに動画がありません。",
        "toplu_indirme": "一括ダウンロード", "video_baslatildi": "{n}件の動画を開始しました。",
        "ayarlar_title": "設定", "genel": "一般", "indirme": "ダウンロード",
        "dil_section": "言語", "uygulama_dili": "アプリの言語",
        "dil_not": "言語の変更は次回起動時に有効になります。",
        "tema_section": "テーマ", "renk_temasi": "カラーテーマ",
        "koyu": "ダーク", "acik": "ライト",
        "bildirim_section": "通知",
        "bildirim_tamamlandi": "ダウンロード完了時に通知を表示",
        "bildirim_hata": "エラー時に通知を表示",
        "indirme_konum_section": "ダウンロード場所",
        "varsayilan_klasor": "デフォルトフォルダ",
        "klasor_secilmedi": "未選択 — 毎回確認します",
        "sec": "選択", "temizle": "クリア",
        "format_section": "デフォルトフォーマット",
        "format": "フォーマット", "varsayilan_kalite": "デフォルト品質",
        "performans_section": "パフォーマンス",
        "eszamanli_indirme": "同時ダウンロード数",
        "eszamanli_not": "0 = 無制限、1〜5 = 同時ダウンロード制限",
        "iptal": "キャンセル", "kaydet": "保存", "kapat": "閉じる",
        "hakkinda_title": "について",
        "hakkinda_desc": "YouTube Downloaderは、YouTubeの動画を\nMP3またはMP4形式で簡単にダウンロードできる\n無料のデスクトップアプリです。\n\nyt-dlpとFFmpegを使用しています。",
    },
    "pt": {
        "dosya": "Arquivo", "araclar": "Ferramentas", "ayarlar": "Configurações",
        "gecmis": "Histórico de Downloads", "guncelleme_kontrol": "Verificar Atualizações",
        "hakkinda": "Sobre", "cikis": "Sair",
        "listeyi_ac": "Abrir lista...", "listeyi_kaydet": "Salvar lista...",
        "yapistir": "Colar", "hepsini_indir": "Baixar tudo",
        "listeyi_temizle": "Limpar lista",
        "goster": "Mostrar:", "tumu": "Todos",
        "indiriliyor": "Baixando", "tamamlandi": "Concluído",
        "yukleniyor": "Carregando...", "klasor_sec": "Selecionar pasta",
        "indirme_klasoru_sec": "Selecionar pasta de download",
        "bekliyor": "Aguardando", "duraklatildi": "Pausado",
        "yeniden_deneniyor": "Tentando novamente", "hata": "Erro",
        "toplam": "Total", "video": "vídeo", "tamamlandi_s": "Concluído",
        "indirme_tamamlandi": "Download concluído",
        "indirme_hatasi": "Erro no download",
        "gecersiz_url": "URL inválida",
        "pano_url_yok": "Nenhuma URL válida do YouTube encontrada na área de transferência.",
        "liste_yuklendi": "Lista carregada", "url_eklendi": "{n} URL adicionadas.",
        "gecerli_url_yok": "Nenhuma URL válida encontrada.",
        "liste_kaydedildi": "Salvo", "url_kaydedildi": "{n} URL salvas.",
        "listede_video_yok": "Nenhum vídeo na lista.",
        "toplu_indirme": "Download em lote", "video_baslatildi": "{n} vídeo(s) iniciado(s).",
        "ayarlar_title": "Configurações", "genel": "Geral", "indirme": "Download",
        "dil_section": "IDIOMA", "uygulama_dili": "Idioma do aplicativo",
        "dil_not": "A mudança de idioma terá efeito no próximo início.",
        "tema_section": "TEMA", "renk_temasi": "Tema de cor",
        "koyu": "Escuro", "acik": "Claro",
        "bildirim_section": "NOTIFICAÇÕES",
        "bildirim_tamamlandi": "Mostrar notificação ao concluir download",
        "bildirim_hata": "Mostrar notificação em caso de erro",
        "indirme_konum_section": "LOCAL DE DOWNLOAD",
        "varsayilan_klasor": "Pasta padrão",
        "klasor_secilmedi": "Não selecionada — perguntará cada vez",
        "sec": "Selecionar", "temizle": "Limpar",
        "format_section": "FORMATO PADRÃO",
        "format": "Formato", "varsayilan_kalite": "Qualidade padrão",
        "performans_section": "DESEMPENHO",
        "eszamanli_indirme": "Downloads simultâneos",
        "eszamanli_not": "0 = Ilimitado, 1–5 = Limite de downloads simultâneos",
        "iptal": "Cancelar", "kaydet": "Salvar", "kapat": "Fechar",
        "hakkinda_title": "Sobre",
        "hakkinda_desc": "YouTube Downloader permite baixar vídeos\ndo YouTube em formato MP3 ou MP4.\n\nImpulsionado por yt-dlp e FFmpeg.",
    },
}


class I18nService:
    def __init__(self, language: str = "tr"):
        self._lang = language if language in _TRANSLATIONS else "tr"

    @property
    def language(self) -> str:
        return self._lang

    @language.setter
    def language(self, lang: str):
        if lang in _TRANSLATIONS:
            self._lang = lang

    def t(self, key: str, default: str | None = None, **kwargs) -> str:
        result = (
            _TRANSLATIONS.get(self._lang, {}).get(key)
            or _TRANSLATIONS["tr"].get(key)
            or default or key
        )
        if kwargs:
            try:
                result = result.format(**kwargs)
            except KeyError:
                pass
        return result

    def available_languages(self) -> list[str]:
        return list(_TRANSLATIONS.keys())


# Modül düzeyi singleton — tüm UI bu nesneyi kullanır
_instance: I18nService | None = None

def get_i18n(lang: str | None = None) -> I18nService:
    global _instance
    if _instance is None:
        _instance = I18nService(lang or "tr")
    elif lang and lang != _instance.language:
        _instance.language = lang
    return _instance

def t(key: str, **kwargs) -> str:
    return get_i18n().t(key, **kwargs)

def get_translation(language: str, key: str, default: str | None = None) -> str:
    return I18nService(language).t(key, default)
