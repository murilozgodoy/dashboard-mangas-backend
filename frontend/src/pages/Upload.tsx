import { useState, FormEvent } from "react"
import { API_BASE } from "../config"

const MESES = [
  { value: 1, label: "Jan" }, { value: 2, label: "Fev" }, { value: 3, label: "Mar" },
  { value: 4, label: "Abr" }, { value: 5, label: "Mai" }, { value: 6, label: "Jun" },
  { value: 7, label: "Jul" }, { value: 8, label: "Ago" }, { value: 9, label: "Set" },
  { value: 10, label: "Out" }, { value: 11, label: "Nov" }, { value: 12, label: "Dez" },
]
const anoAtual = new Date().getFullYear()

type Tipo = "polpa" | "extrato"

const COLUNAS_POLPA = "data_pedido, canal, regiao_destino, cliente_segmento, quantidade_kg, preco_unitario_brl_kg, logistica_brl, desconto_brl, lote_id, indice_qualidade_1a10, perda_processamento_pct, nps_0a10"
const COLUNAS_EXTRATO = "data_pedido, canal, regiao_destino, cliente_segmento, quantidade_litros, preco_unitario_brl_l, concentracao_ativa_pct, tipo_solvente, indice_cor_1a10, indice_pureza_1a10, certificacao_exigida, nps_0a10"

type AbaProcessada = { aba: string; tipo: string; competencia: string; linhas_importadas: number; linhas_substituidas: number }

export default function Upload() {
  const [todasAbas, setTodasAbas] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1)
  const [year, setYear] = useState<number>(anoAtual)
  const [tipo, setTipo] = useState<Tipo>("polpa")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{
    success: boolean
    message?: string
    tipo?: string
    competencia?: string
    linhas_importadas?: number
    abas_processadas?: AbaProcessada[]
    total_linhas?: number
    erros?: string[]
  } | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) {
      setResult({ success: false, erros: ["Selecione um arquivo."] })
      return
    }
    setResult(null)
    setLoading(true)
    try {
      const form = new FormData()
      form.append("file", file)
      form.append("year", String(year))
      if (todasAbas) {
        const res = await fetch(`${API_BASE}/api/uploads/todas-abas`, {
          method: "POST",
          body: form,
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          setResult({
            success: false,
            erros: data.detail?.erros || [data.detail?.message || "Erro ao importar."],
          })
          return
        }
        setResult({
          success: true,
          message: data.message || "Importação concluída (todas as abas)",
          abas_processadas: data.abas_processadas || [],
          total_linhas: data.total_linhas ?? 0,
          erros: data.erros?.length ? data.erros : undefined,
        })
      } else {
        form.append("month", String(month))
        form.append("tipo", tipo)
        const res = await fetch(`${API_BASE}/api/uploads`, {
          method: "POST",
          body: form,
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          setResult({
            success: false,
            erros: data.detail?.erros || [data.detail?.message || "Erro ao importar."],
          })
          return
        }
        setResult({
          success: true,
          message: data.message || "Importação concluída",
          tipo: data.tipo,
          competencia: data.competencia,
          linhas_importadas: data.linhas_importadas,
          erros: data.erros?.length ? data.erros : undefined,
        })
      }
      setFile(null)
    } catch (err) {
      setResult({
        success: false,
        erros: [err instanceof Error ? err.message : "Falha na requisição."],
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h2 style={{ margin: "0 0 1rem 0", fontSize: "1.25rem" }}>Enviar planilha Excel</h2>
      <p style={{ color: "#64748b", marginBottom: "1rem", fontSize: "0.875rem" }}>
        Você pode enviar <strong>uma aba</strong> (escolhendo tipo e mês/ano) ou <strong>todas as abas</strong> de um único arquivo (o sistema usa o nome da aba para tipo e mês).
      </p>

      <div style={{ marginBottom: "1.5rem" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={todasAbas}
            onChange={(e) => setTodasAbas(e.target.checked)}
          />
          <span>Processar todas as abas do arquivo</span>
        </label>
        <p style={{ color: "#64748b", margin: "0.25rem 0 0 1.75rem", fontSize: "0.8rem" }}>
          Nome da aba deve conter &quot;Polpa&quot; ou &quot;Extrato&quot; e o mês (Jan, Fev, Jul, Ago, etc.). Ex.: &quot;Polpa congelada - Jul&quot;, &quot;Extrato de manga - Ago&quot;.
        </p>
      </div>

      {!todasAbas && (
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn"
            style={{
              background: tipo === "polpa" ? "#0f172a" : "#e2e8f0",
              color: tipo === "polpa" ? "#fff" : "#334155",
            }}
            onClick={() => setTipo("polpa")}
          >
            Polpa congelada
          </button>
          <button
            type="button"
            className="btn"
            style={{
              background: tipo === "extrato" ? "#0f172a" : "#e2e8f0",
              color: tipo === "extrato" ? "#fff" : "#334155",
            }}
            onClick={() => setTipo("extrato")}
          >
            Extrato de manga
          </button>
        </div>
      )}

      <div className="card">
        <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1rem" }}>
          {todasAbas
            ? "Arquivo Excel com várias abas"
            : tipo === "polpa"
              ? "Planilha Polpa congelada"
              : "Planilha Extrato de manga"}
        </h3>
        {!todasAbas && (
          <p style={{ color: "#64748b", marginBottom: "1rem", fontSize: "0.8rem" }}>
            Colunas esperadas: {tipo === "polpa" ? COLUNAS_POLPA : COLUNAS_EXTRATO}
          </p>
        )}
        <form className="upload-form" onSubmit={handleSubmit}>
          <div>
            <label>Arquivo (.xlsx ou .csv)</label>
            <input
              type="file"
              accept={todasAbas ? ".xlsx,.xls" : ".xlsx,.xls,.csv"}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          {!todasAbas && (
            <div className="row">
              <div>
                <label>Mês</label>
                <select
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                >
                  {MESES.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Ano</label>
                <input
                  type="number"
                  min={2000}
                  max={2100}
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                />
              </div>
            </div>
          )}
          {todasAbas && (
            <div>
              <label>Ano (usado em todas as abas)</label>
              <input
                type="number"
                min={2000}
                max={2100}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </div>
          )}
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading
              ? "Enviando…"
              : todasAbas
                ? "Enviar e processar todas as abas"
                : tipo === "polpa"
                  ? "Enviar planilha Polpa"
                  : "Enviar planilha Extrato"}
          </button>
        </form>
        {result && (
          <div className={`upload-result ${result.success ? "success" : "error"}`} style={{ marginTop: "1rem" }}>
            {result.success && (
              <>
                <strong>{result.message}</strong>
                {result.tipo && <div>Tipo: {result.tipo}</div>}
                {result.competencia && <div>Competência: {result.competencia}</div>}
                {result.linhas_importadas != null && <div>Linhas importadas: {result.linhas_importadas}</div>}
                {result.total_linhas != null && result.total_linhas > 0 && (
                  <div>Total de linhas: {result.total_linhas}</div>
                )}
                {result.abas_processadas && result.abas_processadas.length > 0 && (
                  <div style={{ marginTop: "0.5rem" }}>
                    Abas processadas:
                    <ul style={{ margin: "0.25rem 0 0 1rem", padding: 0 }}>
                      {result.abas_processadas.map((a, i) => (
                        <li key={i}>
                          {a.aba} → {a.tipo}, {a.competencia}, {a.linhas_importadas} linhas
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.erros && result.erros.length > 0 && (
                  <div style={{ marginTop: "0.5rem", color: "#b91c1c" }}>
                    Avisos: <ul style={{ margin: "0.25rem 0 0 1rem" }}>{result.erros.map((err, i) => <li key={i}>{err}</li>)}</ul>
                  </div>
                )}
              </>
            )}
            {!result.success && result.erros && result.erros.length > 0 && (
              <>
                <strong>Erro na importação</strong>
                <ul>
                  {result.erros.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
