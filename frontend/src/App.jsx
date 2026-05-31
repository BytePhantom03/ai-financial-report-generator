import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const STEPS = [
  { id: 'PENDING',          label: 'Queued',                       icon: '⏳', desc: 'Job submitted...' },
  { id: 'EXTRACTING_TEXT',  label: 'Reading Document',             icon: '📄', desc: 'Parsing PDF / CSV / TXT...' },
  { id: 'ANALYZING_WITH_LLM', label: 'AI Extracting Financials',  icon: '🤖', desc: 'Running AI extraction pipeline...' },
  { id: 'COMPILING_PDF',    label: 'Rendering Report',             icon: '📊', desc: 'Building Geojit-style PDF...' },
  { id: 'COMPLETED',        label: 'Report Ready!',                icon: '✅', desc: 'Download your report below.' },
];

const PROVIDER_BADGES = {
  'Gemini 2.0 Flash':      { bg: '#1a73e8', label: '⚡ Gemini 2.0 Flash' },
  'Groq Llama 3.1':        { bg: '#f55036', label: '🦙 Groq Llama 3.1' },
  'OpenAI GPT-4o-mini':    { bg: '#10a37f', label: '🌿 OpenAI GPT-4o' },
  'Rule-based Engine':     { bg: '#666',    label: '⚙️ Rule-based Engine' },
};

export default function App() {
  const [companyName, setCompanyName]   = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobId, setJobId]               = useState(null);
  const [status, setStatus]             = useState('IDLE');
  const [error, setError]               = useState(null);
  const [reportData, setReportData]     = useState(null);
  const [aiProvider, setAiProvider]     = useState('');
  const [dragActive, setDragActive]     = useState(false);
  const [health, setHealth]             = useState(null);
  const fileInputRef = useRef(null);

  // Load health on mount
  useEffect(() => {
    axios.get(`${API_BASE}/health`).then(r => setHealth(r.data)).catch(() => {});
  }, []);

  // Poll for status
  useEffect(() => {
    let interval;
    if (jobId && !['COMPLETED', 'FAILED', 'IDLE'].includes(status)) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${jobId}`);
          setStatus(res.data.status);
          if (res.data.extracted_data)  setReportData(res.data.extracted_data);
          if (res.data.ai_provider)     setAiProvider(res.data.ai_provider);
          if (res.data.status === 'FAILED') setError(res.data.error || 'Unknown error');
        } catch { /* ignore */ }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [jobId, status]);

  const handleSubmit = async () => {
    if (!companyName.trim()) { alert('Enter a company name.'); return; }
    if (!selectedFile)        { alert('Select a file.');         return; }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('company_name', companyName);

    try {
      setStatus('PENDING');
      setError(null);
      setReportData(null);
      setAiProvider('');
      const res = await axios.post(`${API_BASE}/extract`, formData);
      setJobId(res.data.id);
    } catch (err) {
      setStatus('FAILED');
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setSelectedFile(f);
  }, []);

  const reset = () => { setStatus('IDLE'); setJobId(null); setReportData(null); setSelectedFile(null); setCompanyName(''); setError(null); };

  const currentStepIdx = STEPS.findIndex(s => s.id === status);
  const providerBadge  = PROVIDER_BADGES[aiProvider] || PROVIDER_BADGES['Rule-based Engine'];

  const isIdle      = status === 'IDLE';
  const isProcessing = !['IDLE', 'COMPLETED', 'FAILED'].includes(status);
  const isDone      = status === 'COMPLETED' && reportData;
  const isFailed    = status === 'FAILED';

  return (
    <div className="app-root">
      {/* Background orbs */}
      <div className="bg-orb orb1" />
      <div className="bg-orb orb2" />
      <div className="bg-orb orb3" />

      <div className="container">

        {/* ── Header ─────────────────────────────────── */}
        <header className="header">
          <div className="logo-row">
            <div className="logo-icon">📈</div>
            <div>
              <h1 className="brand-title">Bull AI</h1>
              <p className="brand-sub">Financial Research Report Generator</p>
            </div>
          </div>
          <p className="brand-desc">
            Upload any financial document — PDF, CSV, or TXT — and instantly generate a
            professional <strong>Geojit-style 4-page equity research report</strong> with AI.
          </p>

          {/* Provider status bar */}
          {health && (
            <div className="provider-bar">
              <span className={`provider-chip ${health.gemini ? 'active' : 'inactive'}`}>
                ⚡ Gemini {health.gemini ? 'Ready' : 'No Key'}
              </span>
              <span className={`provider-chip ${health.groq ? 'active' : 'inactive'}`}>
                🦙 Groq {health.groq ? 'Ready' : 'No Key'}
              </span>
              <span className={`provider-chip ${health.openai ? 'active' : 'inactive'}`}>
                🌿 OpenAI {health.openai ? 'Ready' : 'No Key'}
              </span>
              <span className="provider-chip active">⚙️ Rule-based Always Ready</span>
            </div>
          )}
        </header>

        {/* ── Input Form ─────────────────────────────── */}
        {(isIdle || isFailed) && (
          <div className="form-card">
            {/* Company name */}
            <div className="form-group">
              <label htmlFor="company-name-input" className="form-label">Company Name</label>
              <input
                id="company-name-input"
                type="text"
                className="form-input"
                placeholder="e.g. ICICI Bank, Zomato, JSW Energy"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              />
            </div>

            {/* File dropzone */}
            <div
              id="file-dropzone"
              className={`dropzone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
              onDragEnter={handleDrag} onDragLeave={handleDrag}
              onDragOver={handleDrag} onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.csv,.txt"
                onChange={e => setSelectedFile(e.target.files?.[0])}
                className="hidden-input"
              />
              {selectedFile ? (
                <div className="file-info">
                  <div className="file-icon">
                    {selectedFile.name.endsWith('.pdf') ? '📕' :
                     selectedFile.name.endsWith('.csv') ? '📊' : '📄'}
                  </div>
                  <p className="file-name">{selectedFile.name}</p>
                  <p className="file-size">{(selectedFile.size / 1024).toFixed(1)} KB · click to change</p>
                </div>
              ) : (
                <div className="drop-hint">
                  <div className="drop-icon">📂</div>
                  <p className="drop-title">Drag & drop your document</p>
                  <p className="drop-sub">PDF (recommended) · CSV · TXT</p>
                  <div className="drop-badges">
                    <span className="badge">Geojit-style template</span>
                    <span className="badge">4-page report</span>
                    <span className="badge">AI-powered charts</span>
                  </div>
                </div>
              )}
            </div>

            {isFailed && (
              <div className="error-box">
                <p className="error-title">⚠ Generation Failed</p>
                <p className="error-msg">{error}</p>
              </div>
            )}

            <button
              id="generate-btn"
              className="generate-btn"
              onClick={handleSubmit}
              disabled={!companyName.trim() || !selectedFile}
            >
              🚀 Generate Geojit Research Report
            </button>
          </div>
        )}

        {/* ── Processing Tracker ─────────────────────── */}
        {isProcessing && (
          <div className="tracker-card">
            <div className="tracker-header">
              <div className="spinner" />
              <span>Processing <strong>{companyName}</strong>...</span>
            </div>
            <div className="steps">
              {STEPS.map((step, idx) => {
                const done   = idx < currentStepIdx;
                const active = idx === currentStepIdx;
                return (
                  <div key={step.id} className={`step ${done ? 'done' : active ? 'active' : 'pending'}`}>
                    <div className="step-icon">
                      {done ? '✅' : active ? <span className="pulse-dot" /> : '○'}
                    </div>
                    <div className="step-text">
                      <span className="step-label">{step.label}</span>
                      {active && <span className="step-desc">{step.desc}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Result ─────────────────────────────────── */}
        {isDone && (
          <div className="result-wrapper">
            {/* Download hero */}
            <div className="result-hero">
              <div className="result-icon">📊</div>
              <h2 className="result-company">{reportData.company_name}</h2>
              <p className="result-meta">{reportData.sector} · {reportData.report_date}</p>

              {aiProvider && (
                <div className="ai-badge" style={{ background: providerBadge.bg }}>
                  {providerBadge.label}
                </div>
              )}

              <a
                id="download-btn"
                href={`${API_BASE}/download/${jobId}`}
                download
                className="download-btn"
              >
                ⬇️ Download PDF Research Report
              </a>
              <button className="reset-link" onClick={reset}>← Generate another report</button>
            </div>

            {/* Data preview */}
            <div className="preview-grid">
              {/* Valuation snapshot */}
              {reportData.valuation && (
                <div className="preview-card">
                  <h3 className="preview-title">Valuation</h3>
                  <div className="val-grid">
                    <div className="val-item">
                      <span className="val-label">Rating</span>
                      <span className={`rating-pill rating-${(reportData.valuation.rating || 'hold').toLowerCase()}`}>
                        {reportData.valuation.rating || '—'}
                      </span>
                    </div>
                    <div className="val-item">
                      <span className="val-label">Target</span>
                      <span className="val-value">₹{reportData.valuation.target || '—'}</span>
                    </div>
                    <div className="val-item">
                      <span className="val-label">CMP</span>
                      <span className="val-value">₹{reportData.valuation.cmp || '—'}</span>
                    </div>
                    <div className="val-item">
                      <span className="val-label">Return</span>
                      <span className="val-value upside">{reportData.valuation.upside || '—'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Key highlights */}
              <div className="preview-card">
                <h3 className="preview-title">Key Highlights</h3>
                <ul className="highlights-list">
                  {(reportData.highlights || []).slice(0, 5).map((h, i) => (
                    <li key={i}><span className="bullet">•</span>{h}</li>
                  ))}
                </ul>
              </div>

              {/* Income statement */}
              <div className="preview-card span-2">
                <h3 className="preview-title">Financial Snapshot (Annual)</h3>
                {reportData.financials?.income_statement?.length > 0 ? (
                  <table className="fin-table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>FY23A</th>
                        <th>FY24A</th>
                        <th>FY25A</th>
                        <th>FY26E</th>
                        <th>FY27E</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.financials.income_statement.slice(0, 8).map((r, i) => (
                        <tr key={i}>
                          <td className="metric-col">{r.metric}</td>
                          <td>{r.fy23a}</td>
                          <td>{r.fy24a}</td>
                          <td>{r.fy25a}</td>
                          <td className="highlight-col">{r.fy26e}</td>
                          <td className="highlight-col">{r.fy27e}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="no-data">Upload a richer document with Gemini/Groq API key for detailed financials.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
