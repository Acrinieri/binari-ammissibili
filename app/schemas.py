from pydantic import BaseModel


class OrderBase(BaseModel):
    item: str
    quantity: int


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: int

    class Config:
        orm_mode = True
