from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.responses import error_response
#TODO: Add more exception handlers in this

#MJ: HTTP Exceptions
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    print(exc.detail)
    return error_response(exc.detail, http_status=exc.status_code)

#MJ: Validation Exceptions
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "success": False,
            "message": "Validation error",
            "data": exc.errors()
        },
    )

#MJ: General Exceptions
async def general_exception_handler(request: Request, exc: Exception):
    return error_response("Internal server error", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#SH: OpenAI Exception
class LLMServiceError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM Service Error: {detail}",
            headers={"Retry-After": "30"},  # Proper HTTP headers for retry
        )

class InvalidAPIKeyError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OpenAI API Key",
        )
class OpenAIException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API Error: {detail}",
        )