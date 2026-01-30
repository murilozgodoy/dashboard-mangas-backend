"""
Endpoints de visão financeira: resumo, receita por tipo, série temporal, ticket médio.
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["financeiro"])


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


@router.get("/financeiro/resumo")
async def get_financeiro_resumo(
    tipo: Literal["polpa", "extrato", "todos"] = Query("todos"),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """
    Resumo financeiro do período: receita total, registros, ticket médio, quantidade.
    Se tipo=todos, retorna também receita_polpa e receita_extrato.
    """
    match = _filtro_periodo(from_comp, to_comp, group_id)

    if tipo == "todos":
        polpa = get_collection("polpa")
        extrato = get_collection("extrato")
        pipe = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": None, "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
        ]
        r_polpa = next(polpa.aggregate(pipe), None)
        r_extrato = next(extrato.aggregate(pipe), None)
        receita_polpa = float(r_polpa["receita"] or 0) if r_polpa else 0
        receita_extrato = float(r_extrato["receita"] or 0) if r_extrato else 0
        receita_total = receita_polpa + receita_extrato
        registros = (r_polpa["registros"] or 0 if r_polpa else 0) + (r_extrato["registros"] or 0 if r_extrato else 0)
        ticket_medio = receita_total / registros if registros else 0
        return {
            "receita_total": round(receita_total, 2),
            "receita_polpa": round(receita_polpa, 2),
            "receita_extrato": round(receita_extrato, 2),
            "registros": registros,
            "ticket_medio": round(ticket_medio, 2),
            "from": from_comp,
            "to": to_comp,
            "tipo": tipo,
        }

    sales = get_collection(tipo)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": None, "receita": {"$sum": "$receita"}, "registros": {"$sum": 1}}},
    ]
    if tipo == "polpa":
        pipeline[1]["$group"]["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        pipeline[1]["$group"]["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    row = next(sales.aggregate(pipeline), None)
    if not row:
        out = {
            "receita_total": 0,
            "registros": 0,
            "ticket_medio": 0,
            "from": from_comp,
            "to": to_comp,
            "tipo": tipo,
        }
        if tipo == "polpa":
            out["quantidade_kg"] = 0
        else:
            out["quantidade_litros"] = 0
        return out
    receita = float(row["receita"] or 0)
    registros = row["registros"] or 0
    ticket_medio = receita / registros if registros else 0
    out = {
        "receita_total": round(receita, 2),
        "registros": registros,
        "ticket_medio": round(ticket_medio, 2),
        "from": from_comp,
        "to": to_comp,
        "tipo": tipo,
    }
    if tipo == "polpa":
        out["quantidade_kg"] = float(row.get("quantidade_kg") or 0)
    else:
        out["quantidade_litros"] = float(row.get("quantidade_litros") or 0)
    return out


@router.get("/financeiro/receita-por-periodo")
async def get_financeiro_receita_por_periodo(
    tipo: Literal["polpa", "extrato", "todos"] = Query("todos"),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """
    Receita por competência (mês). Se tipo=todos, retorna receita_polpa e receita_extrato por período.
    """
    match = _filtro_periodo(from_comp, to_comp, group_id)

    if tipo == "todos":
        polpa = get_collection("polpa")
        extrato = get_collection("extrato")
        pipe_p = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$competencia", "receita": {"$sum": "$receita"}}},
            {"$sort": {"_id": 1}},
        ]
        pipe_e = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$competencia", "receita": {"$sum": "$receita"}}},
            {"$sort": {"_id": 1}},
        ]
        by_period_p = {r["_id"]: float(r["receita"] or 0) for r in polpa.aggregate(pipe_p)}
        by_period_e = {r["_id"]: float(r["receita"] or 0) for r in extrato.aggregate(pipe_e)}
        periodos = sorted(set(by_period_p) | set(by_period_e))
        dados = []
        for p in periodos:
            dados.append({
                "periodo": p,
                "receita": by_period_p.get(p, 0) + by_period_e.get(p, 0),
                "receita_polpa": by_period_p.get(p, 0),
                "receita_extrato": by_period_e.get(p, 0),
            })
        return {"dados": dados, "tipo": tipo}

    sales = get_collection(tipo)
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
