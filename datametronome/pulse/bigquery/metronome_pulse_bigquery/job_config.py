"""BigQuery QueryJobConfig helpers for positional and named parameters."""

from typing import Any

from google.cloud import bigquery  # type: ignore


def build_query_job_config(
    positional: list[Any] | None = None,
    named: dict[str, Any] | None = None,
):
    """Build job config for client.query().

    Use **named** when SQL uses ``@param`` (e.g. ``LIMIT @lim``). Use **positional**
    for legacy anonymous parameters (ScalarQueryParameter with name None).
    """
    query_parameters: list = []

    if named:
        for pname, val in named.items():
            if isinstance(val, bool):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "BOOL", val)
                )
            elif isinstance(val, int):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "INT64", val)
                )
            elif isinstance(val, float):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "FLOAT64", val)
                )
            elif isinstance(val, str):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "STRING", val)
                )
            elif val is None:
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "STRING", None)
                )
            else:
                query_parameters.append(
                    bigquery.ScalarQueryParameter(pname, "STRING", str(val))
                )
    elif positional:
        for param in positional:
            if isinstance(param, bool):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "BOOL", param)
                )
            elif isinstance(param, int):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "INT64", param)
                )
            elif isinstance(param, float):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "FLOAT64", param)
                )
            elif isinstance(param, str):
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "STRING", param)
                )
            elif param is None:
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "STRING", None)
                )
            else:
                query_parameters.append(
                    bigquery.ScalarQueryParameter(None, "STRING", str(param))
                )

    if not query_parameters:
        return None
    return bigquery.QueryJobConfig(query_parameters=query_parameters)
