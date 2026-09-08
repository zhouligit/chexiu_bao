from fastapi import APIRouter, Depends, File, UploadFile

from app.core.response import success
from app.dependencies import CurrentUser, get_current_user
from app.services.ocr_service import OcrService

router = APIRouter(tags=["OCR"])


@router.post("/ocr/plate")
async def recognize_plate(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await OcrService.recognize_plate(file)
    return success(result)
