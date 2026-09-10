from sqlalchemy.orm import Session
from sqlalchemy import func
from src.weather.weather_model import WilayahModel
import requests

def find_adm4_by_location(db: Session, location_name: str) -> dict | None:
  keyword = location_name.strip()

  matched = (db.query(WilayahModel).filter(WilayahModel.nama.ilike(f"%{keyword}%")).order_by(func.length(WilayahModel.kode).asc()).first())

  if not matched:
    return None

  if len(matched.kode) == 13:
    return {
      "adm4": matched.kode,
      "kelurahan": matched.nama,
      "kecamatan": matched.kecamatan,
      "kabupaten": matched.kabupaten,
      "provinsi": matched.provinsi,
      "level": "desa"
    }

  child_adm4 = (db.query(WilayahModel).filter(WilayahModel.kode.like(f"{matched.kode}.%"), func.length(WilayahModel.kode) == 13).first())

  if child_adm4:
    return{
      "adm4": child_adm4.kode,
      "kelurahan": child_adm4.nama,
      "kecamatan": child_adm4.kecamatan,
      "kabupaten": child_adm4.kabupaten,
      "provinsi": child_adm4.provinsi,
      "level": "induk"
    }
  
  return None

def fetch_bmkg_weather(adm4_code: str) -> dict | None:
  url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4_code}"

  try:
    response = requests.get(url, timeout=10)

    if(response.status_code == 200):
      return response.json()
    
    return None
  except Exception as e:
    print(f"Error fetching BMKG data: {e}")

  return None