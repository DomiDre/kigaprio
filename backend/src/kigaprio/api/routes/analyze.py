"""Analysis endpoints."""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from kigaprio.config import settings
from kigaprio.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    JobStatus,
)
from kigaprio.services.excel_generator import ExcelGenerator
from kigaprio.services.file_processor import FileProcessor

router = APIRouter()

# In-memory storage for analysis jobs (use Redis in production)
analysis_jobs: dict[str, dict[str, Any]] = {}


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="Start Analysis",
    description="""
    Start background analysis of uploaded files.

    **Process:**
    1. Validates that all file paths exist
    2. Creates a background job with unique ID
    3. Returns job ID for status tracking

    **Analysis includes:**
    - **Images:** Dimensions, format, color information, transparency
    - **PDFs:** Page count, text extraction, metadata
    """,
)
async def start_analysis(
    request: AnalysisRequest, background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """Start analysis of uploaded files."""

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Validate file paths
    valid_paths = []
    for path in request.file_paths:
        if not Path(path).exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        valid_paths.append(path)

    # Initialize job status
    analysis_jobs[job_id] = {
        "status": JobStatus.PROCESSING,
        "files": valid_paths,
        "progress": 0,
        "results": None,
        "error": None,
    }

    # Start background processing
    background_tasks.add_task(process_files, job_id, valid_paths)

    return AnalysisResponse(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        message=f"Started analysis of {len(valid_paths)} files",
    )


@router.get(
    "/analyze/{job_id}/download",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Excel file with analysis results",
        },
        404: {"model": ErrorResponse, "description": "Job not found"},
        400: {"model": ErrorResponse, "description": "Analysis not completed"},
    },
    summary="Download Results",
    description="""
    Download analysis results as an Excel file.

    **Requirements:**
    - Job must be in 'completed' status
    - Results file must exist

    **Excel format:**
    - Multiple sheets with detailed analysis
    - Auto-formatted columns
    - File-type specific data columns
    """,
)
async def download_results(job_id: str):
    """Download analysis results as Excel file."""

    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = analysis_jobs[job_id]

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    if not job["results"]:
        raise HTTPException(status_code=404, detail="Results file not found")

    return FileResponse(
        path=job["results"],
        filename=f"analysis_results_{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


async def process_files(job_id: str, file_paths: list[str]):
    """Background task to process files."""

    try:
        processor = FileProcessor()
        excel_gen = ExcelGenerator()

        results = []
        total_files = len(file_paths)

        for i, file_path in enumerate(file_paths):
            # Update progress
            progress = int((i / total_files) * 100)
            analysis_jobs[job_id]["progress"] = progress

            # Process file
            result = await processor.process_file(file_path)
            results.append(result)

        # Generate Excel file
        output_path = Path(settings.OUTPUT_DIR) / f"results_{job_id}.xlsx"
        output_path.parent.mkdir(exist_ok=True)

        excel_file = excel_gen.generate_report(results, str(output_path))

        # Update job status
        analysis_jobs[job_id].update(
            {"status": JobStatus.COMPLETED, "progress": 100, "results": excel_file}
        )

    except Exception as e:
        analysis_jobs[job_id].update({"status": JobStatus.FAILED, "error": str(e)})
