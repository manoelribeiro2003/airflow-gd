import argparse
import sys
from os import getenv
from pprint import pprint

from dotenv import load_dotenv
from office365.graph_client import GraphClient

# from office365.sharepoint.fields. import  ColumnDefinitionCollection
load_dotenv()


def show_columns(
    site_url: str | None = None,
    list_name: str | None = None,
):
    # Fallback para variáveis de ambiente se os argumentos forem None
    site_url = site_url or getenv("SHAREPOINT_SITE_URL")
    list_name = list_name or getenv("SHAREPOINT_LIST_NAME")

    if not site_url or not list_name:
        pprint("❌ Erro: site_url e list_name precisam ser definidos via args ou .env")
        sys.exit(1)

    client = GraphClient(
        tenant=getenv("SHAREPOINT_TENANT_ID", ""),
    ).with_client_secret(
        getenv("SHAREPOINT_CLIENT_ID", ""),
        getenv("SHAREPOINT_CLIENT_SECRET", ""),
    )

    print(f"🔍 Buscando colunas em: {list_name}...")

    site = client.sites.get_by_url(site_url)
    sp_list = site.lists.get_by_name(list_name)

    return sp_list.columns.get().execute_query()


def main():
    parser = argparse.ArgumentParser(description="Lista colunas de uma lista SharePoint")

    # Tornando os argumentos opcionais no terminal: se não passar, usa o env
    parser.add_argument("--site", help="URL do site SharePoint")
    parser.add_argument("--list", help="Nome da lista")
    parser.add_argument("--json", help="Saida em json", default=False, action="store_true")

    args = parser.parse_args()

    try:
        columns = show_columns(site_url=args.site, list_name=args.list)

        print(f"\033[1;32m{'NOME INTERNO':<35} | {'NOME DE EXIBIÇÃO'}\033[0m")
        pprint("-" * 70)

        if args.json:
            print({col.name: col.display_name for col in columns})
            return

        for col in columns:
            # Formatação simples e nativa
            print(f"{col.name:<35} | {col.display_name}")

    except Exception as e:
        print(f"❌ Falha na conexão: {e}")


if __name__ == "__main__":
    main()
