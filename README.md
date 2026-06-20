# TranscreveJá

Aplicação FastAPI para transcrição de áudio usando Whisper.

Setup rápido (Windows):

```powershell
cd C:\Users\Angelo Gabriel Gomes\Documents\Transcritor\transcreveja
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Executar localmente:

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload
# acessar http://127.0.0.1:8000
```

Antes de subir para o GitHub, confirme que `.gitignore` está correto (evite subir `.venv`).
