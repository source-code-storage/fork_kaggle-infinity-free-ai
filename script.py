import os
import re
import time
import shutil
import subprocess

print("=" * 70)
print(" SETUP COMPLETO: GEMMA 4 E4B + OPEN WEBUI + CLOUDFLARE (2x T4)")
print("=" * 70)

# 1. Limpeza total de processos anteriores
print("\n[1/6] Encerrando processos e liberando portas/VRAM...")
!pkill -9 -f ollama
!pkill -9 -f open-webui
!pkill -9 -f cloudflared
time.sleep(2)

# 2. Configurar variáveis de ambiente (armazenar no disco do Kaggle)
os.environ["OLLAMA_MODELS"] = "/kaggle/working/ollama_models"
os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
os.environ["OLLAMA_ORIGINS"] = "*"
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
os.environ["DATA_DIR"] = "/kaggle/working/open_webui_data"
os.environ["WEBUI_AUTH"] = "False"  # Desativa login inicial para acesso direto

env = os.environ.copy()
OLLAMA_LOG = "/kaggle/working/ollama.log"
OPEN_WEBUI_LOG = "/kaggle/working/open-webui.log"

ollama_log_file = open(OLLAMA_LOG, "w", buffering=1)
webui_log_file = open(OPEN_WEBUI_LOG, "w", buffering=1)

# 3. Instalar pacotes de sistema, Ollama, Open WebUI e Cloudflared
print("\n[2/6] Instalando dependências, Ollama, Open WebUI e Cloudflared...")
!sudo apt-get update -qq -y && sudo apt-get install -y -qq zstd wget lshw > /dev/null 2>&1
!curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
!sudo pip install -q uv && sudo uv pip install --system -q open-webui

!wget -q -nc https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!sudo dpkg -i cloudflared-linux-amd64.deb > /dev/null 2>&1

# 4. Iniciar o daemon do Ollama
print("\n[3/6] Iniciando daemon do Ollama...")
ollama_proc = subprocess.Popen(
    ["sudo", "ollama", "serve"],
    env=env,
    stdout=ollama_log_file,
    stderr=subprocess.STDOUT
)
time.sleep(5)

if ollama_proc.poll() is not None:
    ollama_log_file.flush()
    print("\n❌ Ollama falhou ao iniciar:")
    !tail -n 100 /kaggle/working/ollama.log
    raise RuntimeError(
        f"Ollama encerrou com código {ollama_proc.returncode}"
    )

# 5. Baixar o modelo Gemma 4 E4B
MODEL = "gemma4:e4b"
print(f"\n[4/6] Baixando {MODEL} no Ollama...")
pull_res = subprocess.run(f"sudo ollama pull {MODEL}", shell=True)
if pull_res.returncode != 0:
    # Fallback caso a tag na biblioteca use variação de nomenclatura
    MODEL = "gemma4:4b"
    print(f"Tentando tag alternativa: {MODEL}...")
    !ollama pull {MODEL}

# 6. Iniciar o servidor Open WebUI na porta 8080
print("\n[5/6] Iniciando interface Open WebUI...")
webui_proc = subprocess.Popen(
    ["sudo", "open-webui", "serve", "--port", "8080"],
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
time.sleep(10)

if webui_proc.poll() is not None:
    webui_log_file.flush()
    print("\n❌ Open WebUI falhou ao iniciar:")
    !tail -n 100 /kaggle/working/open-webui.log
    raise RuntimeError(
        f"Open WebUI encerrou com código {webui_proc.returncode}"
    )
    
# 7. Criar túnel Cloudflare para a porta 8080 do Open WebUI
print("\n[6/6] Criando túnel público HTTPS Cloudflare...")
tunnel_proc = subprocess.Popen(
    [
        "sudo", "cloudflared", "tunnel",
        "--url", "http://127.0.0.1:8080",
        "--http-host-header", "localhost"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Capturar a URL pública
public_url = None
for _ in range(35):
    line = tunnel_proc.stderr.readline()
    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
    if match:
        public_url = match.group(0)
        break
    time.sleep(0.5)

print("\n" + "=" * 70)
if public_url:
    print("🚀 OPEN WEBUI PRONTO E ONLINE!")
    print(f"👉 URL de Acesso: {public_url}")
    print(f"👉 Modelo:        {MODEL}")
    print("=" * 70)
    print("\nAbra o link acima no navegador para conversar com o Gemma 4.")
else:
    print("⚠️ Não foi possível capturar a URL automaticamente. Verifique os logs do túnel.")
print("=" * 70)
