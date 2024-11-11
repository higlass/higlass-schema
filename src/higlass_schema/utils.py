from typing import Any, Dict, TypeVar

import pydantic_core.core_schema as core_schema
from pydantic import BaseModel, TypeAdapter
from pydantic._internal._core_utils import CoreSchemaOrField, is_core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue


class _GenerateJsonSchema(GenerateJsonSchema):
    def field_title_should_be_set(self, schema: CoreSchemaOrField) -> bool:
        return_value = super().field_title_should_be_set(schema)
        if return_value and is_core_schema(schema):
            return False
        return return_value

    def nullable_schema(self, schema: core_schema.NullableSchema) -> JsonSchemaValue:
        inner_json_schema = self.generate_inner(schema["schema"])
        # ignore the nullable
        return inner_json_schema

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        if schema.get("default") is None:
            return self.generate_inner(schema["schema"])
        return super().default_schema(schema)

    def union_schema(self, schema: core_schema.UnionSchema) -> JsonSchemaValue:
        return super().union_schema(schema)

    def generate(
        self, schema: core_schema.CoreSchema, mode: JsonSchemaMode = "validation"
    ) -> JsonSchemaValue:
        json_schema = super().generate(schema, mode=mode)
        # clear the titles from the definitions
        for d in json_schema.get("$defs", {}).values():
            d.pop("title", None)
        return json_schema


# Schema modifiers
ModelT = TypeVar("ModelT", bound=BaseModel)


def get_schema_of(type_: object):
    return TypeAdapter(type_).json_schema(schema_generator=_GenerateJsonSchema)


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
