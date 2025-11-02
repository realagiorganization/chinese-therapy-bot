from fastapi import APIRouter, Depends

from app.api.deps import get_response_evaluator
from app.schemas.evaluation import ResponseEvaluationRequest, ResponseEvaluationResponse
from app.services.evaluation import ResponseEvaluator


router = APIRouter()


@router.post(
    "/response",
    response_model=ResponseEvaluationResponse,
    summary="Evaluate an assistant response for quality and guardrail compliance.",
)
async def evaluate_response(
    payload: ResponseEvaluationRequest,
    evaluator: ResponseEvaluator = Depends(get_response_evaluator),
) -> ResponseEvaluationResponse:
    result = evaluator.evaluate(payload)
    return ResponseEvaluationResponse(result=result)
