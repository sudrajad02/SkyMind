# WeatherChat Simple

WeatherChat Simple adalah aplikasi *backend* berbasis **FastAPI** yang menyediakan layanan chat interaktif untuk membicarakan cuaca. Aplikasi ini terhubung dengan model AI eksternal (melalui OpenRouter format) untuk bertindak sebagai **SkyMind**, sebuah asisten cuaca yang dirancang secara jujur dan transparan untuk memberikan estimasi pola iklim umum (karena tidak memiliki akses ke data cuaca real-time).

Aplikasi ini mendukung fitur percakapan bersambung (menjaga konteks obrolan atau *chat history*) berdasarkan *Session*.

## Fitur Utama
* **Session Management**: Membuat dan mengelola sesi percakapan agar konteks riwayat chat (`chat history`) bisa diteruskan secara berkelanjutan ke AI.
* **Chat Integration dengan AI**: Integrasi API AI dengan *System Prompt* ketat yang memastikan AI:
  * Hanya menjawab topik cuaca.
  * Murni memberikan estimasi dan bukan data *real-time*.
  * Mengembalikan data dalam format JSON yang terstruktur.
* **Database Relasional**: Menyimpan riwayat obrolan (pesan dari pengguna maupun asisten) dengan menggunakan **SQLAlchemy**.

## Teknologi yang Digunakan
* **Python 3.10+** (Direkomendasikan menggunakan [uv](https://github.com/astral-sh/uv) sebagai package manager)
* **FastAPI** (Framework Web)
* **SQLAlchemy** (ORM untuk Database)
* **Pydantic** (Validasi DTO & Request Body)
* **Uvicorn** (ASGI Server)
* **Requests** (HTTP Client untuk memanggil API AI)

## Prasyarat
* Python terinstal di sistem Anda.
* Server Database yang kompatibel dengan SQLAlchemy (seperti MySQL, PostgreSQL, atau SQLite).
* API Key dari provider AI (seperti OpenRouter atau OpenAI).

## Cara Instalasi

1. **Clone repository ini**
   ```bash
   git clone <url-repo-anda>
   cd weatherchat-simple
   ```

2. **Buat file Environment Variables (`.env`)**
   Buat file bernama `.env` di folder *root* proyek Anda dan isi dengan variabel berikut:
   ```env
   # Database Configuration
   DATABASE_URL=mysql+pymysql://username:password@localhost/nama_database
   
   # AI API Configuration
   AI_URL=https://openrouter.ai/api/v1/chat/completions  # Atau endpoint AI lainnya
   API_KEY=your_api_key_here
   MODEL=nama_model_ai_pilihan_anda (contoh: openai/gpt-3.5-turbo)
   ```

3. **Install dependensi**
   Jika menggunakan `uv`:
   ```bash
   uv sync
   ```
   Atau jika menggunakan `pip`:
   ```bash
   pip install -r requirements.txt
   ```

## Cara Menjalankan Aplikasi

Aplikasi bisa dijalankan menggunakan Uvicorn. Jika Anda menggunakan `uv`, jalankan perintah berikut:

```bash
uv run uvicorn main:app --reload
```

Server akan berjalan di `http://localhost:8000`. Anda juga dapat mengakses dokumentasi interaktif otomatis (Swagger UI) di `http://localhost:8000/docs`.

## Endpoint API

### 1. Session (`/session`)
* **`POST /session/`**
  Membuat sesi obrolan baru.
  * **Payload / Body:**
    ```json
    {
      "title": "Percakapan Cuaca Jakarta"
    }
    ```

### 2. Chat (`/chat`)
* **`POST /chat/`**
  Mengirim pesan ke asisten AI di sesi tertentu. Sistem secara otomatis menyertakan *history* pesan sebelumnya ke dalam *request* AI untuk menjaga konteks.
  * **Payload / Body:**
    ```json
    {
      "session_id": 1,
      "content": "Besok cuaca di Jakarta biasanya seperti apa ya?"
    }
    ```
* **`GET /chat/{session_id}`**
  Mengambil seluruh riwayat pesan (dari pengguna maupun asisten) berdasarkan ID sesi.

## Arsitektur & Struktur Proyek
Aplikasi ini dipecah dengan memisahkan *concern* pada tiga layer utama (seperti *Clean Architecture* sederhana):
* **Controller**: Menerima request HTTP dan memvalidasi tipe data (DTO).
* **Service**: Berisi logika bisnis (menyusun Payload AI, parsing respons JSON, mengatur history chat).
* **Model**: Berisi skema *database* SQLAlchemy.

```text
weatherchat-simple/
├── .env
├── .gitignore
├── main.py                     # Entry point & inisialisasi aplikasi (FastAPI + DB creation)
├── pyproject.toml
├── src/
│   ├── config/
│   │   └── db.py               # Konfigurasi koneksi Database Engine
│   ├── session/
│   │   ├── dto/session_dto.py  # Data Transfer Object untuk Session
│   │   ├── session_controller.py
│   │   ├── session_model.py
│   │   └── session_service.py
│   └── chat/
│       ├── dto/chat_dto.py     # Data Transfer Object untuk Chat
│       ├── chat_controller.py
│       ├── chat_model.py
│       └── chat_service.py
```
