from unittest.mock import MagicMock, patch

import pytest
import requests

from config import Config
from services.confiforms import (
    ConfiFormsCsvSource,
    ConfiFormsRestSource,
    DataSourceError,
    _extract_entries,
    get_data_source,
)


def make_config(**overrides) -> Config:
    defaults = dict(
        data_source_type="rest",
        confluence_url="https://confluence.example.com",
        confluence_username="svc-account",
        confluence_api_token="token123",
        confiform_endpoint="/rest/confiforms-data/1.0/entry/MyForm",
    )
    defaults.update(overrides)
    return Config(**defaults)


def test_extract_entries_accepts_bare_list():
    assert _extract_entries([{"a": 1}]) == [{"a": 1}]


def test_extract_entries_accepts_wrapped_dict():
    assert _extract_entries({"entries": [{"a": 1}]}) == [{"a": 1}]


def test_extract_entries_rejects_unknown_shape():
    with pytest.raises(DataSourceError):
        _extract_entries(42)


def test_rest_source_fetches_and_parses_json():
    config = make_config()
    source = ConfiFormsRestSource(config)

    mock_response = MagicMock()
    mock_response.json.return_value = {"entries": [{"Title": "Row 1"}]}
    mock_response.raise_for_status.return_value = None

    with patch.object(source.session, "get", return_value=mock_response) as mock_get:
        rows = source.fetch()

    assert rows == [{"Title": "Row 1"}]
    called_url = mock_get.call_args.args[0]
    assert called_url == "https://confluence.example.com/rest/confiforms-data/1.0/entry/MyForm"


def test_rest_source_raises_data_source_error_on_request_failure():
    config = make_config()
    source = ConfiFormsRestSource(config)

    with patch.object(source.session, "get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(DataSourceError):
            source.fetch()


def test_rest_source_requires_endpoint_configuration():
    config = make_config(confiform_endpoint="")
    source = ConfiFormsRestSource(config)
    with pytest.raises(DataSourceError):
        source.fetch()


def test_csv_source_parses_rows():
    config = make_config(data_source_type="csv")
    source = ConfiFormsCsvSource(config)

    mock_response = MagicMock()
    mock_response.text = "Title,Status\nRow 1,Open\nRow 2,Closed\n"
    mock_response.encoding = "utf-8"
    mock_response.raise_for_status.return_value = None

    with patch.object(source.session, "get", return_value=mock_response):
        rows = source.fetch()

    assert rows == [
        {"Title": "Row 1", "Status": "Open"},
        {"Title": "Row 2", "Status": "Closed"},
    ]


def test_get_data_source_factory_selects_implementation():
    config = make_config(data_source_type="rest")
    assert isinstance(get_data_source(config), ConfiFormsRestSource)


def test_get_data_source_factory_rejects_unknown_type():
    config = make_config(data_source_type="carrier-pigeon")
    with pytest.raises(DataSourceError):
        get_data_source(config)
