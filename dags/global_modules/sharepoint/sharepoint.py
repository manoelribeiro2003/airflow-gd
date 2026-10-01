import json
from datetime import datetime, timedelta, timezone

import pandas as pd
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.sharepoint.datetime_resolve import DatetimeConfig, resolve_with_config
from global_modules.sharepoint.envs import env
from global_modules.sharepoint.utils import (
    map_to_json,
    parse_by_schema,
    parse_datetime,
    parse_number,
)
from office365.graph_client import GraphClient
from office365.runtime.auth.user_credential import UserCredential
from office365.runtime.client_request_exception import ClientRequestException
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.listitems.collection import ListItemCollection
from sqlalchemy import types as sa_types

log = LoggingMixin().log


def _serialize(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, ensure_ascii=False, default=str)


def print_progress(items: ListItemCollection):
    # type: (ListItemCollection) -> None
    log.info("Items read: {0} ✅".format(len(items)))


def fetch_sharepoint_items(  # noqa: PLR0913, PLR0917
    list_fields: dict[str, sa_types.TypeEngine],
    expand_fields: list[str] | None = None,
    datetime_columns: list[str] | None = None,
    page_size: int = 1000,
    retrieve: int | None = 10_000,
    site_url: str | None = None,
    list_name: str | None = None,
):
    """
    `Deprecated` Use fetch_sharepoint_items_with_graph_api.\n
    Recupera os registros de uma lista do Sharepoint.

    Todos os campos serão retornados como `str`

    Para funciona, é necessário fornecer um usuário e senha que tenha acesso a lista do
    Sharepoint. Esses dados devem ser fornecidos via variável de ambiente
    `SHAREPOINT_USERNAME` e `SHAREPOINT_USER_PASSWORD`. Se não fornecido um `ValueError`
    será gerado.

    :param list_fields: Um dicionário contendo os nomes das colunas da lista como key e o
        tipo do banco de dados como value `dict[field_name, sqlalchemy.types]`. Exemplo:
        `{'Title': sqlalchemy.types.VARCHAR(255), 'fabrica/Title':
        sqlalchemy.types.VARCHAR(255)}`.

    :type list_fields: dict[str, sqlalchemy.types]

    :param expand_fields: Uma lista com o nome das colunas que são referencia de outra
        lista (colunas do tipo lookup/consulta).
    :type expand_fields: list[str] | None

    :param datetime_columns: Uma lista com o nome das colunas que são datetime para que
        seja feito a conversão.
    :type datetime_columns: list[str] | None

    :param page_size: Quantidade registros a serem recuperados por vez pela api do
        sharepoint.
    :type page_size: int, `default: 1000`.

    :param retrieve: Total de linhas a serem recuperadas da lista. O calculo é
        `ID - retrieve`, onde `ID` é o campo que o Sharepoint preenche automaticamente.
        Em uma lista com `50_000` linhas e queremos recuperar `10_000`, serão retornados
        todos os registro com `ID > 40_000`.
    :type retrieve: int | None, `Default: 10_000`.

    :param site_url: Site onde a lista se encontra exemplo:
        `https://grendenecombr.sharepoint.com/sites/dados_industriais`. Se `None` for
        passado tentamos pegar da variável de ambiente `SHAREPOINT_SITE_URL` se não
        encontrar será gerado um `ValueError`.
    :type site_url: str | None

    :param list_name: Nome das lista para recuperar os dados. Se `None` for passado
        tentamos pegar da variável de ambiente `SHAREPOINT_SITE_URL` se não encontrar
        será gerado um `ValueError`.

    :type list_name: str | None

    :return: Um `Pandas.DataFrame` contendo os dados.
    :rtype: DataFrame
    """
    initial_id: int | None = None

    if site_url is None:
        site_url = env("SHAREPOINT_SITE_URL")

    ctx = ClientContext(site_url).with_credentials(
        UserCredential(env("SHAREPOINT_USERNAME"), env("SHAREPOINT_USER_PASSWORD")),
    )

    if list_name is None:
        list_name = env("SHAREPOINT_LIST_NAME")

    sp_list = ctx.web.lists.get_by_title(list_name)

    query = sp_list.items

    if retrieve is not None:
        last_item = (
            query.select(["ID"]).top(page_size).order_by("ID desc").top(1).get().execute_query()
        )
        initial_id = last_item.to_json()[0]["ID"] - retrieve

    query = query.clear_state().select(list(list_fields.keys()))

    if datetime_columns is not None:
        query = query.expand(expand_fields)  # type: ignore

    if initial_id is not None:
        query = query.filter(f"ID ge {initial_id}")

    paged_items = query.top(page_size).get().execute_query()

    def to_df(items) -> pd.DataFrame:
        return pd.DataFrame(map_to_json(items.to_json()), dtype=str).drop(
            columns=["Id"],
            errors="ignore",
        )

    all_items = to_df(paged_items)

    while True:
        if not paged_items.has_next:
            break
        paged_items = paged_items._get_next().execute_query()
        all_items = pd.concat([all_items, to_df(paged_items)], ignore_index=True)

    if datetime_columns is not None:
        all_items = parse_datetime(all_items, datetime_columns)  # type: ignore

    all_items = parse_number(all_items, list_fields)

    return all_items


def fetch_sharepoint_items_with_graph_api(  # noqa: PLR0913, PLR0917
    list_fields: dict[str, sa_types.TypeEngine],
    page_size=1000,
    start_date: datetime | None = None,
    site_url: str | None = None,
    list_name: str | None = None,
    datetime_config: DatetimeConfig | None = None,
):
    """
    Recupera os registros de uma lista do SharePoint via Microsoft Graph API.

    Campos são selecionados via `$expand=fields($select=...)`. Todos os valores são recebidos
    como `str` e convertidos automaticamente conforme os tipos definidos em `list_fields` via
    `parse_by_schema`: inteiros → `Int64`, decimais/floats → `float64`, booleanos → `boolean`,
    datas → `datetime64`, datetimes com `timezone=True` → UTC, datetimes sem timezone → naive.

    Requer as variáveis de ambiente: `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`,
    `SHAREPOINT_CLIENT_SECRET`. Se não fornecidas, um `ValueError` será gerado.

    :param list_fields: Dicionário `{nome_do_campo: tipo_sqlalchemy}`. As keys definem quais
        campos serão selecionados; os values controlam a conversão de tipos.
        Exemplo: `{'Title': sa_types.VARCHAR(255), 'Quantidade': sa_types.Integer()}`.
    :type list_fields: dict[str, sqlalchemy.types.TypeEngine]

    :param page_size: Registros recuperados por página.
    :type page_size: int, `default: 1000`.

    :param start_date: Data de corte para o filtro `Modified ge`. Se `None`, usa
        `now(UTC) - SHAREPOINT_SEARCH_DAYS` dias.
    :type start_date: datetime | None

    :param site_url: URL do site SharePoint. Se `None`, usa a variável `SHAREPOINT_SITE_URL`.
    :type site_url: str | None

    :param list_name: Nome da lista. Se `None`, usa a variável `SHAREPOINT_LIST_NAME`.
    :type list_name: str | None

    :return: `pandas.DataFrame` com os dados da lista.
    :rtype: pandas.DataFrame
    """
    if site_url is None:
        site_url = env("SHAREPOINT_SITE_URL")

    if list_name is None:
        list_name = env("SHAREPOINT_LIST_NAME")

    client = GraphClient(
        tenant=env("SHAREPOINT_TENANT_ID"),
    ).with_client_secret(
        env("SHAREPOINT_CLIENT_ID"),
        env("SHAREPOINT_CLIENT_SECRET"),
    )

    site = client.sites.get_by_url(site_url)
    sp_list = site.lists.get_by_name(list_name)

    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=int(env("SHAREPOINT_SEARCH_DAYS")))

    # Graph API expõe campos customizados via $expand=fields, não via $select direto
    query = (
        sp_list.items
        .expand([f"fields($select={','.join(list_fields)})"])
        .order_by("fields/Modified desc")
        .filter(f"fields/Modified ge '{start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}'")
    )

    paged_items = (
        query
        .paged(
            page_size,
            page_loaded=print_progress,  # pyright: ignore[reportArgumentType]
        )
        .get()
        .execute_query()
    )

    # Campos ficam em item.fields (FieldValueSet); serializar valores complexos para string
    all_raw = [
        {k: _serialize(v) for k, v in item.fields.properties.items()} for item in paged_items
    ]

    all_items = pd.DataFrame(all_raw, dtype=str).drop(
        columns=["parentReference", "__etag"],
        errors="ignore",
    )

    # Garante que todas as colunas do seu dicionário list_fields existam.
    # See: https://learn.microsoft.com/en-my/answers/questions/1347883/ms-graph-api-not-returning-spol-list-values-but-ca#:~:text=Response%20will%20not%20return%20object,select%20filter%20and%20sort%20operations
    for col_name in list_fields:
        if col_name not in all_items.columns:
            all_items[col_name] = None  # Cria a coluna vazia se a API a omitiu

    # Resolve datas (dd/MM vs MM/dd + fuso) ANTES do parse_by_schema. Quando há config,
    # essas colunas já saem como datetime64 e o parse_by_schema não as toca novamente.
    if datetime_config is not None:
        all_items = resolve_with_config(all_items, datetime_config)

    all_items = parse_by_schema(all_items, list_fields)

    return all_items


def download_sharepoint_file_with_graph_api(
    drive_path: str,
    site_url: str | None = None,
) -> bytes:
    """
    Baixa o conteúdo binário de um arquivo de uma document library (drive) do SharePoint
    via Microsoft Graph API.

    Diferente de `fetch_sharepoint_items_with_graph_api` (que lê itens de lista), esta função
    acessa o `drive` padrão do site e resolve o arquivo por caminho relativo à raiz da
    biblioteca (ex.: `Arquivos Melhorias/volumes.parquet`).

    Requer as variáveis de ambiente: `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`,
    `SHAREPOINT_CLIENT_SECRET`. Se não fornecidas, um `ValueError` será gerado.

    :param drive_path: Caminho do arquivo relativo à raiz da document library.
    :type drive_path: str

    :param site_url: URL do site SharePoint. Se `None`, usa a variável `SHAREPOINT_SITE_URL`.
    :type site_url: str | None

    :raises FileNotFoundError: Se o arquivo não existir na document library.

    :return: Conteúdo binário do arquivo.
    :rtype: bytes
    """
    if site_url is None:
        site_url = env("SHAREPOINT_SITE_URL")

    client = GraphClient(
        tenant=env("SHAREPOINT_TENANT_ID"),
    ).with_client_secret(
        env("SHAREPOINT_CLIENT_ID"),
        env("SHAREPOINT_CLIENT_SECRET"),
    )

    site = client.sites.get_by_url(site_url)
    drive_item = site.drive.root.get_by_path(drive_path)

    try:
        content = drive_item.get_content().execute_query()
    except ClientRequestException as exc:
        # 404/itemNotFound -> erro explícito; demais erros propagam intactos.
        if getattr(exc.response, "status_code", None) == 404:  # noqa: PLR2004
            raise FileNotFoundError(
                f"Arquivo '{drive_path}' não encontrado na document library de '{site_url}'."
            ) from exc
        raise

    data = content.value
    if not data:
        raise FileNotFoundError(f"Arquivo '{drive_path}' retornou conteúdo vazio em '{site_url}'.")

    log.info("Arquivo baixado: %s (%d MB) ✅", drive_path, len(data) / 1024 / 1024)
    return data
