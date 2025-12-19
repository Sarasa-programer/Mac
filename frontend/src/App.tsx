import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { AudioUploader } from './components/AudioUploader';
import { RealTimeRecorder } from './components/RealTimeRecorder';
import { CaseDetail } from './components/CaseDetail';
import { SettingsView } from './components/SettingsView';
import { ConfirmModal } from './components/ConfirmModal';
import { analyzeAudioCase, saveCase, fetchCases, deleteCase, deleteAllCases } from './services/apiService';
import type { CanonicalCase } from './services/apiService';
import { UserRole } from './types';
import type { MedicalCase } from './types';
import { BookOpen, Users, Clock, ChevronRight, Search, Trash2 } from 'lucide-react';
import clsx from 'clsx';

function App() {
  const [currentRole, setCurrentRole] = useState<UserRole>(UserRole.PROFESSOR);
  const [activeView, setActiveView] = useState('dashboard');
  const [cases, setCases] = useState<MedicalCase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState<MedicalCase | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [userEmail, setUserEmail] = useState("doctor@hospital.org");
  
  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  
  useEffect(() => {
    fetchCases()
      .then(data => {
        setCases(data);
        setError(null);
      })
      .catch(err => {
        console.error("Dashboard Load Error:", err);
        setError("Failed to connect to the database. Please ensure the backend server is running.");
      });
  }, []);

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);
    try {
      const analysis = await analyzeAudioCase(file);
      
      // Map to Canonical Case for Unified Save
      const canonicalCase: CanonicalCase = {
          source: "upload",
          transcript: analysis.transcript || "",
          summary: {
              chief_complaint: analysis.summary?.chiefComplaint || "",
              dashboard_chief_complaint: analysis.summary?.dashboardChiefComplaint || "",
              hpi: analysis.summary?.history || "",
              vitals: typeof analysis.summary?.vitals === 'object' && analysis.summary?.vitals !== null
                  ? Object.entries(analysis.summary.vitals).map(([k,v]) => `${k}: ${v}`).join(', ')
                  : (analysis.summary?.vitals || ""),
              assessment: "",
              plan: ""
          },
          differential_dx: ((analysis.differentialDiagnosis || []) as unknown[])
              .map((d: unknown) => {
                  if (typeof d === 'string') {
                      return { disease: d, reasoning: "" };
                  }
                  if (d && typeof d === 'object') {
                      const obj = d as Record<string, unknown>;
                      const diseaseName = obj.disease || obj.condition;
                      if (typeof diseaseName === 'string' && diseaseName.trim()) {
                          return {
                              disease: diseaseName,
                              reasoning: String(obj.reasoning || obj.rationale || "")
                          };
                      }
                  }
                  return null;
              })
              .filter((item): item is { disease: string; reasoning: string } => item !== null),
          nelson: [{
              title: "Nelson Textbook Reference",
              recommendation: analysis.nelsonContext || ""
          }],
          pubmed: [], 
          created_at: new Date().toISOString()
      };

      const savedCase = await saveCase(canonicalCase);
      setCases([savedCase, ...cases]);
      setSelectedCase(savedCase);
    } catch (error) {
      console.error("Failed to analyze case:", error);
      alert("Failed to analyze case. Please check your API key and try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleNavigate = (view: string) => {
    setActiveView(view);
    setSelectedCase(null); // Clear selected case when navigating top-level
  };

  const handleDeleteCase = async (e: React.MouseEvent, id: string | number) => {
    e.stopPropagation(); // Prevent row click
    if (window.confirm("Are you sure you want to delete this case? This action cannot be undone.")) {
      try {
        await deleteCase(id);
        setCases(cases.filter(c => c.id !== id));
      } catch (err: unknown) {
        const error = err as Error;
        alert(error.message);
      }
    }
  };

  const getChiefComplaint = (c: MedicalCase): string => {
    const summary = c.summary;
    return (
      summary?.dashboardChiefComplaint ||
      summary?.dashboard_chief_complaint ||
      c.chief_complaint ||
      summary?.chiefComplaint ||
      "Unknown Complaint"
    );
  };

  const handleDeleteAll = async () => {
    try {
      await deleteAllCases();
      setCases([]);
      setSelectedCase(null);
      setIsDeleteModalOpen(false);
    } catch (err: unknown) {
      const error = err as Error;
      alert(error.message || "Failed to delete all cases.");
    }
  };

  return (
    <div className="flex min-h-screen font-sans text-apple-text selection:bg-apple-blue/30">
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDeleteAll}
        title="Delete All Cases?"
        message="This action cannot be undone. All cases, transcripts, and summaries will be permanently removed."
        confirmPhrase="DELETE ALL"
        isDangerous={true}
      />
      <Sidebar 
        currentRole={currentRole} 
        activeView={selectedCase ? '' : activeView} // Deactivate sidebar items if viewing a specific case details
        onNavigate={handleNavigate} 
      />

      <main className="ml-72 flex-1 p-8 min-h-screen overflow-x-hidden">
        {/* Header */}
        <header className="flex justify-between items-center mb-10">
            <div>
                <h2 className="text-3xl font-semibold text-white tracking-tight">
                    {activeView === 'dashboard' ? 'Dashboard' : 
                     activeView === 'upload' ? 'Upload Case' : 
                     activeView === 'library' ? 'Case Library' : 'Settings'}
                </h2>
                <p className="text-apple-gray mt-1">
                    Welcome back, Dr. Ahadinia 
                </p>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex bg-white/5 backdrop-blur-md p-1 rounded-xl border border-white/10">
                    {Object.values(UserRole).map((role) => (
                        <button
                            key={role}
                            onClick={() => setCurrentRole(role)}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-xs font-medium transition-all duration-300",
                                currentRole === role
                                    ? "bg-white/10 text-white shadow-sm border border-white/5"
                                    : "text-apple-gray hover:text-white hover:bg-white/5"
                            )}
                        >
                            {role.charAt(0) + role.slice(1).toLowerCase()}
                        </button>
                    ))}
                </div>
            </div>
        </header>

        {/* Dynamic Content */}
        <div className="relative animate-fade-in">
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 flex items-center gap-3 backdrop-blur-md">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    {error}
                </div>
            )}

            {activeView === 'settings' ? (
                <SettingsView userEmail={userEmail} onSave={(email) => setUserEmail(email)} />
            ) : selectedCase ? (
                <CaseDetail 
                    data={selectedCase} 
                    onBack={() => setSelectedCase(null)} 
                    userRole={currentRole}
                />
            ) : activeView === 'upload' ? (
               <div className="max-w-3xl mx-auto space-y-8">
                   <div className="glass-card p-8">
                       <h3 className="text-xl font-medium text-white mb-6">Upload Audio Recording</h3>
                       <AudioUploader onUpload={handleFileUpload} isProcessing={isProcessing} />
                   </div>
                   
                   <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/10"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-4 bg-[#050511] text-apple-gray">Or record directly</span>
                        </div>
                   </div>

                   <div className="glass-card p-8">
                       <h3 className="text-xl font-medium text-white mb-6">Real-time Recording</h3>
                       <RealTimeRecorder 
                           onTranscriptionUpdate={() => {}} 
                           onCaseSaved={(newCase) => {
                               setCases([newCase, ...cases]);
                               setSelectedCase(newCase);
                           }}
                       />
                   </div>
               </div>
            ) : (
                <div className="space-y-8">
                    {/* Stats Row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                            { label: 'Total Cases', value: cases.length, icon: BookOpen, color: 'text-blue-400' },
                            { label: 'Pending Review', value: '3', icon: Clock, color: 'text-amber-400' },
                            { label: 'Active Students', value: '12', icon: Users, color: 'text-emerald-400' },
                        ].map((stat, i) => (
                            <div key={i} className="glass-card p-6 flex items-center justify-between group hover:bg-white/10 transition-colors cursor-default">
                                <div>
                                    <p className="text-apple-gray text-sm font-medium">{stat.label}</p>
                                    <p className="text-3xl font-semibold text-white mt-2">{stat.value}</p>
                                </div>
                                <div className={clsx("w-12 h-12 rounded-full bg-white/5 flex items-center justify-center border border-white/5 group-hover:scale-110 transition-transform duration-300", stat.color)}>
                                    <stat.icon className="w-6 h-6" />
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Recent Cases Table */}
                    <div className="glass-card overflow-hidden">
                        <div className="p-6 border-b border-white/5 flex justify-between items-center gap-4">
                            <h3 className="text-lg font-medium text-white">Recent Cases</h3>
                            <div className="flex items-center gap-3">
                                <div className="relative">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray" />
                                    <input 
                                        type="text" 
                                        placeholder="Search cases..." 
                                        className="pl-9 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-white/30 focus:outline-none focus:ring-1 focus:ring-apple-blue/50 w-64 transition-all"
                                    />
                                </div>
                                {cases.length > 0 && (
                                  <button
                                    onClick={() => setIsDeleteModalOpen(true)}
                                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 transition-colors"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                    Delete All Cases
                                  </button>
                                )}
                            </div>
                        </div>
                        
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="border-b border-white/5 text-apple-gray text-xs uppercase tracking-wider">
                                        <th className="px-6 py-4 font-medium">Case ID</th>
                                        <th className="px-6 py-4 font-medium">Date</th>
                                        <th className="px-6 py-4 font-medium">Chief Complaint</th>
                                        <th className="px-6 py-4 font-medium">Status</th>
                                        <th className="px-6 py-4 font-medium text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {cases.length === 0 ? (
                                        <tr>
                                            <td colSpan={5} className="px-6 py-12 text-center text-apple-gray">
                                                No cases found. Upload a new case to get started.
                                            </td>
                                        </tr>
                                    ) : (
                                        cases.map((c) => (
                                            <tr 
                                                key={c.id} 
                                                onClick={() => setSelectedCase(c)}
                                                className="group hover:bg-white/5 transition-colors cursor-pointer"
                                            >
                                                <td className="px-6 py-4 text-white/60 font-mono text-xs">#{c.id}</td>
                                                <td className="px-6 py-4 text-white">
                                                    {new Date(c.date).toLocaleDateString()}
                                                </td>
                                                <td className="px-6 py-4 text-white font-medium">
                                                    {getChiefComplaint(c)}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                        Analyzed
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex items-center justify-end gap-2">
                                                        <button 
                                                            className="p-2 hover:bg-white/10 rounded-lg text-apple-gray hover:text-white transition-colors"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setSelectedCase(c);
                                                            }}
                                                        >
                                                            <ChevronRight className="w-4 h-4" />
                                                        </button>
                                                        <button 
                                                            className="p-2 hover:bg-red-500/10 rounded-lg text-apple-gray hover:text-red-400 transition-colors"
                                                            onClick={(e) => handleDeleteCase(e, c.id)}
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
      </main>
    </div>
  );
}

export default App;
