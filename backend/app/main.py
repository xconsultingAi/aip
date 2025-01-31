from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.app_routers import router as app_routers
from app.core.responses import success_response
from datetime import datetime
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

app = FastAPI()
load_dotenv()
#MJ: Include all endpoints
app.include_router(app_routers, prefix="/api")


#MJ: Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

#MJ: Enable CORS (we will be using two different domains for Frontend and backend)
origins= settings.ALLOWED_ORIGINS.split(",") #TODO: MJ: This is not working - need to fix it
print(origins)
origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000"
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#MJ: Unsecured route for health check
@app.get("/")
def status():    
    return success_response(message="Ready...", data={"timestamp": datetime.now().isoformat()}) 

