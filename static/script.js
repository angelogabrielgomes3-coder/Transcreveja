const uploadForm = document.getElementById("upload-form");
const audioInput = document.getElementById("audioFile");
const selectedFileText = document.getElementById("selected-file");
const progressContainer = document.getElementById("progress-container");
const uploadProgress = document.getElementById("upload-progress");
const statusBox = document.getElementById("status-box");
const statusText = document.getElementById("status-text");
const resultPanel = document.getElementById("result-panel");
const processingMeta = document.getElementById("processing-meta");
const transcriptText = document.getElementById("transcript-text");
const copyButton = document.getElementById("copy-button");
const downloadButton = document.getElementById("download-button");

let transcriptFilename = "";
let currentTranscript = "";

const allowedTypes = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg", "audio/x-ogg"];
const maxFileSize = 150 * 1024 * 1024; // 150 MB

function showStatus(message) {
  statusBox.hidden = false;
  statusText.textContent = message;
}

function hideStatus() {
  statusBox.hidden = true;
  statusText.textContent = "";
}

function updateProgress(value) {
  uploadProgress.style.width = `${value}%`;
}

function updateSelectedFile(filename) {
  selectedFileText.textContent = filename || "Nenhum arquivo selecionado";
}

audioInput.addEventListener("change", () => {
  const file = audioInput.files[0];
  if (!file) {
    updateSelectedFile("");
    return;
  }

  if (!allowedTypes.includes(file.type)) {
    showStatus("Formato inválido. Utilize mp3, wav, m4a ou ogg.");
    audioInput.value = "";
    updateSelectedFile("");
    return;
  }

  if (file.size === 0) {
    showStatus("O áudio está vazio. Escolha outro arquivo.");
    audioInput.value = "";
    updateSelectedFile("");
    return;
  }

  if (file.size > maxFileSize) {
    showStatus("O arquivo excede 150MB. Escolha um arquivo menor.");
    audioInput.value = "";
    updateSelectedFile("");
    return;
  }

  hideStatus();
  updateSelectedFile(file.name);
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = audioInput.files[0];

  if (!file) {
    showStatus("Selecione um arquivo de áudio antes de enviar.");
    return;
  }

  resultPanel.hidden = true;
  processingMeta.textContent = "";
  transcriptText.textContent = "";
  transcriptFilename = "";
  currentTranscript = "";

  const formData = new FormData();
  formData.append("audio_file", file);

  progressContainer.hidden = false;
  updateProgress(10);
  showStatus("Enviando arquivo...");

  try {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/transcribe", true);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        updateProgress(percent);
      }
    };

    xhr.onreadystatechange = () => {
      if (xhr.readyState === XMLHttpRequest.HEADERS_RECEIVED) {
        updateProgress(100);
        showStatus("Transcrevendo áudio...");
      }
    };

    xhr.onload = () => {
      progressContainer.hidden = true;
      updateProgress(0);
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText);
          processingMeta.textContent = `Processado em ${response.elapsed_seconds} s · ${response.duration_seconds} s de áudio · ${response.word_count} palavras · ${response.character_count} caracteres`;
          transcriptText.textContent = response.transcript;
          transcriptFilename = response.transcript_file;
          currentTranscript = response.transcript;
          resultPanel.hidden = false;
          showStatus("Transcrição concluída com sucesso.");
        } catch (error) {
          showStatus("Resposta inválida do servidor. Tente enviar novamente.");
        }
      } else {
        let message = "Ocorreu um erro durante a transcrição.";
        try {
          const errorData = JSON.parse(xhr.responseText || "{}");
          message = errorData.detail || message;
        } catch (_) {
          if (xhr.responseText) {
            message = xhr.responseText;
          }
        }
        showStatus(message);
      }
    };

    xhr.onerror = () => {
      progressContainer.hidden = true;
      updateProgress(0);
      showStatus("Falha na requisição. Tente novamente mais tarde.");
    };

    xhr.ontimeout = () => {
      progressContainer.hidden = true;
      updateProgress(0);
      showStatus("Tempo limite de upload excedido. Tente novamente.");
    };

    xhr.send(formData);
  } catch (error) {
    progressContainer.hidden = true;
    updateProgress(0);
    showStatus("Erro inesperado ao enviar o arquivo.");
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentTranscript) return;

  try {
    await navigator.clipboard.writeText(currentTranscript);
    showStatus("Transcrição copiada para a área de transferência.");
  } catch (error) {
    showStatus("Não foi possível copiar o texto automaticamente.");
  }
});

downloadButton.addEventListener("click", () => {
  if (!transcriptFilename) return;

  const anchor = document.createElement("a");
  anchor.href = `/download/${encodeURIComponent(transcriptFilename)}`;
  anchor.download = transcriptFilename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
});
