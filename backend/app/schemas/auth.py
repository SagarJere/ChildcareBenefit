from pydantic import BaseModel, ConfigDict, Field

from app.schemas.employee import EmployeeProfile


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    employee_id: str = Field(min_length=1, max_length=20)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee: EmployeeProfile
