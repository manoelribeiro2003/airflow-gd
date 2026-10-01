from typing import Any

from airflow.exceptions import AirflowException
from airflow.providers.common.sql.sensors.sql import SqlSensor


class CustomSqlSensor(SqlSensor):
    """
    Override function poke() to show results from a specific query and validate:

    Show query results and validate a count of states and end date.

    - state = 0 no result was found
    - end_date = None, the target dag has not ended yet.
    """

    def poke(self, context: Any) -> bool:
        hook = self._get_hook()
        self.log.info("Poking: %s (with parameters %s)", self.sql, self.parameters)

        records = hook.get_records(self.sql, self.parameters)

        self.log.info("Results from query: %s", records)

        if not records:
            if self.fail_on_empty:
                raise AirflowException("No rows returned, raising as per fail_on_empty flag")
            return False

        # 🔁 validações
        validation = [row for row in records if 0 in row]
        wait_for_completion = [row for row in records if None in row]

        # 🔁 failure callback
        if self.failure:
            if not callable(self.failure):
                raise AirflowException(f"failure is present, but not callable -> {self.failure}")
            if self.failure(records):
                raise AirflowException(f"Failure criteria met. failure({records}) returned True")

        # 🔁 success callback
        if self.success:
            if not callable(self.success):
                raise AirflowException(f"success is present, but not callable -> {self.success}")
            return bool(self.success(records))

        # 🔁 regra principal
        if not wait_for_completion:
            if not validation:
                return True

            raise AirflowException(
                f"The dag(s) {validation} were not executed in the specific period."
            )

        return False
