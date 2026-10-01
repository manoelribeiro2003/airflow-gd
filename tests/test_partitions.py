"""Testes do cálculo de limites das partições mensais."""

from datetime import date, datetime

import pytest
from global_modules.partitions import monthly_partition_bounds


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (date(2026, 3, 15), (date(2026, 3, 1), date(2026, 4, 1))),
        (date(2026, 1, 1), (date(2026, 1, 1), date(2026, 2, 1))),
        (date(2026, 1, 31), (date(2026, 1, 1), date(2026, 2, 1))),
        (date(2026, 12, 31), (date(2026, 12, 1), date(2027, 1, 1))),
        (date(2028, 2, 29), (date(2028, 2, 1), date(2028, 3, 1))),
    ],
)
def test_monthly_partition_bounds_cobre_o_mes_da_referencia(reference, expected):
    assert monthly_partition_bounds(reference) == expected


def test_monthly_partition_bounds_aceita_datetime_e_devolve_date():
    start, end = monthly_partition_bounds(datetime(2026, 12, 20, 23, 59))

    assert (start, end) == (date(2026, 12, 1), date(2027, 1, 1))
    assert type(start) is date
    assert type(end) is date
