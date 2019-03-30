"""Base target."""
import abc
from typing import Any, Dict, Optional

from marshmallow import ValidationError


class BaseTarget(metaclass=abc.ABCMeta):
    """Base target."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self.valid_data: Dict[str, Any] = {}
        self.validation_error: Optional[ValidationError] = None

    @abc.abstractmethod
    def process(self) -> bool:
        """Process the target data."""
        pass

    @property
    def unique_key(self):
        """Unique key for the data, based on the ID that was set by the caller."""
        return f"(^{self.valid_data['id']})"
