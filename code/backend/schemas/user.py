import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class UserRegister(BaseModel):
    account: str = Field(..., description="Phone number (digits only)")
    password: str = Field(..., description="6-digit password")
    nickname: str = Field(..., description="Nickname (English or Chinese)")
    role: str = Field(..., description="student, teacher, or admin")
    major_code: str = Field(None, description="Major code (e.g. AIBA)")

    @field_validator('account')
    @classmethod
    def validate_account(cls, v):
        if not re.match(r'^\d{11}$', v):
            raise ValueError('Account must be an 11-digit phone number')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Password must be exactly 6 digits')
        return v

    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]+$', v):
            raise ValueError('Nickname must contain only English or Chinese characters')
        return v


class UserLogin(BaseModel):
    account: str
    password: str


class UserUpdate(BaseModel):
    nickname: str = Field(..., description="Nickname")
    major_code: str = Field(None, description="Major code")

    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]+$', v):
            raise ValueError('Nickname must contain only English or Chinese characters')
        return v

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., description="6-digit password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Password must be exactly 6 digits')
        return v
