"""
Configuração do projeto e contrato das planilhas Excel (polpa e extrato).
"""
import os
from pathlib import Path

# Carrega variáveis do .env (se existir)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# MongoDB
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "dashboard_mangas")
POLPA_COLLECTION = "polpa"
EXTRATO_COLLECTION = "extrato"
UPLOADS_LOG_COLLECTION = "uploads_log"

# Tipos de planilha aceitos
TIPOS_VALIDOS = ["polpa", "extrato"]

# Contrato POLPA CONGELADA (primeira aba, cabeçalho na primeira linha)
COLUNAS_POLPA = [
    "data_pedido",
    "canal",
    "regiao_destino",
    "cliente_segmento",
    "quantidade_kg",
    "preco_unitario_brl_kg",
    "logistica_brl",
    "desconto_brl",
    "lote_id",
    "indice_qualidade_1a10",
    "perda_processamento_pct",
    "nps_0a10",
]

# Contrato EXTRATO DE MANGA (primeira aba, cabeçalho na primeira linha)
COLUNAS_EXTRATO = [
    "data_pedido",
    "canal",
    "regiao_destino",
    "cliente_segmento",
    "quantidade_litros",
    "preco_unitario_brl_l",
    "concentracao_ativa_pct",
    "tipo_solvente",
    "indice_cor_1a10",
    "indice_pureza_1a10",
    "certificacao_exigida",
    "nps_0a10",
]

# Extensões aceitas
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
