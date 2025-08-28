from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

class Factura(Base):
    __tablename__ = "facturas"

    id=Column(Integer, primary_key=True, index=True)
    servicio=Column(String,)
    monto=Column(Float)
    vencimiento=Column(Date)
    estado=Column(String, default="pendiente")
    pdf_path=Column(String, nullable=True)

