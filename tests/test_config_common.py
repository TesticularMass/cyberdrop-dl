import importlib
import sys
from pathlib import Path

import pydantic.fields
import pytest
from pydantic import BaseModel, ValidationError

from cyberdrop_dl.config import _common


class ExampleSection(BaseModel):
    alias_value: str = _common.Field("default", "Legacy_Value")
    bounded_value: int = _common.Field(5, ge=1)


class ExampleSettings(_common.ConfigModel):
    section: ExampleSection = _common.Field(ExampleSection(), "Section")


def test_field_accepts_validation_alias_without_private_sentinel() -> None:
    original_unset = pydantic.fields._Unset
    try:
        delattr(pydantic.fields, "_Unset")
        sys.modules.pop("cyberdrop_dl.config._common", None)
        common = importlib.import_module("cyberdrop_dl.config._common")
    finally:
        pydantic.fields._Unset = original_unset
        sys.modules["cyberdrop_dl.config._common"] = _common

    class ExampleSection(BaseModel):
        alias_value: str = common.Field("default", "Legacy_Value")
        bounded_value: int = common.Field(5, ge=1)

    class ExampleSettings(common.ConfigModel):
        section: ExampleSection = common.Field(ExampleSection(), "Section")

    config = ExampleSettings.model_validate({"Section": {"Legacy_Value": "updated", "bounded_value": 7}})
    assert config.section.alias_value == "updated"
    assert config.section.bounded_value == 7


def test_field_without_alias_still_passes_field_kwargs() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExampleSettings.model_validate({"Section": {"bounded_value": 0}})

    assert any(
        error["loc"] == ("Section", "bounded_value")
        and error["type"] == "greater_than_equal"
        and "greater than or equal to 1" in error["msg"]
        for error in exc_info.value.errors()
    )


def test_load_file_writes_defaults_for_missing_config(tmp_path: Path) -> None:
    config_path = tmp_path / "example.yaml"
    config = ExampleSettings.load_file(config_path, update_if_has_string="obsolete-marker")

    assert config.section.alias_value == "default"
    assert config.section.bounded_value == 5

    contents = config_path.read_text(encoding="utf8")
    assert "section:" in contents
    assert "alias_value: default" in contents
