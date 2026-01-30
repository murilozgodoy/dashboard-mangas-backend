"""
Endpoints de análise por canal: ranking (receita e registros), receita por mês por canal.
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal
from collections import defaultdict

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["canal"])


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


@router.get("/canal/ranking")
async def get_canal_ranking(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
):
    """Ranking de canais por receita, com quantidade de registros por canal."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$canal", "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    canais = [
        {"canal": r["_id"] or "(não informado)", "receita": float(r["receita"] or 0), "registros": r["registros"] or 0}
        for r in cur
    ]
    return {"canais": canais, "tipo": tipo}


@router.get("/canal/receita-por-mes")
async def get_canal_receita_por_mes(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit_canais: int = Query(5, ge=1, le=10),
):
    """
    Receita por competência (mês) para os top N canais.
    Retorna lista de { canal, dados: [ { periodo, receita } ] }.
    """
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)

    # Primeiro: top canais por receita total
    pipe_top = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$canal", "receita": {"$sum": "$receita"}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit_canais},
    ]
    top_canais = [r["_id"] or "(não informado)" for r in sales.aggregate(pipe_top)]
    if not top_canais:
        return {"canais": [], "tipo": tipo}

    # Agrupar por competência e canal
    pipe_ts = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {"canal": {"$in": top_canais}}},
        {"$group": {"_id": {"competencia": "$competencia", "canal": "$canal"}, "receita": {"$sum": "$receita"}}},
    ]
    by_canal: dict[str, list[dict]] = defaultdict(list)
    for r in sales.aggregate(pipe_ts):
        comp = r["_id"]["competencia"]
        canal = r["_id"]["canal"] or "(não informado)"
        by_canal[canal].append({"periodo": comp, "receita": float(r["receita"] or 0)})

    # Ordenar períodos em cada canal e manter ordem dos top
    result = []
    for canal in top_canais:
        dados = sorted(by_canal.get(canal, []), key=lambda x: x["periodo"])
        result.append({"canal": canal, "dados": dados})
    return {"canais": result, "tipo": tipo}
