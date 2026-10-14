# -*- coding: utf-8 -*-
"""RetryEngine hata sınıflandırması."""

import pytest

from ytdownloader.core.retry_engine import RetryEngine


@pytest.mark.parametrize("msg", [
    "Unable to download webpage: <urlopen error timed out>",
    "<urlopen error [WinError 10054] An existing connection was forcibly closed>",
    "<urlopen error [Errno 11001] getaddrinfo failed>",   # Wi-Fi kısa süre koptu
    "HTTP Error 503: Service Unavailable",
])
def test_transient_errors_are_retried(msg):
    assert RetryEngine().is_retryable(msg)


@pytest.mark.parametrize("msg", [
    "ERROR: Video unavailable",
    "ERROR: Unsupported URL: https://example.com",
    "HTTP Error 404: Not Found",
    "Sign in to confirm your age",
])
def test_permanent_errors_are_not_retried(msg):
    assert not RetryEngine().is_retryable(msg)
