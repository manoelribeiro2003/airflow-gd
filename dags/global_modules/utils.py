from pathlib import Path

DUCKDB_THREADS = 3
DUCKDB_SAVE_PARQUET_CONFIG: dict[str, str | bool | int | float | list[str]] = {
    # "threads": 3,
    "preserve_insertion_order": False,
    # "memory_limit": "3GB",
}

GLOBAL_FILES_PATH = Path(__file__).parents[1].joinpath("global_files")


def get_parquet_file(sufixo: str, root_path: str):
    """
    Facilita o criação de arquivos `.parquet`.

    :param sufixo: Sufixo para compor o final do nome do arquivo.
    :type sufixo: str
    :param root_path: Caminho da pasta para colocar o arquivo. Se for um arquivo,
        será considerado a pasta deste.
    :type root_path: str
    :return: `Path` que representa o arquivo `.parquet`
    :rtype: Path
    """
    file = get_path_file(f"extract_data_{str(sufixo)}.parquet", root_path)
    return file


def get_sentinel_file(name: str, root_path: str) -> Path:
    """
    Facilita a criação de arquivos sentinela `.finished` para controle de idempotência.

    :param name: Nome lógico do passo (ex: "copy_to_stage").
    :type name: str
    :param root_path: Caminho da pasta ou arquivo de referência.
    :type root_path: str
    :return: `Path` que representa o arquivo sentinela `.finished`
    :rtype: Path
    """
    return get_path_file(f"{name}.finished", root_path)


def get_path_file(name: str, root_path: str) -> Path:
    f = Path(root_path)
    root_dir = f.parent if f.is_file() else f
    return root_dir / name


# reads the sql file and returns the query
def read_sql_file(filename: str, root_path: str):
    """
    Recupera o conteúdo de um arquivo que está em uma pasta `sql_files`.

    :param filename: Nome do arquivo `sql`.
    :type filename: str
    :param root_path: Caminho da pasta onde a pasta `sql_files` está. Se for um arquivo,
        será considerado a pasta deste.
    :type root_path: str
    :return: O conteúdo do arquivo.
    :rtype: str
    """
    f = Path(root_path)
    root_dir = f.parent if f.is_file() else f
    sql_file = root_dir.joinpath("sql_files", filename)

    if not sql_file.exists():
        raise ValueError(f"O arquivo '{sql_file.resolve()}' não existe.")

    return sql_file.read_text()
