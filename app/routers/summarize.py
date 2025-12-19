from fastapi import APIRouter, Depends
from app.models.schemas import TextRequest, SuccessResponse, ErrorResponse
from app.services.llm_service import UnifiedLLMService

router = APIRouter(prefix="/api", tags=["llm"])

async def get_llm():
    return UnifiedLLMService()

@router.post("/summarize", response_model=SuccessResponse | ErrorResponse)
async def summarize(data: TextRequest, llm: UnifiedLLMService = Depends(get_llm)):
    try:
        result = await llm.summarize(data.text)
        return SuccessResponse(status="success", result=result)
    except Exception as e:
        return ErrorResponse(status="error", message=str(e))
