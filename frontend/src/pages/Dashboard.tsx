import { useState, useEffect } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts"
import { API_BASE } from "../config"

type Tipo = "polpa" | "extrato"

type Metrics = {
  receita_total: number
  registros: number
  quantidade_kg?: number
  quantidade_litros?: number
  from?: string
  to?: string
  tipo: string
}

type TimeseriesPoint = { periodo: string; receita: number; quantidade_kg?: number; quantidade_litros?: number }

type TopCanal = { canal: string; receita: number }

type UploadEntry = {
  competencia: string
  tipo?: string
  source_file: string
  uploaded_at: string | null
  linhas_importadas: number
  linhas_substituidas: number
}

export default function Dashboard() {
  const [tipo, setTipo] = useState<Tipo>("polpa")
  const [periods, setPeriods] = useState<string[]>([])
  const [fromComp, setFromComp] = useState<string>("")
  const [toComp, setToComp] = useState<string>("")
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([])
  const [topCanais, setTopCanais] = useState<TopCanal[]>([])
  const [uploads, setUploads] = useState<UploadEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const base = `?tipo=${tipo}`
        const params = fromComp || toComp ? `&from_comp=${fromComp || ""}&to_comp=${toComp || ""}` : ""
        const [periodsRes, metricsRes, tsRes, canaisRes, uploadsRes] = await Promise.all([
          fetch(`${API_BASE}/api/periods${base}`),
          fetch(`${API_BASE}/api/metrics${base}${params}`),
          fetch(`${API_BASE}/api/timeseries/revenue${base}${params}`),
          fetch(`${API_BASE}/api/top-canais${base}${params}&limit=10`),
          fetch(`${API_BASE}/api/uploads?limit=30`),
        ])
        if (cancelled) return
        const periodsData = await periodsRes.json()
        const metricsData = await metricsRes.json()
        const tsData = await tsRes.json()
        const canaisData = await canaisRes.json()
        const uploadsData = await uploadsRes.json()
        const periodList = periodsData.periods || []
        setPeriods(periodList)
        setMetrics(metricsData)
        setTimeseries(tsData.dados || [])
        setTopCanais(canaisData.canais || [])
        setUploads(uploadsData.uploads || [])
        if (periodList.length > 0 && !fromComp && !toComp) {
          const sorted = [...periodList].sort()
          setFromComp(sorted[0])
          setToComp(sorted[sorted.length - 1])
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro ao carregar dados.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [tipo, fromComp, toComp])

  if (loading && !metrics) {
    return (
      <div className="container">
        <div className="loading">Carregando…</div>
      </div>
    )
  }
  if (error) {
    return (
      <div className="container">
        <div className="error-msg">{error}</div>
      </div>
    )
  }

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v)
  const formatNumber = (v: number) => new Intl.NumberFormat("pt-BR").format(v)
  const quantidadeLabel = tipo === "polpa" ? "Quantidade (kg)" : "Quantidade (L)"
  const quantidadeVal = tipo === "polpa"
    ? (metrics?.quantidade_kg ?? 0)
    : (metrics?.quantidade_litros ?? 0)

  return (
    <div className="container">
      <div className="filters-row" style={{ marginBottom: "1rem" }}>
        <label>Tipo:</label>
        <select value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}>
          <option value="polpa">Polpa congelada</option>
          <option value="extrato">Extrato de manga</option>
        </select>
        <label>De (competência):</label>
        <select value={fromComp} onChange={(e) => setFromComp(e.target.value)}>
          <option value="">—</option>
          {periods.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <label>Até:</label>
        <select value={toComp} onChange={(e) => setToComp(e.target.value)}>
          <option value="">—</option>
          {periods.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="label">Receita total</div>
          <div className="value">{formatCurrency(metrics?.receita_total ?? 0)}</div>
          {(fromComp || toComp) && <div className="sub">Período selecionado</div>}
        </div>
        <div className="kpi-card">
          <div className="label">{quantidadeLabel}</div>
          <div className="value">{formatNumber(quantidadeVal)}</div>
        </div>
        <div className="kpi-card">
          <div className="label">Registros</div>
          <div className="value">{formatNumber(metrics?.registros ?? 0)}</div>
        </div>
      </div>

      <div className="chart-section">
        <h3>Receita por mês ({tipo === "polpa" ? "Polpa" : "Extrato"})</h3>
        {timeseries.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={timeseries} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="periodo" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatCurrency(v)} />
              <Tooltip formatter={(v: number) => [formatCurrency(v), "Receita"]} />
              <Line type="monotone" dataKey="receita" stroke="#0f172a" strokeWidth={2} dot={{ r: 4 }} name="Receita" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p style={{ color: "#64748b", margin: 0 }}>Nenhum dado no período.</p>
        )}
      </div>

      <div className="chart-section">
        <h3>Top 10 canais por receita</h3>
        {topCanais.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={topCanais}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="canal" width={95} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [formatCurrency(v), "Receita"]} />
              <Bar dataKey="receita" fill="#334155" radius={[0, 4, 4, 0]} name="Receita" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p style={{ color: "#64748b", margin: 0 }}>Nenhum dado.</p>
        )}
      </div>

      <div className="chart-section">
        <h3>Uploads realizados</h3>
        {uploads.length > 0 ? (
          <table className="uploads-table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Competência</th>
                <th>Arquivo</th>
                <th>Data do upload</th>
                <th>Linhas importadas</th>
                <th>Substituídas</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((u, i) => (
                <tr key={i}>
                  <td>{u.tipo ?? "—"}</td>
                  <td>{u.competencia}</td>
                  <td>{u.source_file}</td>
                  <td>{u.uploaded_at ? new Date(u.uploaded_at).toLocaleString("pt-BR") : "—"}</td>
                  <td>{u.linhas_importadas}</td>
                  <td>{u.linhas_substituidas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: "#64748b", margin: 0 }}>Nenhum upload registrado.</p>
        )}
      </div>
    </div>
  )
}
