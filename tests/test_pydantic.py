"""Tests for Pydantic BaseModel integration."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from tknpack import decode, encode


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


class ModelWithUUID(BaseModel):
    id: UUID
    name: str


class ModelWithList(BaseModel):
    name: str
    tags: list[str]


class ModelWithDict(BaseModel):
    name: str
    metadata: dict[str, int]


class TestEncodeBasic:
    def test_simple_model(self):
        model = SimpleModel(name="Ada", age=30, active=True)
        result = encode(model)
        assert "name: Ada" in result
        assert "age: 30" in result
        assert "active: true" in result

    def test_nested_model(self):
        model = NestedModel(id=1, details=SimpleModel(name="Bob", age=25, active=False))
        result = encode(model)
        assert "id: 1" in result
        assert "details:" in result
        assert "  name: Bob" in result

    def test_model_with_optional_none(self):
        model = ModelWithOptional(name="Test")
        result = encode(model)
        assert "name: Test" in result
        assert "nickname: null" in result
        assert "score: 0" in result

    def test_model_with_optional_set(self):
        model = ModelWithOptional(name="Test", nickname="T", score=42)
        result = encode(model)
        assert "nickname: T" in result
        assert "score: 42" in result

    def test_model_with_list(self):
        model = ModelWithList(name="Test", tags=["a", "b", "c"])
        result = encode(model)
        assert "tags[3]: a,b,c" in result

    def test_model_with_dict(self):
        model = ModelWithDict(name="Test", metadata={"x": 1, "y": 2})
        result = encode(model)
        assert "metadata:" in result
        assert "  x: 1" in result


class TestDecodeBasic:
    def test_simple_round_trip(self):
        model = SimpleModel(name="Ada", age=30, active=True)
        toon_str = encode(model)
        restored = decode(toon_str, SimpleModel)
        assert restored == model

    def test_nested_round_trip(self):
        model = NestedModel(id=1, details=SimpleModel(name="Bob", age=25, active=False))
        toon_str = encode(model)
        restored = decode(toon_str, NestedModel)
        assert restored == model

    def test_optional_none_round_trip(self):
        model = ModelWithOptional(name="Test")
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithOptional)
        assert restored == model

    def test_optional_set_round_trip(self):
        model = ModelWithOptional(name="Test", nickname="T", score=42)
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithOptional)
        assert restored == model

    def test_list_round_trip(self):
        model = ModelWithList(name="Test", tags=["a", "b", "c"])
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithList)
        assert restored == model

    def test_enum_round_trip(self):
        model = ModelWithEnum(name="Test", status=Status.ACTIVE)
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithEnum)
        assert restored == model

    def test_uuid_round_trip(self):
        uid = UUID("12345678-1234-5678-1234-567812345678")
        model = ModelWithUUID(id=uid, name="Test")
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithUUID)
        assert restored == model

    def test_datetime_round_trip(self):
        model = ModelWithDatetime(name="Test", created_at=datetime(2024, 1, 15, 10, 30))
        toon_str = encode(model)
        restored = decode(toon_str, ModelWithDatetime)
        assert restored == model
