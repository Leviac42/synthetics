"""Pydantic models for API"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class MonitorCreate(BaseModel):
    """Model for creating a monitor"""
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    schedule_cron: str = Field(..., description="Cron expression, e.g., '*/5 * * * *'")
    enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)


class MonitorUpdate(BaseModel):
    """Model for updating a monitor"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    schedule_cron: Optional[str] = None
    enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    tags: Optional[Dict[str, str]] = None


class MonitorResponse(BaseModel):
    """Model for monitor response"""
    id: int
    name: str
    url: str
    schedule_cron: str
    enabled: bool
    timeout_seconds: int
    tags: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExecutionLogResponse(BaseModel):
    """Model for execution log response"""
    id: int
    monitor_id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    ttfb_ms: Optional[float]
    dom_content_loaded_ms: Optional[float]
    page_load_time_ms: Optional[float]
    har_data: Optional[Dict[str, Any]]


class ExecuteNowRequest(BaseModel):
    """Model for execute now request"""
    monitor_id: int
