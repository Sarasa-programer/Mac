from faster_whisper import WhisperModel
from transformers import pipeline
from keybert import KeyBERT
from Bio import Entrez
import os
import torch

# Configuration
Entrez.email = os.getenv("ENTREZ_EMAIL", "your.email@example.com")

class AIPipeline:
    def __init__(self):
        # 1) Transcription model (faster-whisper)
        # Using "tiny" or "base" for faster CPU inference if GPU not available
        # User suggested "small", keeping that but adding cpu_threads for performance
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"Loading Whisper model on {device} with {compute_type}...")
        self.transcriber = WhisperModel(
            model_size="small",
            device=device,
            compute_type=compute_type
        )

        # 2) Summarization pipeline (HuggingFace)
        # Explicitly checking for MPS (Metal Performance Shaders) for Mac
        hf_device = -1
        if torch.cuda.is_available():
            hf_device = 0
        elif torch.backends.mps.is_available():
            # Hugging Face pipelines support mps via device="mps" string or torch.device object in recent versions
            # usually device argument expects integer for cuda:N or -1 for cpu. 
            # For safe compatibility with standard pipeline, sticking to -1 (CPU) unless explicit CUDA.
            # However, we can try using "mps" if supported by the specific pipeline version, 
            # but simpler to default to CPU to avoid compatibility issues during demo.
            pass
            
        print(f"Loading Summarization pipeline on device {hf_device}...")
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=hf_device
        )

        # 3) Keyword extractor (KeyBERT)
        print("Loading KeyBERT...")
        self.keyword_extractor = KeyBERT(model="all-MiniLM-L6-v2")

    async def transcribe(self, audio_path: str) -> str:
        """
        Uses Faster-Whisper to transcribe the audio file.
        Returns the full transcript as text.
        """
        # Run in executor to avoid blocking the async loop since faster-whisper is synchronous
        # But for simplicity here following user's sync pattern in async def (which blocks)
        # Ideally should use run_in_executor. 
        # For now, implementing as direct call per user snippet.
        segments, _ = self.transcriber.transcribe(audio_path, beam_size=5)
        transcript = " ".join([segment.text for segment in segments])
        return transcript

    async def summarize(self, text: str, max_length: int = 256) -> str:
        """
        Summarizes the input text using a transformer summarization pipeline.
        """
        # Truncate text if too long for the model (BART limit is usually 1024 tokens)
        # The pipeline handles truncation usually, but good to be safe.
        summary_chunks = self.summarizer(
            text,
            max_length=max_length,
            min_length=50,
            do_sample=False,
            truncation=True
        )
        return summary_chunks[0]["summary_text"]

    async def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """
        Extracts top_n keywords using KeyBERT.
        """
        keywords = self.keyword_extractor.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=top_n
        )
        # Return only the keyword strings
        return [kw[0] for kw in keywords]

    async def search_papers(self, keywords: list[str], retmax: int = 5) -> list[dict]:
        """
        Searches PubMed via Entrez for relevant papers based on keywords.
        Returns a list of dicts: {title, url, snippet}.
        """
        if not keywords:
            return []
            
        # Take top 3 keywords for search to avoid over-constraint
        search_terms = keywords[:3]
        query = " AND ".join(search_terms) # Using AND for more relevant results, or OR for broader
        
        try:
            handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record["IdList"]
            papers = []
            
            if not id_list:
                return []

            handle = Entrez.efetch(db="pubmed", id=id_list, rettype="abstract", retmode="xml")
            fetch = Entrez.read(handle)
            handle.close()
            
            # fetch can be a list or dict depending on result count
            articles = fetch["PubmedArticle"]
            if not isinstance(articles, list):
                articles = [articles]
                
            for article_data in articles:
                try:
                    article = article_data["MedlineCitation"]["Article"]
                    title = article["ArticleTitle"]
                    
                    abstract_text = ""
                    if "Abstract" in article and "AbstractText" in article["Abstract"]:
                        abstract_list = article["Abstract"]["AbstractText"]
                        if isinstance(abstract_list, list):
                            abstract_text = " ".join([str(x) for x in abstract_list])
                        else:
                            abstract_text = str(abstract_list)
                    
                    pmid = article_data["MedlineCitation"]["PMID"]
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    
                    papers.append({
                        "title": str(title),
                        "url": url,
                        "snippet": abstract_text[:200] + "..." if abstract_text else "No abstract available."
                    })
                except Exception as e:
                    print(f"Error parsing paper: {e}")
                    continue
                    
            return papers
            
        except Exception as e:
            print(f"Error searching papers: {e}")
            return []
