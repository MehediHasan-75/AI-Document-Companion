"""
File Controller Module
----------------------

Handles orchestration of file operations and returns only doc_id.
"""

from fastapi import UploadFile, HTTPException, status
from typing import List, Dict

from src.services.file_service import file_service

class FileController:
    """
    Controller for managing file uploads and deletions.
    """

    def __init__(self):
        self.service = file_service

    # --------------------------------------------------------------------------
    def upload_file(self, file: UploadFile) -> Dict[str, str]:
        """
        Handle single file upload.

        Returns:
            dict: { "doc_id": str }
        """
        try:
            doc_id = self.service.save_upload(file)
            return {"doc_id": doc_id}
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during upload: {str(e)}"
            )

    # --------------------------------------------------------------------------
    def upload_multiple_files(self, files: List[UploadFile]) -> List[Dict[str, str]]:
        """
        Handle multiple file uploads.

        Returns:
            list of dicts with doc_id only
        """
        results = []
        for file in files:
            try:
                results.append(self.upload_file(file))
            except HTTPException as e:
                results.append({"file": file.filename, "error": e.detail})
        return results

    # --------------------------------------------------------------------------
    def delete_file(self, doc_id: str) -> None:
        """
        Delete a file using its doc_id.
        """
        self.service.delete_file(doc_id)

# Singleton instance
file_controller = FileController()