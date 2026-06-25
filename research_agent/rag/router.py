
from fastapi import APIRouter
from pydantic import BaseModel
from . import pipeline

router = APIRouter(
    prefix="/rag",
    tags=["rag"]
)

class QuestionRequest(BaseModel):
    run_id: str | int
    question: str

@router.post("/ask")
async def ask(request: QuestionRequest):

    result = await pipeline.answer_question(
        request.run_id,
        request.question
    )

    return result

'''
#Test the rag connection
from fastapi import APIRouter, Request

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/ask")
async def ask(request: Request):

    body = await request.json()

    print("\nBODY RECEIVED:")
    print(body)

    return {"ok": True}
'''