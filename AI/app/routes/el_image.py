# # app/routes/el_image.py
# from fastapi import APIRouter, UploadFile, File, HTTPException, Query
# from fastapi.responses import JSONResponse
# from uuid import uuid4
# from typing import List
# from app.core.schemas import PredictionResponse
# from app.core.config import settings
# from app.helpers.aws_s3 import upload_image_to_s3
# from app.helpers.aws_sqs import send_image_to_queue
# from datetime import datetime

# router = APIRouter(prefix="/EL-Image-AI", tags=["EL Image AI"])

# @router.post("",
#     response_model=PredictionResponse,
#     status_code=202,
#     summary="Classify one or multiple EL images",
#     description="Upload one or more EL images for defect/good classification. Supports batch upload."
# )
# async def classify_el_image(
#     files: List[UploadFile] = File(
#         ...,
#         description="One or more EL images (jpg, jpeg, png)"
#     ),
#     threshold: float = Query(
#         default=settings.CONFIDENCE_THRESHOLD_DEFAULT,
#         ge=0.0, le=1.0,
#         description="Confidence threshold (0.0 to 1.0)"
#     )
# ):
#     # Validate number of files
#     if len(files) > settings.MAX_FILES_PER_REQUEST:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Maximum {settings.MAX_FILES_PER_REQUEST} images allowed per request"
#         )

#     if not files:
#         raise HTTPException(
#             status_code=400, 
#             detail="At least one image is required"
#         )

#     job_id = str(uuid4())
#     output_prefix = f"jobs/{job_id}/output/"
#     results = []
#     errors = []

#     for file in files:
#         try:
#             # Validate file type
#             if not file.content_type or not file.content_type.startswith("image/"):
#                 errors.append(f"File {file.filename} is not an image (type: {file.content_type})")
#                 continue

#             # Read file content
#             content = await file.read()
            
#             # Validate file size
#             if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
#                 errors.append(f"File {file.filename} exceeds size limit of {settings.MAX_IMAGE_SIZE_MB}MB")
#                 continue

#             if settings.USE_SQS:
#                 # ASYNC MODE: Upload to S3 and queue for processing
#                 try:
#                     # Upload image to S3
#                     key = upload_image_to_s3(content, file.filename, job_id)
                    
#                     # Send message to SQS
#                     send_image_to_queue(
#                         job_id=job_id,
#                         image_key=key,
#                         filename=file.filename,
#                         output_prefix=output_prefix,
#                         threshold=threshold
#                     )
#                 except Exception as e:
#                     errors.append(f"Failed to queue {file.filename}: {str(e)}")
#             else:
#                 # SYNC MODE: Process directly (no S3/SQS)
#                 try:
#                     from app.core.model import predict_image
                    
#                     # Run inference
#                     prediction, confidence, above_threshold = predict_image(content, threshold)
                    
#                     # Add to results
#                     results.append({
#                         "filename": file.filename,
#                         "prediction": prediction,
#                         "confidence": confidence,
#                         "above_threshold": above_threshold,
#                         "processed_at": datetime.utcnow().isoformat() + "Z"
#                     })
#                 except Exception as e:
#                     errors.append(f"Failed to process {file.filename}: {str(e)}")

#         except Exception as e:
#             errors.append(f"Unexpected error with {file.filename}: {str(e)}")

#     # Determine response status and message
#     successful_files = len(results) if not settings.USE_SQS else (len(files) - len(errors))
    
#     if errors and successful_files == 0:
#         # All files failed
#         status_code = 500
#         status_text = "failed"
#         message = f"All {len(files)} files failed: {', '.join(errors[:3])}"
#         if len(errors) > 3:
#             message += f" and {len(errors)-3} more errors"
#     elif errors and successful_files > 0:
#         # Partial success
#         status_code = 207  # Multi-Status
#         status_text = "partial"
#         message = f"Processed {successful_files}/{len(files)} files. Errors: {', '.join(errors[:3])}"
#         if len(errors) > 3:
#             message += f" and {len(errors)-3} more errors"
#     else:
#         # All successful
#         status_code = 202 if settings.USE_SQS else 200
#         status_text = "queued" if settings.USE_SQS else "completed"
#         message = "Images queued for processing" if settings.USE_SQS else "All images processed successfully"

#     # Prepare response
#     response_content = {
#         "success": len(errors) == 0,
#         "job_id": job_id,
#         "status": status_text,
#         "message": message,
#         "file_count": len(files),
#         "results": results if not settings.USE_SQS else None,
#         "status_check_url": f"/EL-Image-AI/status/{job_id}",
#         "queued_at": datetime.utcnow().isoformat() + "Z"
#     }

#     # Add error information if any
#     if errors:
#         response_content["errors"] = errors[:10]  # Limit to first 10 errors

#     return JSONResponse(
#         status_code=status_code,
#         content=response_content
#     )


# # Optional: Add a simple status endpoint (placeholder for future implementation)
# @router.get("/status/{job_id}", summary="Check job status")
# async def get_job_status(job_id: str):
#     """
#     Get the status of a processing job.
#     Note: This is a placeholder. Full implementation would check a database or S3 for results.
#     """
#     return JSONResponse(
#         status_code=501,  # Not Implemented
#         content={
#             "job_id": job_id,
#             "status": "not_implemented",
#             "message": "Status tracking is not yet implemented. In async mode, check S3 for results at: jobs/{job_id}/output/",
#             "note": "Results are stored as JSON files in S3 with the pattern: jobs/{job_id}/output/{filename}.json"
#         }
#     )


# # Optional: Add a health check endpoint
# @router.get("/health", summary="Health check")
# async def health_check():
#     """
#     Simple health check endpoint to verify the API is running.
#     """
#     from app.core.model import load_model
    
#     try:
#         # Try to load the model (won't actually load if already loaded)
#         load_model()
#         model_status = "loaded"
#     except Exception as e:
#         model_status = f"error: {str(e)}"
    
#     return {
#         "status": "healthy",
#         "mode": "async" if settings.USE_SQS else "sync",
#         "model": model_status,
#         "timestamp": datetime.utcnow().isoformat() + "Z"
#     }




# app/routes/el_image.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
from typing import List
from app.core.schemas import PredictionResponse
from app.core.config import settings
from app.helpers.aws_s3 import upload_image_to_s3
from app.helpers.aws_sqs import send_image_to_queue
from datetime import datetime

router = APIRouter(prefix="/EL-Image-AI", tags=["EL Image AI"])

@router.post("",
    response_model=PredictionResponse,
    status_code=202,
    summary="Classify one or multiple EL images",
    description="Upload one or more EL images for defect/good classification. Uses confidence threshold from configuration."
)
async def classify_el_image(
    files: List[UploadFile] = File(
        ...,
        description="One or more EL images (jpg, jpeg, png)"
    )
    # REMOVED: threshold parameter - now using settings.CONFIDENCE_THRESHOLD_DEFAULT internally
):
    # Get threshold from settings (loaded from .env file)
    threshold = settings.CONFIDENCE_THRESHOLD_DEFAULT
    
    # Validate number of files
    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {settings.MAX_FILES_PER_REQUEST} images allowed per request"
        )

    if not files:
        raise HTTPException(
            status_code=400, 
            detail="At least one image is required"
        )

    job_id = str(uuid4())
    output_prefix = f"jobs/{job_id}/output/"
    results = []
    errors = []

    for file in files:
        try:
            # Validate file type
            if not file.content_type or not file.content_type.startswith("image/"):
                errors.append(f"File {file.filename} is not an image (type: {file.content_type})")
                continue

            # Read file content
            content = await file.read()
            
            # Validate file size
            if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                errors.append(f"File {file.filename} exceeds size limit of {settings.MAX_IMAGE_SIZE_MB}MB")
                continue

            if settings.USE_SQS:
                # ASYNC MODE: Upload to S3 and queue for processing
                try:
                    # Upload image to S3
                    key = upload_image_to_s3(content, file.filename, job_id)
                    
                    # Send message to SQS with threshold from settings
                    send_image_to_queue(
                        job_id=job_id,
                        image_key=key,
                        filename=file.filename,
                        output_prefix=output_prefix,
                        threshold=threshold  # Using settings value
                    )
                except Exception as e:
                    errors.append(f"Failed to queue {file.filename}: {str(e)}")
            else:
                # SYNC MODE: Process directly (no S3/SQS)
                try:
                    from app.core.model import predict_image
                    
                    # Run inference with threshold from settings
                    prediction, confidence, above_threshold = predict_image(content, threshold)
                    
                    # Add to results
                    results.append({
                        "filename": file.filename,
                        "prediction": prediction,
                        "confidence": confidence,
                        "above_threshold": above_threshold,
                        "processed_at": datetime.utcnow().isoformat() + "Z"
                    })
                except Exception as e:
                    errors.append(f"Failed to process {file.filename}: {str(e)}")

        except Exception as e:
            errors.append(f"Unexpected error with {file.filename}: {str(e)}")

    # Determine response status and message
    successful_files = len(results) if not settings.USE_SQS else (len(files) - len(errors))
    
    if errors and successful_files == 0:
        # All files failed
        status_code = 500
        status_text = "failed"
        message = f"All {len(files)} files failed: {', '.join(errors[:3])}"
        if len(errors) > 3:
            message += f" and {len(errors)-3} more errors"
    elif errors and successful_files > 0:
        # Partial success
        status_code = 207  # Multi-Status
        status_text = "partial"
        message = f"Processed {successful_files}/{len(files)} files. Errors: {', '.join(errors[:3])}"
        if len(errors) > 3:
            message += f" and {len(errors)-3} more errors"
    else:
        # All successful
        status_code = 202 if settings.USE_SQS else 200
        status_text = "queued" if settings.USE_SQS else "completed"
        message = "Images queued for processing" if settings.USE_SQS else "All images processed successfully"

    # Prepare response
    response_content = {
        "success": len(errors) == 0,
        "job_id": job_id,
        "status": status_text,
        "message": message,
        "file_count": len(files),
        "results": results if not settings.USE_SQS else None,
        "status_check_url": f"/EL-Image-AI/status/{job_id}",
        "queued_at": datetime.utcnow().isoformat() + "Z",
        "threshold_used": threshold  # Optional: include in response to show what threshold was used
    }

    # Add error information if any
    if errors:
        response_content["errors"] = errors[:10]  # Limit to first 10 errors

    return JSONResponse(
        status_code=status_code,
        content=response_content
    )


# Optional: Add a simple status endpoint (placeholder for future implementation)
@router.get("/status/{job_id}", summary="Check job status")
async def get_job_status(job_id: str):
    """
    Get the status of a processing job.
    Note: This is a placeholder. Full implementation would check a database or S3 for results.
    """
    return JSONResponse(
        status_code=501,  # Not Implemented
        content={
            "job_id": job_id,
            "status": "not_implemented",
            "message": "Status tracking is not yet implemented. In async mode, check S3 for results at: jobs/{job_id}/output/",
            "note": "Results are stored as JSON files in S3 with the pattern: jobs/{job_id}/output/{filename}.json"
        }
    )


# Optional: Add a health check endpoint
@router.get("/health", summary="Health check")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    from app.core.model import load_model
    
    try:
        # Try to load the model (won't actually load if already loaded)
        load_model()
        model_status = "loaded"
    except Exception as e:
        model_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "mode": "async" if settings.USE_SQS else "sync",
        "model": model_status,
        "threshold": settings.CONFIDENCE_THRESHOLD_DEFAULT,  # Show current threshold
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }