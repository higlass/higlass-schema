from __future__ import annotations

import json
from collections import OrderedDict
from typing import (
    Any,
    Dict,
    Generator,
    Generic,
    Literal,
    Tuple,
    TypeVar,
    Union,
)

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Extra, Field
from pydantic.class_validators import root_validator
from pydantic.generics import GenericModel as PydanticGenericModel
from typing_extensions import Annotated, TypedDict

from .utils import exclude_properties_titles, get_schema_of, simplify_enum_schema


# Override Basemodel
class BaseModel(PydanticBaseModel):
    class Config:
        # wether __setattr__ should perform validation
        validate_assignment = True
        # exclude titles by defualt
        schema_extra = staticmethod(lambda s, _: exclude_properties_titles(s))

    # nice repr if printing with rich
    def __rich_repr__(self):
        return iter(self)

    def dict(self, exclude_none: bool = True, **kwargs):
        return super().dict(exclude_none=exclude_none, **kwargs)

    def json(self, exclude_none: bool = True, **kwargs):
        return super().json(exclude_none=exclude_none, **kwargs)


# Override Defaults for generic models
class GenericModel(PydanticGenericModel):
    class Config:
        # wether __setattr__ should perform validation
        validate_assignment = True
        # exclude titles by defualt
        schema_extra = staticmethod(lambda s, _: exclude_properties_titles(s))

    # nice repr if printing with rich
    def __rich_repr__(self):
        return iter(self)

    def dict(self, exclude_none: bool = True, **kwargs):
        return super().dict(exclude_none=exclude_none, **kwargs)

    def json(self, exclude_none: bool = True, **kwargs):
        return super().json(exclude_none=exclude_none, **kwargs)


##################################################
# General                                        #
##################################################

Domain = Tuple[float, float]


class OverlayOptions(BaseModel):
    extent: list[list[int]] | None = None
    minWidth: float | None = None
    fill: str | None = None
    fillOpacity: float | None = None
    stroke: str | None = None
    strokeOpacity: float | None = None
    strokeWidth: float | None = None
    strokePos: str | list[str] | None = None
    outline: str | None = None
    outlineOpacity: float | None = None
    outlineWidth: float | None = None
    outlinePos: str | list[str] | None = None


class Overlay(BaseModel):
    type: str | None = None
    uid: str | None = None
    chromInfoPath: str | None = None
    includes: list[str] | None = None
    options: OverlayOptions | None = None


##################################################
# Locks                                          #
##################################################


# Locks are tricky to describe with python's type system
# because _some_ keys are static (e.g., the lock `uid`) while
# the rest of the keys are dynamic (the view uids) and
# satisfy a different type constraint.
#
# In JSON schema, this is type can be described using an "object"
# "type" with "additionalProperties" or "patternProperties" field.
#
# ```json
# {
#   "type": "object",
#   "properties": {
#     "uid": { "type: "string" }
#   },
#   "additionalProperties": {
#     "type": "array",
#     "minLength": 3,
#     "maxLength": 3,
#     "items": [
#       { "type": "number" },
#       { "type": "number" },
#       { "type": "number" }
#     ]
#   }
# }
# ```
#
# The lock classes implement pydantic Models which:
#
# (1) Performs the appropriate validation/serde for this object
#
# (2) Exports the appropriate JSON schema using "additionalProperties"
#     field via a custom `schema_extra` extension.
#
# This could probably be implemented generally with
# pydantic.generics.Generic/typing.Generic, but we implement
# concretely for the different lock types.


LockEntry = Tuple[float, float, float]


# We'd rather have tuples in our final model, because a
# __root__ model is clunky from a python user perspective.
# We create this class to get validation for free in `root_validator`
class _LockEntryModel(BaseModel):
    __root__: LockEntry


class Lock(BaseModel):
    uid: str | None = None

    class Config:
        extra = Extra.allow

        @staticmethod
        def schema_extra(schema: dict[str, Any], _) -> None:
            exclude_properties_titles(schema)
            schema["additionalProperties"] = get_schema_of(LockEntry)

    def __iter__(self) -> Generator[tuple[str, LockEntry], None, None]:
        for key, val in super().__iter__():
            if key not in self.__fields__:
                yield key, val

    # can only validate on creation for "extra" fields
    @root_validator(pre=True)
    def validate_locks(cls, values: dict[str, Any]):
        for k in values:
            if k not in cls.__fields__:
                # validate using our custom validator
                model = _LockEntryModel.parse_obj(values[k])
                # get back the root type
                values[k] = model.__root__
        return values


class ValueScaleLockEntry(TypedDict):
    view: str
    track: str


class _ValueScaleLockEntryModel(BaseModel):
    __root__: ValueScaleLockEntry


class ValueScaleLock(BaseModel):
    uid: str | None = None
    ignoreOffScreenValues: bool | None = None

    class Config:
        extra = Extra.allow

        @staticmethod
        def schema_extra(schema: dict[str, Any], _) -> None:
            exclude_properties_titles(schema)
            schema["additionalProperties"] = get_schema_of(ValueScaleLockEntry)

    def __iter__(self) -> Generator[tuple[str, ValueScaleLockEntry], None, None]:
        for key, val in super().__iter__():
            if key not in self.__fields__:
                yield key, val

    # can only validate on creation for "extra" fields
    @root_validator(pre=True)
    def validate_locks(cls, values: dict[str, Any]):
        for k in values:
            if k not in cls.__fields__:
                # validate using our custom validator
                model = _ValueScaleLockEntryModel.parse_obj(values[k])
                # read back as a regular dict
                values[k] = model.__root__
        return values


class AxisSpecificLock(BaseModel):
    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], _: Any) -> None:
            exclude_properties_titles(schema)
            schema["properties"]["axis"] = simplify_enum_schema(
                schema["properties"]["axis"]
            )

    axis: Literal["x", "y"]
    lock: str


class AxisSpecificLocks(BaseModel):
    x: AxisSpecificLock | None = None
    y: AxisSpecificLock | None = None


class LocationLocks(BaseModel):
    locksByViewUid: dict[str, str | AxisSpecificLocks] = Field(
        default_factory=dict
    )
    locksDict: dict[str, Lock] = Field(default_factory=dict)


class ZoomLocks(BaseModel):
    class Config:
        extra = Extra.forbid

    locksByViewUid: dict[str, str] = Field(default_factory=dict)
    locksDict: dict[str, Lock] = Field(default_factory=dict)


class ValueScaleLocks(BaseModel):
    class Config:
        extra = Extra.forbid

    locksByViewUid: dict[str, str] = Field(default_factory=dict)
    locksDict: dict[str, ValueScaleLock] = Field(default_factory=dict)


##################################################
# Tracks                                         #
##################################################

TrackTypeT = TypeVar("TrackTypeT", bound=str)
TrackOptions = Dict[str, Any]
TilesetInfo = Dict[str, Any]
Tile = Dict[str, Any]


class Data(BaseModel):
    type: str | None = None
    url: str | None = None
    server: str | None = None
    filetype: str | None = None
    children: list | None = None
    tilesetInfo: TilesetInfo | None = None
    tiles: Tile | None = None


class BaseTrack(GenericModel, Generic[TrackTypeT]):
    class Config:
        extra = Extra.allow

        @staticmethod
        def schema_extra(schema: dict[str, Any], _: Any) -> None:
            exclude_properties_titles(schema)
            props = schema["properties"]
            if "enum" in props["type"] or "allOf" in props["type"]:
                props["type"] = simplify_enum_schema(props["type"])

    type: TrackTypeT
    uid: str | None = None
    width: int | None = None
    height: int | None = None
    options: TrackOptions | None = None


class Tileset(BaseModel):
    tilesetUid: str | None = None
    server: str | None = None


ViewportProjectionTrackType = Literal[
    "viewport-projection-center",
    "viewport-projection-vertical",
    "viewport-projection-horizontal",
]

EnumTrackType = Union[
    ViewportProjectionTrackType,
    Literal[
        "multivec",
        "1d-heatmap",
        "line",
        "point",
        "bar",
        "divergent-bar",
        "stacked-interval",
        "gene-annotations",
        "linear-2d-rectangle-domains",
        "chromosome-labels",
        "linear-heatmap",
        "1d-value-interval",
        "2d-annotations",
        "2d-chromosome-annotations",
        "2d-chromosome-grid",
        "2d-chromosome-labels",
        "2d-rectangle-domains",
        "2d-tiles",
        "arrowhead-domains",
        "bedlike",
        "cross-rule",
        "dummy",
        "horizontal-1d-annotations",
        "horizontal-1d-heatmap",
        "horizontal-1d-tiles",
        "horizontal-1d-value-interval",
        "horizontal-2d-rectangle-domains",
        "horizontal-bar",
        "horizontal-chromosome-grid",
        "horizontal-chromosome-labels",
        "horizontal-divergent-bar",
        "horizontal-gene-annotations",
        "horizontal-heatmap",
        "horizontal-line",
        "horizontal-multivec",
        "horizontal-point",
        "horizontal-rule",
        "horizontal-vector-heatmap",
        "image-tiles",
        "left-axis",
        "left-stacked-interval",
        "mapbox-tiles",
        "osm-2d-tile-ids",
        "osm-tiles",
        "raster-tiles",
        "simple-svg",
        "square-markers",
        "top-axis",
        "top-stacked-interval",
        "vertical-1d-annotations",
        "vertical-1d-heatmap",
        "vertical-1d-tiles",
        "vertical-1d-value-interval",
        "vertical-2d-rectangle-domains",
        "vertical-bar",
        "vertical-bedlike",
        "vertical-chromosome-grid",
        "vertical-chromosome-labels",
        "vertical-gene-annotations",
        "vertical-heatmap",
        "vertical-line",
        "vertical-multivec",
        "vertical-point",
        "vertical-rule",
        "vertical-vector-heatmap",
    ],
]


class EnumTrack(BaseTrack[EnumTrackType], Tileset):
    class Config:
        extra = Extra.ignore

    data: Data | None = None
    chromInfoPath: str | None = None
    fromViewUid: str | None = None
    x: float | None = None
    y: float | None = None


class HeatmapTrack(BaseTrack[Literal["heatmap"]], Tileset):
    class Config:
        extra = Extra.ignore

    data: Data | None = None
    position: str | None = None
    transforms: list | None = None


class IndependentViewportProjectionTrack(BaseTrack[ViewportProjectionTrackType]):
    class Config:
        extra = Extra.ignore

    fromViewUid: None = None
    projectionXDomain: Domain | None = None
    projectionYDomain: Domain | None = None
    transforms: list | None = None
    x: float | None = None
    y: float | None = None


class CombinedTrack(BaseTrack[Literal["combined"]]):
    class Config:
        extra = Extra.ignore

    contents: list[Track]
    position: str | None = None


Track = Union[
    EnumTrack,
    CombinedTrack,
    HeatmapTrack,
    IndependentViewportProjectionTrack,
    BaseTrack,
]

# CombinedTrack is recursive and needs delayed evaluation of annoations
CombinedTrack.update_forward_refs()


##################################################
# View                                           #
##################################################


TrackT = TypeVar("TrackT", bound=Track)

TrackPosition = Literal["left", "right", "top", "bottom", "center", "whole", "gallery"]


class Tracks(GenericModel, Generic[TrackT]):
    """Track layout within a View."""

    class Config:
        extra = Extra.ignore

    left: list[TrackT] | None = None
    right: list[TrackT] | None = None
    top: list[TrackT] | None = None
    bottom: list[TrackT] | None = None
    center: list[TrackT] | None = None
    whole: list[TrackT] | None = None
    gallery: list[TrackT] | None = None

    def __iter__(self) -> Generator[tuple[TrackPosition, TrackT], None, None]:
        for pos, tlist in super().__iter__():
            if tlist is None:
                continue
            for track in tlist:
                yield pos, track  # type: ignore


class Layout(BaseModel):
    """Size and position of a View."""

    class Config:
        extra = Extra.ignore

    x: int = Field(default=0, description="The X Position")
    y: int = Field(default=0, description="The Y Position")
    w: int = Field(default=12, description="Width")
    h: int = Field(default=12, description="Height")
    moved: bool | None = None
    static: bool | None = None


class GenomePositionSearchBox(BaseModel):
    """Locations to search within a View."""

    autocompleteServer: str | None = Field(
        default=None,
        examples=["//higlass.io/api/v1"],
        description="The Autocomplete Server URL",
    )
    autocompleteId: str | None = Field(
        default=None,
        examples=["OHJakQICQD6gTD7skx4EWA"],
        description="The Autocomplete ID",
    )
    chromInfoServer: str | None = Field(
        default=None,
        examples=["//higlass.io/api/v1"],
        description="The Chrominfo Server URL",
    )
    chromInfoId: str | None = Field(
        default=None,
        examples=["hg19"],
        description="The Chromosome Info ID",
    )
    visible: bool | None = Field(
        default=None,
        description="The Visible Schema",
    )


class View(GenericModel, Generic[TrackT]):
    """An arrangment of Tracks to display within a given Layout."""

    class Config:
        extra = Extra.forbid

    layout: Layout
    tracks: Tracks[TrackT]
    uid: str | None = None
    autocompleteSource: str | None = None
    chromInfoPath: str | None = None
    genomePositionSearchBox: GenomePositionSearchBox | None = None
    genomePositionSearchBoxVisible: bool | None = None
    initialXDomain: Domain | None = None
    initialYDomain: Domain | None = None
    overlays: list[Overlay] | None = None
    selectionView: bool | None = None
    zoomFixed: bool | None = None
    zoomLimits: tuple[float, float | None] = (1, None)


##################################################
# Viewconf                                       #
##################################################

ViewT = TypeVar("ViewT", bound=View)


class Viewconf(GenericModel, Generic[ViewT]):
    """Root object describing a HiGlass visualization."""

    class Config:
        extra = Extra.forbid
        title = "HiGlass viewconf"

        @staticmethod
        def schema_extra(schema: dict[str, Any], _) -> None:
            exclude_properties_titles(schema)
            # manually add minItems for views
            # because pydantic.conlist breaks generics and Annotated
            # fields don't added
            for prop in ["views"]:
                schema["properties"][prop]["minItems"] = 1

    editable: bool | None = True
    viewEditable: bool | None = True
    tracksEditable: bool | None = True
    zoomFixed: bool | None = None
    compactLayout: bool | None = None
    exportViewUrl: str | None = None
    trackSourceServers: list[str] | None = None
    views: Annotated[list[ViewT], Field(min_items=1)] | None = None
    zoomLocks: ZoomLocks | None = None
    locationLocks: LocationLocks | None = None
    valueScaleLocks: ValueScaleLocks | None = None
    chromInfoPath: str | None = None


def schema():
    root = Viewconf.schema()

    # remove titles in defintions
    for d in root["definitions"].values():
        d.pop("title", None)

    # nice ordering, insert additional metadata
    ordered_root = OrderedDict(
        [
            ("$schema", "http://json-schema.org/draft-07/schema#"),
            ("$id", "https://higlass.io/#viewconf"),
            *root.items(),
        ]
    )

    return dict(ordered_root)


def schema_json(**kwargs):
    return json.dumps(schema(), **kwargs)
