from fastapi import FastAPI
from . import models
from .database import engine
from .auth import router as auth_router
from .parser import procesar_facturas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router, prefix="/auth")


@app.get("/")
def read_root():
    return {"msg": "Backend de Expense Tracker esta levantado"}

@app.get("/procesar")
def procesar():
    procesar_facturas()
    return {"msg": "Proceso de facturas iniciado"}




