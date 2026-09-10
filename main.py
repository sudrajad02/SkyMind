import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.session.session_controller import router as session_router
from src.chat.chat_controller import router as chat_router
from src.auth.auth_controller import router as auth_router
from src.config.db import Base, engine
from src.session.session_model import SessionModel
from src.chat.chat_model import ChatModel
from src.auth.auth_model import UserModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x != "body"]
        field = ".".join(loc)
        msg = err.get("msg", "")
        if field:
            errors.append(f"{field}: {msg}")
        else:
            errors.append(msg)
    error_message = "; ".join(errors) if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": False,
            "data": None,
            "error": error_message
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": False,
            "data": None,
            "error": exc.detail
        },
        headers=getattr(exc, "headers", None)
    )

Base.metadata.create_all(bind=engine)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Waktu: {process_time:.4f}s")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(session_router)
app.include_router(chat_router)

@app.get("/")
async def root():
	return {"status": True, "data": {"message": "Hello World"}, "error": None}