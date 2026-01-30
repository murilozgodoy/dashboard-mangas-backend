"""
Conexão com MongoDB.
"""
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from config import MONGODB_URL, DB_NAME, POLPA_COLLECTION, EXTRATO_COLLECTION, UPLOADS_LOG_COLLECTION

_client: MongoClient | None = None


def get_db() -> Database:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URL)
    return _client[DB_NAME]


def get_polpa_collection() -> Collection:
    return get_db()[POLPA_COLLECTION]


def get_extrato_collection() -> Collection:
    return get_db()[EXTRATO_COLLECTION]


def get_collection(tipo: str):
    """Retorna a coleção para o tipo (polpa ou extrato)."""
    if tipo == "polpa":
        return get_polpa_collection()
    if tipo == "extrato":
        return get_extrato_collection()
    raise ValueError(f"tipo inválido: {tipo}. Use 'polpa' ou 'extrato'.")


def get_uploads_log_collection() -> Collection:
    return get_db()[UPLOADS_LOG_COLLECTION]
