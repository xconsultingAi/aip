from typing import Any, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi import status

class BaseResponse(BaseModel):
    status_code: int
    success: bool
    message: str

class DataResponse(BaseResponse):
    data: Optional[Any] = None

#MJ: Default API Response (Success)
def success_response(message: str, data: list | dict | BaseModel, status_code: int = 200):
    
    if isinstance(data, BaseModel):
        data = data.model_dump()
    elif isinstance(data, list) and data and isinstance(data[0], BaseModel):
        data = [item.model_dump() for item in data]

    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "success": True,
            "message": message,
            "data": data,
        },
    )

#MJ: Default API Response (Error)
def error_response(
    message: str,
    http_status: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={
            "status_code": http_status,
            "success": False,
            "message": message,
            "data": None
        }
    )
