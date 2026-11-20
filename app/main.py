from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import Customer, Order, Service
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    CustomerSales,
    LatestSale,
    OrderCreate,
    OrderOut,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)


def money(value) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01'))}"


def service_out(row: Service) -> ServiceOut:
    return ServiceOut(
        id=row.id,
        name=row.name,
        description=row.description,
        suggested_price=money(row.suggested_price),
    )


def customer_out(row: Customer) -> CustomerOut:
    return CustomerOut(id=row.id, name=row.name, email=row.email)


def order_out(row: Order) -> OrderOut:
    return OrderOut(
        id=row.id,
        customer_id=row.customer_id,
        service_id=row.service_id,
        service_name=row.service_name,
        service_description=row.service_description,
        amount=money(row.amount),
        created_at=row.created_at,
        canceled=row.canceled,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TinyShop", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/services", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    row = Service(
        name=payload.name,
        description=payload.description,
        suggested_price=payload.suggested_price,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return service_out(row)


@app.get("/services", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    rows = db.scalars(select(Service).order_by(Service.id)).all()
    return [service_out(row) for row in rows]


@app.get("/services/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db)):
    row = db.get(Service, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="service not found")
    return service_out(row)


@app.patch("/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db)):
    row = db.get(Service, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="service not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return service_out(row)


@app.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    row = Customer(name=payload.name, email=payload.email)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already registered")
    db.refresh(row)
    return customer_out(row)


@app.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    rows = db.scalars(select(Customer).order_by(Customer.id)).all()
    return [customer_out(row) for row in rows]


@app.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    row = db.get(Customer, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer_out(row)


@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    service = db.get(Service, payload.service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="service not found")
    row = Order(
        customer_id=customer.id,
        service_id=service.id,
        service_name=service.name,
        service_description=service.description,
        amount=service.suggested_price,
        created_at=datetime.now(timezone.utc),
        canceled=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return order_out(row)


@app.get("/orders", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    rows = db.scalars(select(Order).order_by(Order.created_at.desc(), Order.id.desc())).all()
    return [order_out(row) for row in rows]


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    row = db.get(Order, order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order_out(row)


@app.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    row = db.get(Order, order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    if row.canceled:
        raise HTTPException(status_code=409, detail="order already canceled")
    row.canceled = True
    db.commit()
    db.refresh(row)
    return order_out(row)


@app.get("/reports/sales/latest", response_model=list[LatestSale])
def latest_sales(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Order.id,
            Customer.id,
            Customer.name,
            Order.service_description,
            Order.amount,
            Order.created_at,
        )
        .join(Customer, Customer.id == Order.customer_id)
        .where(Order.canceled.is_(False))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(10)
    ).all()
    return [
        LatestSale(
            order_id=order_id,
            customer_id=customer_id,
            customer_name=customer_name,
            service_description=description,
            amount=money(amount),
            created_at=created_at,
        )
        for order_id, customer_id, customer_name, description, amount, created_at in rows
    ]


@app.get("/reports/sales/by-customer", response_model=list[CustomerSales])
def sales_by_customer(db: Session = Depends(get_db)):
    total = func.sum(Order.amount)
    rows = db.execute(
        select(Customer.id, Customer.name, func.count(Order.id), total)
        .join(Order, Order.customer_id == Customer.id)
        .where(Order.canceled.is_(False))
        .group_by(Customer.id, Customer.name)
        .order_by(total.desc(), Customer.id)
    ).all()
    return [
        CustomerSales(
            customer_id=customer_id,
            customer_name=customer_name,
            order_count=int(order_count),
            total_amount=money(total_amount),
        )
        for customer_id, customer_name, order_count, total_amount in rows
    ]
