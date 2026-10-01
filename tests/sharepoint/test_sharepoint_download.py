"""Testes do download de arquivo binário (drive) do SharePoint via Graph API."""

from unittest.mock import MagicMock, patch

import pytest
from global_modules.sharepoint.sharepoint import download_sharepoint_file_with_graph_api
from office365.runtime.client_request_exception import ClientRequestException

SITE_URL = "https://example.sharepoint.com/sites/teste"
DRIVE_PATH = "Arquivos Melhorias/volumes.parquet"


@pytest.fixture(autouse=True)
def _patch_env():
    """Evita acesso a Airflow Variables: env() sempre retorna um valor dummy."""
    with patch("global_modules.sharepoint.sharepoint.env", return_value="dummy"):
        yield


def _build_client_mock(*, content_value=b"PARQUET", raise_exc=None):
    """Monta o mock da cadeia GraphClient -> site -> drive -> item -> get_content."""
    drive_item = MagicMock()
    get_content = drive_item.get_content.return_value
    if raise_exc is not None:
        get_content.execute_query.side_effect = raise_exc
    else:
        content = MagicMock()
        content.value = content_value
        get_content.execute_query.return_value = content

    site = MagicMock()
    site.drive.root.get_by_path.return_value = drive_item

    client = MagicMock()
    client.with_client_secret.return_value = client
    client.sites.get_by_url.return_value = site

    return client, drive_item


@patch("global_modules.sharepoint.sharepoint.GraphClient")
def test_download_retorna_bytes(graph_client_cls):
    client, drive_item = _build_client_mock(content_value=b"PARQUET")
    graph_client_cls.return_value = client

    data = download_sharepoint_file_with_graph_api(DRIVE_PATH, site_url=SITE_URL)

    assert data == b"PARQUET"
    drive_item.get_content.assert_called_once()


@patch("global_modules.sharepoint.sharepoint.GraphClient")
def test_download_arquivo_ausente_levanta_filenotfound(graph_client_cls):
    response = MagicMock()
    response.status_code = 404
    response.headers.get.return_value = ""
    response.content = b""
    exc = ClientRequestException(response=response)

    client, _ = _build_client_mock(raise_exc=exc)
    graph_client_cls.return_value = client

    with pytest.raises(FileNotFoundError, match="não encontrado"):
        download_sharepoint_file_with_graph_api(DRIVE_PATH, site_url=SITE_URL)


@patch("global_modules.sharepoint.sharepoint.GraphClient")
def test_download_conteudo_vazio_levanta_filenotfound(graph_client_cls):
    client, _ = _build_client_mock(content_value=b"")
    graph_client_cls.return_value = client

    with pytest.raises(FileNotFoundError, match="vazio"):
        download_sharepoint_file_with_graph_api(DRIVE_PATH, site_url=SITE_URL)
