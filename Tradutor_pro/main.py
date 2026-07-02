from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes.upload import router as upload_router
from app.routes.download import router as download_router
from app.routes.translation import router as translation_router

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

templates = Jinja2Templates(
    directory="app/templates"
)

@app.get("/")  # e pasta templates , que puxa nosso index com css, para tela
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

app.include_router(upload_router)
app.include_router(download_router)
app.include_router(translation_router)
