import { analyzeAudioCase as analyzeApi, findPubMedArticles as findPubMedApi } from './apiService';
import type { MedicalCase, PubMedArticle } from '../types';

export const processCase = async (file: File): Promise<Partial<MedicalCase>> => {
  console.log(`Processing case via Backend Pipeline (ali ai services)...`);
  // The backend now handles the AI logic (Groq -> Gemini/GPT)
  // We route all requests through the secure backend API.
  return analyzeApi(file);
};

export const findArticles = async (keywords: string[]): Promise<PubMedArticle[]> => {
  const response = await findPubMedApi(keywords);
  return response.results;
};
