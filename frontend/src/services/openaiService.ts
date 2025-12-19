import OpenAI from 'openai';
import type { MedicalCase, PubMedArticle } from '../types';

const openai = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
});

export const analyzeAudioCase = async (file: File): Promise<Partial<MedicalCase>> => {
  try {
    if (file.size > 25 * 1024 * 1024) {
      throw new Error('File size exceeds 25MB limit for OpenAI Whisper');
    }

    // 1. Transcription
    const transcription = await openai.audio.transcriptions.create({
      file: file,
      model: 'whisper-1',
    });

    const transcriptText = transcription.text;

    // 2. Analysis
    const systemPrompt = `You are a pediatric expert. Analyze this morning report. Return a JSON object with:
    - chiefComplaint: string
    - history: string
    - vitals: string
    - differentialDiagnosis: string[] (5 items)
    - keywords: string[] (search terms)
    - nelsonContext: string (summary of the condition from Nelson Textbook of Pediatrics)
    `;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: transcriptText },
      ],
      response_format: { type: 'json_object' },
    });

    const analysisContent = completion.choices[0].message.content;
    if (!analysisContent) {
      throw new Error('No analysis generated');
    }

    const analysis = JSON.parse(analysisContent);

    // 3. Return merged object
    return {
      transcript: transcriptText,
      summary: {
        chiefComplaint: analysis.chiefComplaint,
        history: analysis.history,
        vitals: analysis.vitals,
      },
      differentialDiagnosis: analysis.differentialDiagnosis,
      keywords: analysis.keywords,
      nelsonContext: analysis.nelsonContext,
      status: 'completed',
    };
  } catch (error) {
    console.error('OpenAI processing error:', error);
    throw error;
  }
};

export const findPubMedArticles = async (keywords: string[]): Promise<PubMedArticle[]> => {
  // OpenAI lacks a search tool, return constructed objects
  return keywords.map((keyword) => ({
    title: `Search PubMed for ${keyword}`,
    url: `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(keyword)}`,
    snippet: 'Click to view search results on PubMed',
  }));
};
