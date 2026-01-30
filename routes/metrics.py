"""
Endpoints de leitura para o dashboard: métricas por tipo (polpa ou extrato).
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal

from services.db import get_collection, get_uploads_log_collection

router = APIRouter(prefix="/api", tags=["metrics"])


def _filtro_periodo(from_comp: Optional[str], to_comp: Optional[str], group_id: Optional[str]):
    match = {}
    if from_comp or to_comp:
        match["competencia"] = {}
        if from_comp:
            match["competencia"]["$gte"] = from_comp
        if to_comp:
            match["competencia"]["$lte"] = to_comp
    if group_id:
        match["group_id"] = group_id
    return match


@router.get("/metrics")
async def get_metrics(
    tipo: Literal["polpa", "extrato"] = Query(..., description="polpa ou extrato"),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """KPIs agregados no período (receita total, quantidade, registros)."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {
            "$group": {
                "_id": None,
                "receita_total": {"$sum": "$receita"},
                "registros": {"$sum": 1},
            }
        },
    ]
    if tipo == "polpa":
        pipeline[1]["$group"]["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        pipeline[1]["$group"]["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    cur = sales.aggregate(pipeline)
    row = next(cur, None)
    if not row:
        out = {"receita_total": 0, "registros": 0, "from": from_comp, "to": to_comp, "tipo": tipo}
        if tipo == "polpa":
            out["quantidade_kg"] = 0
        else:
            out["quantidade_litros"] = 0
        return out
    out = {
        "receita_total": float(row["receita_total"] or 0),
        "registros": row["registros"],
        "from": from_comp,
        "to": to_comp,
        "tipo": tipo,
    }
    if tipo == "polpa":
        out["quantidade_kg"] = float(row.get("quantidade_kg") or 0)
    else:
        out["quantidade_litros"] = float(row.get("quantidade_litros") or 0)
    return out


@router.get("/timeseries/revenue")
async def get_timeseries_revenue(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Receita por mês (competência) para gráfico de linha."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$competencia", "receita": {"$sum": "$receita"}}},
        {"$sort": {"_id": 1}},
    ]
    if tipo == "polpa":
        pipeline[1]["$group"]["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        pipeline[1]["$group"]["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    cur = sales.aggregate(pipeline)
    dados = []
    for r in cur:
        item = {"periodo": r["_id"], "receita": float(r["receita"] or 0)}
        if tipo == "polpa":
            item["quantidade_kg"] = float(r.get("quantidade_kg") or 0)
        else:
            item["quantidade_litros"] = float(r.get("quantidade_litros") or 0)
        dados.append(item)
    return {"dados": dados, "tipo": tipo}


@router.get("/top-canais")
async def get_top_canais(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Ranking de canais por receita."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$canal", "receita": {"$sum": "$receita"}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    canais = [{"canal": r["_id"], "receita": float(r["receita"] or 0)} for r in cur]
    return {"canais": canais, "tipo": tipo}


@router.get("/top-regioes")
async def get_top_regioes(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Ranking de regiões por receita."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$regiao_destino", "receita": {"$sum": "$receita"}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    regioes = [{"regiao": r["_id"], "receita": float(r["receita"] or 0)} for r in cur]
    return {"regioes": regioes, "tipo": tipo}


@router.get("/periods")
async def get_periods(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
):
    """Lista competências disponíveis para o tipo."""
    sales = get_collection(tipo)
    match = {"group_id": group_id} if group_id else {}
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$competencia"}},
        {"$sort": {"_id": -1}},
    ]
    cur = sales.aggregate(pipeline)
    periodos = [r["_id"] for r in cur]
    return {"periodos": periodos, "tipo": tipo}


@router.get("/uploads")
async def get_uploads_history(
    tipo: Optional[Literal["polpa", "extrato"]] = Query(None, description="Filtrar por tipo"),
    group_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Histórico de uploads (competência, tipo, data, linhas importadas)."""
    uploads = get_uploads_log_collection()
    match = {}
    if tipo:
        match["tipo"] = tipo
    if group_id:
        match["group_id"] = group_id
    cursor = uploads.find(match).sort("uploaded_at", -1).limit(limit)
    lista = []
    for doc in cursor:
        lista.append({
            "competencia": doc.get("competencia"),
            "tipo": doc.get("tipo"),
            "group_id": doc.get("group_id"),
            "source_file": doc.get("source_file"),
            "uploaded_at": doc.get("uploaded_at").isoformat() if doc.get("uploaded_at") else None,
            "linhas_importadas": doc.get("linhas_importadas", 0),
            "linhas_substituidas": doc.get("linhas_substituidas", 0),
        })
    return {"uploads": lista}
