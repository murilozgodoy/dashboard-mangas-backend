"""
Endpoints de geografia: receita e métricas por macro região do Brasil (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
"""
from fastapi import APIRouter, Query
from typing import Optional, Literal

from services.db import get_collection

router = APIRouter(prefix="/api", tags=["geografia"])

# Mapeamento: regiao_destino (como vem na base) -> macro região IBGE
REGIAO_PARA_MACRO: dict[str, str] = {
    # Norte
    "norte": "Norte",
    "acre": "Norte", "ac": "Norte",
    "amazonas": "Norte", "am": "Norte",
    "amapá": "Norte", "ap": "Norte", "amapa": "Norte",
    "pará": "Norte", "pa": "Norte", "para": "Norte",
    "rondônia": "Norte", "ro": "Norte", "rondonia": "Norte",
    "roraima": "Norte", "rr": "Norte",
    "tocantins": "Norte", "to": "Norte",
    # Nordeste
    "nordeste": "Nordeste",
    "alagoas": "Nordeste", "al": "Nordeste",
    "bahia": "Nordeste", "ba": "Nordeste",
    "ceará": "Nordeste", "ce": "Nordeste", "ceara": "Nordeste",
    "maranhão": "Nordeste", "ma": "Nordeste", "maranhao": "Nordeste",
    "paraíba": "Nordeste", "pb": "Nordeste", "paraiba": "Nordeste",
    "pernambuco": "Nordeste", "pe": "Nordeste",
    "piauí": "Nordeste", "pi": "Nordeste", "piaui": "Nordeste",
    "rio grande do norte": "Nordeste", "rn": "Nordeste",
    "sergipe": "Nordeste", "se": "Nordeste",
    # Centro-Oeste
    "centro-oeste": "Centro-Oeste", "centro oeste": "Centro-Oeste",
    "distrito federal": "Centro-Oeste", "df": "Centro-Oeste",
    "goiás": "Centro-Oeste", "go": "Centro-Oeste", "goias": "Centro-Oeste",
    "mato grosso": "Centro-Oeste", "mt": "Centro-Oeste",
    "mato grosso do sul": "Centro-Oeste", "ms": "Centro-Oeste",
    # Sudeste
    "sudeste": "Sudeste",
    "espírito santo": "Sudeste", "es": "Sudeste", "espirito santo": "Sudeste",
    "minas gerais": "Sudeste", "mg": "Sudeste",
    "rio de janeiro": "Sudeste", "rj": "Sudeste",
    "são paulo": "Sudeste", "sp": "Sudeste", "sao paulo": "Sudeste", "paulista": "Sudeste",
    # Sul
    "sul": "Sul",
    "paraná": "Sul", "pr": "Sul", "parana": "Sul",
    "rio grande do sul": "Sul", "rs": "Sul", "gaúcho": "Sul", "gaucho": "Sul",
    "santa catarina": "Sul", "sc": "Sul",
}


def _normalizar_regiao(s: str) -> str:
    if not s:
        return ""
    return str(s).strip().lower()


def _macro_regiao(regiao_destino: str) -> Optional[str]:
    """Retorna a macro região (Norte, Nordeste, etc.) ou None se não reconhecida."""
    n = _normalizar_regiao(regiao_destino)
    if not n:
        return None
    # Match exato
    if n in REGIAO_PARA_MACRO:
        return REGIAO_PARA_MACRO[n]
    # Contém (ex: "São Paulo - Capital" -> Sudeste)
    for key, macro in REGIAO_PARA_MACRO.items():
        if len(key) > 2 and key in n:
            return macro
    # Região já é macro
    if n in ("norte", "nordeste", "centro-oeste", "centro oeste", "sudeste", "sul"):
        return n.replace("centro oeste", "Centro-Oeste").replace("centro-oeste", "Centro-Oeste").capitalize()
    if n == "norte":
        return "Norte"
    if n == "nordeste":
        return "Nordeste"
    if n == "sudeste":
        return "Sudeste"
    if n == "sul":
        return "Sul"
    return None


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


@router.get("/geografia/regioes")
async def get_geografia_regioes(
    tipo: Literal["polpa", "extrato"] = Query(...),
    group_id: Optional[str] = Query(None),
    from_comp: Optional[str] = Query(None),
    to_comp: Optional[str] = Query(None),
):
    """
    Retorna receita, quantidade e registros por macro região do Brasil (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
    Útil para colorir mapa e comparar regiões.
    """
    sales = get_collection(tipo)
    match = _filtro_periodo(from_comp, to_comp, group_id)
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {"$group": {"_id": "$regiao_destino", "receita": {"$sum": "$receita"}, "count": {"$sum": 1}}},
    ]
    if tipo == "polpa":
        pipeline[1]["$group"]["quantidade_kg"] = {"$sum": "$quantidade_kg"}
    else:
        pipeline[1]["$group"]["quantidade_litros"] = {"$sum": "$quantidade_litros"}
    cur = sales.aggregate(pipeline)

    # Agrupar por macro região
    macro_totals: dict[str, dict] = {}
    for r in cur:
        regiao_destino = r.get("_id") or ""
        macro = _macro_regiao(regiao_destino)
        if not macro:
            macro = "Outros"
        if macro not in macro_totals:
            macro_totals[macro] = {
                "regiao": macro,
                "receita": 0.0,
                "registros": 0,
                "quantidade_kg": 0.0,
                "quantidade_litros": 0.0,
            }
        macro_totals[macro]["receita"] += float(r.get("receita") or 0)
        macro_totals[macro]["registros"] += r.get("count") or 0
        if tipo == "polpa":
            macro_totals[macro]["quantidade_kg"] += float(r.get("quantidade_kg") or 0)
        else:
            macro_totals[macro]["quantidade_litros"] += float(r.get("quantidade_litros") or 0)

    # Ordem fixa: Norte, Nordeste, Centro-Oeste, Sudeste, Sul, Outros
    ordem = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "Outros"]
    regioes = []
    for nome in ordem:
        if nome in macro_totals:
            regioes.append(macro_totals[nome])
    for nome, data in macro_totals.items():
        if nome not in ordem:
            regioes.append(data)

    return {"regioes": regioes, "tipo": tipo}
