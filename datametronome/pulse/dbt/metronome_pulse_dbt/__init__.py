"""dbt artifact connector for DataMetronome — read-only metadata access."""

from .connector import DbtReadonlyPulse

__version__ = "0.1.0"
__all__ = ["DbtReadonlyPulse"]
