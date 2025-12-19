import type { MedicalCase, PubMedArticle } from '../types';

// Client-side Gemini service is deprecated in favor of Backend API for security.
// Logic has been moved to backend/app/services/gemini_service.py

export const analyzeAudioCase = async (): Promise<Partial<MedicalCase>> => {
  throw new Error("Client-side analysis is disabled. Please use the backend API.");
};

export const findPubMedArticles = async (): Promise<PubMedArticle[]> => {
    throw new Error("Client-side search is disabled. Please use the backend API.");
};
