import numpy as np
import pandas as pd
from global_modules.sharepoint.sql_cast import build_select_with_cast, sa_type_to_duckdb
from office365.sharepoint.lists.list import List
from sqlalchemy import types as sa_types

__all__ = [
    "build_select_with_cast",
    "sa_type_to_duckdb",
]

EXCLUDE_FIELDS = (
    "Attachments,ItemChildCount,FolderChildCount,DocIcon,LinkTitle,"
    "LinkTitleNoMenu,Edit,ContentType,AppEditor,AppAuthor"
).split(",")


def get_columns(sp_list: List):
    fields = sp_list.fields.get().execute_query()

    field: dict[str, str]
    simple_fields: list[dict[str, str]] = []
    expand_fields: list[dict[str, str]] = []

    def _filter(x):
        return (
            (not x.hidden)
            and (not x.internal_name.startswith("_"))
            and (x.internal_name not in EXCLUDE_FIELDS)
        )

    view_fields = list(filter(_filter, fields))

    for f in view_fields:
        field = {
            "select": f.internal_name,
            "internal_name": f.internal_name,
            "display_name": f.title,
            "type": f.type_as_string,
        }  # type: ignore

        if f.type_as_string in {"Lookup", "User"}:
            field["select"] += "/Id"
            expand_fields.append(field)

        simple_fields.append(field)

    return simple_fields, expand_fields


def flatten_dict(d: dict, parent_key: str = "", sep: str = "_") -> dict:
    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def map_to_json(data):
    # type: (list[dict]) -> list[dict]

    return [flatten_dict(item) for item in data]


def parse_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    formats = ["%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"]
    df = df.copy()
    for col in columns:
        parsed = pd.to_datetime(df[col], utc=True, errors="coerce")
        if parsed.isna().any():
            original = df[col]
            for fmt in formats:
                fallback = pd.to_datetime(original, format=fmt, errors="coerce").dt.tz_localize(
                    "UTC"
                )
                parsed = parsed.fillna(fallback)
        df[col] = parsed
    return df


def parse_number(
    df: pd.DataFrame,
    schema: dict[str, sa_types.TypeEngine],
) -> pd.DataFrame:
    df = df.replace(["nan", "None"], np.nan)

    for col, col_type in schema.items():
        if col not in df.columns:
            continue

        if isinstance(col_type, sa_types.Integer):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            continue

        if isinstance(col_type, sa_types.Float):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _parse_bool_series(series: pd.Series) -> pd.Series:
    def _cast(v):
        if pd.isna(v) or v in {"nan", "None", ""}:
            return pd.NA
        if isinstance(v, bool):
            return v
        return str(v).lower() in {"true", "1"}

    return series.map(_cast).astype("boolean")


def _parse_dt_with(series: pd.Series, tz=False) -> pd.Series:
    # dayfirst=True evita o swap dd/MM vs MM/dd da inferência do pandas (Power Automate
    # manda dd/MM/yyyy). Para resolução por-campo com âncora, ver datetime_resolve.py.
    formats = ["%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"]
    parsed = pd.to_datetime(series, utc=tz, dayfirst=True, errors="coerce")
    if parsed.isna().any():
        for fmt in formats:
            if tz:
                fallback = pd.to_datetime(series, format=fmt, errors="coerce").dt.tz_localize("UTC")
            else:
                fallback = pd.to_datetime(series, format=fmt, errors="coerce")

            parsed = parsed.fillna(fallback)

    return parsed


def parse_by_schema(
    df: pd.DataFrame,
    schema: dict[str, sa_types.TypeEngine],
) -> pd.DataFrame:
    """Converte colunas do DataFrame conforme os tipos SQLAlchemy definidos em `schema`."""
    df = df.copy()
    df = df.replace(["nan", "None"], np.nan)

    for col, col_type in schema.items():
        if col not in df.columns:
            continue

        if isinstance(col_type, type):
            col_type = col_type()  # noqa: PLW2901

        # Colunas já resolvidas por resolve_datetimes (datetime64) não são reprocessadas.
        if isinstance(col_type, (sa_types.DateTime, sa_types.Date)) and (
            pd.api.types.is_datetime64_any_dtype(df[col])
        ):
            continue

        if isinstance(col_type, sa_types.Boolean):
            df[col] = _parse_bool_series(df[col])
        elif isinstance(col_type, sa_types.Integer):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif isinstance(col_type, sa_types.Numeric):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif isinstance(col_type, sa_types.DateTime):
            if col_type.timezone:
                df[col] = _parse_dt_with(df[col], tz=True)
            else:
                df[col] = _parse_dt_with(df[col], tz=False)
        elif isinstance(col_type, sa_types.Date):
            df[col] = _parse_dt_with(df[col], tz=False)

    return df
