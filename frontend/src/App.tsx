import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import Upload from "./pages/Upload"
import Dashboard from "./pages/Dashboard"

function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <h1>Dashboard Mangas</h1>
        <nav className="app-nav">
          <NavLink to="/" end>Upload</NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
