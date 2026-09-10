from sqlalchemy import Column, String
from src.config.db import Base

class WilayahModel(Base):
  __tablename__ = "wilayah"

  kode = Column(String(13), primary_key=True)
  nama = Column(String(100), nullable=False)
  kecamatan = Column(String(100), nullable=True)
  kabupaten = Column(String(100), nullable=True)
  provinsi = Column(String(100), nullable=True)