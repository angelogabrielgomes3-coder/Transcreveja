# Instalação no Windows

## 1. Instalar Python 3.11

**Baixe de:** https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe

Ou acesse https://www.python.org/downloads/windows/ e baixe Python 3.11.

**Importante:** Na tela de instalação, **marque a opção "Add Python to PATH"** ✓

## 2. Instalar ffmpeg (necessário para Whisper)

Baixe o ffmpeg de: https://ffmpeg.org/download.html

**No Windows:**
- Extraia a pasta baixada
- Adicione o caminho do ffmpeg ao PATH do Windows, OU
- Copie os arquivos para `C:\Windows\System32\`

Para verificar se está instalado:
```bash
ffmpeg -version
```

## 3. Criar ambiente virtual e instalar dependências

Abra o terminal (CMD ou PowerShell) dentro da pasta do projeto `transcreveja` e execute:

```bash
cd C:\Users\Angelo Gabriel Gomes\Documents\Transcritor\transcreveja
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Nota:** Na primeira vez que rodar Whisper, ele vai baixar o modelo (~1.4 GB), pode levar alguns minutos.

## 4. Rodar o servidor

```bash
cd C:\Users\Angelo Gabriel Gomes\Documents\Transcritor\transcreveja
.venv\Scripts\activate
uvicorn main:app --reload
```

A aplicação estará disponível em: http://localhost:8000

## Se der erro "ffmpeg not found"

Se o servidor não encontrar ffmpeg/ffprobe, instale o binário do ffmpeg e adicione-o ao PATH.

### Instalar via Chocolatey (recomendado)

```bash
choco install ffmpeg
```

### Ou instale manualmente

1. Baixe o pacote em https://ffmpeg.org/download.html
2. Extraia o conteúdo
3. Adicione a pasta `bin` do ffmpeg ao PATH do Windows
4. Feche e reabra o terminal para carregar a nova variável de ambiente

> Observação importante: se você já tiver um caminho antigo no PATH que não existe mais, remova-o. Um caminho inválido pode fazer o PowerShell/CMD falhar mesmo com outra instalação de ffmpeg presente.

Se você vir:

```text
'ffmpeg' não é reconhecido como um comando interno ou externo,
um programa operável ou um arquivo em lotes.
```

então o `ffmpeg` não está disponível no PATH do PowerShell/CMD atual.

### Verificação

```bash
ffmpeg -version
```

Se isso ainda falhar, adicione manualmente o caminho da pasta `bin`, por exemplo:

```powershell
setx PATH "%PATH%;C:\ProgramData\chocolatey\bin"
```

ou, se você instalou via WinGet, adicione:

```powershell
setx PATH "%PATH%;%USERPROFILE%\AppData\Local\Microsoft\WinGet\Links"
```

ou use as Configurações de Sistema > Variáveis de Ambiente.

### Importante

`pip install pydub` instala apenas a biblioteca Python. Ele não instala o `ffmpeg` ou `ffprobe`.

---

**Dúvidas?** Todos os erros devem indicar qual passo falhou. Siga os passos na ordem!
