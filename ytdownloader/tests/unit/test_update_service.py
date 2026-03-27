# -*- coding: utf-8 -*-
"""
UpdateService — _parse_version ve sürüm karşılaştırma testleri.
Qt widget'ı açmayan, saf fonksiyon testleri.
"""

import pytest
from ytdownloader.services.update_service import _parse_version


class TestParseVersion:
    """_parse_version() sürüm dizisini int tuple'ına çevirir."""

    def test_standard_three_part(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_single_digit_parts(self):
        assert _parse_version("0.0.1") == (0, 0, 1)

    def test_multi_digit_minor(self):
        # Asıl düzeltmenin hedefi: 10 sayısal olarak 9'dan büyük olmalı
        assert _parse_version("1.10.0") == (1, 10, 0)

    def test_whitespace_stripped(self):
        assert _parse_version("  2.0.0  ") == (2, 0, 0)

    def test_non_numeric_part_becomes_zero(self):
        assert _parse_version("1.0.alpha") == (1, 0, 0)

    def test_empty_string(self):
        # Boş string → (0,) veya () — crash olmamalı
        result = _parse_version("")
        assert isinstance(result, tuple)


class TestVersionComparison:
    """
    Eski string karşılaştırması yerine _parse_version ile tuple karşılaştırması.
    Temel senaryo: "1.10.0" > "1.9.0" string olarak False dönerdi.
    """

    @pytest.mark.parametrize("newer, older", [
        ("1.10.0", "1.9.0"),    # asıl düzeltme senaryosu
        ("2.0.0",  "1.9.9"),    # major bump
        ("1.0.1",  "1.0.0"),    # patch bump
        ("1.1.0",  "1.0.99"),   # minor > patch
        ("10.0.0", "9.9.9"),    # çift haneli major
    ])
    def test_newer_greater_than_older(self, newer, older):
        assert _parse_version(newer) > _parse_version(older)

    @pytest.mark.parametrize("v", [
        ("1.9.0",  "1.10.0"),   # eski string davranışında hatalı True dönerdi
        ("1.0.0",  "1.0.0"),    # eşit
        ("0.9.9",  "1.0.0"),
    ])
    def test_not_greater(self, v):
        a, b = v
        assert not (_parse_version(a) > _parse_version(b))

    def test_equal_versions_not_greater(self):
        assert not (_parse_version("1.0.0") > _parse_version("1.0.0"))

    def test_string_comparison_would_fail_but_tuple_passes(self):
        """
        Regresyon testi: eski kod "1.10.0" > "1.9.0" = False döndürürdü.
        Yeni kod True döndürmeli.
        """
        assert "1.10.0" < "1.9.0"                              # string davranışı (kırık)
        assert _parse_version("1.10.0") > _parse_version("1.9.0")  # düzeltilmiş davranış
