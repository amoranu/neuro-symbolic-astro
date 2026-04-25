"""BirthDetails + ChartConfig (spec §5.1)."""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


# Recognized native-gender literals. None = unspecified (legacy /
# anonymous data). Classical Parashari karaka assignments are
# universally Sun=father / Moon=mother (BPHS Ch. 32) regardless of
# native gender; gender-asymmetric karakas are spouse (Venus for
# male, Jupiter for female) and a handful of progeny / intimate-
# relation queries. See `astroql.engine.karaka` for the full mapping.
_VALID_GENDERS = ("M", "F", None)


@dataclass
class BirthDetails:
    date: date
    time: Optional[str]
    tz: str
    lat: float
    lon: float
    time_accuracy: str = "exact"
    # Native gender — "M" / "F" / None (unspecified). Used by the
    # karaka resolver for queries whose karaka assignment is gender-
    # asymmetric (spouse, certain progeny configurations). Not used
    # by father / mother / longevity / career queries.
    gender: Optional[str] = None

    def __post_init__(self) -> None:
        if self.gender not in _VALID_GENDERS:
            raise ValueError(
                f"BirthDetails.gender must be one of "
                f"{_VALID_GENDERS!r}, got {self.gender!r}"
            )


@dataclass
class ChartConfig:
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"
    karaka_scheme: str = "7"
    dasha_systems: List[str] = field(
        default_factory=lambda: ["vimshottari"]
    )
    vargas: List[str] = field(default_factory=lambda: ["D1", "D9"])
