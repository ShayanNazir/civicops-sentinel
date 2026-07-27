from dataclasses import dataclass

from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from app.integrations.nyc_boundaries.schemas import (
    CensusTractFeature,
)


@dataclass(frozen=True, slots=True)
class NYCGeography:
    """Geographic context resolved for one coordinate."""

    census_tract_geoid: str
    census_tract_code: str
    census_tract_label: str
    borough_tract_code: str
    borough_code: str
    borough_name: str
    nta_code: str | None
    nta_name: str | None
    cdta_code: str | None
    cdta_name: str | None


@dataclass(frozen=True, slots=True)
class BoundaryRecord:
    """Internal association between geometry and metadata."""

    geometry: BaseGeometry
    geography: NYCGeography


class NYCBoundaryIndex:
    """In-memory spatial index over NYC census-tract boundaries."""

    def __init__(
        self,
        features: list[CensusTractFeature],
    ) -> None:
        records: list[BoundaryRecord] = []

        for feature in features:
            geometry = shape(feature.geometry)

            if not geometry.is_valid:
                geometry = make_valid(geometry)

            if geometry.is_empty:
                continue

            properties = feature.properties

            geography = NYCGeography(
                census_tract_geoid=properties.geoid,
                census_tract_code=properties.ct2020,
                census_tract_label=properties.ctlabel,
                borough_tract_code=properties.boroct2020,
                borough_code=properties.borocode,
                borough_name=properties.boroname,
                nta_code=properties.nta2020,
                nta_name=properties.ntaname,
                cdta_code=properties.cdta2020,
                cdta_name=properties.cdtaname,
            )

            records.append(
                BoundaryRecord(
                    geometry=geometry,
                    geography=geography,
                )
            )

        if not records:
            raise ValueError("No usable NYC boundary features were provided")

        self._records = tuple(records)
        self._geometries = [record.geometry for record in self._records]
        self._tree = STRtree(self._geometries)

    @property
    def size(self) -> int:
        """Return the number of indexed boundary records."""

        return len(self._records)

    def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> NYCGeography | None:
        """Resolve a latitude and longitude to NYC geography."""

        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        # Shapely uses x, y ordering: longitude first, latitude second.
        point = Point(longitude, latitude)

        matches: list[NYCGeography] = []

        for candidate_index in self._tree.query(point):
            record = self._records[int(candidate_index)]

            # covers() also handles points lying directly on a boundary.
            if record.geometry.covers(point):
                matches.append(record.geography)

        if not matches:
            return None

        # A point exactly on a shared border may match multiple polygons.
        # Use the GEOID to produce a deterministic result.
        return min(
            matches,
            key=lambda geography: geography.census_tract_geoid,
        )
