import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  FileCode, LogOut, UploadCloud, FileText, CheckCircle2, 
  AlertTriangle, Clock, RefreshCw, Sparkles, ChevronRight, User, Trash2,
  Database, Scale, History, Percent, DollarSign, Calendar, Eye, ShieldAlert, Check, X, Flame, MessageSquare, Download, ListFilter, FileSpreadsheet
} from 'lucide-react';

const Dashboard = () => {
  const { user, token, logout } = useAuth();
  
  // Tabs configuration
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState('analytics'); // 'analytics', 'documents', 'reconciler'
  const [activeTab, setActiveTab] = useState('invoice'); // 'invoice' or 'po'
  
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [recentUploads, setRecentUploads] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [uploadStatus, setUploadStatus] = useState(null); 
  const fileInputRef = useRef(null);

  // Phase 3 & 4 state variables
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docLines, setDocLines] = useState([]);
  const [loadingLines, setLoadingLines] = useState(false);
  const [candidateDoc, setCandidateDoc] = useState(null);
  const [similarities, setSimilarities] = useState([]);
  const [loadingSimilarities, setLoadingSimilarities] = useState(false);

  // Phase 5 & 6 state variables
  const [matches, setMatches] = useState([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [docFlags, setDocFlags] = useState([]);
  const [reconciling, setReconciling] = useState(false);
  const [reconcileResult, setReconcileResult] = useState(null);

  // Phase 9 & 10 state variables
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(true);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingAudits, setLoadingAudits] = useState(false);
  
  // Manual approval overlay states
  const [showApprovalOverlay, setShowApprovalOverlay] = useState(false);
  const [activeApprovalMatch, setActiveApprovalMatch] = useState(null);
  const [approvalComment, setApprovalComment] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  const fetchRecentUploads = async () => {
    try {
      const res = await fetch('/api/recent-uploads', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setRecentUploads(data);
      }
    } catch (err) {
      console.error("Failed to load uploads log", err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const fetchMatches = async () => {
    setLoadingMatches(true);
    try {
      const res = await fetch('/api/matches', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setMatches(data);
      }
    } catch (err) {
      console.error("Failed to load matches log", err);
    } finally {
      setLoadingMatches(false);
    }
  };

  const fetchAnalytics = async () => {
    setLoadingAnalytics(true);
    try {
      const res = await fetch('/api/analytics', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const fetchAuditLogs = async () => {
    setLoadingAudits(true);
    try {
      const res = await fetch('/api/audit-logs', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch (err) {
      console.error("Failed to load audits", err);
    } finally {
      setLoadingAudits(false);
    }
  };

  useEffect(() => {
    fetchRecentUploads();
    fetchMatches();
    fetchAnalytics();
    fetchAuditLogs();
  }, [token]);

  // Fetch lines and flags for selected document
  useEffect(() => {
    if (selectedDoc) {
      setLoadingLines(true);
      setDocLines([]);
      setCandidateDoc(null);
      setSimilarities([]);
      setDocFlags([]);
      setReconcileResult(null);

      // Fetch Lines
      fetch(`/api/documents/${selectedDoc.id}/lines`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Failed to load lines");
      })
      .then(data => {
        setDocLines(data);
        setLoadingLines(false);
      })
      .catch(err => {
        console.error(err);
        setLoadingLines(false);
      });

      // Fetch Flags
      fetch(`/api/documents/${selectedDoc.id}/flags`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => {
        if (res.ok) return res.json();
        return [];
      })
      .then(data => {
        setDocFlags(data);
      })
      .catch(err => console.error(err));
    }
  }, [selectedDoc, token]);

  // Fetch similarities when selected document and candidate document are both active
  useEffect(() => {
    if (selectedDoc && candidateDoc) {
      setLoadingSimilarities(true);
      setSimilarities([]);
      fetch(`/api/documents/${selectedDoc.id}/features?candidate_id=${candidateDoc.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Failed to load features");
      })
      .then(data => {
        setSimilarities(data);
        setLoadingSimilarities(false);
      })
      .catch(err => {
        console.error(err);
        setLoadingSimilarities(false);
      });
    }
  }, [selectedDoc, candidateDoc, token]);

  // Run auto-reconciliation matching engine (Phase 5 & 6)
  const handleReconcile = async (invoiceId) => {
    setReconciling(true);
    setReconcileResult(null);
    try {
      const res = await fetch(`/api/reconcile/${invoiceId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setReconcileResult(data);
        fetchRecentUploads();
        fetchMatches();
        fetchAnalytics();
        
        // Refresh flags list for selected invoice
        fetch(`/api/documents/${invoiceId}/flags`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(flags => setDocFlags(flags));
      }
    } catch (err) {
      console.error("Match reconciliation failed", err);
    } finally {
      setReconciling(false);
    }
  };

  // AP manual workflow actions (Phase 10)
  const submitApprovalDecision = async (matchId, action) => {
    setSubmittingAction(true);
    try {
      const res = await fetch(`/api/matches/${matchId}/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ comment: approvalComment })
      });
      if (res.ok) {
        setApprovalComment('');
        setShowApprovalOverlay(false);
        fetchMatches();
        fetchRecentUploads();
        fetchAnalytics();
        fetchAuditLogs();
        if (selectedDoc) {
          setSelectedDoc(prev => prev ? { ...prev, status: action === 'approve' ? 'approved' : action === 'needs-review' ? 'anomaly' : 'processed' } : null);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingAction(false);
    }
  };

  // Export report downloads (Phase 11)
  const handleExportReport = async (reportType, format) => {
    try {
      const res = await fetch(`/api/reports/export?report_type=${reportType}&format=${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        if (format === 'csv') {
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `invomatch_${reportType}_report.csv`;
          document.body.appendChild(a);
          a.click();
          a.remove();
        } else if (format === 'html') {
          const htmlText = await res.text();
          const blob = new Blob([htmlText], { type: 'text/html' });
          const url = window.URL.createObjectURL(blob);
          window.open(url, '_blank');
        }
        fetchAuditLogs(); // Refresh logs
      } else {
        alert("Failed to export report.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Download original file (Phase 10)
  const handleDownload = async (docId, fileName) => {
    try {
      const res = await fetch(`/api/documents/${docId}/download`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        fetchAuditLogs(); // Refresh history
      } else {
        alert("Failed to download document file.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Launch approval overlay
  const launchApprovalOverlay = (matchItem) => {
    setActiveApprovalMatch(matchItem);
    setApprovalComment('');
    setShowApprovalOverlay(true);
    
    // Fetch details for line comparing in approval workspace
    fetch(`/api/recent-uploads`, { headers: { 'Authorization': `Bearer ${token}` } })
      .then(res => res.json())
      .then(uploads => {
        const invDoc = uploads.find(u => u.id === matchItem.invoice_id);
        const poDoc = uploads.find(u => u.id === matchItem.po_id);
        if (invDoc && poDoc) {
          setSelectedDoc(invDoc);
          setCandidateDoc(poDoc);
        }
      });
  };

  // Drag-and-drop triggers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pdf' && ext !== 'csv') {
      setUploadStatus({
        type: 'error',
        message: 'Unsupported format. Please upload PDF or CSV files.'
      });
      setSelectedFile(null);
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadStatus({
        type: 'error',
        message: 'File size exceeds the maximum limit of 10MB.'
      });
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    setUploadStatus(null);
  };

  const handleUploadSubmit = async (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!selectedFile) return;

    setUploading(true);
    setUploadProgress(10);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setUploadProgress(40);
      const endpoint = activeTab === 'invoice' ? '/api/upload/invoice' : '/api/upload/po';
      setUploadProgress(70);
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      setUploadProgress(90);
      const data = await res.json();

      if (res.ok) {
        setUploadStatus({
          type: 'success',
          message: data.message || `${activeTab === 'invoice' ? 'Invoice' : 'Purchase Order'} uploaded and parsed successfully.`
        });
        setSelectedFile(null);
        fetchRecentUploads();
        fetchAnalytics();
        fetchMatches();
      } else if (res.status === 409) {
        setUploadStatus({
          type: 'duplicate',
          message: data.detail || 'Duplicate file detected.'
        });
      } else {
        setUploadStatus({
          type: 'error',
          message: data.detail || 'Upload failed.'
        });
      }
    } catch (err) {
      console.error("Upload failed", err);
      setUploadStatus({
        type: 'error',
        message: 'Network error or server connection failed.'
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const getRiskSeverityColor = (score) => {
    if (score >= 81) return { bg: 'bg-red-500/10 border-red-500/20 text-red-400', label: 'Critical' };
    if (score >= 61) return { bg: 'bg-orange-500/10 border-orange-500/20 text-orange-400', label: 'High' };
    if (score >= 31) return { bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400', label: 'Medium' };
    return { bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400', label: 'Low' };
  };

  const getFeatureLabel = (key) => {
    const labels = {
      "vendor_similarity": "Vendor similarity",
      "sku_similarity": "SKU code match",
      "description_similarity": "Description similarity",
      "qty_difference_rel": "Quantity variance",
      "price_difference_rel": "Price variance",
      "total_difference_rel": "Subtotal discrepancy",
      "date_difference_days": "Date gap",
      "historical_avg_diff": "Historical average deviation"
    };
    return labels[key] || key.replace("_", " ");
  };

  const candidateFiles = recentUploads.filter(doc => 
    selectedDoc && doc.id !== selectedDoc.id && doc.document_type !== selectedDoc.document_type
  );

  const getReconcilerRows = () => {
    const rows = [];

    // 1. Add all active matches
    matches.forEach(match => {
      rows.push({
        type: 'match',
        id: `match-${match.id}`,
        matchId: match.id,
        invoiceId: match.invoice_id,
        poId: match.po_id,
        vendor_name: match.vendor_name,
        invoice_file_name: match.invoice_file_name,
        invoice_number: match.invoice_number,
        invoice_amount: match.invoice_amount,
        po_file_name: match.po_file_name,
        po_number: match.po_number,
        po_amount: match.po_amount,
        confidence: match.match_score * 100,
        risk_score: match.risk_score,
        flags_count: match.flags_count,
        status: match.status,
        originalMatch: match
      });
    });

    // 2. Add unmatched invoices
    recentUploads
      .filter(doc => doc.document_type === 'invoice')
      .forEach(doc => {
        const isMatched = matches.some(m => m.invoice_id === doc.id);
        if (!isMatched) {
          rows.push({
            type: 'unmatched_invoice',
            id: `doc-${doc.id}`,
            docId: doc.id,
            vendor_name: doc.vendor_name || 'Vendor: pending',
            invoice_file_name: doc.file_name,
            invoice_number: doc.doc_number || 'Extracting...',
            invoice_amount: doc.total_amount || 0.0,
            po_file_name: '—',
            po_number: 'Unmatched',
            po_amount: 0.0,
            confidence: 0,
            risk_score: doc.status === 'anomaly' ? 70 : 0,
            flags_count: doc.status === 'anomaly' ? 1 : 0,
            status: doc.status,
            document_type: 'invoice'
          });
        }
      });

    // 3. Add unmatched POs
    recentUploads
      .filter(doc => doc.document_type === 'po')
      .forEach(doc => {
        const isMatched = matches.some(m => m.po_id === doc.id);
        if (!isMatched) {
          rows.push({
            type: 'unmatched_po',
            id: `doc-${doc.id}`,
            docId: doc.id,
            vendor_name: doc.vendor_name || 'Vendor: pending',
            invoice_file_name: '—',
            invoice_number: 'Unmatched',
            invoice_amount: 0.0,
            po_file_name: doc.file_name,
            po_number: doc.doc_number || 'Extracting...',
            po_amount: doc.total_amount || 0.0,
            confidence: 0,
            risk_score: 0,
            flags_count: 0,
            status: doc.status,
            document_type: 'po'
          });
        }
      });

    return rows;
  };

  return (
    <div className="min-h-screen pb-16 bg-[#0B0F19]">
      {/* Header bar */}
      <nav className="sticky top-0 z-40 w-full backdrop-glass border-b border-brand-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-primary to-brand-secondary shadow-glow-primary">
              <FileCode className="h-5.5 w-5.5 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-slate-100">InvoMatch</span>
              <span className="ml-2 rounded-md bg-brand-primary/10 border border-brand-primary/20 px-2 py-0.5 text-xs text-brand-primary font-semibold font-mono">REPORTS v5.0</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2.5 rounded-xl bg-slate-900/60 border border-brand-border py-1.5 px-3">
              <div className="h-6 w-6 rounded-full bg-brand-primary/20 flex items-center justify-center">
                <User className="h-3.5 w-3.5 text-brand-primary" />
              </div>
              <div className="text-left leading-none">
                <p className="text-xs font-semibold text-slate-200">{user?.username}</p>
                <p className="text-[10px] text-brand-muted uppercase tracking-wider mt-0.5">{user?.role}</p>
              </div>
            </div>

            <button 
              onClick={logout}
              className="flex items-center justify-center gap-2 rounded-xl bg-slate-900 border border-brand-border p-2.5 sm:px-4 sm:py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800/80 hover:border-brand-primary/30 transition-all duration-200"
            >
              <LogOut className="h-4.5 w-4.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 mt-10">
        
        {/* Workspace Workspace Tab Buttons */}
        <div className="flex gap-4 border-b border-brand-border/60 pb-4 mb-8">
          <button
            onClick={() => setActiveWorkspaceTab('analytics')}
            className={`pb-2 text-sm font-bold border-b-2 transition-all ${
              activeWorkspaceTab === 'analytics'
                ? 'border-brand-primary text-white'
                : 'border-transparent text-brand-muted hover:text-slate-200'
            }`}
          >
            Dashboard & Analytics
          </button>
          <button
            onClick={() => { setActiveWorkspaceTab('documents'); fetchRecentUploads(); }}
            className={`pb-2 text-sm font-bold border-b-2 transition-all ${
              activeWorkspaceTab === 'documents'
                ? 'border-brand-primary text-white'
                : 'border-transparent text-brand-muted hover:text-slate-200'
            }`}
          >
            Document Archives & Uploads
          </button>
          <button
            onClick={() => { setActiveWorkspaceTab('reconciler'); fetchMatches(); }}
            className={`pb-2 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeWorkspaceTab === 'reconciler'
                ? 'border-brand-primary text-white'
                : 'border-transparent text-brand-muted hover:text-slate-200'
            }`}
          >
            <Sparkles className="h-4 w-4 text-brand-primary" />
            AI Reconciliation Workspace ({getReconcilerRows().length})
          </button>
        </div>

        {/* Tab 1: Dashboard & Analytics (Phase 9 & 11) */}
        {activeWorkspaceTab === 'analytics' && (
          <div className="space-y-10 animate-fade-in">
            {loadingAnalytics ? (
              <div className="flex h-64 items-center justify-center">
                <LoaderIcon className="animate-spin h-10 w-10 text-brand-primary" />
              </div>
            ) : !analytics ? (
              <div className="text-center py-10 text-brand-muted text-sm">Analytics calculations failed.</div>
            ) : (
              <>
                {/* Analytics Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">Uploaded Invoices</p>
                    <p className="text-2xl font-bold text-white mt-1.5">{analytics.summary.total_invoices}</p>
                  </div>
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">Purchase Orders</p>
                    <p className="text-2xl font-bold text-slate-300 mt-1.5">{analytics.summary.total_pos}</p>
                  </div>
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">Reconciled Rate</p>
                    <p className="text-2xl font-bold text-brand-accent mt-1.5">{Math.round(analytics.summary.match_rate_percent)}%</p>
                  </div>
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">Pending Review</p>
                    <p className="text-2xl font-bold text-amber-400 mt-1.5">{analytics.summary.pending}</p>
                  </div>
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">Needs Review</p>
                    <p className="text-2xl font-bold text-purple-400 mt-1.5">{analytics.summary.needs_review}</p>
                  </div>
                  <div className="backdrop-glass rounded-xl p-4 border border-brand-border text-left bg-gradient-to-t from-red-500/5 to-transparent">
                    <p className="text-[10px] font-bold text-brand-muted uppercase tracking-wider">High Risk Invoices</p>
                    <p className="text-2xl font-bold text-red-400 mt-1.5">{analytics.summary.high_risk}</p>
                  </div>
                </div>

                {/* SVG Visual Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Gauge: Reconciled rate */}
                  <div className="backdrop-glass rounded-2xl p-5 border border-brand-border flex flex-col items-center">
                    <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider self-start mb-4">Overall Match Rate</h3>
                    <div className="relative flex items-center justify-center h-40 w-40">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle cx="80" cy="80" r="60" stroke="#1E293B" strokeWidth="12" fill="transparent" />
                        <circle 
                          cx="80" 
                          cy="80" 
                          r="60" 
                          stroke="url(#accentGrad)" 
                          strokeWidth="12" 
                          fill="transparent" 
                          strokeDasharray={2 * Math.PI * 60}
                          strokeDashoffset={2 * Math.PI * 60 * (1 - analytics.summary.match_rate_percent / 100)}
                          strokeLinecap="round"
                        />
                        <defs>
                          <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#06b6d4" />
                            <stop offset="100%" stopColor="#6366f1" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute flex flex-col items-center">
                        <span className="text-3xl font-extrabold text-white">{Math.round(analytics.summary.match_rate_percent)}%</span>
                        <span className="text-[9px] text-brand-muted font-semibold uppercase tracking-widest mt-1">Reconciled</span>
                      </div>
                    </div>
                  </div>

                  {/* SVG Vertical bar: Risk distribution */}
                  <div className="backdrop-glass rounded-2xl p-5 border border-brand-border">
                    <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider mb-6">Risk Distribution</h3>
                    <div className="flex items-end justify-around h-36 px-4">
                      {Object.entries(analytics.risk_distribution).map(([level, count]) => {
                        const maxCount = Math.max(...Object.values(analytics.risk_distribution), 1);
                        const pct = (count / maxCount) * 100;
                        const colors = {
                          Low: 'bg-emerald-500',
                          Medium: 'bg-amber-500',
                          High: 'bg-orange-500',
                          Critical: 'bg-red-500'
                        };
                        return (
                          <div key={level} className="flex flex-col items-center w-12 group">
                            <span className="text-xs font-bold text-slate-300 mb-2 opacity-0 group-hover:opacity-100 transition-all font-mono">{count}</span>
                            <div className="w-6 bg-slate-950 rounded-md overflow-hidden flex items-end h-24">
                              <div className={`w-full rounded-md ${colors[level]}`} style={{ height: `${pct}%` }}></div>
                            </div>
                            <span className="text-[10px] text-brand-muted font-bold mt-2">{level}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* SVG Horizontal bars: Top Vendor Performance */}
                  <div className="backdrop-glass rounded-2xl p-5 border border-brand-border">
                    <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider mb-4">Vendor Match Averages</h3>
                    {analytics.vendor_performance.length === 0 ? (
                      <div className="flex h-36 items-center justify-center text-xs text-brand-muted">No vendor records found.</div>
                    ) : (
                      <div className="space-y-3.5 max-h-[160px] overflow-y-auto pr-1">
                        {analytics.vendor_performance.map((item, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-[11px] font-semibold text-slate-300">
                              <span>{item.vendor} ({item.invoice_count} bill)</span>
                              <span className="font-mono text-brand-primary">{Math.round(item.average_match_score)}% Score</span>
                            </div>
                            <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden">
                              <div className="h-full bg-gradient-to-r from-brand-primary to-brand-secondary rounded-full" style={{ width: `${item.average_match_score}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Queue lists grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Pending AP Action queue */}
                  <div className="backdrop-glass rounded-2xl p-6 border border-brand-border">
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 mb-4">
                      <Clock className="h-4.5 w-4.5 text-amber-400" />
                      Pending AP Approval Queue
                    </h3>
                    
                    <div className="overflow-x-auto">
                      {matches.filter(m => m.status === 'pending').length === 0 ? (
                        <div className="text-center py-10 text-xs text-brand-muted">No invoices pending human review.</div>
                      ) : (
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-brand-border/60 text-slate-400 font-semibold uppercase pb-2">
                              <th className="py-2 pr-2">Vendor</th>
                              <th className="py-2 px-2">Invoice No</th>
                              <th className="py-2 px-2 text-center">Confidence</th>
                              <th className="py-2 px-2 text-center">Risk Score</th>
                              <th className="py-2 pl-2 text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-brand-border/30">
                            {matches.filter(m => m.status === 'pending').map(match => {
                              const rInfo = getRiskSeverityColor(match.risk_score);
                              return (
                                <tr key={match.id} className="hover:bg-white/[0.01]">
                                  <td className="py-2.5 pr-2 font-semibold text-slate-300 truncate max-w-[120px]">{match.vendor_name}</td>
                                  <td className="py-2.5 px-2 text-slate-400 font-mono">{match.invoice_number}</td>
                                  <td className="py-2.5 px-2 text-center font-mono font-bold text-brand-primary">{Math.round(match.match_score * 100)}%</td>
                                  <td className="py-2.5 px-2 text-center">
                                    <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded border ${rInfo.bg}`}>{rInfo.label}</span>
                                  </td>
                                  <td className="py-2.5 pl-2 text-right">
                                    <button 
                                      onClick={() => launchApprovalOverlay(match)}
                                      className="px-2.5 py-1 rounded bg-brand-primary/10 border border-brand-primary/20 text-brand-primary font-semibold hover:bg-brand-primary hover:text-white transition-all"
                                    >
                                      Review
                                    </button>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>

                  {/* High Risk AP queue */}
                  <div className="backdrop-glass rounded-2xl p-6 border border-brand-border">
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 mb-4">
                      <ShieldAlert className="h-4.5 w-4.5 text-red-400" />
                      Critical High Risk Queue ({matches.filter(m => m.risk_score >= 61).length})
                    </h3>

                    <div className="overflow-x-auto">
                      {matches.filter(m => m.risk_score >= 61).length === 0 ? (
                        <div className="text-center py-10 text-xs text-brand-muted">No high-risk discrepancies flagged on active matches.</div>
                      ) : (
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-brand-border/60 text-slate-400 font-semibold uppercase pb-2">
                              <th className="py-2 pr-2">Vendor</th>
                              <th className="py-2 px-2">Invoice No</th>
                              <th className="py-2 px-2 text-center">Risk Score</th>
                              <th className="py-2 px-2 text-center">Status</th>
                              <th className="py-2 pl-2 text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-brand-border/30">
                            {matches.filter(m => m.risk_score >= 61).map(match => {
                              const rInfo = getRiskSeverityColor(match.risk_score);
                              return (
                                <tr key={match.id} className="hover:bg-white/[0.01]">
                                  <td className="py-2.5 pr-2 font-bold text-slate-200 truncate max-w-[120px]">{match.vendor_name}</td>
                                  <td className="py-2.5 px-2 text-slate-400 font-mono">{match.invoice_number}</td>
                                  <td className="py-2.5 px-2 text-center">
                                    <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border ${rInfo.bg}`}>{Math.round(match.risk_score)} ({rInfo.label})</span>
                                  </td>
                                  <td className="py-2.5 px-2 text-center text-slate-300 uppercase font-semibold text-[10px]">{match.status}</td>
                                  <td className="py-2.5 pl-2 text-right">
                                    <button 
                                      onClick={() => launchApprovalOverlay(match)}
                                      className="px-2.5 py-1 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-semibold hover:bg-red-500 hover:text-white transition-all"
                                    >
                                      Inspect
                                    </button>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                </div>

                {/* Business Audit Reports Exporter block (Phase 11) */}
                <div className="backdrop-glass rounded-2xl p-6 border border-brand-border text-left space-y-4">
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <FileSpreadsheet className="h-4.5 w-4.5 text-brand-primary" />
                    Business Audit Reports Exporter (CSV & HTML-PDF)
                  </h3>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
                    {/* Monthly */}
                    <div className="rounded-xl border border-brand-border bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-bold text-slate-200">Monthly Uploads</p>
                        <p className="text-[10px] text-brand-muted mt-1 leading-normal">Monthly volumes, match statistics, and total values.</p>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleExportReport('monthly', 'csv')}
                          className="flex-1 py-1 px-2 rounded bg-brand-primary/10 border border-brand-primary/20 text-brand-primary font-semibold text-[10px] hover:bg-brand-primary hover:text-white transition-all text-center"
                        >
                          CSV
                        </button>
                        <button 
                          onClick={() => handleExportReport('monthly', 'html')}
                          className="flex-1 py-1 px-2 rounded bg-brand-secondary/10 border border-brand-secondary/20 text-brand-secondary font-semibold text-[10px] hover:bg-brand-secondary hover:text-white transition-all text-center"
                        >
                          HTML
                        </button>
                      </div>
                    </div>

                    {/* Vendor */}
                    <div className="rounded-xl border border-brand-border bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-bold text-slate-200">Vendor performance</p>
                        <p className="text-[10px] text-brand-muted mt-1 leading-normal">Aggregated match scores, risk, and billing amounts by vendor.</p>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleExportReport('vendor', 'csv')}
                          className="flex-1 py-1 px-2 rounded bg-brand-primary/10 border border-brand-primary/20 text-brand-primary font-semibold text-[10px] hover:bg-brand-primary hover:text-white transition-all text-center"
                        >
                          CSV
                        </button>
                        <button 
                          onClick={() => handleExportReport('vendor', 'html')}
                          className="flex-1 py-1 px-2 rounded bg-brand-secondary/10 border border-brand-secondary/20 text-brand-secondary font-semibold text-[10px] hover:bg-brand-secondary hover:text-white transition-all text-center"
                        >
                          HTML
                        </button>
                      </div>
                    </div>

                    {/* Anomaly */}
                    <div className="rounded-xl border border-brand-border bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-bold text-red-400">Anomaly warnings</p>
                        <p className="text-[10px] text-brand-muted mt-1 leading-normal">Suspicious invoices list, active flags, severity, and SHAP logs.</p>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleExportReport('anomaly', 'csv')}
                          className="flex-1 py-1 px-2 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-semibold text-[10px] hover:bg-red-500 hover:text-white transition-all text-center"
                        >
                          CSV
                        </button>
                        <button 
                          onClick={() => handleExportReport('anomaly', 'html')}
                          className="flex-1 py-1 px-2 rounded bg-brand-secondary/10 border border-brand-secondary/20 text-brand-secondary font-semibold text-[10px] hover:bg-brand-secondary hover:text-white transition-all text-center"
                        >
                          HTML
                        </button>
                      </div>
                    </div>

                    {/* Audit */}
                    <div className="rounded-xl border border-brand-border bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-bold text-slate-200">Audit trail logs</p>
                        <p className="text-[10px] text-brand-muted mt-1 leading-normal">System operations timeline, login entries, and download records.</p>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleExportReport('audit', 'csv')}
                          className="flex-1 py-1 px-2 rounded bg-brand-primary/10 border border-brand-primary/20 text-brand-primary font-semibold text-[10px] hover:bg-brand-primary hover:text-white transition-all text-center"
                        >
                          CSV
                        </button>
                        <button 
                          onClick={() => handleExportReport('audit', 'html')}
                          className="flex-1 py-1 px-2 rounded bg-brand-secondary/10 border border-brand-secondary/20 text-brand-secondary font-semibold text-[10px] hover:bg-brand-secondary hover:text-white transition-all text-center"
                        >
                          HTML
                        </button>
                      </div>
                    </div>

                    {/* Finance */}
                    <div className="rounded-xl border border-brand-border bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-bold text-slate-200">Finance summary</p>
                        <p className="text-[10px] text-brand-muted mt-1 leading-normal">Balance sheets of totals approved, pending matching, and high risk.</p>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleExportReport('finance', 'csv')}
                          className="flex-1 py-1 px-2 rounded bg-brand-primary/10 border border-brand-primary/20 text-brand-primary font-semibold text-[10px] hover:bg-brand-primary hover:text-white transition-all text-center"
                        >
                          CSV
                        </button>
                        <button 
                          onClick={() => handleExportReport('finance', 'html')}
                          className="flex-1 py-1 px-2 rounded bg-brand-secondary/10 border border-brand-secondary/20 text-brand-secondary font-semibold text-[10px] hover:bg-brand-secondary hover:text-white transition-all text-center"
                        >
                          HTML
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Timeline: AP Audit logs trail */}
                <div className="backdrop-glass rounded-2xl p-6 border border-brand-border">
                  <h3 className="text-sm font-bold text-slate-100 flex items-center justify-between mb-4">
                    <span className="flex items-center gap-2">
                      <ListFilter className="h-4.5 w-4.5 text-brand-secondary" />
                      AP Transactions Audit logs trail
                    </span>
                    <button 
                      onClick={fetchAuditLogs}
                      disabled={loadingAudits}
                      className="p-1 rounded bg-slate-900 border border-brand-border text-xs text-brand-muted hover:text-slate-200"
                    >
                      Refresh
                    </button>
                  </h3>
                  
                  {loadingAudits ? (
                    <div className="flex py-10 justify-center">
                      <LoaderIcon className="animate-spin h-6 w-6 text-brand-secondary" />
                    </div>
                  ) : auditLogs.length === 0 ? (
                    <div className="text-center py-6 text-xs text-brand-muted">No audit actions recorded in history.</div>
                  ) : (
                    <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                      {auditLogs.map((log) => (
                        <div key={log.id} className="flex gap-4 border-l-2 border-brand-border/40 pl-4 py-1 relative">
                          <div className="absolute -left-[5.5px] top-2.5 h-2.5 w-2.5 rounded-full bg-brand-secondary"></div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between text-xs font-semibold">
                              <span className="text-slate-200">{log.action}</span>
                              <span className="font-mono text-brand-muted text-[10px]">{new Date(log.created_at).toLocaleString()}</span>
                            </div>
                            <p className="text-xs text-slate-400 mt-1">{log.details}</p>
                            <p className="text-[10px] text-brand-muted mt-0.5">Executor: {log.username}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab 2: Documents & Uploads */}
        {activeWorkspaceTab === 'documents' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left panel: File Uploader */}
            <div className="lg:col-span-1 space-y-6">
              <div className="backdrop-glass rounded-3xl p-6 border border-brand-border shadow-glass">
                <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <UploadCloud className="h-5 w-5 text-brand-primary" />
                  Upload & Parse Document
                </h2>

                {/* Tabs */}
                <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-950 p-1.5 mb-6 border border-white/5">
                  <button
                    onClick={() => { setActiveTab('invoice'); setSelectedFile(null); setUploadStatus(null); }}
                    className={`py-2 px-3 text-sm font-semibold rounded-lg transition-all ${
                      activeTab === 'invoice' 
                        ? 'bg-brand-primary text-white shadow-glow-primary' 
                        : 'text-brand-muted hover:text-slate-200'
                    }`}
                  >
                    Invoice
                  </button>
                  <button
                    onClick={() => { setActiveTab('po'); setSelectedFile(null); setUploadStatus(null); }}
                    className={`py-2 px-3 text-sm font-semibold rounded-lg transition-all ${
                      activeTab === 'po' 
                        ? 'bg-brand-primary text-white shadow-glow-primary' 
                        : 'text-brand-muted hover:text-slate-200'
                    }`}
                  >
                    Purchase Order
                  </button>
                </div>

                {/* File Dropzone */}
                <div
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current.click()}
                  className={`relative flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-6 cursor-pointer transition-all duration-200 ${
                    dragActive 
                      ? 'border-brand-primary bg-brand-primary/5 shadow-glow-primary' 
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileChange}
                    accept=".pdf,.csv"
                    className="hidden"
                  />

                  <UploadCloud className={`h-12 w-12 text-slate-500 mb-4 transition-transform ${dragActive ? 'scale-110 text-brand-primary' : ''}`} />
                  
                  <p className="text-sm font-semibold text-slate-300 text-center">
                    Drag & drop file here, or <span className="text-brand-primary hover:underline">browse</span>
                  </p>
                  <p className="text-xs text-brand-muted mt-2 text-center">
                    Supports PDF or CSV formats (Max 10MB)
                  </p>
                </div>

                {/* Selected File Details */}
                {selectedFile && (
                  <div className="mt-5 rounded-2xl bg-slate-900/80 border border-brand-border p-4 animate-fade-in">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-200 truncate">{selectedFile.name}</p>
                        <p className="text-xs text-brand-muted">{formatBytes(selectedFile.size)}</p>
                      </div>
                      <button 
                        onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                        className="p-1.5 text-slate-500 hover:text-red-400 rounded-lg hover:bg-white/5 transition-all"
                      >
                        <Trash2 className="h-4.5 w-4.5" />
                      </button>
                    </div>

                    {uploading ? (
                      <div className="mt-4 space-y-2">
                        <div className="flex justify-between text-xs font-semibold text-brand-muted">
                          <span>Uploading & Parsing...</span>
                          <span>{uploadProgress}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-brand-primary to-brand-secondary rounded-full transition-all duration-150"
                            style={{ width: `${uploadProgress}%` }}
                          ></div>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={handleUploadSubmit}
                        className="mt-4 w-full py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primary/95 text-white font-semibold shadow-glow-primary active:scale-[0.98] transition-all duration-150"
                      >
                        Upload & Run Parser
                      </button>
                    )}
                  </div>
                )}

                {/* Upload Result Status Panels */}
                {uploadStatus && (
                  <div className="mt-5 animate-fade-in">
                    {uploadStatus.type === 'success' && (
                      <div className="flex items-start gap-3 rounded-2xl bg-emerald-950/30 border border-emerald-500/20 p-4 text-emerald-400">
                        <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
                        <div className="text-xs font-medium">
                          <p className="font-bold">Structured Data Extracted</p>
                          <p className="mt-1 leading-relaxed">{uploadStatus.message}</p>
                        </div>
                      </div>
                    )}

                    {uploadStatus.type === 'duplicate' && (
                      <div className="flex items-start gap-3 rounded-2xl bg-amber-950/30 border border-amber-500/20 p-4 text-amber-400">
                        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                        <div className="text-xs font-medium">
                          <p className="font-bold">Duplicate Blocked</p>
                          <p className="mt-1 leading-relaxed">{uploadStatus.message}</p>
                        </div>
                      </div>
                    )}

                    {uploadStatus.type === 'error' && (
                      <div className="flex items-start gap-3 rounded-2xl bg-red-950/30 border border-red-500/20 p-4 text-red-400">
                        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                        <div className="text-xs font-medium">
                          <p className="font-bold">Upload Denied</p>
                          <p className="mt-1 leading-relaxed">{uploadStatus.message}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Right panel: Recent Uploads Log */}
            <div className="lg:col-span-2 space-y-8">
              <div className="backdrop-glass rounded-3xl p-6 border border-brand-border shadow-glass flex flex-col">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-bold text-slate-100">Upload History Log</h2>
                    <p className="text-xs text-brand-muted mt-0.5">Click any document row to view parsed lines, mismatch flags, and candidate comparisons</p>
                  </div>
                  
                  <button 
                    onClick={fetchRecentUploads}
                    disabled={loadingRecent}
                    className="p-2 rounded-xl bg-slate-900 border border-brand-border text-brand-muted hover:text-white transition-all disabled:opacity-50"
                  >
                    <RefreshCw className={`h-4 w-4 ${loadingRecent ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                {/* Log Table Container */}
                <div className="overflow-x-auto">
                  {loadingRecent ? (
                    <div className="flex h-48 items-center justify-center">
                      <LoaderIcon className="animate-spin h-8 w-8 text-brand-primary" />
                    </div>
                  ) : recentUploads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-48 rounded-2xl border border-dashed border-slate-800 bg-slate-900/10">
                      <FileText className="h-10 w-10 text-slate-600 mb-3" />
                      <p className="text-sm font-semibold text-slate-400">No uploads recorded</p>
                      <p className="text-xs text-slate-600 mt-1">Upload an invoice or PO to begin</p>
                    </div>
                  ) : (
                    <table className="w-full min-w-[600px] border-collapse text-left text-sm text-slate-300">
                      <thead>
                        <tr className="border-b border-brand-border/60 text-slate-400 font-semibold pb-3 text-xs uppercase tracking-wider font-sans">
                          <th className="pb-3 pr-4 font-semibold">Type</th>
                          <th className="pb-3 px-4 font-semibold">Document Details</th>
                          <th className="pb-3 px-4 font-semibold">Extracted Metadata</th>
                          <th className="pb-3 px-4 font-semibold text-right">Amount</th>
                          <th className="pb-3 pl-4 font-semibold text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-brand-border/40">
                        {recentUploads.map((doc) => (
                          <tr 
                            key={doc.id} 
                            className={`group transition-colors cursor-pointer ${
                              selectedDoc?.id === doc.id 
                                ? 'bg-brand-primary/10 border-l-2 border-brand-primary' 
                                : 'hover:bg-white/[0.02]'
                            }`}
                            onClick={() => setSelectedDoc(doc)}
                          >
                            <td className="py-3.5 pr-4 whitespace-nowrap pl-2">
                              <span className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold ${
                                doc.document_type === 'invoice'
                                  ? 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-400'
                                  : 'bg-violet-500/10 border border-violet-500/20 text-violet-400'
                              }`}>
                                {doc.document_type === 'invoice' ? 'Invoice' : 'PO'}
                              </span>
                            </td>

                            <td className="py-3.5 px-4 max-w-[200px]">
                              <div className="font-semibold text-slate-200 truncate group-hover:text-brand-primary transition-colors">
                                {doc.file_name}
                              </div>
                              <div className="flex items-center gap-2 mt-1 text-[11px] text-brand-muted">
                                <span className="font-mono">{doc.id}</span>
                                <span>•</span>
                                <span>{formatBytes(doc.file_size)}</span>
                              </div>
                            </td>

                            <td className="py-3.5 px-4 whitespace-nowrap">
                              <div className="text-slate-300 font-medium">
                                {doc.doc_number || 'Extracting...'}
                              </div>
                              <div className="text-[11px] text-brand-muted mt-0.5">
                                {doc.vendor_name || 'Vendor: pending'}
                              </div>
                            </td>

                            <td className="py-3.5 px-4 text-right whitespace-nowrap font-mono font-semibold text-slate-200">
                              {doc.total_amount ? `$${doc.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}` : '—'}
                            </td>

                            <td className="py-3.5 pl-4 text-right whitespace-nowrap pr-2">
                              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                doc.status === 'approved' || doc.status === 'matched'
                                  ? 'bg-emerald-500/10 text-emerald-400'
                                  : doc.status === 'anomaly'
                                  ? 'bg-red-500/10 text-red-400'
                                  : 'bg-amber-500/10 text-amber-400'
                              }`}>
                                <span className="h-1.5 w-1.5 rounded-full bg-current"></span>
                                {doc.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Detail view splitter */}
              {selectedDoc && (
                <div className="backdrop-glass rounded-3xl p-6 border border-brand-border shadow-glass animate-slide-up space-y-6">
                  
                  {/* Header details */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-brand-border/60 pb-5 gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-brand-primary px-2 py-0.5 rounded bg-brand-primary/10 border border-brand-primary/20">
                          {selectedDoc.document_type}
                        </span>
                        <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${
                          selectedDoc.status === 'approved' || selectedDoc.status === 'matched'
                            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                            : selectedDoc.status === 'anomaly'
                            ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                            : 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
                        }`}>
                          {selectedDoc.status}
                        </span>
                      </div>
                      <h3 className="text-xl font-bold text-white mt-2 flex items-center gap-2">
                        <FileText className="h-5.5 w-5.5 text-brand-primary" />
                        {selectedDoc.file_name}
                      </h3>
                      <p className="text-xs text-brand-muted mt-1">Vendor: <span className="text-slate-300 font-semibold">{selectedDoc.vendor_name}</span></p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 max-w-full">
                      {(selectedDoc.document_type === 'invoice' || selectedDoc.document_type === 'po') && selectedDoc.status === 'processed' && (
                        <button
                          onClick={() => handleReconcile(selectedDoc.id)}
                          disabled={reconciling}
                          className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-white rounded-xl bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-primary/90 hover:to-brand-secondary/90 shadow-glow-primary active:scale-[0.98] transition-all disabled:opacity-50"
                        >
                          <Sparkles className={`h-4 w-4 ${reconciling ? 'animate-spin' : ''}`} />
                          {reconciling ? 'Running AI Engine...' : 'Run Auto Match Engine'}
                        </button>
                      )}

                      {/* Download document action */}
                      <button
                        onClick={() => handleDownload(selectedDoc.id, selectedDoc.file_name)}
                        className="flex items-center gap-1.5 px-3 py-2 text-xs rounded-xl bg-slate-900 border border-brand-border text-slate-300 hover:text-white transition-all"
                      >
                        <Download className="h-4 w-4" />
                        Download
                      </button>

                      {/* Display compare candidate selectors */}
                      <div className="text-left max-w-full">
                        <select 
                          className="bg-slate-900 border border-brand-border text-xs rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:ring-1 focus:ring-brand-primary w-full sm:w-auto max-w-[260px] md:max-w-[320px] truncate"
                          value={candidateDoc?.id || ''}
                          onChange={(e) => {
                            const doc = candidateFiles.find(c => c.id === e.target.value);
                            setCandidateDoc(doc || null);
                          }}
                        >
                          <option value="">-- Choose Candidate --</option>
                          {candidateFiles.map(c => (
                            <option key={c.id} value={c.id}>
                              {c.document_type.toUpperCase()}: {c.doc_number} ({c.vendor_name})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Discrepancy Alerts (Flags list) with XAI explanations */}
                  {docFlags.length > 0 && (
                    <div className="rounded-2xl border border-red-500/20 bg-red-950/20 p-4 space-y-3 animate-fade-in">
                      <div className="flex items-center gap-2 text-xs font-bold text-red-400">
                        <ShieldAlert className="h-4 w-4" />
                        <span>Suspicious Anomaly Alerts Detected ({docFlags.length})</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {docFlags.map((flag) => (
                          <div key={flag.id} className="rounded-xl border border-red-500/10 bg-slate-950/40 p-3 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] uppercase font-extrabold text-red-400 tracking-wider flex items-center gap-1">
                                <Flame className="h-3.5 w-3.5 text-red-400" />
                                {flag.flag_type.replace("_", " ")}
                              </span>
                              <span className={`text-[9px] font-extrabold uppercase px-1.5 rounded ${
                                flag.severity === 'high' || flag.severity === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                              }`}>{flag.severity}</span>
                            </div>
                            <p className="text-xs font-semibold text-slate-200 mt-1">{flag.description}</p>
                            <div className="rounded-lg bg-slate-900/60 p-2 mt-2 border border-white/5">
                              <p className="text-[10px] text-brand-primary font-bold uppercase tracking-wider">AI Explanation (Perturbation SHAP)</p>
                              <p className="text-[10px] text-slate-300 mt-1 leading-normal italic">{flag.explained_by_ai}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Compare view split */}
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h4 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                        <Database className="h-4.5 w-4.5 text-brand-primary" />
                        Structured Data Rows ({docLines.length})
                      </h4>
                      {loadingLines ? (
                        <div className="flex justify-center py-10">
                          <LoaderIcon className="animate-spin h-6 w-6 text-brand-primary" />
                        </div>
                      ) : (
                        <div className="overflow-x-auto rounded-2xl border border-brand-border bg-slate-900/30 max-h-[300px]">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="border-b border-brand-border bg-slate-900/60 text-slate-400 font-semibold uppercase">
                                <th className="py-2.5 px-3">#</th>
                                <th className="py-2.5 px-3">SKU</th>
                                <th className="py-2.5 px-3">Description</th>
                                <th className="py-2.5 px-3 text-right">Qty</th>
                                <th className="py-2.5 px-3 text-right">Unit Price</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-brand-border/40 font-mono">
                              {docLines.map(line => (
                                <tr key={line.id} className="hover:bg-white/[0.01]">
                                  <td className="py-2.5 px-3 font-semibold text-brand-muted">{line.line_number}</td>
                                  <td className="py-2.5 px-3 font-bold text-slate-200">{line.sku}</td>
                                  <td className="py-2.5 px-3 text-slate-400 font-sans truncate max-w-[120px]">{line.description}</td>
                                  <td className="py-2.5 px-3 text-right text-slate-200">{line.quantity}</td>
                                  <td className="py-2.5 px-3 text-right text-brand-primary">${line.unit_price.toFixed(2)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>

                    <div className="space-y-4">
                      <h4 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                        <Scale className="h-4.5 w-4.5 text-brand-secondary" />
                        Feature Engineering & SHAP Values
                      </h4>
                      {!candidateDoc ? (
                        <div className="flex flex-col items-center justify-center py-12 rounded-2xl border border-dashed border-slate-800 bg-slate-900/10 text-center">
                          <Sparkles className="h-8 w-8 text-brand-muted mb-2 animate-pulse" />
                          <p className="text-xs font-semibold text-slate-400">Select a comparison candidate</p>
                        </div>
                      ) : loadingSimilarities ? (
                        <div className="flex justify-center py-12">
                          <LoaderIcon className="animate-spin h-6 w-6 text-brand-secondary" />
                        </div>
                      ) : (
                        <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                          {similarities.map((item, idx) => (
                            <div key={idx} className="rounded-xl border border-brand-border bg-slate-900/40 p-3.5 space-y-3 hover:border-brand-primary/20 transition-all">
                              <div className="flex items-center justify-between border-b border-brand-border/40 pb-2 text-[11px]">
                                <span className="font-bold text-slate-200">Line {item.invoice_line_number} vs Line {item.po_line_number}</span>
                                <span className="font-mono text-brand-muted text-[10px]">Date Diff: {item.vector.date_difference_days} days</span>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-brand-muted">SKU match</span>
                                  <span className="font-mono font-semibold text-slate-200">{Math.round(item.vector.sku_similarity * 100)}%</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-brand-muted">Desc sim</span>
                                  <span className="font-mono font-semibold text-slate-200">{Math.round(item.vector.description_similarity * 100)}%</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: AI Matches lists table */}
        {activeWorkspaceTab === 'reconciler' && (
          <div className="backdrop-glass rounded-3xl p-6 border border-brand-border shadow-glass flex flex-col space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-brand-secondary animate-pulse" />
                AI Auto-Reconciliation Matches
              </h2>
              <p className="text-xs text-brand-muted mt-0.5">Click any matches to access comment annotations and transaction reviews.</p>
            </div>

            {loadingMatches ? (
              <div className="flex h-48 items-center justify-center">
                <LoaderIcon className="animate-spin h-8 w-8 text-brand-primary" />
              </div>
            ) : getReconcilerRows().length === 0 ? (
              <div className="text-center py-12 text-sm text-brand-muted">No matches or uploaded documents found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] border-collapse text-left text-sm text-slate-300">
                  <thead>
                    <tr className="border-b border-brand-border/60 text-slate-400 font-semibold pb-3 text-xs uppercase tracking-wider font-sans">
                      <th className="pb-3 pr-4">Vendor</th>
                      <th className="pb-3 px-4">Invoice details</th>
                      <th className="pb-3 px-4">Purchase Order</th>
                      <th className="pb-3 px-4 text-center">Confidence</th>
                      <th className="pb-3 px-4 text-center">Risk Score</th>
                      <th className="pb-3 px-4 text-center">Flags</th>
                      <th className="pb-3 px-4 text-center">Status</th>
                      <th className="pb-3 pl-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-border/40 font-sans">
                    {getReconcilerRows().map((row) => {
                      const isMatch = row.type === 'match';
                      const riskInfo = isMatch ? getRiskSeverityColor(row.risk_score) : null;
                      return (
                        <tr key={row.id} className="hover:bg-white/[0.02] transition-all">
                          <td className="py-3.5 pr-4 font-bold text-slate-100 whitespace-nowrap">{row.vendor_name}</td>
                          
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            {row.invoice_file_name === '—' ? (
                              <span className="text-slate-600 font-mono italic">Not Matched</span>
                            ) : (
                              <>
                                <div className="font-semibold text-slate-200">{row.invoice_file_name}</div>
                                <div className="text-[11px] text-brand-muted mt-0.5">No: {row.invoice_number} • ${row.invoice_amount.toFixed(2)}</div>
                              </>
                            )}
                          </td>
                          
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            {row.po_file_name === '—' ? (
                              <span className="text-slate-600 font-mono italic">Not Matched</span>
                            ) : (
                              <>
                                <div className="font-semibold text-slate-200">{row.po_file_name}</div>
                                <div className="text-[11px] text-brand-muted mt-0.5">No: {row.po_number} • ${row.po_amount.toFixed(2)}</div>
                              </>
                            )}
                          </td>
                          
                          <td className="py-3.5 px-4 text-center whitespace-nowrap font-mono font-bold text-brand-primary">
                            {isMatch ? `${Math.round(row.confidence)}%` : '—'}
                          </td>
                          
                          <td className="py-3.5 px-4 text-center whitespace-nowrap font-mono">
                            {isMatch ? (
                              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-xs font-bold ${riskInfo.bg}`}>
                                {Math.round(row.risk_score)} ({riskInfo.label})
                              </span>
                            ) : row.status === 'anomaly' ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-xs font-bold bg-red-500/10 border-red-500/20 text-red-400">
                                70 (High)
                              </span>
                            ) : (
                              <span className="text-slate-600 font-mono">—</span>
                            )}
                          </td>
                          
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            {isMatch ? (
                              row.flags_count > 0 ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-red-500/10 text-red-400 font-semibold border border-red-500/20">
                                  <ShieldAlert className="h-3 w-3" /> {row.flags_count} flags
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-brand-accent font-semibold border border-emerald-500/20">
                                  <Check className="h-3 w-3" /> Clean
                                </span>
                              )
                            ) : row.status === 'anomaly' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-red-500/10 text-red-400 font-semibold border border-red-500/20">
                                <ShieldAlert className="h-3 w-3" /> 1 flag
                              </span>
                            ) : (
                              <span className="text-slate-600 font-mono">—</span>
                            )}
                          </td>
                          
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              row.status === 'approved' || row.status === 'matched'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : row.status === 'rejected' || row.status === 'anomaly'
                                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                : row.status === 'needs_review'
                                ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            }`}>
                              <span className="h-1.5 w-1.5 rounded-full bg-current"></span>
                              {row.status.replace("_", " ")}
                            </span>
                          </td>
                          
                          <td className="py-3.5 pl-4 text-right whitespace-nowrap pr-2">
                            {isMatch ? (
                              <button
                                onClick={() => launchApprovalOverlay(row.originalMatch)}
                                className="px-3 py-1.5 rounded-xl bg-slate-900 border border-brand-border text-xs text-slate-200 hover:text-white font-semibold hover:border-brand-primary/40 transition-all"
                              >
                                Open Workspace
                              </button>
                            ) : row.status === 'processed' ? (
                              <button
                                onClick={() => handleReconcile(row.docId, row.document_type)}
                                disabled={reconciling}
                                className="px-3 py-1.5 rounded-xl bg-brand-primary/10 border border-brand-primary/20 text-xs text-brand-primary hover:bg-brand-primary hover:text-white font-semibold transition-all flex items-center gap-1 inline-flex"
                              >
                                <Sparkles className={`h-3.5 w-3.5 ${reconciling ? 'animate-spin' : ''}`} />
                                Match
                              </button>
                            ) : (
                              <span className="text-slate-600 font-mono pr-4">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {/* AP Approval Workflow Overlay Workspace Modal (Phase 10) */}
      {showApprovalOverlay && activeApprovalMatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-3xl border border-brand-border bg-[#0B0F19] p-6 shadow-2xl relative space-y-6">
            
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-brand-border/60 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-brand-primary uppercase px-2 py-0.5 rounded bg-brand-primary/10 border border-brand-primary/20">
                    Match Proposal ID: {activeApprovalMatch.id}
                  </span>
                  <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                    activeApprovalMatch.status === 'approved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {activeApprovalMatch.status}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white mt-2 flex items-center gap-2">
                  <MessageSquare className="h-5.5 w-5.5 text-brand-primary" />
                  AP Review & Decision Workspace
                </h2>
                <p className="text-xs text-brand-muted mt-0.5">Vendor: <span className="text-slate-200 font-semibold">{activeApprovalMatch.vendor_name}</span></p>
              </div>
              
              <button 
                onClick={() => setShowApprovalOverlay(false)}
                className="p-1.5 text-slate-500 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Document comparisons block */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-brand-border p-4 bg-slate-900/40 text-left">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-indigo-400">INVOICE FILE</span>
                  <button 
                    onClick={() => handleDownload(activeApprovalMatch.invoice_id, activeApprovalMatch.invoice_file_name)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                    title="Download original file"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </div>
                <p className="text-sm font-semibold text-slate-200 truncate">{activeApprovalMatch.invoice_file_name}</p>
                <p className="text-[11px] text-brand-muted mt-1">Invoice No: {activeApprovalMatch.invoice_number} • Total Billed: <span className="text-white font-semibold">${activeApprovalMatch.invoice_amount.toFixed(2)}</span></p>
              </div>

              <div className="rounded-xl border border-brand-border p-4 bg-slate-900/40 text-left">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-violet-400">PURCHASE ORDER</span>
                  <button 
                    onClick={() => handleDownload(activeApprovalMatch.po_id, activeApprovalMatch.po_file_name)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                    title="Download original file"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </div>
                <p className="text-sm font-semibold text-slate-200 truncate">{activeApprovalMatch.po_file_name}</p>
                <p className="text-[11px] text-brand-muted mt-1">PO No: {activeApprovalMatch.po_number} • PO Allocations: <span className="text-white font-semibold">${activeApprovalMatch.po_amount.toFixed(2)}</span></p>
              </div>
            </div>

            {/* Flag discrepancy detail log */}
            {docFlags.length > 0 && (
              <div className="rounded-2xl border border-red-500/20 bg-red-950/20 p-4 space-y-2">
                <div className="text-xs font-bold text-red-400 flex items-center gap-1.5">
                  <ShieldAlert className="h-4 w-4" />
                  <span>Unresolved Discrepancies ({docFlags.length})</span>
                </div>
                {docFlags.map(flag => (
                  <div key={flag.id} className="text-xs bg-slate-950/40 p-2.5 rounded-lg border border-red-500/10">
                    <p className="font-semibold text-slate-200">{flag.description}</p>
                    <p className="text-[10px] text-brand-muted mt-0.5 italic">SHAP explanation: {flag.explained_by_ai}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Feature Importance charts */}
            {similarities.length > 0 && similarities[0].shap_importances && (
              <div className="rounded-2xl border border-brand-border p-4 bg-slate-900/30">
                <h4 className="text-xs font-bold text-brand-secondary uppercase tracking-wider flex items-center gap-1 mb-3">
                  <Sparkles className="h-4 w-4" />
                  SHAP Explainability Feature Contributions
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(similarities[0].shap_importances)
                    .filter(([_, val]) => val > 1.0)
                    .map(([feat, val]) => (
                      <div key={feat} className="space-y-1 text-left">
                        <div className="flex justify-between text-[10px] text-slate-300">
                          <span>{getFeatureLabel(feat)}</span>
                          <span className="font-mono text-brand-secondary">+{Math.round(val)}% risk</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-brand-secondary to-pink-500" style={{ width: `${val}%` }}></div>
                        </div>
                      </div>
                    ))
                  }
                </div>
              </div>
            )}

            {/* Comment Section & AP Action buttons */}
            <div className="space-y-3.5 text-left border-t border-brand-border/40 pt-5">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">AP Annotations & Comments</label>
              <textarea
                value={approvalComment}
                onChange={(e) => setApprovalComment(e.target.value)}
                placeholder="Submit comments, notes, or audit review explanations..."
                className="w-full h-20 bg-slate-950 border border-brand-border text-sm text-slate-200 rounded-2xl p-3 focus:outline-none focus:ring-1 focus:ring-brand-primary placeholder:text-slate-600"
              />

              <div className="flex flex-wrap gap-3 pt-2">
                <button
                  onClick={() => submitApprovalDecision(activeApprovalMatch.id, 'approve')}
                  disabled={submittingAction}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-sm active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  <Check className="h-4 w-4" />
                  Approve Payment
                </button>
                <button
                  onClick={() => submitApprovalDecision(activeApprovalMatch.id, 'reject')}
                  disabled={submittingAction}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold shadow-sm active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  <X className="h-4 w-4" />
                  Reject Match
                </button>
                <button
                  onClick={() => submitApprovalDecision(activeApprovalMatch.id, 'needs-review')}
                  disabled={submittingAction || !approvalComment}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold shadow-sm active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  title={!approvalComment ? "Leave a comment to flag for review" : ""}
                >
                  <AlertTriangle className="h-4 w-4" />
                  Flag Needs Review
                </button>
                <button
                  onClick={() => setShowApprovalOverlay(false)}
                  className="px-5 py-2.5 rounded-xl bg-slate-900 border border-brand-border text-slate-300 hover:text-white transition-all ml-auto"
                >
                  Cancel
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

// Simple custom loader icon wrapper
const LoaderIcon = ({ className }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

export default Dashboard;
