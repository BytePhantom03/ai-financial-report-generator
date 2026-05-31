import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const STEPS = [
  { id: 'PENDING', label: 'Queued', icon: '⏳' },
  { id: 'EXTRACTING_TEXT', label: 'Extracting Text from Document', icon: '📄' },
  { id: 'ANALYZING_WITH_LLM', label: 'AI Analyzing Financials', icon: '🤖' },
  { id: 'COMPILING_PDF', label: 'Rendering Geojit PDF', icon: '📊' },
  { id: 'COMPLETED', label: 'Report Ready!', icon: '✅' },
];

export default function App() {
  const [companyName, setCompanyName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('IDLE');
  const [error, setError] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Poll for status
  useEffect(() => {
    let interval;
    if (jobId && !['COMPLETED', 'FAILED', 'IDLE'].includes(status)) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${jobId}`);
          setStatus(res.data.status);
          if (res.data.status === 'COMPLETED') {
            setReportData(res.data.extracted_data);
          }
          if (res.data.status === 'FAILED') {
            setError(res.data.error || 'Unknown error');
          }
        } catch (err) {
          console.error(err);
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [jobId, status]);

  const handleSubmit = async () => {
    if (!companyName.trim()) { alert('Please enter a company name.'); return; }
    if (!selectedFile) { alert('Please select a file.'); return; }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('company_name', companyName);

    try {
      setStatus('PENDING');
      setError(null);
      setReportData(null);
      const res = await axios.post(`${API_BASE}/extract`, formData);
      setJobId(res.data.id);
    } catch (err) {
      setStatus('FAILED');
      setError(err.message);
    }
  };

  const handleDrag = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(e.type === 'dragenter' || e.type === 'dragover'); };
  const handleDrop = (e) => { e.preventDefault(); setDragActive(false); if (e.dataTransfer.files?.[0]) setSelectedFile(e.dataTransfer.files[0]); };

  const currentStepIdx = STEPS.findIndex(s => s.id === status);

  return (
    <div className="min-h-screen py-8 px-4">
      {/* Header */}
      <div className="max-w-3xl mx-auto text-center mb-10">
        <div className="inline-flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl" style={{background:'#004B87'}}>
            <span className="text-white">📈</span>
          </div>
          <h1 className="text-3xl font-bold" style={{color:'#004B87'}}>
            Geojit AI Research
          </h1>
        </div>
        <p className="text-gray-500 text-sm max-w-lg mx-auto">
          Upload a financial context document (PDF, CSV, or TXT) and instantly generate a professional Geojit-style research report.
        </p>
      </div>

      {/* Input Form */}
      {(status === 'IDLE' || status === 'COMPLETED' || status === 'FAILED') && (
        <div className="max-w-xl mx-auto space-y-5">
          {/* Company Name */}
          <div className="glass-panel rounded-xl p-5">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Company Name</label>
            <input
              type="text"
              className="w-full px-4 py-3 rounded-lg border border-gray-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm"
              placeholder="e.g. ICICI Bank, Zomato Ltd, Infosys"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
          </div>

          {/* File Upload */}
          <div
            className={`glass-panel rounded-xl p-8 text-center cursor-pointer transition-all border-2 border-dashed ${
              dragActive ? 'border-blue-500 bg-blue-50/30' : selectedFile ? 'border-green-400 bg-green-50/20' : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input ref={fileInputRef} type="file" accept=".pdf,.csv,.txt" onChange={(e) => setSelectedFile(e.target.files?.[0])} className="hidden" />
            {selectedFile ? (
              <div>
                <div className="text-4xl mb-2">✅</div>
                <p className="font-semibold text-gray-800">{selectedFile.name}</p>
                <p className="text-xs text-gray-500 mt-1">{(selectedFile.size / 1024).toFixed(1)} KB • Click to change</p>
              </div>
            ) : (
              <div>
                <div className="text-4xl mb-2">📂</div>
                <p className="font-semibold text-gray-700">Drag & drop your context document</p>
                <p className="text-xs text-gray-400 mt-1">Supports PDF, CSV, and TXT files</p>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!companyName.trim() || !selectedFile}
            className="w-full py-3.5 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-lg active:scale-[0.98]"
            style={{background: !companyName.trim() || !selectedFile ? '#aaa' : '#004B87'}}
          >
            🚀 Generate Geojit Research Report
          </button>

          {/* Error */}
          {status === 'FAILED' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-center">
              <p className="text-red-700 font-semibold">Generation Failed</p>
              <p className="text-red-500 text-xs mt-1">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Processing Tracker */}
      {!['IDLE', 'COMPLETED', 'FAILED'].includes(status) && (
        <div className="max-w-md mx-auto glass-panel rounded-2xl p-8">
          <h3 className="text-lg font-bold text-gray-800 mb-6 text-center">Processing Document...</h3>
          <div className="space-y-4">
            {STEPS.map((step, idx) => {
              const done = idx < currentStepIdx || status === 'COMPLETED';
              const active = idx === currentStepIdx && status !== 'COMPLETED';
              return (
                <div key={step.id} className={`flex items-center gap-3 transition-all ${done ? 'text-gray-800' : active ? 'text-blue-700' : 'text-gray-300'}`}>
                  <span className="text-xl w-8 text-center">{done ? '✅' : active ? '⏳' : '○'}</span>
                  <span className={`text-sm ${active ? 'font-bold' : ''}`}>{step.label}</span>
                  {active && <span className="ml-auto text-xs text-blue-500 animate-pulse">Processing...</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Results */}
      {status === 'COMPLETED' && reportData && (
        <div className="max-w-3xl mx-auto mt-8 space-y-6">
          {/* Download Card */}
          <div className="glass-panel rounded-2xl p-8 text-center">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">{reportData.company_name}</h2>
            <p className="text-gray-500 text-sm mb-6">{reportData.sector} • {reportData.report_date}</p>
            <a
              href={`${API_BASE}/download/${jobId}`}
              download
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-white font-semibold text-sm transition-all hover:shadow-xl active:scale-95"
              style={{background:'#004B87'}}
            >
              ⬇️ Download Geojit-Style PDF Report
            </a>
          </div>

          {/* Preview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Highlights */}
            <div className="glass-panel rounded-xl p-5">
              <h3 className="font-bold text-gray-800 mb-3 text-sm">Key Highlights</h3>
              <ul className="space-y-2">
                {reportData.highlights?.slice(0, 5).map((h, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-2"><span>•</span><span>{h}</span></li>
                ))}
              </ul>
            </div>
            {/* Financials Preview */}
            <div className="glass-panel rounded-xl p-5">
              <h3 className="font-bold text-gray-800 mb-3 text-sm">Financial Snapshot</h3>
              {reportData.financials?.income_statement?.length > 0 ? (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b">
                      <th className="text-left py-1">Metric</th>
                      <th className="text-right py-1">FY25A</th>
                      <th className="text-right py-1">FY26E</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.financials.income_statement.slice(0, 5).map((r, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-1.5 text-gray-700">{r.metric}</td>
                        <td className="py-1.5 text-right text-gray-600">{r.fy25a}</td>
                        <td className="py-1.5 text-right font-medium" style={{color:'#004B87'}}>{r.fy26e}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="text-xs text-gray-400">No income statement data extracted.</p>}
            </div>
          </div>

          {/* Generate Another */}
          <div className="text-center">
            <button
              onClick={() => { setStatus('IDLE'); setJobId(null); setReportData(null); setSelectedFile(null); setCompanyName(''); }}
              className="text-sm text-blue-600 hover:underline"
            >
              ← Generate another report
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
