"""
Endpoints de análise avançada: preço médio, logística, desconto (polpa), concentração, tipo solvente, certificação (extrato).
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["analise"])


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


@router.get("/analise/preco-medio-periodo")
async def get_preco_medio_periodo(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Preço unitário médio por competência. Polpa: BRL/kg; Extrato: BRL/L."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    campo = "preco_unitario_brl_kg" if tipo == "polpa" else "preco_unitario_brl_l"
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {campo: {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$competencia", "preco_medio": {"$avg": f"${campo}"}, "registros": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    cur = sales.aggregate(pipeline)
    dados = [
        {"periodo": r["_id"], "preco_medio": round(float(r.get("preco_medio") or 0), 2), "registros": r["registros"]}
        for r in cur
    ]
    return {"dados": dados, "tipo": tipo}


@router.get("/analise/polpa-logistica-desconto")
async def get_polpa_logistica_desconto(
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Polpa: logística total e desconto total por competência."""
    sales = get_collection("polpa")
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {
            "$group": {
                "_id": "$competencia",
                "logistica_total": {"$sum": {"$ifNull": ["$logistica_brl", 0]}},
                "desconto_total": {"$sum": {"$ifNull": ["$desconto_brl", 0]}},
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
            "logistica_total": round(float(r.get("logistica_total") or 0), 2),
            "desconto_total": round(float(r.get("desconto_total") or 0), 2),
            "registros": r["registros"],
        })
    return {"dados": dados}


@router.get("/analise/extrato-concentracao")
async def get_extrato_concentracao(
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Extrato: concentração ativa média (%) por competência."""
    sales = get_collection("extrato")
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$match": {"concentracao_ativa_pct": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$competencia", "concentracao_media": {"$avg": "$concentracao_ativa_pct"}, "registros": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    cur = sales.aggregate(pipeline)
    dados = [
        {"periodo": r["_id"], "concentracao_media": round(float(r.get("concentracao_media") or 0), 2), "registros": r["registros"]}
        for r in cur
    ]
    return {"dados": dados}


@router.get("/analise/extrato-tipo-solvente")
async def get_extrato_tipo_solvente(
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
):
    """Extrato: receita e registros por tipo_solvente (para Pie/Bar)."""
    sales = get_collection("extrato")
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$tipo_solvente", "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    itens = [
        {"tipo_solvente": r["_id"] or "(não informado)", "receita": float(r["receita"] or 0), "registros": r["registros"]}
        for r in cur
    ]
    return {"itens": itens}


@router.get("/analise/extrato-certificacao")
async def get_extrato_certificacao(
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
):
    """Extrato: receita e registros por certificacao_exigida (para Pie/Bar)."""
    sales = get_collection("extrato")
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$certificacao_exigida", "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        {"$sort": {"receita": -1}},
        {"$limit": limit},
    ]
    cur = sales.aggregate(pipeline)
    itens = [
        {"certificacao": str(r["_id"]) if r["_id"] is not None else "(não informado)", "receita": float(r["receita"] or 0), "registros": r["registros"]}
        for r in cur
    ]
    return {"itens": itens}


@router.get("/analise/receita-quantidade-periodo")
async def get_receita_quantidade_periodo(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """Receita e quantidade por competência (para ComposedChart dual axis)."""
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    group = {"_id": "$competencia", "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}
    if tipo == "polpa":
        group["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        group["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": group},
        {"$sort": {"_id": 1}},
    ]
    cur = sales.aggregate(pipeline)
    dados = []
    for r in cur:
        item = {"periodo": r["_id"], "receita": float(r.get("receita") or 0)}
        if tipo == "polpa":
            item["quantidade"] = float(r.get("quantidade_kg") or 0)
        else:
            item["quantidade"] = float(r.get("quantidade_litros") or 0)
        dados.append(item)
    return {"dados": dados, "tipo": tipo}
