import sentry_sdk
import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi_limiter import FastAPILimiter
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


from common.config import cfg
from common.config import sentry_config
from common.exceptions import HTTPExceptionJSON, UnexpectedRelationshipState
from common.injection import Cache, PubSubStore, configure, injector
from common.database.beanie import connect
from common.exceptions import UnexpectedRelationshipState

from authentication.api import auth_router
from authentication.avatar.api import avatar_router
from common.utils.mail.api import mail_router

# Init FastAPI app
app = FastAPI()

# Add middlewares
if cfg.sentry_dsn:
    sentry_sdk.init(**sentry_config)
    asgi_app = SentryAsgiMiddleware(app)

# CORS
if not cfg.prod:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Add routers
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(avatar_router, tags=["avatar"])
api_router.include_router(mail_router, tags=["mail"])
app.mount("/web/avatars", StaticFiles(directory=cfg.avatar_data_folder), name="avatar")
app.include_router(api_router)


# Add exception handlers
@app.exception_handler(HTTPExceptionJSON)
def http_exception_handler(request: Request, exc: HTTPExceptionJSON):

    json_data = jsonable_encoder(exc.data)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"message": exc.detail, "code": exc.code, "error": json_data},
    )


@app.exception_handler(UnexpectedRelationshipState)
async def unicorn_exception_handler(request: Request, exc: UnexpectedRelationshipState):
    return JSONResponse(
        status_code=400, content={"message": "UnexpectedRelationshipState"}
    )


# Startup event handler
@app.on_event("startup")
async def startup():
    # Init dependency injection graph and services
    await configure()
    await FastAPILimiter.init(injector.get(Cache))

    # Connect to database
    await connect()


# Shutdown event handler
@app.on_event("shutdown")
async def shutdown():
    ...


if __name__ == "__main__":
    uvicorn.run(app, log_level=cfg.fastapi_log_level)
