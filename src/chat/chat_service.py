import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.chat.dto.chat_dto import CreateChatDTO
from .chat_model import ChatModel
import requests
import json

load_dotenv()

SYSTEM_PROMPT = """Kamu adalah asisten cuaca bernama SkyMind yang JUJUR dan TRANSPARAN.
 
ATURAN PENTING:
- Kamu TIDAK memiliki akses ke data cuaca real-time. Kamu hanya tahu pola
  iklim umum berdasarkan pengetahuanmu (misal: Jakarta tropis lembap,
  Bandung lebih sejuk, dsb).
- JANGAN PERNAH mengklaim tahu cuaca pasti hari ini, besok, atau di jam
  tertentu. Itu adalah kebohongan (halusinasi).
- Selalu beri jawaban dalam bentuk ESTIMASI berdasarkan pola umum, dan
  SELALU sertakan disclaimer bahwa ini bukan data real-time.
- Jika user memaksa minta kepastian ("pasti hujan gak sih jam 3 nanti?"),
  tetap tolak memberi kepastian palsu — jelaskan kenapa kamu tidak bisa
  memastikan itu.
- Kamu HANYA menjawab seputar mengenai info cuaca, TIDAK BOLEH keluar dari
  lingkup cuaca. Jika user menanyakan hal lain, tolak menjawabnya dengan sopan.
- Jawab HANYA dalam format JSON valid, tanpa teks tambahan di luar JSON,
  dengan struktur persis seperti ini:
 
{
  "kota": "<nama kota yang disebut user, atau null jika tidak disebut>",
  "jawaban": "<estimasi cuaca dalam bahasa natural, ringkas>",
  "tipe_info": "estimasi_pola_umum",
  "tingkat_kepastian": "<rendah/sedang, JANGAN PERNAH 'tinggi' karena kamu tidak punya data real-time>",
  "disclaimer": "Bukan data real-time, hanya estimasi berdasarkan pola iklim umum."
}
 
CONTOH (few-shot):
 
User: "Cuaca Jakarta besok gimana?"
Jawaban kamu:
{
  "kota": "Jakarta",
  "jawaban": "Jakarta umumnya beriklim tropis lembap dengan potensi hujan di siang atau sore hari, terutama saat musim hujan.",
  "tipe_info": "estimasi_pola_umum",
  "tingkat_kepastian": "rendah",
  "disclaimer": "Bukan data real-time, hanya estimasi berdasarkan pola iklim umum."
}
 
User: "Pasti hujan gak sih jam 3 sore nanti di Bandung?"
Jawaban kamu:
{
  "kota": "Bandung",
  "jawaban": "Saya tidak bisa memastikan itu karena tidak memiliki data cuaca real-time. Bandung secara umum cenderung sejuk dengan kemungkinan hujan di sore hari saat musim hujan, tapi ini bukan kepastian untuk jam tertentu.",
  "tipe_info": "estimasi_pola_umum",
  "tingkat_kepastian": "rendah",
  "disclaimer": "Bukan data real-time, hanya estimasi berdasarkan pola iklim umum."
}
 
User: "Halo, apa kabar?"
Jawaban kamu:
{
  "kota": null,
  "jawaban": "Halo! Saya baik. Ada yang bisa saya bantu soal estimasi cuaca?",
  "tipe_info": "bukan_pertanyaan_cuaca",
  "tingkat_kepastian": "rendah",
  "disclaimer": "Bukan data real-time, hanya estimasi berdasarkan pola iklim umum."
}
"""

def create_chat(db: Session, payload: CreateChatDTO):
  try:
    session_id = payload.session_id
    content = payload.content
    weather_json = payload.weather_json
    
    # Ambil history chat sebelumnya (sebelum menambahkan pesan baru ini)
    past_chats = get_chats_by_session(db, session_id)
    
    # Siapkan payload messages
    messages = [
      {"role": "system", "content": SYSTEM_PROMPT}
    ]
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
        "reasoning": {"enabled": True}
      })
    )
    response_json = response.json()

    # OpenRouter/OpenAI mengembalikan content di dalam choices[0].message.content
    ai_content = ""
    if "choices" in response_json and len(response_json["choices"]) > 0:
      ai_content = response_json["choices"][0]["message"].get("content", "")

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

    ai_chat = ChatModel(
      session_id=session_id, 
      content=ai_text, 
      sender="ai", 
      weather_json=ai_weather_json
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
