from pydantic import BaseModel, Field


class RedisKeyDocument(BaseModel):
    id: str = Field(exclude=True)

    def get_document_id(self) -> str:
        return f"{self.__class__.__name__}:{self.id}"

    @classmethod
    def get_document_key_base_name(cls) -> str:
        return cls.__name__
