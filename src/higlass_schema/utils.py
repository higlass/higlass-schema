from typing import Any, Dict, TypeVar

from pydantic import BaseModel, schema_of


def simplify_schema(root_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Lift defintion reference to root if only definition"""
    # type of root is not a reference to a definition
    if "$ref" not in root_schema:
        return root_schema

    defs = list(root_schema["definitions"].values())
    if len(defs) != 1:
        return root_schema

    return defs[0]


## Schema modifiers
ModelT = TypeVar("ModelT", bound=BaseModel)


def exclude_properties_titles(schema: Dict[str, Any]) -> None:
    """Remove automatically generated tiles for pydantic classes."""
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)


def get_schema_of(type_: Any):
    schema = schema_of(type_)
    schema = simplify_schema(schema)
    exclude_properties_titles(schema)
    # remove autogenerated title
    schema.pop("title")
    return schema


def simplify_enum_schema(schema: Dict[str, Any]):
    # reduce union of enums into single enum
    if "anyOf" in schema:
        enum = []
        for entry in schema["anyOf"]:
            assert "enum" in entry
            enum.extend(entry["enum"])
        return {"enum": enum}

    enum = schema["enum"]

    # if there is only one enum entry, make it a const
    if len(enum) == 1:
        return {"const": enum[0]}

    return {"enum": enum}
