import base64
import re
from io import BytesIO

import httpx
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import BadRequestError

PLATE_PATTERN = re.compile(
    r"^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领"
    r"A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]$"
)


class OcrService:
    @staticmethod
    async def recognize_plate(file: UploadFile) -> dict:
        content = await file.read()
        if not content:
            raise BadRequestError("请上传图片")
        if len(content) > 5 * 1024 * 1024:
            raise BadRequestError("图片大小不能超过 5MB")

        settings = get_settings()
        if settings.baidu_ocr_api_key and settings.baidu_ocr_secret_key:
            plate = await OcrService._baidu_plate(content, settings)
            if plate:
                return {"plate_number": plate, "source": "baidu"}

        plate = OcrService._hyperlpr_plate(content)
        if plate:
            return {"plate_number": plate, "source": "hyperlpr"}

        raise BadRequestError("未能识别车牌，请手动输入或更换清晰图片")

    @staticmethod
    def _normalize_plate(text: str) -> str | None:
        cleaned = text.strip().upper().replace(" ", "").replace("·", "")
        if PLATE_PATTERN.match(cleaned):
            return cleaned
        return None

    @staticmethod
    def _hyperlpr_plate(content: bytes) -> str | None:
        try:
            import numpy as np
            from hyperlpr3 import LicensePlateCatcher
        except ImportError:
            return None

        try:
            from PIL import Image

            image = Image.open(BytesIO(content)).convert("RGB")
            catcher = LicensePlateCatcher()
            results = catcher(np.array(image))
            for item in results or []:
                if isinstance(item, (list, tuple)) and item:
                    plate = OcrService._normalize_plate(str(item[0]))
                    if plate:
                        return plate
                elif isinstance(item, dict):
                    plate = OcrService._normalize_plate(str(item.get("plate", "")))
                    if plate:
                        return plate
        except Exception:
            return None
        return None

    @staticmethod
    async def _baidu_plate(content: bytes, settings) -> str | None:
        token = await OcrService._baidu_token(settings.baidu_ocr_api_key, settings.baidu_ocr_secret_key)
        if not token:
            return None

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://aip.baidubce.com/rest/2.0/ocr/v1/license_plate",
                params={"access_token": token},
                data={"image": base64.b64encode(content).decode()},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = response.json()
            words = data.get("words_result", {}).get("number")
            if words:
                return OcrService._normalize_plate(words)
        return None

    @staticmethod
    async def _baidu_token(api_key: str, secret_key: str) -> str | None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": api_key,
                    "client_secret": secret_key,
                },
            )
            data = response.json()
            return data.get("access_token")
