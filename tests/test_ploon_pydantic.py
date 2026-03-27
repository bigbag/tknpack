"""Tests for Pydantic BaseModel integration with PLOON format."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from tknpack import Format, decode, encode


class SimpleModel(BaseModel):
    name: str
    age: int
    active: bool


class NestedModel(BaseModel):
    id: int
    details: SimpleModel


class ModelWithOptional(BaseModel):
    name: str
    nickname: str | None = None
    score: int = 0


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ModelWithEnum(BaseModel):
    name: str
    status: Status


class ModelWithDatetime(BaseModel):
    name: str
    created_at: datetime


class ModelWithList(BaseModel):
    name: str
    tags: list[str]


class TestEncodePloon:
    def test_simple_model(self):
        model = SimpleModel(name="Ada", age=30, active=True)
        result = encode(model, format=Format.PLOON)
        assert "[root#1]" in result
        assert "Ada" in result
        assert "30" in result
        assert "true" in result

    def test_model_with_optional_none(self):
        model = ModelWithOptional(name="Test")
        result = encode(model, format=Format.PLOON)
        assert "Test" in result
        assert "null" in result

    def test_model_with_list(self):
        model = ModelWithList(name="Test", tags=["a", "b", "c"])
        result = encode(model, format=Format.PLOON)
        assert "tags#()" in result
        assert "a,b,c" in result


class TestDecodePloon:
    def test_simple_round_trip(self):
        model = SimpleModel(name="Ada", age=30, active=True)
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, SimpleModel, format=Format.PLOON)
        assert restored == model

    def test_optional_none_round_trip(self):
        model = ModelWithOptional(name="Test")
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, ModelWithOptional, format=Format.PLOON)
        assert restored == model

    def test_optional_set_round_trip(self):
        model = ModelWithOptional(name="Test", nickname="T", score=42)
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, ModelWithOptional, format=Format.PLOON)
        assert restored == model

    def test_list_round_trip(self):
        model = ModelWithList(name="Test", tags=["a", "b", "c"])
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, ModelWithList, format=Format.PLOON)
        assert restored == model

    def test_enum_round_trip(self):
        model = ModelWithEnum(name="Test", status=Status.ACTIVE)
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, ModelWithEnum, format=Format.PLOON)
        assert restored == model

    def test_datetime_round_trip(self):
        model = ModelWithDatetime(name="Test", created_at=datetime(2024, 1, 15, 10, 30))
        ploon_str = encode(model, format=Format.PLOON)
        restored = decode(ploon_str, ModelWithDatetime, format=Format.PLOON)
        assert restored == model
