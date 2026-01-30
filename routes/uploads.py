"""
Endpoint de upload de planilha Excel: polpa ou extrato.
"""
import datetime
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional, Literal

from services.db import get_collection, get_uploads_log_collection
from services.excel_service import (
    validar_arquivo,
    validar_colunas,
    ler_excel,
    ler_excel_todas_abas,
    limpar_e_normalizar,
    dataframe_para_documentos,
)
router = APIRouter(prefix="/api", tags=["uploads"])


def montar_competencia(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


@router.post("/uploads")
async def upload_planilha(
    file: UploadFile = File(...),
    month: int = Form(..., ge=1, le=12),
    year: int = Form(..., ge=2000, le=2100),
    tipo: Literal["polpa", "extrato"] = Form(..., description="Tipo da planilha: polpa ou extrato"),
    group_id: Optional[str] = Form(None),
):
    """
    Recebe planilha Excel (polpa ou extrato), mês e ano.
    Regra: se já existir dados para essa competência + tipo (e group_id), substitui.
    """
    content = await file.read()
    filename = file.filename or "arquivo.xlsx"

    erros = validar_arquivo(filename, content)
    if erros:
        raise HTTPException(status_code=400, detail={"erros": erros})

    df, erros_leitura = ler_excel(content, filename)
    if df is None or erros_leitura:
        raise HTTPException(
            status_code=400,
            detail={"erros": erros_leitura or ["Falha ao ler planilha."]},
        )

    erros_colunas = validar_colunas(df, tipo)
    if erros_colunas:
        raise HTTPException(status_code=400, detail={"erros": erros_colunas})

    df = limpar_e_normalizar(df, tipo)
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail={"erros": ["Nenhum dado válido após limpeza."]},
        )

    competencia = montar_competencia(year, month)
    collection = get_collection(tipo)
    uploads_log = get_uploads_log_collection()

    query = {"competencia": competencia}
    if group_id:
        query["group_id"] = group_id
    deleted = collection.delete_many(query)
    deleted_count = deleted.deleted_count

    docs = dataframe_para_documentos(df, competencia, filename, tipo, group_id)
    if docs:
        collection.insert_many(docs)
    linhas_importadas = len(docs)

    log_entry = {
        "competencia": competencia,
        "tipo": tipo,
        "group_id": group_id,
        "source_file": filename,
        "uploaded_at": datetime.datetime.utcnow(),
        "linhas_importadas": linhas_importadas,
        "linhas_substituidas": deleted_count,
    }
    uploads_log.insert_one(log_entry)

    return {
        "message": "Importação concluída",
        "tipo": tipo,
        "competencia": competencia,
        "linhas_importadas": linhas_importadas,
        "linhas_substituidas": deleted_count,
        "erros": [],
    }


@router.post("/uploads/todas-abas")
async def upload_planilha_todas_abas(
    file: UploadFile = File(...),
    year: int = Form(..., ge=2000, le=2100),
    group_id: Optional[str] = Form(None),
):
    """
    Processa todas as abas do Excel: tipo (Polpa/Extrato) e mês são inferidos pelo nome da aba.
    Ex.: 'Polpa congelada - Jul' -> polpa, 2025-07; 'Extrato de manga - Ago' -> extrato, 2025-08.
    Informe apenas o ano (todas as abas usam esse ano).
    """
    content = await file.read()
    filename = file.filename or "arquivo.xlsx"

    erros = validar_arquivo(filename, content)
    if erros:
        raise HTTPException(status_code=400, detail={"erros": erros})

    if filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={"erros": ["Upload 'todas as abas' exige arquivo .xlsx (várias abas). Para CSV use o upload normal com tipo e mês/ano."]},
        )

    abas = ler_excel_todas_abas(content, filename, year)
    if not abas:
        raise HTTPException(
            status_code=400,
            detail={
                "erros": [
                    "Nenhuma aba reconhecida. O nome da aba deve conter 'Polpa' ou 'Extrato' e o mês (Jan, Fev, Jul, Ago, etc.). "
                    "Ex.: 'Polpa congelada - Jul', 'Extrato de manga - Ago'."
                ]
            },
        )

    uploads_log = get_uploads_log_collection()
    resumo: list[dict] = []
    erros_geral: list[str] = []

    for sheet_name, df, tipo, competencia in abas:
        erros_col = validar_colunas(df, tipo)
        if erros_col:
            erros_geral.append(f"{sheet_name} ({tipo}, {competencia}): {', '.join(erros_col)}")
            continue
        df_limpo = limpar_e_normalizar(df, tipo)
        if df_limpo.empty:
            erros_geral.append(f"{sheet_name}: nenhum dado válido após limpeza.")
            continue
        collection = get_collection(tipo)
        query = {"competencia": competencia}
        if group_id:
            query["group_id"] = group_id
        deleted = collection.delete_many(query)
        deleted_count = deleted.deleted_count
        docs = dataframe_para_documentos(df_limpo, competencia, filename, tipo, group_id)
        if docs:
            collection.insert_many(docs)
        linhas = len(docs)
        resumo.append({
            "aba": sheet_name,
            "tipo": tipo,
            "competencia": competencia,
            "linhas_importadas": linhas,
            "linhas_substituidas": deleted_count,
        })
        log_entry = {
            "competencia": competencia,
            "tipo": tipo,
            "group_id": group_id,
            "source_file": filename,
            "sheet_name": sheet_name,
            "uploaded_at": datetime.datetime.utcnow(),
            "linhas_importadas": linhas,
            "linhas_substituidas": deleted_count,
        }
        uploads_log.insert_one(log_entry)

    return {
        "message": "Importação concluída (todas as abas processadas)",
        "ano": year,
        "abas_processadas": resumo,
        "total_linhas": sum(r["linhas_importadas"] for r in resumo),
        "erros": erros_geral,
    }
