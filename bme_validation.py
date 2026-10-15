"""Validation for canonical Bosch collection sessions."""

from typing import List

from bme_model import SessionModel


class SessionValidationError(ValueError):
    """Raised when a collection session violates its schema."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_session(session: SessionModel) -> None:
    """Validate measurement structure without judging Bosch configuration."""
    errors = []
    columns = session.measurements.columns
    column_names = [column.name for column in columns]
    data = session.measurements.data

    if len(column_names) != len(set(column_names)):
        errors.append("Measurement column names are not unique")

    missing_columns = [
        name for name in column_names if name not in data.columns
    ]
    if missing_columns:
        errors.append(
            "Measurement data is missing columns: " + ", ".join(missing_columns)
        )

    if errors:
        raise SessionValidationError(errors)
