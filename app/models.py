from pydantic import BaseModel, Field, field_validator


class ScanRequest(BaseModel):
    barcode: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)

    @field_validator("barcode")
    @classmethod
    def barcode_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("barcode must not be blank")
        return value


class ScanResponse(BaseModel):
    status: str
    barcode: str
    received_at: str


class HealthResponse(BaseModel):
    status: str
