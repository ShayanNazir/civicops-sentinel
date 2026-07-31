from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CensusTractProperties(BaseModel):
    """Validated properties attached to an NYC census-tract feature."""

    geoid: str
    ct2020: str
    ctlabel: str
    boroct2020: str
    borocode: str
    boroname: str

    nta2020: str | None = None
    ntaname: str | None = None
    cdta2020: str | None = None
    cdtaname: str | None = None

    model_config = ConfigDict(extra="ignore")


class CensusTractFeature(BaseModel):
    """One census-tract feature from an NYC GeoJSON response."""

    type: Literal["Feature"]
    geometry: dict[str, Any]
    properties: CensusTractProperties


class CensusTractFeatureCollection(BaseModel):
    """GeoJSON collection returned by NYC Open Data."""

    type: Literal["FeatureCollection"]
    features: list[CensusTractFeature] = Field(default_factory=list)
