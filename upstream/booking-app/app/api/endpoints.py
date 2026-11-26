from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database.database import get_db
from app.crud import crud
from app.schemas import schemas
from app.worker import celery_app
from app.utils.cache import get_cached_units, set_cached_units, invalidate_units_cache
from app.utils.idempotency import check_idempotency, save_idempotent_response, clear_idempotency_key

router = APIRouter()

@router.post("/guests/", response_model=schemas.GuestResponse)
def create_guest(guest: schemas.GuestCreate, db: Session = Depends(get_db)):
    return crud.create_guest(db=db, guest=guest)

@router.get("/guests/", response_model=List[schemas.GuestResponse])
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_guests(db=db, skip=skip, limit=limit)

@router.post("/units/", response_model=schemas.UnitResponse)
def create_unit(unit: schemas.UnitCreate, db: Session = Depends(get_db)):
    db_unit = crud.create_unit(db=db, unit=unit)
    invalidate_units_cache()
    return db_unit

@router.get("/units/", response_model=List[schemas.UnitResponse])
def read_units(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 1. Try to read from Redis cache
    cached_units = get_cached_units(skip=skip, limit=limit)
    if cached_units is not None:
        return cached_units
    
    # 2. On cache miss, fetch from PostgreSQL
    db_units = crud.get_units(db=db, skip=skip, limit=limit)
    
    # 3. Store serialized data in Redis with 60s TTL
    units_data = [schemas.UnitResponse.model_validate(u).model_dump() for u in db_units]
    set_cached_units(skip=skip, limit=limit, units_data=units_data, ttl=60)
    
    return db_units

@router.post("/reservations/", response_model=schemas.ReservationResponse)
async def create_reservation(
    reservation: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    # 1. Network retry check via Idempotency-Key
    if idempotency_key:
        in_progress, cached_receipt = check_idempotency(idempotency_key)
        if cached_receipt:
            return cached_receipt
        if in_progress:
            raise HTTPException(
                status_code=409,
                detail="A reservation request with this Idempotency-Key is currently in progress."
            )

    # 2. Execute reservation with PostgreSQL Row-Level Locking
    try:
        db_reservation = crud.create_reservation(db=db, reservation=reservation)
    except ValueError as e:
        if idempotency_key:
            clear_idempotency_key(idempotency_key)
        
        detail_msg = str(e)
        if "already reserved" in detail_msg:
            raise HTTPException(status_code=409, detail=detail_msg)
        raise HTTPException(status_code=404, detail=detail_msg)
    except Exception as e:
        if idempotency_key:
            clear_idempotency_key(idempotency_key)
        raise e

    # 3. Invalidate unit cache so availability is immediately fresh
    invalidate_units_cache()

    # 4. Save response in Redis for network retry protection
    if idempotency_key:
        receipt_data = {
            "id": db_reservation.id,
            "guest_id": db_reservation.guest_id,
            "unit_id": db_reservation.unit_id,
            "check_in_date": db_reservation.check_in_date.isoformat(),
            "check_out_date": db_reservation.check_out_date.isoformat(),
            "status": db_reservation.status
        }
        save_idempotent_response(idempotency_key, receipt_data)

    # 5. Send confirmation email through Celery
    email_data = {
        "to_email": db_reservation.guest.email,
        "subject": "Reservation Confirmation",
        "template_name": "reservation_confirmation",
        "context": {
            "guest_name": db_reservation.guest.name,
            "unit_name": db_reservation.unit.name,
            "check_in_date": reservation.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": reservation.check_out_date.strftime("%Y-%m-%d"),
            "reservation_id": db_reservation.id
        }
    }
    celery_app.send_task('send_reservation_email', args=[email_data])

    return db_reservation

@router.get("/reservations/", response_model=List[schemas.ReservationResponse])
def read_reservations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_reservations(db=db, skip=skip, limit=limit)

@router.put("/reservations/{reservation_id}", response_model=schemas.ReservationResponse)
def update_reservation(reservation_id: int, reservation_update: schemas.ReservationUpdate, db: Session = Depends(get_db)):
    try:
        updated = crud.update_reservation(db=db, reservation_id=reservation_id, reservation_update=reservation_update)
        invalidate_units_cache()
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
