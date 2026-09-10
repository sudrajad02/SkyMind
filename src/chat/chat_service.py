import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.chat.dto.chat_dto import CreateChatDTO
from .chat_model import ChatModel
import requests
import json
from src.weather.weather_service import find_adm4_by_location, fetch_bmkg_weather

load_dotenv()

SYSTEM_PROMPT = """Kamu adalah asisten cuaca bernama SkyMind yang RAMAH, CERDAS, dan TRANSPARAN.
ATURAN PENTING:
1. JIKA TERSEDIA DATA RESMI BMKG PADA KONTEKS:
   - Gunakan data tersebut untuk menjawab prakiraan cuaca real-time secara akurat.
   - Jelaskan kondisi cuaca, suhu, kelembapan, dan angin dengan bahasa yang santai, ramah, dan informatif.
   - Set "tipe_info": "data_realtime_bmkg"
   - Set "tingkat_kepastian": "tinggi"
   - Set "disclaimer": "Data resmi bersumber langsung dari BMKG Indonesia."
   - Jika terdapat "CATATAN TINGKAT LOKASI (INDUK)" pada konteks, jelaskan secara ramah bahwa prakiraan ini mewakili wilayah induk berdasarkan titik kelurahan tersebut, lalu tawarkan kepada user untuk memasukkan nama desa atau kelurahan jika ingin perkiraan cuaca yang lebih tepat/akurat.
2. JIKA TIDAK ADA DATA BMKG (hanya pertanyaan cuaca umum atau wilayah tidak ditemukan):
   - Berikan estimasi berdasarkan pola iklim umum daerah tersebut.
   - Tolak memberi kepastian jam tertentu dan ingatkan bahwa ini hanya perkiraan pola iklim.
   - Set "tipe_info": "estimasi_pola_umum"
   - Set "tingkat_kepastian": "rendah"
   - Set "disclaimer": "Bukan data real-time, hanya estimasi berdasarkan pola iklim umum."
3. JIKA BUKAN PERTANYAAN CUACA (sapaan, basa-basi):
   - Jawab sapaan dengan ramah dan tawarkan bantuan terkait info cuaca.
   - Set "kota": null
   - Set "tipe_info": "bukan_pertanyaan_cuaca"
   - Set "tingkat_kepastian": null
   - Set "disclaimer": null
4. FORMAT KELUARAN:
   Jawab HANYA dalam format JSON valid tanpa teks tambahan apa pun di luar JSON:
{
  "kota": "<nama kota/wilayah atau null>",
  "jawaban": "<teks jawaban natural, ramah, dan informatif untuk user>",
  "tipe_info": "<data_realtime_bmkg | estimasi_pola_umum | bukan_pertanyaan_cuaca>",
  "tingkat_kepastian": "<tinggi | sedang | rendah | null>",
  "disclaimer": "<teks disclaimer atau null>"
}
CONTOH:
User: "Cuaca Jakarta hari ini gimana?" (Dengan data BMKG: Cerah Berawan, 31°C, 68%, 12 km/jam)
Jawaban:
{
  "kota": "Jakarta",
  "jawaban": "Cuaca di Jakarta saat ini terpantau cerah berawan dengan suhu udara sekitar 31°C. Kelembapan udara berkisar 68% dengan angin berhembus sekitar 12 km/jam. Cuaca cukup bersahabat untuk beraktivitas di luar ruangan!",
  "tipe_info": "data_realtime_bmkg",
  "tingkat_kepastian": "tinggi",
  "disclaimer": "Data resmi bersumber langsung dari BMKG Indonesia."
}
User: "Halo, apa kabar?" (Tanpa Data BMKG)
Jawaban:
{
  "kota": null,
  "jawaban": "Halo! Saya SkyMind, asisten prakiraan cuaca Anda. Mau tahu info cuaca di daerah mana hari ini?",
  "tipe_info": "bukan_pertanyaan_cuaca",
  "tingkat_kepastian": null,
  "disclaimer": null
}
"""

def create_chat(db: Session, payload: CreateChatDTO):
  try:
    session_id = payload.session_id
    content = payload.content
    weather_json = payload.weather_json

    lokasi = extraction_location_with_ai(content)
    print(f"Lokasi terdeksi oleh AI: {lokasi}")

    adm4_info = None
    raw_bmkg = None
    cuaca_list = None
    cuaca_terkini = None
    bmkg_weather_data = None
    weather_context = ""

    if lokasi:
      adm4_info = find_adm4_by_location(db, lokasi)
      
      if adm4_info:
        raw_bmkg = fetch_bmkg_weather(adm4_info["adm4"])
        
        if raw_bmkg and "data" in raw_bmkg and len(raw_bmkg["data"]) > 0:
          bmkg_weather_data = raw_bmkg

          cuaca_list = raw_bmkg["data"][0].get("cuaca", [[]])[0]

          if cuaca_list:
            cuaca_terkini = cuaca_list[0]
            
            catatan_lokasi = ""
            if adm4_info.get("level") == "induk":
              catatan_lokasi = f"""
            - CATATAN TINGKAT LOKASI (INDUK):
              Lokasi yang dicari user ('{lokasi}') adalah wilayah induk (kabupaten/kota/kecamatan), bukan titik desa/kelurahan spesifik.
              Data cuaca yang diambil ini bersumber dari perwakilan Kelurahan/Desa {adm4_info.get('kelurahan') or '-'}.
              Sampaikan kepada user bahwa ini adalah perkiraan untuk wilayah tersebut berdasarkan titik kelurahan tersebut, lalu tawarkan dengan ramah: "Jika ingin informasi cuaca yang lebih tepat dan akurat, silakan sebutkan nama kelurahan atau desa Anda."
              """

            weather_context = f"""
            DATA RESMI BMKG REAL-TIME:
            - Kecamatan: {adm4_info.get('kecamatan') or '-'}
            - Kelurahan: {adm4_info.get('kelurahan') or '-'}
            - Kabupaten: {adm4_info.get('kabupaten') or '-'}
            - Provinsi: {adm4_info.get('provinsi') or '-'}
            - Kondisi Cuaca: {cuaca_terkini.get('weather_desc', '-')}
            - Suhu: {cuaca_terkini.get('t', '-')}°C
            - Kelembapan: {cuaca_terkini.get('hu', '-')}%
            - Kecepatan Angin: {cuaca_terkini.get('ws', '-')} km/jam
            {catatan_lokasi}
            Gunakan data resmi BMKG di atas untuk menjawab user secara akurat dan informatif!
            """
    
    print(f"Lokasi terdeksi dari DB: lokasi: {lokasi}, info: {adm4_info}, raw_data: {raw_bmkg}, cuaca_list: {cuaca_list}, cuaca_terkini: {cuaca_terkini}")

    # Ambil history chat sebelumnya (sebelum menambahkan pesan baru ini)
    past_chats = get_chats_by_session(db, session_id)
    
    # Siapkan payload messages
    messages = [
      {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if weather_context:
      messages.append({"role": "system", "content": weather_context})
    
    for chat in past_chats:
      role = "user" if chat.sender == "user" else "assistant"
      messages.append({"role": role, "content": chat.content})
    
    # Tambahkan pesan dari user saat ini
    messages.append({"role": "user", "content": content})

    new_chat = ChatModel(session_id=session_id, content=content, sender="user", weather_json=weather_json)
    db.add(new_chat)

    response = requests.post(os.getenv("AI_URL"), 
      headers={
        "Authorization": f"Bearer {os.getenv("API_KEY")}",
        "Content-Type": "application/json",
      },
      data=json.dumps({
        "model": os.getenv("MODEL"),
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.3
      })
    )
    response_json = response.json()

    # OpenRouter/OpenAI mengembalikan content di dalam choices[0].message.content
    ai_content = ""
    if "choices" in response_json and len(response_json["choices"]) > 0:
      ai_content = response_json["choices"][0]["message"].get("content", "")
    else:
      print(f"OpenRouter Error / Response: {response_json}")
      ai_content = "Maaf, sistem cuaca sedang sibuk. Silakan coba beberapa saat lagi."

    # Karena SYSTEM_PROMPT memaksa output JSON, kita parse JSON-nya
    ai_text = ai_content
    ai_weather_json = None
    
    try:
      # Bersihkan backtick jika AI masih mengirim markdown block (```json ... ```)
      clean_content = ai_content.strip()
      if clean_content.startswith("```json"):
        clean_content = clean_content[7:-3].strip()
      elif clean_content.startswith("```"):
        clean_content = clean_content[3:-3].strip()

      parsed_json = json.loads(clean_content)
      
      # Jika format sesuai, kita jadikan 'jawaban' sebagai teks utama
      # dan sisa propertinya disimpan di weather_json
      if "jawaban" in parsed_json:
        ai_text = parsed_json.pop("jawaban")
        ai_weather_json = parsed_json
      else:
        ai_weather_json = parsed_json
    except json.JSONDecodeError:
      # Jika AI membangkang dan mengirim teks biasa
      pass

    final_weather = bmkg_weather_data if bmkg_weather_data else ai_weather_json

    ai_chat = ChatModel(
      session_id=session_id, 
      content=ai_text, 
      sender="ai", 
      weather_json=final_weather
    )
    db.add(ai_chat)
    
    db.commit()
    db.refresh(new_chat)
    db.refresh(ai_chat)
    
    # Kembalikan model ai_chat agar controller tidak error saat mengakses result.id dll
    return ai_chat
  except Exception as e:
    db.rollback()
    import traceback
    traceback.print_exc()
    print(f"Error creating chat: {e}")
    return None

def get_chats_by_session(db: Session, session_id: int):
  try:
    return db.query(ChatModel).filter(ChatModel.session_id == session_id).order_by(ChatModel.created_at.asc()).all()
  except Exception as e:
    print(f"Error fetching chats: {e}")
    return []

def extraction_location_with_ai(user_message: str) -> str | None:
  prompt = """Kamu adalah entitas ekstraktor lokasi. Tugasmu HANYA mengambil nama kota/kabupaten/daerah di Indonesia yang ditanyakan cuacanya oleh user.
    Aturan:
    - Jawab HANYA dalam JSON: {"lokasi": "<nama_kota>"}
    - Jika user tidak menanyakan cuaca suatu daerah, jawab: {"lokasi": null}
    - Jangan tambahkan teks apapun di luar JSON.
    Contoh:
    User: "Cuaca di Bandung gimana?" -> {"lokasi": "Bandung"}
    User: "Panas banget nih hari ini" -> {"lokasi": null}
    User: "Besok mau ke Malioboro, hujan gak?" -> {"lokasi": "Yogyakarta"}
    User: "Halo apa kabar?" -> {"lokasi": null}
    User: "Bagaimana Cuaca Monas?" -> {"lokasi": "Jakarta"}
    """
  
  try:
    response = requests.post(os.getenv("AI_URL"), 
      headers={
        "Authorization": f"Bearer {os.getenv("API_KEY")}",
        "Content-Type": "application/json",
      },
      data=json.dumps({
        "model": os.getenv("MODEL"),
        "messages": [{
          "role": "system", 
          "content": prompt
        },
        {
          "role": "user",
          "content": user_message
        }],
        "temperature": 0,
        "max_tokens": 50
      })
    )

    result = response.json()
    ai_reply = result["choices"][0]["message"]["content"].strip()
    
    if ai_reply.startswith("```"):
      ai_reply = ai_reply.split("```")[1]
      if ai_reply.startswith("json"):
        ai_reply = ai_reply[4:]

    parsed_json = json.loads(ai_reply.strip())
    
    return parsed_json.get("lokasi")
  except Exception as e:
    print(f"Error extracting location: {e}")
    return None
    
