"""
Leitura, validação e normalização de planilhas Excel para importação (polpa e extrato).
"""
import io
import datetime
import pandas as pd
from typing import Any, Literal

from config import (
    COLUNAS_POLPA,
    COLUNAS_EXTRATO,
    ALLOWED_EXTENSIONS,
)

TipoPlanilha = Literal["polpa", "extrato"]


def _extensao_valida(filename: str) -> bool:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS


def validar_arquivo(filename: str, content: bytes) -> list[str]:
    erros: list[str] = []
    if not filename or not content:
        erros.append("Arquivo vazio ou nome ausente.")
        return erros
    if not _extensao_valida(filename):
        erros.append(f"Extensão inválida. Aceitas: {', '.join(ALLOWED_EXTENSIONS)}")
        return erros
    return erros


def _colunas_obrigatorias(tipo: TipoPlanilha) -> list[str]:
    return COLUNAS_POLPA if tipo == "polpa" else COLUNAS_EXTRATO


def validar_colunas(df: pd.DataFrame, tipo: TipoPlanilha) -> list[str]:
    """
    Verifica se todas as colunas obrigatórias do tipo existem.
    """
    erros: list[str] = []
    obrigatorias = _colunas_obrigatorias(tipo)
    colunas_planilha = [str(c).strip().lower() for c in df.columns]
    for obrig in obrigatorias:
        if obrig.lower() not in colunas_planilha:
            erros.append(f"Coluna obrigatória ausente ({tipo}): {obrig}")
    return erros


def _normalizar_nome_coluna(s: str) -> str:
    return str(s).strip().lower()


# Mapeamento nome do mês (aba) -> número (1-12)
MESES_ABA: dict[str, int] = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _extrair_mes_da_aba(nome_aba: str) -> int | None:
    """Extrai o mês do nome da aba (ex: 'Polpa congelada - Jul' -> 7)."""
    nome = nome_aba.strip().lower()
    for mes_str, num in MESES_ABA.items():
        if mes_str in nome:
            return num
    return None


def _extrair_tipo_da_aba(nome_aba: str) -> TipoPlanilha | None:
    """Extrai o tipo do nome da aba: 'polpa' ou 'extrato'."""
    nome = nome_aba.strip().lower()
    if "polpa" in nome:
        return "polpa"
    if "extrato" in nome:
        return "extrato"
    return None


def ler_excel(content: bytes, filename: str) -> tuple[pd.DataFrame | None, list[str]]:
    """
    Lê o Excel/CSV (primeira aba no caso de xlsx).
    Normaliza nomes das colunas para minúsculas.
    """
    erros: list[str] = []
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
    except Exception as e:
        erros.append(f"Erro ao ler arquivo: {e}")
        return None, erros

    if df is None or df.empty:
        erros.append("Planilha sem dados.")
        return None, erros

    df.columns = [_normalizar_nome_coluna(c) for c in df.columns]
    return df, erros


def ler_excel_todas_abas(
    content: bytes,
    filename: str,
    year: int,
) -> list[tuple[str, pd.DataFrame, TipoPlanilha, str]]:
    """
    Lê todas as abas do Excel. Para cada aba: infere tipo (Polpa/Extrato) e mês pelo nome.
    Retorna lista de (nome_aba, df, tipo, competencia).
    Abas cujo nome não contiver 'polpa' ou 'extrato', ou não tiver mês (Jan-Dez), são ignoradas.
    """
    if filename.lower().endswith(".csv"):
        return []
    result: list[tuple[str, pd.DataFrame, TipoPlanilha, str]] = []
    try:
        xl = pd.ExcelFile(io.BytesIO(content))
    except Exception:
        return []
    for sheet_name in xl.sheet_names:
        tipo = _extrair_tipo_da_aba(sheet_name)
        mes = _extrair_mes_da_aba(sheet_name)
        if tipo is None or mes is None:
            continue
        try:
            df = pd.read_excel(xl, sheet_name=sheet_name)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df.columns = [_normalizar_nome_coluna(c) for c in df.columns]
        competencia = f"{year:04d}-{mes:02d}"
        result.append((sheet_name, df, tipo, competencia))
    return result


def limpar_e_normalizar(df: pd.DataFrame, tipo: TipoPlanilha) -> pd.DataFrame:
    """
    Mantém apenas colunas do contrato do tipo, remove linhas vazias,
    converte numéricos e troca NaN por None.
    """
    obrigatorias = _colunas_obrigatorias(tipo)
    cols_presentes = [c for c in df.columns if _normalizar_nome_coluna(c) in [x.lower() for x in obrigatorias]]
    if not cols_presentes:
        return pd.DataFrame()
    df = df[cols_presentes].copy()

    df = df.dropna(how="all")
    df = df[df.astype(str).ne("").any(axis=1)]

    # Colunas numéricas por tipo
    if tipo == "polpa":
        numericas = [
            "quantidade_kg", "preco_unitario_brl_kg", "logistica_brl", "desconto_brl",
            "indice_qualidade_1a10", "perda_processamento_pct", "nps_0a10",
        ]
    else:
        numericas = [
            "quantidade_litros", "preco_unitario_brl_l", "concentracao_ativa_pct",
            "indice_cor_1a10", "indice_pureza_1a10", "nps_0a10",
        ]
    for col in numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.where(pd.notna(df), None)
    return df


def _valor_nativo(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (pd.Timestamp, datetime.datetime)):
        return v.isoformat() if hasattr(v, "isoformat") else str(v)
    if hasattr(v, "item"):
        return v.item()
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def _calcular_receita(row: dict, tipo: TipoPlanilha) -> float | None:
    """Calcula receita para KPIs/gráficos (armazenada no documento)."""
    try:
        if tipo == "polpa":
            q = row.get("quantidade_kg")
            p = row.get("preco_unitario_brl_kg")
            log = row.get("logistica_brl") or 0
            desc = row.get("desconto_brl") or 0
            if q is None or p is None:
                return None
            return float(q) * float(p) - float(log) - float(desc)
        else:
            q = row.get("quantidade_litros")
            p = row.get("preco_unitario_brl_l")
            if q is None or p is None:
                return None
            return float(q) * float(p)
    except (TypeError, ValueError):
        return None


def dataframe_para_documentos(
    df: pd.DataFrame,
    competencia: str,
    source_file: str,
    tipo: TipoPlanilha,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Converte cada linha em documento MongoDB com metadados e campo receita (calculado).
    """
    uploaded_at = datetime.datetime.utcnow()
    docs: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        d = {k: _valor_nativo(v) for k, v in row.to_dict().items()}
        receita = _calcular_receita(d, tipo)
        if receita is not None:
            d["receita"] = round(receita, 2)
        d["competencia"] = competencia
        d["source_file"] = source_file
        d["uploaded_at"] = uploaded_at
        d["tipo"] = tipo
        if group_id:
            d["group_id"] = group_id
        docs.append(d)
    return docs
