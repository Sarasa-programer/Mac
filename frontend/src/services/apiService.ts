import { apiClient } from '../api/client';
import type { AxiosError } from 'axios';
import type { MedicalCase, PubMedArticle } from '../types';

interface JobResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export const analyzeAudioCase = async (file: File, provider: string = 'groq'): Promise<Partial<MedicalCase>> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('provider', provider);

  try {
    // 1. Submit Async Analysis Job
    const jobRes = await apiClient.post<JobResponse>('/audio/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    
    const jobId = jobRes.data.job_id;
    if (!jobId) throw new Error("Failed to start analysis job");

    // 2. Poll for results
    let attempts = 0;
    while (attempts < 60) { // Timeout after 60s
        await new Promise(r => setTimeout(r, 1000));
        const statusRes = await apiClient.get<JobResponse>(`/audio/jobs/${jobId}`);
        const status = statusRes.data.status;
        
        if (status === 'completed') {
            let result = statusRes.data.result;
            
            // Handle stringified JSON result
            if (typeof result === 'string') {
                try {
                    result = JSON.parse(result);
                } catch (e) {
                    console.error("Failed to parse job result:", e);
                }
            }

            // Map result to MedicalCase structure
            return {
                title: result.title,
                transcript: result.transcript,
                // Nested structure for CaseDetail.tsx
                summary: result.summary,
                differentialDiagnosis: result.differentialDiagnosis || result.differential_diagnosis,
                nelsonContext: result.nelsonContext || result.nelson_context,
                keywords: result.keywords,
                // Flattened/Mapped fields for other components/legacy support
                chief_complaint: result.summary?.chiefComplaint || result.summary?.chief_complaint,
                description: result.summary?.history, 
                diagnosis: (result.differentialDiagnosis || result.differential_diagnosis)?.[0], 
                differential_diagnosis: result.differentialDiagnosis || result.differential_diagnosis,
                management_plan: result.nelsonContext || result.nelson_context
            };
        }
        
        if (status === 'failed') {
            throw new Error(statusRes.data.error || "Analysis failed");
        }
        
        attempts++;
    }
    
    throw new Error("Analysis timed out");

  } catch (err: unknown) {
    const error = err as AxiosError;
    const status = error.response?.status;
    type ErrorDetail = { detail?: string } | undefined;
    const data = error.response?.data as ErrorDetail;
    const message = data?.detail || error.message;

    if (!error.response) {
      console.error("Network Error Details:", error);
      throw new Error('Backend unreachable. Please ensure the server is running and accessible (check VPN/Firewall).');
    }
    if (status === 400) {
      throw new Error(`Invalid Input: ${message}`);
    }
    if (status === 401) {
      throw new Error('Unauthorized: Please log in again.');
    }
    if (status === 429) {
      throw new Error('Rate limit exceeded. Please try again later.');
    }
    throw new Error(message || 'Unknown error during analysis.');
  }
};

export interface PubMedResponse {
    results: PubMedArticle[];
    bmj_topics_markdown?: string;
    error_details?: {
        code: string;
        message: string;
        timestamp: string;
        context: string;
    };
}

export const findPubMedArticles = async (keywords: string[]): Promise<PubMedResponse> => {
    try {
        const query = keywords.join(" ");
        const response = await apiClient.post('/pubmed/search', { query });
        
        const data = response.data;
        // Handle SuccessResponse wrapper
        const result = data.result || data;

        if (result.bmj_topics_markdown) {
            return {
                results: [],
                bmj_topics_markdown: result.bmj_topics_markdown
            };
        }
        
        // Check for backend-reported errors in successful response (200 OK but error content)
        if (result.error_details) {
            return {
                results: result.results || [],
                error_details: result.error_details
            };
        }
        
        return {
            results: result.results || []
        };
    } catch (err: unknown) {
        // Fallback to simple link generation if API fails completely
        console.error("PubMed/BMJ API failed, falling back to links:", err);
        return {
            results: keywords.map((keyword) => ({
                title: `Search PubMed for ${keyword}`,
                url: `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(keyword)}`,
                snippet: 'Click to view search results on PubMed',
            })),
            error_details: {
                code: "NETWORK_ERROR",
                message: "Service unreachable",
                timestamp: new Date().toISOString(),
                context: "Using direct search links as fallback"
            }
        };
    }
};

export interface CanonicalCase {
   source: "realtime" | "upload";
   transcript: string;
   summary: {
     chief_complaint: string;
     dashboard_chief_complaint?: string;
     hpi: string;
     vitals: string;
     assessment: string;
     plan: string;
   };
   differential_dx: Array<{ disease: string; reasoning: string }>;
   nelson: Array<{ title: string; chapter?: string; recommendation?: string }>;
   pubmed: Array<{ title: string; pmid?: string; link?: string; summary?: string }>;
   created_at?: string;
}

export const saveCase = async (caseData: CanonicalCase): Promise<MedicalCase> => {
  try {
    const response = await apiClient.post<MedicalCase>('/cases/save', caseData);
    return response.data;
  } catch (err: unknown) {
    const error = err as AxiosError;
    const message = (error.response?.data as any)?.detail || error.message;
    throw new Error(`Failed to save case: ${message}`);
  }
};

export const fetchCases = async (): Promise<MedicalCase[]> => {
  try {
    // Note: Backend router uses @router.get("/") which maps to /cases/
    // Adding trailing slash avoids 307 Temporary Redirect
    const response = await apiClient.get<MedicalCase[]>('/cases/');
    return response.data;
  } catch (err: unknown) {
    const error = err as AxiosError;
    const message = (error.response?.data as any)?.detail || error.message;
    console.error("Failed to fetch cases:", message);
    throw new Error(message || "Failed to load cases");
  }
};

export const deleteCase = async (id: string | number): Promise<void> => {
  try {
    await apiClient.delete(`/cases/${id}`);
  } catch (err: unknown) {
    const error = err as AxiosError;
    const message = (error.response?.data as any)?.detail || error.message;
    throw new Error(`Failed to delete case: ${message}`);
  }
};

export const deleteAllCases = async (): Promise<void> => {
  try {
    await apiClient.delete('/cases/all');
  } catch (err: unknown) {
    const error = err as AxiosError;
    const message = (error.response?.data as any)?.detail || error.message;
    throw new Error(`Failed to delete all cases: ${message}`);
  }
};

export const expandPubMedQuery = async (query: string): Promise<string> => {
    try {
        const response = await apiClient.post('/pubmed/expand', { query });
        if (response.data.status === 'success' && response.data.result) {
            return response.data.result.expanded;
        }
        throw new Error('Failed to expand query');
    } catch (err: unknown) {
        const error = err as AxiosError;
        const message = (error.response?.data as any)?.detail || error.message;
        throw new Error(`Query expansion failed: ${message}`);
    }
};
