from airflow.utils.log.logging_mixin import LoggingMixin

log = LoggingMixin().log


def log_message(message: str):
    log.info(message)
