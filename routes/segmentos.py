"""
Endpoints de análise por segmento de cliente (cliente_segmento).
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal
from collections import defaultdict

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["segmentos"])


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


@router.get("/segmentos/ranking")
async def get_segmentos_ranking(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
):
    """Ranking de segmentos de cliente por receita e registros."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$cliente_segmento", "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    if tipo == "polpa":
        pipeline[1]["$group"]["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        pipeline[1]["$group"]["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    cur = sales.aggregate(pipeline)
    segmentos = []
    for r in cur:
        item = {
            "segmento": r["_id"] or "(não informado)",
            "receita": float(r["receita"] or 0),
            "registros": r["registros"] or 0,
        }
        if tipo == "polpa":
            item["quantidade_kg"] = float(r.get("quantidade_kg") or 0)
        else:
            item["quantidade_litros"] = float(r.get("quantidade_litros") or 0)
        segmentos.append(item)
    return {"segmentos": segmentos, "tipo": tipo}


@router.get("/segmentos/receita-por-mes")
async def get_segmentos_receita_por_mes(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit_segmentos: int = Query(5, ge=1, le=10),
):
    """Receita por competência para os top N segmentos."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)

    pipe_top = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$cliente_segmento", "receita": {"$sum": "$receita"}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit_segmentos},
    ]
    top_segmentos = [r["_id"] or "(não informado)" for r in sales.aggregate(pipe_top)]
    if not top_segmentos:
        return {"segmentos": [], "tipo": tipo}

    pipe_ts = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {"cliente_segmento": {"$in": top_segmentos}}},
        {"$group": {"_id": {"competencia": "$competencia", "segmento": "$cliente_segmento"}, "receita": {"$sum": "$receita"}}},
    ]
    by_segmento = defaultdict(list)
    for r in sales.aggregate(pipe_ts):
        comp = r["_id"]["competencia"]
        seg = r["_id"]["segmento"] or "(não informado)"
        by_segmento[seg].append({"periodo": comp, "receita": float(r["receita"] or 0)})

    result = []
    for seg in top_segmentos:
        dados = sorted(by_segmento.get(seg, []), key=lambda x: x["periodo"])
        result.append({"segmento": seg, "dados": dados})
    return {"segmentos": result, "tipo": tipo}
