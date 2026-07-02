# -*- coding: utf-8 -*-
"""
DownloadState — indirme durumu Finite State Machine.

Geçersiz durum geçişleri StateError fırlatır.
Bu sayede race condition'lardan kaynaklanan imkânsız durumlar
derleme zamanında değil, çalışma zamanında hemen yakalanır.
"""

from enum import Enum, auto
from typing import FrozenSet


class DownloadState(Enum):
    PENDING    = auto()   # Kuyruğa eklendi, henüz başlamadı
    FETCHING   = auto()   # Video bilgisi alınıyor
    QUEUED     = auto()   # Bilgi alındı, indirme sırası bekleniyor
    ACTIVE     = auto()   # Aktif olarak indiriliyor
    PAUSING    = auto()   # Durdurma isteği gönderildi, henüz durmadı
    PAUSED     = auto()   # Durduruldu, .part dosyası diskte bekliyor
    MERGING    = auto()   # FFmpeg video+ses birleştiriyor
    COMPLETED  = auto()   # Başarıyla tamamlandı
    CANCELLED  = auto()   # Kullanıcı iptal etti
    ERROR      = auto()   # Hata ile sonuçlandı
    RETRYING   = auto()   # Otomatik yeniden deneme bekleniyor


# Her durumdan hangi durumlara geçilebileceğini tanımlar.
# Burada olmayan bir geçiş → StateError
VALID_TRANSITIONS: dict[DownloadState, FrozenSet[DownloadState]] = {
    DownloadState.PENDING:   frozenset({DownloadState.FETCHING,  DownloadState.QUEUED,    DownloadState.CANCELLED}),
    DownloadState.FETCHING:  frozenset({DownloadState.QUEUED,    DownloadState.ERROR,     DownloadState.CANCELLED}),
    DownloadState.QUEUED:    frozenset({DownloadState.ACTIVE,    DownloadState.PAUSING,   DownloadState.ERROR,
                                        DownloadState.CANCELLED}),
    DownloadState.ACTIVE:    frozenset({DownloadState.PAUSING,   DownloadState.MERGING,   DownloadState.COMPLETED,
                                        DownloadState.ERROR,     DownloadState.CANCELLED, DownloadState.RETRYING}),
    DownloadState.PAUSING:   frozenset({DownloadState.PAUSED,    DownloadState.ACTIVE,    DownloadState.ERROR,
                                        DownloadState.CANCELLED}),
    DownloadState.PAUSED:    frozenset({DownloadState.ACTIVE,    DownloadState.ERROR,     DownloadState.CANCELLED}),
    DownloadState.MERGING:   frozenset({DownloadState.COMPLETED, DownloadState.ERROR}),
    DownloadState.COMPLETED: frozenset(),   # terminal
    DownloadState.CANCELLED: frozenset(),   # terminal
    DownloadState.ERROR:     frozenset({DownloadState.RETRYING,  DownloadState.CANCELLED}),
    DownloadState.RETRYING:  frozenset({DownloadState.ACTIVE,    DownloadState.CANCELLED, DownloadState.ERROR}),
}

# Terminal durumlar — bu durumlardan çıkış yok
TERMINAL_STATES: FrozenSet[DownloadState] = frozenset({
    DownloadState.COMPLETED,
    DownloadState.CANCELLED,
})


class StateError(Exception):
    """Geçersiz durum geçişi denendiğinde fırlatılır."""
    pass


def is_valid_transition(from_state: DownloadState, to_state: DownloadState) -> bool:
    """Geçişin geçerli olup olmadığını kontrol eder."""
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())
