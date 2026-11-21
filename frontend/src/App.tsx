import { useEffect, useState } from 'react'
import { Activity, AlertCircle, Box, Check, ChevronDown, Code2, FilePlus2, FolderOpen, Gauge, Layers3, Loader2, MessageSquare, RefreshCw, Send, Settings2, Sparkles, Workflow } from 'lucide-react'

type Doc = { id?: string; name?: string; [key: string]: unknown }
type Config = { app_name: string; ai_provider: string; onshape_configured: boolean; cloud_ai_configured: boolean; ollama_model: string; cloud_ai_model: string }
type Usage = { successful_calls_recorded_by_app: number; note: string }
const API = 'http://127.0.0.1:8000/api'
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Request failed (' + response.status + ')')
  return data as T
}
export default function App() {
  const [config, setConfig] = useState<Config | null>(null)
  const [documents, setDocuments] = useState<Doc[]>([])
  const [selected, setSelected] = useState('')
  const [provider, setProvider] = useState<'ollama' | 'cloud'>('ollama')
  const [prompt, setPrompt] = useState('Create a simple parametric mounting bracket with two holes. Explain the modelling steps and dimensions.')
  const [plan, setPlan] = useState('')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [newDocName, setNewDocName] = useState('My AI CAD Project')
  async function refresh() {
    setError(''); setNotice('')
    try {
      const cfg = await api<Config>('/config'); setConfig(cfg); setProvider(cfg.ai_provider === 'cloud' ? 'cloud' : 'ollama')
      setUsage(await api<Usage>('/usage'))
      if (cfg.onshape_configured) {
        const raw = await api<unknown>('/onshape/documents')
        const list = Array.isArray(raw) ? raw : ((raw as { items?: Doc[] })?.items || [])
        setDocuments(list as Doc[])
      } else setDocuments([])
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not connect to backend') }
  }
  useEffect(() => { void refresh() }, [])
  async function createDocument() {
    setBusy(true); setError(''); setNotice('')
    try { await api('/onshape/documents', { method: 'POST', body: JSON.stringify({ name: newDocName }) }); setNotice('Document created in Onshape. Refreshing list…'); await refresh() }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not create document') } finally { setBusy(false) }
  }
  async function askAI() {
    if (!prompt.trim()) return
    setBusy(true); setError(''); setNotice(''); setPlan('')
    try {
      const doc = documents.find(d => d.id === selected)
      const result = await api<{ plan: string; executed: boolean }>('/ai/plan', { method: 'POST', body: JSON.stringify({ prompt, context: doc ? JSON.stringify({ selected_document: doc }) : '', provider }) })
      setPlan(result.plan); setNotice('Plan generated. No CAD changes have been made.'); setUsage(await api<Usage>('/usage'))
    } catch (e) { setError(e instanceof Error ? e.message : 'AI request failed') } finally { setBusy(false) }
  }
  const activeDoc = documents.find(d => d.id === selected)
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Box size={21}/></div><div><strong>Onshape AI</strong><span>STUDIO</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <button className="nav-item active"><Workflow size={17}/> AI CAD Workspace</button>
      <button className="nav-item" onClick={() => setShowSettings(v => !v)}><Settings2 size={17}/> Connection settings <ChevronDown size={14} className="nav-end"/></button>
      {showSettings && <div className="settings-note">Credentials are configured in backend/.env. They are never sent to this browser UI.</div>}
      <div className="side-divider"/><div className="workspace-label row-label"><span>ONSHAPE DOCUMENTS</span><button title="Refresh documents" onClick={() => void refresh()}><RefreshCw size={14}/></button></div>
      {config?.onshape_configured ? <div className="doc-list">{documents.length ? documents.map((doc, i) => <button key={doc.id || i} className={'doc-item ' + (selected === doc.id ? 'selected' : '')} onClick={() => setSelected(doc.id || '')}><FolderOpen size={15}/><span>{doc.name || 'Untitled document'}</span></button>) : <p className="muted small">No documents returned.</p>}</div> : <p className="muted small side-hint">Add your Onshape API credentials to the backend .env file.</p>}
      <div className="side-bottom"><div className="status-line"><span className={'status-dot ' + (config?.onshape_configured ? 'online' : '')}/>{config?.onshape_configured ? 'Onshape configured' : 'Onshape not connected'}</div><div className="status-line"><span className="status-dot online"/>{config?.ai_provider === 'cloud' ? 'Cloud AI selected' : 'Local AI selected'}</div></div>
    </aside>
    <main className="main-area"><header className="topbar"><div><span className="crumb">Workspace</span><span className="crumb-sep">/</span><strong>AI CAD Studio</strong></div><div className="top-actions"><select className="provider-select" value={provider} onChange={e => setProvider(e.target.value as 'ollama' | 'cloud')}><option value="ollama">Local Ollama</option><option value="cloud" disabled={!config?.cloud_ai_configured}>Cloud AI</option></select><span className="model-chip"><Sparkles size={14}/>{config?.ai_provider === 'cloud' ? config.cloud_ai_model : config?.ollama_model || 'Checking AI…'}</span><button className="icon-btn" onClick={() => void refresh()} title="Refresh status"><RefreshCw size={17}/></button><div className="avatar">AI</div></div></header>
      <div className="content"><section className="welcome"><div className="eyebrow"><Sparkles size={14}/> AI-POWERED PARAMETRIC DESIGN</div><h1>Design with intent.<br/><span>Build with precision.</span></h1><p>Describe the part you want to create. Your AI assistant will turn the idea into a structured, reviewable CAD plan for Onshape.</p></section>
        {error && <div className="alert error"><AlertCircle size={17}/><span>{error}</span></div>}{notice && <div className="alert success"><Check size={17}/><span>{notice}</span></div>}
        {!config?.onshape_configured && <div className="connect-card"><div className="connect-icon"><Settings2 size={20}/></div><div><strong>Connect your Onshape account</strong><p>Add ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY to backend/.env, then restart the backend.</p></div></div>}
        <div className="studio-grid"><section className="panel prompt-panel"><div className="panel-heading"><div className="panel-icon purple"><MessageSquare size={17}/></div><div><h2>Design prompt</h2><p>Describe your part, dimensions, and design intent.</p></div><span className="step-tag">01</span></div>
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe what you want to design…" rows={7}/><div className="prompt-footer"><span className="muted small">Be specific about dimensions and constraints.</span><button className="primary-btn" onClick={() => void askAI()} disabled={busy || !prompt.trim()}>{busy ? <Loader2 className="spin" size={16}/> : <Sparkles size={16}/>} Generate plan <Send size={14}/></button></div>
          <div className="suggestions"><span>TRY:</span><button onClick={() => setPrompt('Design a 60 × 40 × 8 mm mounting plate with four 5 mm holes, 5 mm from each corner.')}>Mounting plate</button><button onClick={() => setPrompt('Plan a hollow cylindrical spacer, 20 mm outer diameter, 10 mm inner diameter, 30 mm tall.')}>Spacer</button><button onClick={() => setPrompt('Create a small L-bracket with 4 mm wall thickness and two mounting holes on each flange.')}>L-bracket</button></div></section>
          <section className="panel doc-panel"><div className="panel-heading"><div className="panel-icon green"><Layers3 size={17}/></div><div><h2>Onshape project</h2><p>Select a document for design context.</p></div><span className="step-tag">02</span></div>
            <label className="field-label">ACTIVE DOCUMENT</label><div className="select-wrap"><select value={selected} onChange={e => setSelected(e.target.value)}><option value="">No document selected</option>{documents.map((d, i) => <option key={d.id || i} value={d.id || ''}>{d.name || 'Untitled document'}</option>)}</select><ChevronDown size={15}/></div>
            {activeDoc ? <div className="doc-detail"><div className="doc-detail-icon"><FolderOpen size={18}/></div><div><strong>{activeDoc.name}</strong><span>{activeDoc.id}</span></div></div> : <div className="empty-doc"><FolderOpen size={25}/><span>Select an existing document or create a new one.</span></div>}
            <div className="create-row"><input value={newDocName} onChange={e => setNewDocName(e.target.value)} aria-label="New document name"/><button className="secondary-btn" onClick={() => void createDocument()} disabled={busy || !config?.onshape_configured || !newDocName.trim()}><FilePlus2 size={15}/> Create</button></div><p className="muted tiny">Creating a document uses one Onshape write request.</p></section></div>
        <section className="panel result-panel"><div className="panel-heading"><div className="panel-icon amber"><Code2 size={17}/></div><div><h2>Design plan</h2><p>Review the proposed modelling approach before making changes.</p></div><span className="step-tag">03</span></div>
          {plan ? <pre className="plan-output">{plan}</pre> : <div className="empty-result"><div className="empty-illustration"><Workflow size={27}/></div><strong>Your design plan will appear here</strong><span>AI-generated operations and FeatureScript drafts are suggestions only. Nothing is sent to your document automatically.</span></div>}</section>
        <div className="bottom-stats"><div><Activity size={16}/><span>App-recorded successful Onshape calls</span><strong>{usage?.successful_calls_recorded_by_app ?? '—'}</strong></div><div><Gauge size={16}/><span>Request strategy</span><strong>Cached reads · Low concurrency</strong></div><div><Code2 size={16}/><span>FeatureScript</span><strong>Draft only</strong></div></div><p className="footnote">Usage count reflects this app instance only. Check Onshape Developer settings for your actual account allocation.</p>
      </div></main></div>
