import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.chat.dto.chat_dto import CreateChatDTO
from .chat_model import ChatModel
from src.session.session_model import SessionModel
import requests
import json
from src.weather.weather_service import find_adm4_by_location, fetch_bmkg_weather

load_dotenv()

SYSTEM_PROMPT = """Kamu adalah asisten cuaca bernama SkyMind yang RAMAH, CERDAS, dan TRANSPARAN.
ATURAN PENTING:
1. JIKA TERSEDIA DATA RESMI BMKG PADA KONTEKS:
   - Gunakan data tersebut untuk menjawab prakiraan cuaca secara akurat.
   - Jelaskan kondisi cuaca, suhu, kelembapan, dan angin dengan bahasa yang santai, ramah, dan informatif.
   - Set "tipe_info": "data_realtime_bmkg"
   - Set "tingkat_kepastian": "tinggi"
   - Set "disclaimer": "Data resmi bersumber langsung dari BMKG Indonesia."
   - Jika terdapat "CATATAN TINGKAT LOKASI (INDUK)" pada konteks, jelaskan secara ramah bahwa prakiraan ini mewakili wilayah induk berdasarkan titik kelurahan tersebut, lalu tawarkan kepada user untuk memasukkan nama desa atau kelurahan jika ingin perkiraan cuaca yang lebih tepat/akurat.
   - RENTANG WAKTU & BATASAN 3 HARI KE DEPAN:
     * Data resmi BMKG HANYA mencakup maksimal 3 hari ke depan: Hari Ini (Hari 1), Besok (Hari 2), dan Lusa (Hari 3).
     * JIKA USER TIDAK MENYEBUTKAN WAKTU/TANGGAL: Selalu gunakan data waktu/slot jam pertama yang tersedia pada Hari ke-1 (cuaca saat ini / terdekat).
     * Jika user menanyakan cuaca hari ini, jawab berdasarkan data Hari ke-1 (slot jam terdekat saat ini).
     * Jika user menanyakan cuaca besok atau lusa, jawab berdasarkan data Hari ke-2 atau Hari ke-3 (sesuaikan dengan waktu yang ditanyakan: pagi, siang, sore, atau malam).
     * BATASAN PENTING: JIKA USER MENANYAKAN CUACA DI LUAR 3 HARI (misal: 4 hari lagi, minggu depan, bulan depan, dll):
       Jelaskan dengan sopan dan ramah bahwa data resmi BMKG hanya tersedia untuk maksimal 3 hari ke depan (Hari Ini, Besok, dan Lusa), sehingga prakiraan resmi BMKG untuk waktu tersebut belum tersedia.
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
5. KALIMAT PENUTUP:
   - Di akhir teks "jawaban", SELALU tambahkan kalimat penutup yang ramah dan menawarkan bantuan lanjutan, seperti:
     "Ada yang bisa saya bantu lagi?" atau "Ada informasi cuaca daerah atau waktu lain yang ingin Anda ketahui?"
CONTOH:
User: "Cuaca Jakarta hari ini gimana?" (Dengan data BMKG: Cerah Berawan, 31°C, 68%, 12 km/jam)
Jawaban:
{
  "kota": "Jakarta",
  "jawaban": "Cuaca di Jakarta saat ini terpantau cerah berawan dengan suhu udara sekitar 31°C. Kelembapan udara berkisar 68% dengan angin berhembus sekitar 12 km/jam. Cuaca cukup bersahabat untuk beraktivitas di luar ruangan. Ada yang bisa saya bantu lagi terkait info cuaca?",
  "tipe_info": "data_realtime_bmkg",
  "tingkat_kepastian": "tinggi",
  "disclaimer": "Data resmi bersumber langsung dari BMKG Indonesia."
}
User: "Besok di Bandung siang hari hujan gak?" (Dengan data BMKG Hari ke-2 siang: Hujan Ringan, 29°C)
Jawaban:
{
  "kota": "Bandung",
  "jawaban": "Untuk besok siang di Bandung diprakirakan akan terjadi hujan ringan dengan suhu udara sekitar 29°C. Sebaiknya siapkan payung atau jas hujan jika berencana bepergian ya. Ada yang bisa saya bantu lagi?",
  "tipe_info": "data_realtime_bmkg",
  "tingkat_kepastian": "tinggi",
  "disclaimer": "Data resmi bersumber langsung dari BMKG Indonesia."
}
User: "Cuaca Surabaya minggu depan gimana?" (Di luar 3 hari)
Jawaban:
{
  "kota": "Surabaya",
  "jawaban": "Mohon maaf, saat ini data resmi prakiraan cuaca dari BMKG hanya tersedia untuk maksimal 3 hari ke depan (hari ini, besok, dan lusa). Data resmi untuk minggu depan belum tersedia dari BMKG. Silakan cek kembali mendekati hari tersebut ya. Ada wilayah lain yang ingin Anda cek?",
  "tipe_info": "data_realtime_bmkg",
  "tingkat_kepastian": "rendah",
  "disclaimer": "Prakiraan resmi BMKG hanya tersedia maksimal 3 hari ke depan."
}
User: "Halo, apa kabar?" (Tanpa Data BMKG)
Jawaban:
{
  "kota": null,
  "jawaban": "Halo! Saya SkyMind, asisten prakiraan cuaca Anda. Mau tahu info cuaca di daerah mana hari ini? Ada yang bisa saya bantu?",
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

          cuaca_days = raw_bmkg["data"][0].get("cuaca", [])

          if cuaca_days:
            cuaca_list = cuaca_days[0] if len(cuaca_days) > 0 else []
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

            labels = ["Hari ke-1 (Hari Ini)", "Hari ke-2 (Besok)", "Hari ke-3 (Lusa)"]
            rincian_hari = []
            for i, day_slots in enumerate(cuaca_days[:3]):
              label = labels[i] if i < len(labels) else f"Hari ke-{i+1}"
              if not day_slots:
                continue
              tgl = day_slots[0].get("local_datetime", day_slots[0].get("datetime", "")).split()[0]
              slot_strs = []
              for slot in day_slots:
                dt_str = slot.get("local_datetime", slot.get("datetime", ""))
                jam = dt_str.split()[1][:5] if len(dt_str.split()) > 1 else dt_str
                w_desc = slot.get("weather_desc", "-")
                w_temp = slot.get("t", "-")
                w_hu = slot.get("hu", "-")
                w_ws = slot.get("ws", "-")
                w_wd = slot.get("wd", "-")
                slot_strs.append(f"    * Jam {jam} WIB: {w_desc}, Suhu {w_temp}°C, Kelembapan {w_hu}%, Angin {w_ws} km/jam ({w_wd})")

              rincian_hari.append(f"  [{label} - Tanggal {tgl}]:\n" + "\n".join(slot_strs))

            jadwal_cuaca_text = "\n\n".join(rincian_hari)

            weather_context = f"""
            DATA RESMI PRAKIRAAN CUACA BMKG (MAKSIMAL 3 HARI: HARI INI, BESOK, LUSA):
            - Wilayah Terdeteksi: Kelurahan/Desa {adm4_info.get('kelurahan') or '-'}, Kecamatan {adm4_info.get('kecamatan') or '-'}, {adm4_info.get('kabupaten') or '-'}, {adm4_info.get('provinsi') or '-'}
            {catatan_lokasi}

            RINCIAN PRAKIRAAN CUACA 3 HARI DARI BMKG:
{jadwal_cuaca_text}

            BATASAN PENTING BMKG:
            - BMKG HANYA menyediakan data prakiraan resmi untuk maksimal 3 hari ke depan (Hari Ini, Besok, dan Lusa di atas).
            - JIKA USER TIDAK MENYEBUTKAN WAKTU/TANGGAL: Selalu gunakan data waktu/slot jam pertama yang tersedia pada Hari ke-1 (cuaca saat ini / terdekat).
            - Jika user menanyakan cuaca hari ini / saat ini, jawab menggunakan data Hari ke-1 (slot jam terdekat).
            - Jika user menanyakan cuaca besok atau lusa, jawab menggunakan data Hari ke-2 atau Hari ke-3 sesuai waktu/jam yang ditanyakan (pagi/siang/sore/malam).
            - Jika user menanyakan cuaca DI LUAR 3 HARI KE DEPAN (misal: 4 hari lagi, minggu depan, bulan depan, dsb.), jelaskan secara ramah bahwa data resmi prakiraan BMKG hanya tersedia maksimal hingga 3 hari ke depan.
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
        "max_tokens": 2000,
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
        "max_tokens": 300
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
    
