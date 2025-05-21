import logging
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.responses import error_response
from tenacity import RetryError
#TODO: Add more exception handlers in this

logger = logging.getLogger("exception.handler")
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
    logger.exception(f"Unhandled exception: {str(exc)}")
    return error_response("Internal server error", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#SH: OpenAI Exception
def llm_service_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"LLM Service Error: {detail}",
        headers={"Retry-After": "30"},
    )

def invalid_api_key_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid OpenAI API Key",
    )

def openai_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"OpenAI API Error: {detail}",
    )

def network_exception(detail: str = "Connection to AI service failed") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Network Error: {detail}",
        headers={"Retry-After": "30"},
    )

async def retry_error_handler(request: Request, exc: RetryError):
    original_exc = exc.last_attempt.exception()
    logger.error(f"Retry failed after {exc.last_attempt.attempt_number} attempts: {str(original_exc)}")
    return error_response(
        message=f"Operation failed after retries: {str(original_exc)}",
        http_status=status.HTTP_400_BAD_REQUEST
    )
