from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order as OrderModel
from ..schemas import Order, OrderCreate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[Order])
async def list_orders(db: Session = Depends(get_db)) -> list[OrderModel]:
    return db.query(OrderModel).all()


@router.post("", response_model=Order, status_code=201)
async def create_order(
    order: OrderCreate, db: Session = Depends(get_db)
) -> OrderModel:
    db_order = OrderModel(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order
