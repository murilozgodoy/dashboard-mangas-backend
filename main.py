from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.uploads import router as uploads_router
from routes.metrics import router as metrics_router
from routes.geografia import router as geografia_router
from routes.financeiro import router as financeiro_router
from routes.canal import router as canal_router
from routes.segmentos import router as segmentos_router
from routes.qualidade import router as qualidade_router
from routes.analise import router as analise_router

app = FastAPI(title="Dashboard Mangas API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "API Dashboard Mangas. Upload de Excel + métricas. Acesse /docs para documentação."}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.include_router(uploads_router)
app.include_router(metrics_router)
app.include_router(geografia_router)
app.include_router(financeiro_router)
app.include_router(canal_router)
app.include_router(segmentos_router)
app.include_router(qualidade_router)
app.include_router(analise_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
