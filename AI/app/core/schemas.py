# app/core/schemas.py
"""
Pydantic schemas / models for the EL Image AI API
Used for request validation, response formatting, and OpenAPI documentation
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import datetime


class PredictionSingleResult(BaseModel):
    """
    Result for one image in a request (sync or async mode)
    """
    filename: str = Field(..., description="Original filename of the uploaded image")
    prediction: Literal["good", "defect"] = Field(..., description="Classification result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score (0.0–1.0)")
    above_threshold: bool = Field(..., description="Whether confidence meets or exceeds the threshold")
    processed_at: Optional[datetime] = Field(None, description="When the prediction was made")


class PredictionRequest(BaseModel):
    """
    Optional JSON body fields (currently most data comes via multipart form)
    Can be extended later for more complex requests
    """
    confidence_threshold: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for considering a prediction reliable (0.0–1.0)"
    )
    callback_url: Optional[HttpUrl] = Field(
        None,
        description="Optional webhook URL to notify when processing is complete"
    )


class PredictionResponse(BaseModel):
    """
    Main response from POST /EL-Image-AI
    """
    success: bool = Field(..., description="Whether the request was accepted/processed")
    job_id: str = Field(..., description="Unique identifier for this upload batch/job")
    status: Literal["queued", "completed", "failed", "partial"] = Field(
        ..., description="Current status of the job"
    )
    message: str = Field(..., description="Human-readable status message")
    file_count: int = Field(..., ge=0, description="Number of images received")
    results: Optional[List[PredictionSingleResult]] = Field(
        None,
        description="Prediction results (only present in synchronous mode)"
    )
    status_check_url: str = Field(
        ...,
        description="Endpoint to poll for job status/results (e.g. /EL-Image-AI/status/{job_id})"
    )
    queued_at: datetime = Field(..., description="When the request was queued/accepted")


class JobStatusResponse(BaseModel):
    """
    Response from GET /EL-Image-AI/status/{job_id}
    (to be implemented later)
    """
    job_id: str
    status: Literal["queued", "processing", "completed", "failed", "partial"]
    total_files: int
    processed_files: int
    results: Optional[List[PredictionSingleResult]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None