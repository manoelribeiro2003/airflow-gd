"""Testes do driver ODBC central (Variable MSSQL_ODBC_DRIVER)."""

from types import SimpleNamespace

import pytest
from global_modules import mssql


@pytest.fixture
def driver_var(monkeypatch):
    values: dict[str, str] = {}

    def fake_get(key, default=None):
        return values.get(key, default)

    monkeypatch.setattr(mssql.Variable, "get", fake_get)
    return values


def test_get_mssql_driver_usa_padrao_sem_variable(driver_var):
    assert mssql.get_mssql_driver() == "ODBC Driver 17 for SQL Server"


def test_get_mssql_driver_le_variable(driver_var):
    driver_var["MSSQL_ODBC_DRIVER"] = "SQL Server"
    assert mssql.get_mssql_driver() == "SQL Server"


def test_with_mssql_driver_troca_driver_da_url(driver_var):
    driver_var["MSSQL_ODBC_DRIVER"] = "SQL Server"
    url = mssql.with_mssql_driver(
        "mssql+pyodbc://u:p@host/db?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
    )

    assert url.query["driver"] == "SQL Server"
    assert url.query["TrustServerCertificate"] == "yes"


def test_with_mssql_driver_ignora_outros_dialetos(driver_var):
    url = mssql.with_mssql_driver("postgresql+psycopg2://u:p@host/db")

    assert "driver" not in url.query


def test_get_mssql_url_escapa_credenciais(driver_var, monkeypatch):
    conn = SimpleNamespace(login="user", password="p@ss:w/rd", host="srv", schema="elipse")
    monkeypatch.setattr(mssql.BaseHook, "get_connection", lambda conn_id: conn)

    url = mssql.get_mssql_url("elipse_sob")

    assert url.password == "p@ss:w/rd"
    assert url.host == "srv"
    assert url.database == "elipse"
    assert url.query["driver"] == "ODBC Driver 17 for SQL Server"
    assert "p%40ss" in url.render_as_string(hide_password=False)
