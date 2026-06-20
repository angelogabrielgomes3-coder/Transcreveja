import asyncio
import os
import time
from pathlib import Path
from shutil import which
from typing import Optional

import whisper
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Diretórios de armazenamento
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
TRANSCRIPT_FOLDER = BASE_DIR / "transcripts"
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}
MAX_DURATION_SECONDS = 10 * 60  # 10 minutos
MAX_FILE_SIZE_BYTES = 150 * 1024 * 1024  # 150 MB máximo por upload

app = FastAPI(title="TranscreveJá", version="1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Carrega o modelo Whisper localmente na inicialização
# Futuramente, aqui pode incluir seleção de modelo Premium ou modos avançados
# Futuro: adicionar suporte a diferentes idiomas e perfil de voz premium
# Futuro: carregar modelo condicional para planos de maior desempenho
model = whisper.load_model("large")


class TranscriptionResult(BaseModel):
    transcript: str
    duration_seconds: float
    character_count: int
    word_count: int
    elapsed_seconds: float
    filename: str
    transcript_file: str


def ensure_directories() -> None:
    """Garante que as pastas de uploads e transcrições existam."""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Valida se o arquivo tem uma extensão suportada."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file: UploadFile, destination: Path) -> Path:
    """Salva o arquivo enviado no disco."""
    with destination.open("wb") as buffer:
        for chunk in iter(lambda: file.file.read(1024 * 1024), b""):
            buffer.write(chunk)
    return destination


def locate_ffmpeg() -> Optional[str]:
    # Tenta usar o PATH do sistema primeiro.
    ffmpeg_path = which("ffmpeg") or which("avconv")
    if ffmpeg_path:
        return ffmpeg_path

    # Tenta alguns locais comuns no Windows.
    common_paths = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Users\All Users\chocolatey\bin\ffmpeg.exe",
        r"C:\Users\Angelo Gabriel Gomes\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for path in common_paths:
        if Path(path).exists():
            return path

    return None


def is_ffmpeg_available() -> bool:
    return locate_ffmpeg() is not None


def ffmpeg_error_message() -> str:
    return (
        "Não foi possível ler a duração do áudio. "
        "Instale ffmpeg/ffprobe e adicione ao PATH. "
        "Veja https://ffmpeg.org/download.html"
    )


async def get_audio_duration(filepath: Path) -> float:
    """Calcula a duração do áudio em segundos.

    Para arquivos WAV, usa o módulo wave para evitar dependência de ffmpeg.
    Para outros formatos, tenta o whisper.load_audio / pydub como fallback.
    """
    suffix = filepath.suffix.lower()
    if suffix == ".wav":
        import wave

        with wave.open(filepath, "rb") as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
            if rate == 0:
                raise ValueError("Taxa de amostragem inválida.")
            return frames / rate

    # Garante ffmpeg para formatos não-WAV como m4a.
    ffmpeg_path = locate_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError(
            "Não foi possível ler a duração do áudio. "
            "Instale ffmpeg/ffprobe e adicione ao PATH."
        )

    os.environ["FFMPEG_BINARY"] = ffmpeg_path
    os.environ["FFPROBE_BINARY"] = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(filepath))
        return audio.duration_seconds
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível ler a duração do áudio. "
            "Instale ffmpeg/ffprobe e adicione ao PATH."
        ) from exc


def transcribe_audio(filepath: Path) -> str:
    """Transcreve o áudio utilizando Whisper localmente."""
    try:
        result = model.transcribe(str(filepath), fp16=False)
        return result.get("text", "").strip()
    except Exception as exc:
        raise RuntimeError(f"Falha ao transcrever o áudio: {exc}") from exc


def build_transcript_filename(source_filename: str) -> str:
    """Gera nome de arquivo TXT para a transcrição."""
    base_name = Path(source_filename).stem
    timestamp = int(time.time())
    return f"{base_name}_{timestamp}.txt"


def save_transcript_file(text: str, transcript_path: Path) -> None:
    """Salva o texto transcrito em um arquivo TXT."""
    with transcript_path.open("w", encoding="utf-8") as file:
        file.write(text)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_directories()
    # Futuro: inicializar conexões com banco de dados ou cache aqui
    # Futuro: integrar sistema de login e planos premium
    # Futuro: inserir configuração para Google AdSense no front-end


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.post("/transcribe")
async def transcribe(request: Request, audio_file: UploadFile = File(...)) -> JSONResponse:
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi fornecido.")

    if not allowed_file(audio_file.filename):
        raise HTTPException(
            status_code=415,
            detail="Formato inválido. Envie um arquivo mp3, wav, m4a ou ogg.",
        )

    spool_max_size = getattr(audio_file, "spool_max_size", None)
    if spool_max_size is not None and spool_max_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande.")

    # Carrega o arquivo em disco primeiro
    filename = Path(audio_file.filename).name
    save_path = UPLOAD_FOLDER / filename
    try:
        save_upload(audio_file, save_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar o arquivo enviado.")

    file_size = save_path.stat().st_size
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio.")

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Limite de 150 MB.")

    # Futuro: aplicar checagem de arquivos em lote com contas premium
    try:
        duration_seconds = await get_audio_duration(save_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível ler a duração do áudio.")

    if duration_seconds > MAX_DURATION_SECONDS:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="O áudio ultrapassa o limite de 10 minutos.")

    start_time = time.time()
    try:
        transcript_text = await asyncio.to_thread(transcribe_audio, save_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not transcript_text:
        raise HTTPException(status_code=500, detail="Falha na transcrição. O áudio retornou texto vazio.")

    elapsed_seconds = round(time.time() - start_time, 2)
    character_count = len(transcript_text)
    word_count = len(transcript_text.split())
    transcript_filename = build_transcript_filename(filename)
    transcript_path = TRANSCRIPT_FOLDER / transcript_filename
    save_transcript_file(transcript_text, transcript_path)

    response = TranscriptionResult(
        transcript=transcript_text,
        duration_seconds=round(duration_seconds, 2),
        character_count=character_count,
        word_count=word_count,
        elapsed_seconds=elapsed_seconds,
        filename=filename,
        transcript_file=transcript_filename,
    )
    return JSONResponse(response.dict())


@app.get("/download/{filename}")
async def download_transcript(filename: str) -> FileResponse:
    transcript_path = TRANSCRIPT_FOLDER / filename
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de transcrição não encontrado.")
    return FileResponse(transcript_path, media_type="text/plain", filename=filename)
