import { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, Square, Loader2, Radio } from 'lucide-react';
import clsx from 'clsx';
import { saveCase } from '../services/apiService';
import type { CanonicalCase } from '../services/apiService';
import type { MedicalCase } from '../types';

interface RealTimeRecorderProps {
    onTranscriptionUpdate: (text: string) => void;
    onCaseSaved?: (caseData: MedicalCase) => void;
}

export function RealTimeRecorder({ onTranscriptionUpdate, onCaseSaved }: RealTimeRecorderProps) {
    // Task 1: Check JS Execution
    useEffect(() => {
        console.log("JS Loaded - RealTimeRecorder mounted");
    }, []);

    const [isRecording, setIsRecording] = useState(false);
    const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);
    const [transcript, setTranscript] = useState("");
    
    // Plan: Permanent Buffer & Memory Management
    const bufferRef = useRef(""); // To access latest buffer in stopRecording
    const MAX_BUFFER_SIZE = 50000;

    // Plan: Results State
    const [isLoading, setIsLoading] = useState(false);
    const isStoppingRef = useRef(false);
    
    // Connection Management
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const MAX_RECONNECT_ATTEMPTS = 10;
    
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // Stable callback ref
    const onCaseSavedRef = useRef(onCaseSaved);
    useEffect(() => {
        onCaseSavedRef.current = onCaseSaved;
    }, [onCaseSaved]);

    const stopRecording = useCallback(async () => {
        setIsRecording(false);
        setStatus('idle');
        
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        if (isStoppingRef.current) return;
        
        // Guard: Check for minimum transcript length to avoid 422 errors
        const currentBuffer = bufferRef.current;
        if (!currentBuffer || currentBuffer.trim().length < 10) {
            console.warn("Transcript too short for analysis (min 10 chars). Skipping API calls.");
            setIsLoading(false);
            return;
        }

        isStoppingRef.current = true;
        setIsLoading(true);

        try {
            const endpoints = ['/api/summarize', '/api/differential', '/api/nelson', '/api/pubmed'];
            // Use relative path so it works through tunnel/proxy
            const baseUrl = ''; 
            
            const responses = await Promise.allSettled(
                endpoints.map(endpoint => 
                    fetch(`${baseUrl}${endpoint}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: bufferRef.current })
                    })
                    .then(async res => {
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.message || res.statusText);
                        return data;
                    })
                )
            );
            
            const newResults: Record<string, unknown> = {};
            responses.forEach((res, idx) => {
                const key = endpoints[idx].split('/').pop()!;
                if (res.status === 'fulfilled') {
                    const payload = res.value; 
                    let parsedResult = payload.result;
                    
                    if (typeof parsedResult === 'string') {
                        try {
                            parsedResult = JSON.parse(parsedResult);
                        } catch (e) {
                            console.error(`Failed to parse result for ${key}`, e);
                        }
                    }
                    newResults[key] = parsedResult || {};
                } else {
                     newResults[key] = { status: 'error', message: (res.reason as Error).message };
                }
            });

            // Save Case
            /* eslint-disable @typescript-eslint/no-explicit-any */
            const summarize = newResults.summarize as Record<string, any> || {};
            const differential = newResults.differential as Record<string, any> || {};
            const nelson = newResults.nelson as Record<string, any> || {};
            const pubmed = newResults.pubmed as Record<string, any> || {};
            /* eslint-enable @typescript-eslint/no-explicit-any */

            const canonicalCase: CanonicalCase = {
                source: "realtime",
                transcript: bufferRef.current,
                summary: {
                    // Handle both camelCase and snake_case
                    chief_complaint: summarize.chiefComplaint || summarize.chief_complaint || "Real-time Case",
                    dashboard_chief_complaint: summarize.dashboardChiefComplaint || summarize.dashboard_chief_complaint,
                    hpi: summarize.history || "",
                    vitals: typeof summarize.vitals === 'object' && summarize.vitals !== null
                        ? Object.entries(summarize.vitals).map(([k,v]) => `${k}: ${v}`).join(', ') 
                        : (summarize.vitals || ""),
                    assessment: "",
                    plan: ""
                },
                differential_dx: (differential.differential_diagnosis || differential.differentialDiagnosis || [])
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
                    .filter((item: { disease: string; reasoning: string } | null): item is { disease: string; reasoning: string } => item !== null),
                nelson: [{
                    title: "Nelson Textbook Reference",
                    recommendation: nelson.context || nelson.nelsonContext || ""
                }],
                pubmed: (pubmed.results || []).map((p: unknown) => {
                    const article = p as Record<string, unknown>;
                    return {
                        title: (article.title as string) || "Evidence",
                        link: article.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${article.pmid}` : "#",
                        pmid: article.pmid as string,
                        summary: (article.summary as string) || (article.relevance as string) || ""
                    };
                }),
                created_at: new Date().toISOString()
            };
            
            try {
                const saved = await saveCase(canonicalCase);
                if (onCaseSavedRef.current) onCaseSavedRef.current(saved);
            } catch (e) {
                console.error("Failed to save case", e);
            }

        } catch (error) {
            console.error("Analysis failed:", error);
        } finally {
            setIsLoading(false);
            isStoppingRef.current = false;
        }
    }, []);

    useEffect(() => {
        return () => {
            stopRecording();
        };
    }, [stopRecording]);

    const getAudioContext = () => {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (!AudioContextClass) {
            throw new Error("Web Audio API is not supported in this browser.");
        }
        return new AudioContextClass({ sampleRate: 16000 });
    };

    const checkPermissions = async () => {
        // Task 6: Check MediaRecorder support (Diagnostic)
        if (typeof window.MediaRecorder === 'undefined') {
            console.warn("MediaRecorder is not supported in this browser.");
        } else {
            console.log("MediaRecorder is supported.");
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Audio recording is not supported in this browser.");
        }

        try {
            // Check if permission is already granted (if API available)
            if (navigator.permissions && navigator.permissions.query) {
                const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
                if (result.state === 'denied') {
                    throw new Error("Microphone permission denied. Please enable it in browser settings.");
                }
            }
        } catch (e) {
            // Fallback or ignore if query not supported, getUserMedia will handle it
            console.warn("Permission query failed or not supported, proceeding to getUserMedia", e);
        }
    };

    const connectWebSocket = () => {
        return new Promise<void>((resolve, reject) => {
            // Determine WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const publicAddress = import.meta.env.REACT_APP_PUBLIC_ADDRESS;
            const wsUrl = import.meta.env.VITE_WS_URL || 
                         (publicAddress ? publicAddress.replace(/^http/, 'ws') + '/api/v1/realtime' : `${protocol}//${host}/api/v1/realtime`);
            
            console.log("Connecting to WebSocket URL:", wsUrl);

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            // Connection timeout
            const connectionTimeout = setTimeout(() => {
                if (ws.readyState !== WebSocket.OPEN) {
                    ws.close();
                }
            }, 5000);

            ws.onopen = async () => {
                console.log("WebSocket connection established.");
                clearTimeout(connectionTimeout);
                setStatus('connected');
                setIsRecording(true);
                reconnectAttemptsRef.current = 0; // Reset attempts on success
                
                try {
                    // Initialize audio if not already active
                    if (!streamRef.current) {
                        await setupAudio();
                    }
                    resolve();
                } catch (err: unknown) {
                    const audioErr = err as Error;
                    console.error("Audio setup error:", audioErr);
                    setError(audioErr.message || "Failed to initialize audio.");
                    setStatus('error');
                    stopRecording();
                    reject(audioErr);
                }
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'transcription') {
                        const chunk = data.text + " ";
                        setTranscript(prev => {
                             const newText = prev + chunk;
                             onTranscriptionUpdate(newText);
                             return newText;
                        });
                        
                        // Update Buffer
                        const current = bufferRef.current + chunk;
                        bufferRef.current = current.length > MAX_BUFFER_SIZE 
                            ? current.slice(-MAX_BUFFER_SIZE) 
                            : current;
                    }
                } catch (e) {
                    console.error("WS Parse error", e);
                }
            };

            ws.onerror = (e) => {
                console.error("WebSocket Error occurred:", e);
                if (!isStoppingRef.current) {
                    setError("WebSocket connection error. Retrying...");
                }
                // Allow onclose to handle retry logic
            };

            ws.onclose = (event) => {
                clearTimeout(connectionTimeout);
                console.log(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
                
                if (isStoppingRef.current) {
                    return;
                }

                // Automatic Reconnection Logic
                if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttemptsRef.current++;
                    setStatus('connecting');
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 5000);
                    
                    console.log(`Connection lost. Retrying in ${delay}ms... (Attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
                    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connectWebSocket();
                    }, delay);
                } else {
                    console.error("Max reconnection attempts reached.");
                    setError("Connection lost. Server unreachable. Please check your network or try again later.");
                    setStatus('error');
                    stopRecording();
                }
            };
        });
    };

    const startRecording = async () => {
        // Task 3: Check Event Listener
        console.log("Record Clicked");
        
        setError(null);
        try {
            await checkPermissions();
            setStatus('connecting');
            
            reconnectAttemptsRef.current = 0;
            isStoppingRef.current = false;
            
            await connectWebSocket();
        } catch (err: unknown) {
            const error = err as Error;
            console.error("Failed to start recording", error);
            setError(error.message || "Failed to start recording.");
            setStatus('error');
        }
    };

    const setupAudio = async () => {
        try {
            // Task 2: Test Microphone access
            console.log("Requesting microphone access...");
            // Task 5: Get Audio Stream
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            console.log("Microphone access granted. Stream:", stream);

            const audioContext = getAudioContext();
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            audioContextRef.current = audioContext;

            const input = audioContext.createMediaStreamSource(stream);
            
            // Buffer size 4096, 1 input, 1 output
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            processorRef.current = processor;

            input.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = (e) => {
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    
                    // Task 8: Receive Audio Chunk & Downsample if needed
                    const targetSampleRate = 16000;
                    const currentSampleRate = audioContext.sampleRate;
                    
                    let finalData = inputData;

                    if (currentSampleRate !== targetSampleRate) {
                        // Simple downsampling
                        const ratio = currentSampleRate / targetSampleRate;
                        const newLength = Math.floor(inputData.length / ratio);
                        finalData = new Float32Array(newLength);
                        for (let i = 0; i < newLength; i++) {
                            finalData[i] = inputData[Math.floor(i * ratio)];
                        }
                    }

                    // Convert to Int16 PCM
                    const buffer = new ArrayBuffer(finalData.length * 2);
                    const outputView = new DataView(buffer);
                    
                    for (let i = 0; i < finalData.length; i++) {
                        let s = Math.max(-1, Math.min(1, finalData[i]));
                        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        outputView.setInt16(i * 2, s, true);
                    }
                    
                    // Send data
                    try {
                        wsRef.current.send(buffer);
                        // Task 9: Send Audio to Backend (Log size)
                        // console.log("Sent chunk:", buffer.byteLength); 
                    } catch (err) {
                        console.error("WebSocket send error", err);
                    }
                }
            };
            
            // Task 7: Start Recording (State check)
            console.log("Audio processing started. Context State:", audioContext.state);
        } catch (err: unknown) {
            console.error("Audio setup failed", err);
            const error = err as Error;
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                throw new Error("Microphone permission denied.");
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                throw new Error("No microphone found.");
            } else {
                throw new Error("Could not access microphone: " + error.message);
            }
        }
    };



    return (
        <div className="space-y-6">
            <div className="flex flex-col items-center gap-6 py-8">
                {/* Visualizer Circle */}
                <div className={clsx(
                    "relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500",
                    isRecording ? "bg-red-500/10" : "bg-white/5"
                )}>
                    {isRecording && (
                        <>
                            <div className="absolute inset-0 rounded-full border border-red-500/30 animate-ping opacity-20" />
                            <div className="absolute inset-2 rounded-full border border-red-500/20 animate-pulse" />
                        </>
                    )}
                    
                    <button
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isLoading || status === 'connecting'}
                        className={clsx(
                            "relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-xl",
                            isRecording 
                                ? "bg-red-500 text-white hover:bg-red-600 scale-100" 
                                : "bg-white text-black hover:scale-105",
                            (isLoading || status === 'connecting') && "opacity-50 cursor-not-allowed"
                        )}
                    >
                        {isLoading || status === 'connecting' ? (
                            <Loader2 className="w-8 h-8 animate-spin text-apple-gray" />
                        ) : isRecording ? (
                            <Square className="w-8 h-8 fill-current" />
                        ) : (
                            <Mic className="w-8 h-8" />
                        )}
                    </button>
                </div>

                {/* Status Text */}
                <div className="text-center space-y-2">
                    <h3 className="text-xl font-medium text-white">
                        {status === 'connecting' ? "Connecting..." :
                         isRecording ? "Recording in Progress" : 
                         isLoading ? "Processing Audio..." : 
                         "Start Recording"}
                    </h3>
                    <p className={clsx("text-sm", error ? "text-red-400 font-medium" : "text-apple-gray")}>
                        {error ? error :
                         status === 'connecting' ? "Establishing connection..." :
                         isRecording ? "Listening to morning report..." : 
                         "Click the microphone to begin"}
                    </p>
                </div>
            </div>

            {/* Transcript Preview */}
            {(transcript || bufferRef.current) && (
                <div className="glass-panel p-6 rounded-xl animate-fade-in">
                    <div className="flex items-center gap-2 mb-4">
                        <Radio className={clsx("w-4 h-4", isRecording ? "text-red-500 animate-pulse" : "text-apple-gray")} />
                        <h4 className="text-sm font-medium text-white/80">Live Transcript</h4>
                    </div>
                    <div className="h-40 overflow-y-auto font-mono text-sm text-apple-gray/80 leading-relaxed custom-scrollbar">
                        {transcript || bufferRef.current}
                        {isRecording && <span className="inline-block w-2 h-4 bg-red-500/50 ml-1 animate-pulse"/>}
                    </div>
                </div>
            )}
        </div>
    );
}
