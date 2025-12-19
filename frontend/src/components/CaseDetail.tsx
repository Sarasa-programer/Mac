import { useState, useEffect } from 'react';
import type { MedicalCase, PubMedArticle } from '../types';
import { findPubMedArticles, deleteCase, expandPubMedQuery } from '../services/apiService';
import { SmartQueryInput } from './SmartQueryInput';
import { FileText, Activity, BookOpen, Search, Calendar, User, Trash2, ArrowLeft, Stethoscope, Sparkles, Copy, Check } from 'lucide-react';
import clsx from 'clsx';

interface CaseDetailProps {
  data: MedicalCase;
  onBack: () => void;
  onDelete?: () => void;
  userRole?: string;
}

type Tab = 'summary' | 'transcript' | 'differential' | 'research';

export function CaseDetail({ data, onBack, onDelete }: CaseDetailProps) {
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [articles, setArticles] = useState<PubMedArticle[]>([]);
  const [bmjContent, setBmjContent] = useState<string>('');
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [pubmedError, setPubmedError] = useState<any>(null);

  // Query Expansion State
  const [queryInput, setQueryInput] = useState('');
  const [expandedQuery, setExpandedQuery] = useState('');
  const [isExpanding, setIsExpanding] = useState(false);
  const [expansionError, setExpansionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleExpandQuery = async () => {
    if (!queryInput.trim()) return;
    setIsExpanding(true);
    setExpansionError(null);
    try {
        const result = await expandPubMedQuery(queryInput);
        setExpandedQuery(result);
    } catch (err: any) {
        setExpansionError(err.message);
    } finally {
        setIsExpanding(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(expandedQuery);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this case? This action cannot be undone.")) {
        try {
            await deleteCase(data.id);
            if (onDelete) onDelete();
            else onBack(); 
        } catch (err: any) {
            alert(err.message);
        }
    }
  };

  // Helper to normalize summary data
  const getSummary = () => {
    if (!data.summary) return { chiefComplaint: '', history: '', vitals: '' };
    
    // Handle both camelCase (Frontend constructed) and snake_case (Backend API)
    // @ts-ignore - Dynamic access for snake_case properties
    const cc = data.summary.chiefComplaint || data.summary.chief_complaint || '';
    // @ts-ignore
    const hpi = data.summary.history || ''; // history is same in both
    // @ts-ignore
    const vitals = data.summary.vitals || ''; // vitals is same in both
    
    return { chiefComplaint: cc, history: hpi, vitals: vitals };
  };

  const summaryData = getSummary();

  // Helper to normalize Differential Diagnosis
  interface DiffDx {
    condition: string;
    probability?: string;
    reasoning?: string;
  }

  const getDifferential = (): DiffDx[] => {
    if (data.differential_diagnoses && data.differential_diagnoses.length > 0) {
      return data.differential_diagnoses;
    }
    if (data.differentialDiagnosis && data.differentialDiagnosis.length > 0) {
      return data.differentialDiagnosis.map(d => ({ condition: d }));
    }
    return [];
  };

  const differentials = getDifferential();
  const nelsonText = data.nelsonContext || data.nelson_context || '';

  useEffect(() => {
    // If we have pre-loaded articles from backend, use them
    if (data.pubmed_articles && data.pubmed_articles.length > 0 && articles.length === 0) {
      setArticles(data.pubmed_articles.map(a => ({
        title: a.title,
        url: a.url,
        snippet: a.snippet || a.summary || ''
      })));
      return;
    }

    if (activeTab === 'research' && articles.length === 0 && !bmjContent) {
      // Use summary context if available, otherwise keywords
      const context = summaryData.history ? 
          `Chief Complaint: ${summaryData.chiefComplaint}\nHistory: ${summaryData.history}\nVitals: ${summaryData.vitals}` : 
          (data.keywords || []).join(' ');

      if (context) {
          setLoadingArticles(true);
          setPubmedError(null);
          findPubMedArticles([context])
            .then(result => {
                if (result.error_details) {
                    setPubmedError(result.error_details);
                    // Show toast notification
                    const notification = document.createElement('div');
                    notification.className = 'fixed bottom-4 right-4 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded shadow-lg animate-in slide-in-from-right z-50';
                    notification.innerHTML = `
                        <p class="font-bold">Evidence Unavailable</p>
                        <p>Proceeding with clinical analysis without external data.</p>
                    `;
                    document.body.appendChild(notification);
                    setTimeout(() => notification.remove(), 5000);
                }
                
                if (result.bmj_topics_markdown) {
                    setBmjContent(result.bmj_topics_markdown);
                } else {
                    setArticles(result.results || []);
                }
            })
            .catch((err) => {
                setPubmedError({
                    code: "API_ERROR",
                    message: "Failed to connect to evidence service",
                    timestamp: new Date().toISOString(),
                    context: err.message
                });
            })
            .finally(() => setLoadingArticles(false));
      }
    }
  }, [activeTab, data.id, data.keywords, articles.length, data.pubmed_articles, bmjContent, summaryData]);

  const tabs = [
      { id: 'summary', label: 'Summary', icon: FileText },
      { id: 'differential', label: 'Differential', icon: Activity },
      { id: 'research', label: 'Evidence', icon: BookOpen },
      { id: 'transcript', label: 'Transcript', icon: Stethoscope },
  ];

  return (
    <div className="glass-card flex flex-col h-[calc(100vh-8rem)] overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="p-8 border-b border-white/5 bg-black/20">
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-4">
              <button 
                  onClick={onBack}
                  className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-all duration-200 border border-white/5"
              >
                  <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                  <h1 className="text-2xl font-semibold text-white tracking-tight">{data.title}</h1>
                  <div className="flex items-center gap-4 mt-2 text-sm text-apple-gray">
                    <div className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4" />
                        {new Date(data.date).toLocaleDateString()}
                    </div>
                    {data.presenter && (
                        <div className="flex items-center gap-1.5">
                            <User className="w-4 h-4" />
                            {data.presenter}
                        </div>
                    )}
                  </div>
              </div>
              <div className="ml-auto flex items-center gap-3">
                  <span className={clsx(
                      "px-3 py-1 rounded-full text-xs font-medium border",
                      data.status === 'processed' 
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  )}>
                      {data.status.toUpperCase()}
                  </span>
                  <button 
                    onClick={handleDelete}
                    className="p-2 rounded-xl text-apple-gray hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                      <Trash2 className="w-5 h-5" />
                  </button>
              </div>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
              {tabs.map(tab => (
                  <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as Tab)}
                      className={clsx(
                          "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap",
                          activeTab === tab.id
                              ? "bg-white/10 text-white shadow-lg shadow-black/10 border border-white/5"
                              : "text-apple-gray hover:text-white hover:bg-white/5"
                      )}
                  >
                      <tab.icon className="w-4 h-4" />
                      {tab.label}
                  </button>
              ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        {activeTab === 'summary' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-8">
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-apple-blue uppercase tracking-wider flex items-center gap-2">
                            <Activity className="w-4 h-4" /> Chief Complaint
                        </h3>
                        <div className="glass-panel p-6 rounded-xl text-lg text-white font-medium leading-relaxed">
                            "{summaryData.chiefComplaint}"
                        </div>
                    </div>
                    
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-apple-gray uppercase tracking-wider">History of Present Illness</h3>
                        <div className="text-white/80 leading-relaxed space-y-4">
                            {summaryData.history.split('\n').map((para, i) => (
                                <p key={i}>{para}</p>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-8">
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-apple-gray uppercase tracking-wider">Vital Signs</h3>
                        <div className="glass-panel p-6 rounded-xl font-mono text-sm text-emerald-300 leading-relaxed whitespace-pre-wrap">
                            {summaryData.vitals}
                        </div>
                    </div>

                    {data.keywords && (
                        <div className="space-y-3">
                            <h3 className="text-sm font-medium text-apple-gray uppercase tracking-wider">Keywords</h3>
                            <div className="flex flex-wrap gap-2">
                                {data.keywords.map((k, i) => (
                                    <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-white/5 border border-white/10 text-white/70">
                                        #{k}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        )}

        {activeTab === 'differential' && (
            <div className="space-y-6 max-w-4xl mx-auto">
                <h3 className="text-xl font-medium text-white mb-6">Differential Diagnosis</h3>
                <div className="grid gap-4">
                    {differentials.map((dx, i) => (
                        <div key={i} className="glass-panel p-6 rounded-xl group hover:bg-white/5 transition-all duration-300">
                            <div className="flex justify-between items-start mb-2">
                                <h4 className="text-lg font-medium text-white">{dx.condition}</h4>
                                {dx.probability && (
                                    <span className="px-2 py-1 rounded text-xs font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                        {dx.probability}
                                    </span>
                                )}
                            </div>
                            {dx.reasoning && (
                                <p className="text-white/60 text-sm leading-relaxed mt-2 pl-4 border-l-2 border-white/10">
                                    {dx.reasoning}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        )}

        {activeTab === 'research' && (
            <div className="space-y-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div>
                        <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-amber-400" />
                            Nelson Textbook of Pediatrics
                        </h3>
                        <div className="glass-panel p-6 rounded-xl text-white/80 leading-relaxed text-sm">
                            {nelsonText || "No textbook references found."}
                        </div>
                    </div>
                    
                    <div>
                        <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                            <Search className="w-5 h-5 text-blue-400" />
                            BMJ Best Practice – Clinical Topics
                        </h3>
                        {pubmedError && (
                            <div className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300">
                                <div className="flex items-start gap-3">
                                    <div className="p-2 rounded-full bg-red-500/20 text-red-400 shrink-0">
                                        <Activity className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h4 className="text-sm font-semibold text-red-400">
                                                [ERROR] EVIDENCE SERVICE
                                            </h4>
                                            <span className="text-[10px] font-mono text-red-400/60 bg-red-500/10 px-1.5 py-0.5 rounded">
                                                [{pubmedError.timestamp}]
                                            </span>
                                        </div>
                                        <p className="text-sm text-red-200/80 mb-2">
                                            {pubmedError.message}
                                        </p>
                                        <div className="p-3 rounded-lg bg-black/40 border border-white/5 font-mono text-xs text-red-300/70 overflow-x-auto">
                                            <div className="flex flex-col gap-1">
                                                <span>{pubmedError.context}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        {loadingArticles ? (
                            <div className="flex items-center gap-2 text-white/40 text-sm animate-pulse">
                                Analyzing clinical topics...
                            </div>
                        ) : bmjContent ? (
                            <div className="space-y-4">
                                {bmjContent.split('###').filter(s => s.trim() && !s.includes('BMJ Best Practice – Relevant Clinical Topics')).map((section, i) => {
                                    const lines = section.trim().split('\n');
                                    // Remove "1. " etc from title if present
                                    const rawTitle = lines[0] || '';
                                    const title = rawTitle.replace(/^\d+\.\s*/, '').replace(/\*\*/g, '').trim();
                                    
                                    const content = lines.slice(1).join('\n');
                                    // Extract URL
                                    const linkMatch = content.match(/`([^`]+)`/);
                                    const url = linkMatch ? linkMatch[1] : '';
                                    
                                    // Clean text
                                    const text = content.replace(/\*\*BMJ Link:\*\* `[^`]+`/, '').trim();
                                    
                                    if (!title) return null;

                                    return (
                                        <div key={i} className="glass-panel p-6 rounded-xl hover:bg-white/5 transition-all duration-300">
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="text-lg font-medium text-white">{title}</h4>
                                            </div>
                                            <div className="text-white/60 text-sm leading-relaxed whitespace-pre-wrap mb-4">
                                                {text}
                                            </div>
                                            {url && (
                                                <a 
                                                    href={url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition-colors text-sm font-medium border border-blue-500/20"
                                                >
                                                    View on BMJ Best Practice
                                                    <Search className="w-4 h-4" />
                                                </a>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {articles.length > 0 ? (
                                    articles.map((article, i) => {
                                        const isLog = article.url === '#' || !article.url;
                                        const Wrapper = isLog ? 'div' : 'a';
                                        const wrapperProps = isLog ? {} : { href: article.url, target: "_blank", rel: "noreferrer" };
                                        
                                        return (
                                            <Wrapper 
                                                key={i} 
                                                {...wrapperProps}
                                                className={clsx(
                                                    "block glass-panel p-4 rounded-xl transition-all duration-200 group",
                                                    !isLog && "hover:bg-white/10 cursor-pointer",
                                                    isLog && "bg-white/5 border-dashed border-white/20"
                                                )}
                                            >
                                                <h4 className={clsx(
                                                    "text-sm font-medium mb-1 line-clamp-1",
                                                    isLog ? "text-amber-300/80 italic" : "text-blue-300 group-hover:text-blue-200"
                                                )}>
                                                    {article.title}
                                                </h4>
                                                <p className={clsx(
                                                    "text-xs line-clamp-2",
                                                    isLog ? "text-white/60 font-mono" : "text-white/50"
                                                )}>
                                                    {article.snippet}
                                                </p>
                                                
                                                {article.links && article.links.length > 0 && (
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        {article.links.map((link, k) => (
                                                            <a 
                                                                key={k}
                                                                href={`http://localhost:8000${link.url}`}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/10 hover:bg-white/20 text-blue-300 transition-colors flex items-center gap-1.5 border border-white/5"
                                                            >
                                                                <FileText className="w-3 h-3" />
                                                                {link.title}
                                                            </a>
                                                        ))}
                                                    </div>
                                                )}
                                            </Wrapper>
                                        );
                                    })
                                ) : (
                                    !pubmedError && (
                                        <div className="glass-panel p-8 rounded-xl text-center">
                                            <p className="text-white/40">No clinical topics found.</p>
                                        </div>
                                    )
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Query Expansion Component */}
                <div className="border-t border-white/10 pt-8 mt-8">
                    <div className="glass-panel p-8 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-32 bg-blue-500/10 blur-3xl rounded-full pointer-events-none -mr-16 -mt-16"></div>
                        
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 rounded-lg bg-blue-500/20 text-blue-300">
                                    <Sparkles className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-medium text-white">Query Expansion</h3>
                                    <p className="text-sm text-white/50">Generate advanced PubMed boolean strings for precise literature search.</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                                <div className="lg:col-span-2 space-y-6">
                                    <div className="space-y-3">
                                        <label className="text-xs font-medium text-apple-gray uppercase tracking-wider">Clinical Query</label>
                                        <SmartQueryInput 
                                            value={queryInput}
                                            onChange={setQueryInput}
                                            onExpand={handleExpandQuery}
                                            isExpanding={isExpanding}
                                            suggestions={data.keywords || []}
                                        />
                                        
                                        {/* Suggestions */}
                                        {data.keywords && data.keywords.length > 0 && (
                                            <div className="flex flex-wrap gap-2 pt-2">
                                                <span className="text-xs text-white/40 py-1">Suggestions:</span>
                                                {data.keywords.slice(0, 5).map((k, i) => (
                                                    <button
                                                        key={i}
                                                        onClick={() => setQueryInput(k)}
                                                        className="px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-white/60 hover:text-white transition-colors border border-white/5"
                                                    >
                                                        {k}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    {expansionError && (
                                        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                                            Error: {expansionError}
                                        </div>
                                    )}

                                    {expandedQuery && (
                                        <div className="space-y-3 animate-in fade-in slide-in-from-top-4 duration-500">
                                            <div className="flex items-center justify-between">
                                                <label className="text-xs font-medium text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                                    Optimized Boolean String
                                                </label>
                                                <button
                                                    onClick={handleCopy}
                                                    className="text-xs flex items-center gap-1.5 text-white/50 hover:text-white transition-colors"
                                                >
                                                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                                    {copied ? 'Copied!' : 'Copy to clipboard'}
                                                </button>
                                            </div>
                                            <div className="p-4 rounded-xl bg-black/40 border border-emerald-500/20 font-mono text-sm text-emerald-100/90 break-all leading-relaxed relative group">
                                                {expandedQuery}
                                            </div>
                                            <div className="flex gap-4 pt-2">
                                                <a 
                                                    href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(expandedQuery)}`}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="text-xs flex items-center gap-1.5 text-blue-300 hover:text-blue-200 transition-colors"
                                                >
                                                    <Search className="w-3 h-3" />
                                                    Search on PubMed
                                                </a>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Methodology Documentation */}
                                <div className="p-6 rounded-xl bg-white/5 border border-white/5 h-fit">
                                    <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                                        <BookOpen className="w-4 h-4 text-white/60" />
                                        Methodology
                                    </h4>
                                    <div className="space-y-4 text-xs text-white/60 leading-relaxed">
                                        <p>
                                            <strong className="text-white/80 block mb-1">Boolean Logic Application</strong>
                                            Connects related terms with OR (synonyms) and distinct concepts with AND to refine search scope.
                                        </p>
                                        <p>
                                            <strong className="text-white/80 block mb-1">Field Tags</strong>
                                            Applies [Title/Abstract] or [MeSH Terms] tags to target specific article sections for higher relevance.
                                        </p>
                                        <p>
                                            <strong className="text-white/80 block mb-1">Term Expansion</strong>
                                            Automatically includes medical synonyms, acronyms, and variations (e.g., "MI" → "Myocardial Infarction").
                                        </p>
                                        <div className="pt-2 border-t border-white/5 mt-2">
                                            <span className="block text-[10px] uppercase tracking-wider text-white/30 mb-2">Example Transformation</span>
                                            <div className="font-mono text-[10px] bg-black/20 p-2 rounded text-white/50">
                                                "Heart attack"<br/>
                                                ↓<br/>
                                                (Myocardial Infarction[MeSH] OR Heart Attack[Title/Abstract])
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )}

        {activeTab === 'transcript' && (
            <div className="max-w-3xl mx-auto">
                <div className="glass-panel p-8 rounded-xl">
                    <h3 className="text-sm font-medium text-apple-gray uppercase tracking-wider mb-6">Full Transcript</h3>
                    <div className="font-mono text-sm text-white/70 leading-relaxed whitespace-pre-wrap">
                        {data.transcript || "No transcript available."}
                    </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}
