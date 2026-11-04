from pydantic import BaseModel, ConfigDict, Field, EmailStr, model_validator
from typing import List, Optional
from datetime import date

# ----------------- Guest Schemas -----------------
class GuestBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the guest")
    email: EmailStr = Field(..., description="Valid contact email address")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone number")

class GuestCreate(GuestBase):
    pass

class GuestResponse(GuestBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- Unit Schemas -----------------
class UnitBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Unit or room name")
    description: str = Field(..., min_length=5, max_length=500, description="Short description of the unit")
    capacity: int = Field(..., gt=0, le=50, description="Maximum guest capacity (1 to 50)")

class UnitCreate(UnitBase):
    pass

class UnitResponse(UnitBase):
    id: int
    is_available: bool = True
    model_config = ConfigDict(from_attributes=True)


# ----------------- Reservation Schemas -----------------
class ReservationBase(BaseModel):
    guest_id: int = Field(..., gt=0, description="ID of the registered guest")
    unit_id: int = Field(..., gt=0, description="ID of the unit being booked")
    check_in_date: date = Field(..., description="Date of check-in")
    check_out_date: date = Field(..., description="Date of check-out")

    @model_validator(mode="after")
    def validate_dates(self):
        # 1. Enforce that check-out is strictly after check-in
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be strictly after check_in_date")
        
        # 2. Prevent reservations in the past
        if self.check_in_date < date.today():
            raise ValueError("check_in_date cannot be in the past")
            
        return self

class ReservationCreate(ReservationBase):
    pass

class ReservationUpdate(BaseModel):
    guest_id: Optional[int] = Field(None, gt=0)
    unit_id: Optional[int] = Field(None, gt=0)
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_update_dates(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValueError("check_out_date must be strictly after check_in_date")
        return self

class ReservationResponse(ReservationBase):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)