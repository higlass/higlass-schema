import pathlib

import pydantic
import pytest

import higlass_schema as hgs

fixtures = pathlib.Path(__file__).parent / ".." / "fixtures"

valid = fixtures.glob("**/*.json")

@pytest.mark.parametrize("path", list(valid))
def test_valid_viewconf(path: pathlib.Path):
    hgs.Viewconf[hgs.View[hgs.Track]].parse_file(path)

invalid = fixtures.glob("**invalid/*.json")

@pytest.mark.parametrize("path", list(valid))
def test_invalid_viewconf(path: pathlib.Path):
    with pytest.raises(pydantic.ValidationError):
        hgs.Viewconf[hgs.View[hgs.Track]].parse_file(path)
