from pydantic import BaseModel
from typing import List, Tuple


class OCRResult(BaseModel):
    text: str
    confidence: float
    bbox: List[Tuple[int, int]]


class OCRResponse(BaseModel):
    count: int
    results: List[OCRResult]
