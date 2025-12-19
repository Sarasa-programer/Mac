from fastapi import APIRouter, Depends
from typing import List, Optional
from app.models.schemas import TextRequest, SuccessResponse, ErrorResponse
from app.services.llm_service import UnifiedLLMService
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["llm"])

class PubMedQueryRequest(BaseModel):
    query: str
    send_email: bool = False
    email_to: Optional[str] = None

class BatchPubMedQueryRequest(BaseModel):
    queries: List[str]
    send_email: bool = False
    email_to: Optional[str] = None

async def get_llm():
    return UnifiedLLMService()

@router.post("/pubmed", response_model=SuccessResponse | ErrorResponse)
async def pubmed(data: TextRequest, llm: UnifiedLLMService = Depends(get_llm)):
    try:
        result = await llm.bmj_query(data.text)
        return SuccessResponse(status="success", result=result)
    except Exception as e:
        return ErrorResponse(status="error", message=str(e))

@router.post("/pubmed/search", response_model=SuccessResponse | ErrorResponse)
@router.post("/v1/pubmed/search", response_model=SuccessResponse | ErrorResponse)
async def pubmed_search(data: PubMedQueryRequest, llm: UnifiedLLMService = Depends(get_llm)):
    """
    Endpoint compatible with Frontend 'findPubMedArticles'
    Path: /api/pubmed/search OR /api/v1/pubmed/search
    Body: { "query": "..." }
    """
    try:
        # Frontend sends joined keywords as "query"
        # We redirect to BMJ query
        result = await llm.bmj_query(data.query)
        return SuccessResponse(status="success", result=result)
    except Exception as e:
        return ErrorResponse(status="error", message=str(e))

@router.post("/v1/pubmed/batch-search", response_model=SuccessResponse | ErrorResponse)
async def pubmed_batch_search(data: BatchPubMedQueryRequest, llm: UnifiedLLMService = Depends(get_llm)):
    """
    Batch processing for PubMed queries (Upload mode).
    Accepts a list of queries and processes them sequentially.
    """
    try:
        results = []
        for query in data.queries:
            # Process each query
            res = await llm.pubmed_query(query, send_email=data.send_email, email_to=data.email_to)
            results.append(res)
        
        return SuccessResponse(status="success", result=results)
    except Exception as e:
        return ErrorResponse(status="error", message=str(e))

@router.post("/v1/pubmed/expand", response_model=SuccessResponse | ErrorResponse)
async def pubmed_expand(data: PubMedQueryRequest, llm: UnifiedLLMService = Depends(get_llm)):
    """
    Expand a clinical query into a PubMed Boolean string.
    """
    try:
        expanded = await llm.expand_query_public(data.query)
        return SuccessResponse(status="success", result={"original": data.query, "expanded": expanded})
    except Exception as e:
        return ErrorResponse(status="error", message=str(e))
