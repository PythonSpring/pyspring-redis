from uuid import uuid4

from pydantic import ValidationError
import pytest
from py_spring_redis.commons import RedisKeyDocument


class MockRedisKeyDocument(RedisKeyDocument): ...


class TestRedisKeyDocument:
    @pytest.fixture
    def redis_key_document(self):
        """Fixture to provide a RedisKeyDocument instance with a random id."""
        return RedisKeyDocument(id=str(uuid4()))

    def test_get_document_id(self, redis_key_document):
        """Test if get_document_id returns the correct formatted string."""
        document_id = redis_key_document.get_document_id()
        expected_id = f"{redis_key_document.__class__.__name__}:{redis_key_document.id}"
        assert document_id == expected_id, f"Expected {expected_id}, got {document_id}"

    def test_get_document_key_base_name(self):
        """Test if get_document_key_base_name returns the correct class name."""
        assert RedisKeyDocument.get_document_key_base_name() == "RedisKeyDocument"

    def test_inheritantor_did_get_right_document_key_base_name(self):
        """Test if the inheritor class gets the correct class name."""
        assert (
            MockRedisKeyDocument.get_document_key_base_name() == "MockRedisKeyDocument"
        )

    def test_id_field_exclusion(self):
        """Test if id field is excluded when creating the model's dict."""
        redis_key_document = RedisKeyDocument(id=str(uuid4()))
        model_dict = redis_key_document.model_dump(exclude={"id"})
        assert (
            "id" not in model_dict
        ), f"Expected 'id' to be excluded, but got {model_dict}"

    def test_invalid_id_type(self):
        """Test if passing an invalid type to the id field raises a validation error."""
        with pytest.raises(ValidationError):
            RedisKeyDocument(id=123)  # type: ignore # id should be a string, passing an int should raise ValidationError
