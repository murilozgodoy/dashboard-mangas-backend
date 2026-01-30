# Dashboard Mangas

Sistema de **upload mensal de planilhas Excel** (Polpa congelada e Extrato de manga) + **dashboard interativo** com MongoDB.

## O que está implementado

1. **Dois tipos de planilha** – Polpa congelada e Extrato de manga, cada um com seu contrato de colunas.
2. **Competência** – Mês/ano informados no front viram identificador `YYYY-MM` (ex: `2026-01`).
3. **Upload** – Dois fluxos no front: “Polpa congelada” e “Extrato de manga”. Envio via `POST /api/uploads` com `file`, `month`, `year` e `tipo` (polpa | extrato).
4. **Backend** – Valida colunas conforme o tipo, lê a primeira aba, limpa dados, calcula receita e grava na coleção **polpa** ou **extrato** com metadados (`competencia`, `uploaded_at`, `source_file`, `tipo`).
5. **Regra de duplicidade** – Se já existir dado para a mesma competência + tipo (e `group_id`), **substitui** (apaga e insere de novo).
6. **Endpoints de leitura** – Todos aceitam `tipo=polpa` ou `tipo=extrato`: `GET /api/metrics`, `GET /api/timeseries/revenue`, `GET /api/top-canais`, `GET /api/top-regioes`, `GET /api/periods`, `GET /api/uploads`.
7. **Dashboard** – Seletor de tipo (Polpa/Extrato), filtro de período, 3 KPIs (receita, quantidade kg/L, registros), gráfico de linha (receita por mês), ranking de canais, tabela de uploads.

## Contratos das planilhas

- **Uma aba** (ou sempre a primeira).
- **Cabeçalho na primeira linha.**

**Polpa congelada** – colunas:  
`data_pedido`, `canal`, `regiao_destino`, `cliente_segmento`, `quantidade_kg`, `preco_unitario_brl_kg`, `logistica_brl`, `desconto_brl`, `lote_id`, `indice_qualidade_1a10`, `perda_processamento_pct`, `nps_0a10`.

**Extrato de manga** – colunas:  
`data_pedido`, `canal`, `regiao_destino`, `cliente_segmento`, `quantidade_litros`, `preco_unitario_brl_l`, `concentracao_ativa_pct`, `tipo_solvente`, `indice_cor_1a10`, `indice_pureza_1a10`, `certificacao_exigida`, `nps_0a10`.

Receita é calculada no backend: **Polpa** = quantidade_kg × preco_unitario_brl_kg − logistica_brl − desconto_brl; **Extrato** = quantidade_litros × preco_unitario_brl_l.

## Pré-requisitos

- **Python 3.10+**
- **MongoDB** (local ou Atlas)
- **Node.js** (para o frontend de teste)

## Backend

```bash
cd dashboard-mangas-backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py
```

API em **http://localhost:8002**. Documentação em **http://localhost:8002/docs**.

## Frontend (teste)

```bash
cd dashboard-mangas-backend/frontend
npm install
npm run dev
```

Acesse **http://localhost:5173**. Na tela de Upload, escolha “Polpa congelada” ou “Extrato de manga”, selecione o arquivo e informe mês/ano.

## MVP aprovado

- [x] Dois fluxos de upload (Polpa e Extrato).
- [x] Backend grava nas coleções **polpa** e **extrato** com competência e tipo.
- [x] Reenvio do mesmo mês + tipo substitui os dados.
- [x] Dashboard com tipo, 3 KPIs, gráfico temporal e ranking de canais.
- [x] Tabela de uploads com tipo.
