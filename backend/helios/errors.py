from fastapi import HTTPException
from fastapi.responses import JSONResponse


class HeliosError(HTTPException):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status, detail={"code": code, "message": message, "details": details or {}})
        self.code = code
        self.message = message
        self.details = details or {}


def helios_error_handler(_request, exc: HeliosError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
