from fastapi import APIRouter, Depends, File, UploadFile

from app.core.response import success
from app.dependencies import CurrentUser, get_current_user
from app.services.upload_service import UploadService

router = APIRouter(tags=["文件上传"])


@router.post("/uploads")
async def upload_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    url = await UploadService.save_image(file, current_user.store_id)
    return success({"url": url})
