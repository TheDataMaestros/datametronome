"""Turning a configured path into the S3 URI DuckDB scans."""


def quote_literal(value: str) -> str:
    """Single-quote a string for SQL, doubling any embedded quotes.

    Paths come from stave config. Without this a path containing a quote would
    end the literal and the rest would parse as SQL.
    """
    return "'" + value.replace("'", "''") + "'"


def scan_expression(bucket: str, path: str) -> str:
    """The FROM target for one configured table.

    DuckDB picks the reader from the extension itself, including globs and
    .gz/.zst compression, so there is no format table here.

    An absolute s3:// or gs:// URI in the config wins over the stave's bucket,
    so a single stave can span buckets when it has to.
    """
    uri = path if "://" in path else f"s3://{bucket}/{path.lstrip('/')}"
    return quote_literal(uri)
