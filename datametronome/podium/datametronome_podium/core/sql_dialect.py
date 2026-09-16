"""What actually differs between data sources when building check SQL.

Every check used to carry its own ``if postgres ... elif sqlite ... elif
bigquery ... else unsupported`` chain. Most arms were byte-identical copies of
each other, the chains disagreed with one another about which sources a check
supported, and adding a source meant finding all seven and editing each.

Three things vary, and nothing else: identifier quoting, counting rows that
match a condition, and matching a regular expression. They are templates here,
one row per source, so adding a source is one entry and no branching.
"""

from __future__ import annotations

from dataclasses import dataclass

from datametronome_podium.core.query import quote_identifier


def quote_literal(value) -> str:
    """Single-quote a string literal, doubling embedded quotes.

    Check config is editor-supplied and these values are interpolated into
    generated SQL rather than bound as parameters. An unescaped quote ends the
    literal and the rest parses as SQL.
    """
    return "'" + str(value).replace("'", "''") + "'"


@dataclass(frozen=True)
class Dialect:
    """SQL generation rules for one kind of data source."""

    name: str
    quote_style: str = "ansi"
    count_if: str = "COUNT(CASE WHEN {cond} THEN 1 END)"
    #: None where the source cannot match regular expressions at all
    regex: str | None = "{col} ~ {pattern}"

    def quote(self, identifier: str) -> str:
        return quote_identifier(identifier, dialect=self.quote_style)

    def counted(self, condition: str) -> str:
        """Count the rows where condition holds."""
        return self.count_if.format(cond=condition)

    @property
    def supports_regex(self) -> bool:
        return self.regex is not None

    def matches(self, column: str, pattern: str) -> str:
        """A boolean expression: does column match pattern?"""
        if self.regex is None:
            raise ValueError(f"{self.name} has no regular expression support")
        return self.regex.format(col=column, pattern=quote_literal(pattern))

    def in_list(self, column: str, values) -> str:
        """A boolean expression: is column one of values?"""
        return f"{column} IN ({', '.join(quote_literal(v) for v in values)})"


# One row per data source. Everything not named here is unsupported, and the
# check layer says so in one place rather than in seven different else arms.
DIALECTS: dict[str, Dialect] = {
    "postgres": Dialect("postgres"),
    "postgresql": Dialect("postgresql"),
    # Redshift forked from PostgreSQL 8.0 and kept the ~ operator.
    "redshift": Dialect("redshift"),
    "mysql": Dialect("mysql", regex="{col} REGEXP {pattern}"),
    # SQLite's REGEXP is an optional extension that is usually absent.
    "sqlite": Dialect("sqlite", regex=None),
    "bigquery": Dialect(
        "bigquery",
        quote_style="bigquery",
        count_if="COUNTIF({cond})",
        # The r prefix stops BigQuery reading backslashes in the pattern as
        # string escapes before the regex engine sees them.
        regex="REGEXP_CONTAINS({col}, r{pattern})",
    ),
    # s3 staves run on DuckDB, which has no ~ operator.
    "s3": Dialect("s3", regex="regexp_matches({col}, {pattern})"),
}


def dialect_for(data_source_type: str | None) -> Dialect | None:
    """The dialect for a stave's type, or None if checks cannot run against it."""
    return DIALECTS.get((data_source_type or "").lower())
