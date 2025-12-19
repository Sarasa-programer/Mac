export const UserRole = {
  PROFESSOR: 'PROFESSOR',
  RESIDENT: 'RESIDENT',
  STUDENT: 'STUDENT',
} as const;

export type UserRole = typeof UserRole[keyof typeof UserRole];

export type AIProvider = 'openai' | 'gemini' | 'groq';

export interface MedicalCase {
  id: string | number;
  title: string;
  date: string;
  presenter?: string;
  status: string;
  transcript?: string;
  
  // CamelCase (Frontend/Legacy)
  summary?: {
    chiefComplaint: string;
    dashboardChiefComplaint?: string;
    dashboard_chief_complaint?: string;
    history: string;
    vitals: string;
  };
  differentialDiagnosis?: string[];
  keywords?: string[];
  nelsonContext?: string;
  
  // Snake_case (Backend API)
  nelson_context?: string;
  differential_diagnoses?: Array<{
    condition: string;
    probability?: string;
    reasoning?: string;
  }>;
  pubmed_articles?: Array<PubMedArticle>;
  
  // Optional mapped fields for UI compatibility if needed
  chief_complaint?: string;
  description?: string;
  diagnosis?: string;
  differential_diagnosis?: string[];
  management_plan?: string;
}

export interface PubMedArticle {
  title: string;
  url: string;
  snippet?: string;
  summary?: string; // Backend sends summary, frontend mapped to snippet
  links?: Array<{ title: string; url: string }>;
}
