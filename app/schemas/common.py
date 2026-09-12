from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    limit: int
    offset: int
    total: int
