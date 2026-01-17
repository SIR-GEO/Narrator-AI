"""
Simple script to create a downloadable zip of voice embeddings.
Access at: https://your-space.hf.space/download-embeddings
"""

import os
import zipfile
from io import BytesIO
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/download-embeddings")
async def download_embeddings():
    """Create and download a zip file of all voice embeddings"""
    
    embeddings_dir = "voice_embeddings"
    
    if not os.path.exists(embeddings_dir):
        return {"error": "No embeddings found. Run setup first."}
    
    # Create zip file in memory
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(embeddings_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=os.path.dirname(embeddings_dir))
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=voice_embeddings.zip"}
    )

