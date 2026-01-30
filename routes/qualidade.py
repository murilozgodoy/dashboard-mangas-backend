"""
Endpoints de qualidade e NPS: índices e satisfação por período/canal.
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["qualidade"])


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


@router.get("/qualidade/nps-por-periodo")
async def get_nps_por_periodo(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """NPS médio por competência (mês)."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {"nps_0a10": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": "$competencia", "nps_medio": {"$avg": "$nps_0a10"}, "registros": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    cur = sales.aggregate(pipeline)
    dados = [{"periodo": r["_id"], "nps_medio": round(float(r["nps_medio"] or 0), 2), "registros": r["registros"]} for r in cur]
    return {"dados": dados, "tipo": tipo}


@router.get("/qualidade/nps-por-canal")
async def get_nps_por_canal(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
):
    """NPS médio por canal (ranking por receita)."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {"nps_0a10": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": "$canal", "nps_medio": {"$avg": "$nps_0a10"}, "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    canais = [
        {"canal": r["_id"] or "(não informado)", "nps_medio": round(float(r["nps_medio"] or 0), 2), "receita": float(r["receita"] or 0), "registros": r["registros"]}
        for r in cur
    ]
    return {"canais": canais, "tipo": tipo}


@router.get("/qualidade/indices-por-periodo")
async def get_indices_por_periodo(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Índices de qualidade médios por competência. Polpa: qualidade 1-10, perda %. Extrato: cor 1-10, pureza 1-10."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)

    if tipo == "polpa":
        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {
                "$group": {
                    "_id": "$competencia",
                    "qualidade_media": {"$avg": "$indice_qualidade_1a10"},
                    "perda_media": {"$avg": "$perda_processamento_pct"},
                    "registros": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        cur = sales.aggregate(pipeline)
        dados = []
        for r in cur:
            dados.append({
                "periodo": r["_id"],
                "qualidade_media": round(float(r.get("qualidade_media") or 0), 2),
                "perda_media": round(float(r.get("perda_media") or 0), 2),
                "registros": r["registros"],
            })
        return {"dados": dados, "tipo": tipo}

    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {
            "$group": {
                "_id": "$competencia",
                "cor_media": {"$avg": "$indice_cor_1a10"},
                "pureza_media": {"$avg": "$indice_pureza_1a10"},
                "registros": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    cur = sales.aggregate(pipeline)
    dados = []
    for r in cur:
        dados.append({
            "periodo": r["_id"],
            "cor_media": round(float(r.get("cor_media") or 0), 2),
            "pureza_media": round(float(r.get("pureza_media") or 0), 2),
            "registros": r["registros"],
        })
    return {"dados": dados, "tipo": tipo}
