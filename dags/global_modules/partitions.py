from datetime import date, timedelta


def monthly_partition_bounds(reference: date) -> tuple[date, date]:
    """Limites [início, fim) da partição mensal que contém `reference`."""
    start = date(reference.year, reference.month, 1)
    # Dia 1 + 32 dias sempre cai no mês seguinte, qualquer que seja o tamanho do mês.
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end
