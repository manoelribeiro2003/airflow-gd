FROM apache/airflow:2.10.5-python3.12

USER root

ENV SSL_CONFIG="/\[openssl_init\]/!b;n;cssl_conf = ssl_sect\n\n[ssl_sect]\nsystem_default = tls_sect\n\n[tls_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT:@SECLEVEL=0"

RUN apt-get update && apt-get install -y \
  curl \
  gnupg2 \
  iputils-ping \
  sed && \
  # Nescessário para conseguir conectar no SQL Server 2008 no Debian 12.
  sed -i "${SSL_CONFIG}" /etc/ssl/openssl.cnf && \
  # Instalar as dependências do sistema para o driver do SQL Server
  curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc && \
  curl https://packages.microsoft.com/config/debian/11/prod.list | tee /etc/apt/sources.list.d/mssql-release.list && \
  apt-get update && \
  ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools && \
  # Definir o fuso horário para América/Fortaleza
  echo "America/Fortaleza" > /etc/timezone && \
  # limpar o cache
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Definir o fuso horário para América/Fortaleza
ENV TZ=America/Fortaleza

ENV PATH="$PATH:/opt/mssql-tools/bin"

USER airflow

RUN python -m pip install --upgrade pip && \
  pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" \
  apache-airflow-providers-microsoft-mssql[common.sql] \
  pyodbc \
  office365-rest-python-client \
  duckdb \
  connectorx \
  openpyxl \
  dbt-core==1.8.9 \
  dbt-sqlserver==1.8.7 && \
  python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL mssql FROM community'); con.close()" && \
  # Quando instalamos lib do ddb, ele vai precisar de permissão para
  # usar a pasta e precisa de permissão.
  chmod -R 777 /home/airflow/.duckdb/
