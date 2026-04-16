import json
import pytest
from unittest.mock import patch, MagicMock
from lib.exploration.cern_api import format_size, QUICK_PICKS


# ---------------------------------------------------------------------------
# format_size
# ---------------------------------------------------------------------------

class TestFormatSize:
    def test_zero_returns_unknown(self):
        assert format_size(0) == "Unknown Size"

    def test_none_returns_unknown(self):
        assert format_size(None) == "Unknown Size"

    def test_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_one_kilobyte(self):
        assert format_size(1024) == "1.0 KB"

    def test_one_megabyte(self):
        assert format_size(1024 ** 2) == "1.0 MB"

    def test_one_gigabyte(self):
        assert format_size(1024 ** 3) == "1.0 GB"

    def test_one_terabyte(self):
        assert format_size(1024 ** 4) == "1.0 TB"

    def test_fractional_megabytes(self):
        result = format_size(int(1.5 * 1024 ** 2))
        assert "MB" in result
        assert "1.5" in result

    def test_large_file_uses_appropriate_unit(self):
        result = format_size(2 * 1024 ** 3)
        assert "GB" in result


# ---------------------------------------------------------------------------
# QUICK_PICKS constant
# ---------------------------------------------------------------------------

class TestQuickPicks:
    def test_has_four_entries(self):
        assert len(QUICK_PICKS) == 4

    def test_contains_jpsi(self):
        assert "Jpsimumu" in QUICK_PICKS.values()

    def test_contains_zmumu(self):
        assert "Zmumu" in QUICK_PICKS.values()

    def test_contains_ymumu(self):
        assert "Ymumu" in QUICK_PICKS.values()

    def test_contains_doublemu(self):
        assert "DoubleMu" in QUICK_PICKS.values()

    def test_all_labels_are_strings(self):
        for label, query in QUICK_PICKS.items():
            assert isinstance(label, str)
            assert isinstance(query, str)


# ---------------------------------------------------------------------------
# get_cern_data  (urllib mocked — no real network calls)
# ---------------------------------------------------------------------------

def _make_urlopen_mock(payload: dict):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode('utf-8')
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestGetCernData:
    def test_returns_parsed_json_on_success(self):
        fake = {"hits": {"hits": [], "total": 0}}
        with patch('urllib.request.urlopen', return_value=_make_urlopen_mock(fake)):
            from lib.exploration.cern_api import get_cern_data
            result = get_cern_data("unique_query_success_1", only_csv=False)
        assert result == fake

    def test_csv_filter_appended_to_url(self):
        fake = {"hits": {"hits": []}}
        captured_url = []

        def fake_urlopen(req, timeout=None):
            captured_url.append(req.full_url)
            return _make_urlopen_mock(fake)

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            from lib.exploration.cern_api import get_cern_data
            get_cern_data("unique_query_csv_filter", only_csv=True)

        assert "file_format:CSV" in captured_url[0]

    def test_csv_filter_absent_when_disabled(self):
        fake = {"hits": {"hits": []}}
        captured_url = []

        def fake_urlopen(req, timeout=None):
            captured_url.append(req.full_url)
            return _make_urlopen_mock(fake)

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            from lib.exploration.cern_api import get_cern_data
            get_cern_data("unique_query_no_csv_filter", only_csv=False)

        assert "file_format:CSV" not in captured_url[0]

    def test_returns_error_dict_on_network_failure(self):
        with patch('urllib.request.urlopen', side_effect=Exception("connection refused")):
            from lib.exploration.cern_api import get_cern_data
            result = get_cern_data("unique_query_failure_1", only_csv=False)
        assert "error" in result
        assert "connection refused" in result["error"]

    def test_query_spaces_replaced_with_plus(self):
        fake = {"hits": {"hits": []}}
        captured_url = []

        def fake_urlopen(req, timeout=None):
            captured_url.append(req.full_url)
            return _make_urlopen_mock(fake)

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            from lib.exploration.cern_api import get_cern_data
            get_cern_data("Run 2011 dimuon", only_csv=False)

        assert "Run+2011+dimuon" in captured_url[0]
