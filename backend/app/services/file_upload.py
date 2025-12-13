"""
File Upload Service

Service for handling file uploads (images, documents).
Currently stores locally. Can be extended to use S3/MinIO.
"""

import os
import uuid
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import UploadFile, HTTPException, status


class FileUploadService:
    """Service for file upload operations"""
    
    # Allowed file extensions
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv'}
    
    # Max file sizes (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, upload_dir: str = "uploads"):
        """
        Initialize file upload service
        
        Args:
            upload_dir: Base directory for uploads
        """
        self.upload_dir = Path(upload_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create upload directories if they don't exist"""
        subdirs = ['products', 'brands', 'categories', 'temp']
        for subdir in subdirs:
            path = self.upload_dir / subdir
            path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        return Path(filename).suffix.lower()
    
    @staticmethod
    def _generate_unique_filename(original_filename: str) -> str:
        """
        Generate a unique filename
        
        Args:
            original_filename: Original uploaded filename
            
        Returns:
            Unique filename with timestamp and UUID
        """
        ext = Path(original_filename).suffix.lower()
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}{ext}"
    
    def validate_image(self, file: UploadFile) -> None:
        """
        Validate image file
        
        Args:
            file: Uploaded file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check extension
        ext = self._get_file_extension(file.filename or "")
        if ext not in self.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Note: Size check should be done after reading the file
        # This is just a placeholder for the validation method
    
    def validate_document(self, file: UploadFile) -> None:
        """
        Validate document file
        
        Args:
            file: Uploaded file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check extension
        ext = self._get_file_extension(file.filename or "")
        if ext not in self.ALLOWED_DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_DOCUMENT_EXTENSIONS)}"
            )
    
    async def upload_product_image(
        self,
        file: UploadFile,
        product_id: Optional[str] = None
    ) -> dict:
        """
        Upload a product image
        
        Args:
            file: Uploaded image file
            product_id: Optional product ID for organizing files
            
        Returns:
            Dict with filename and URL
        """
        # Validate file
        self.validate_image(file)
        
        # Read file content
        content = await file.read()
        
        # Check size
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename or "image.jpg")
        
        # Determine save path
        if product_id:
            save_dir = self.upload_dir / "products" / product_id
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.upload_dir / "products"
        
        file_path = save_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Generate URL (relative path)
        relative_path = file_path.relative_to(self.upload_dir)
        url = f"/uploads/{relative_path}"
        
        return {
            "filename": unique_filename,
            "url": url,
            "size": len(content),
            "content_type": file.content_type
        }
    
    async def upload_brand_logo(self, file: UploadFile) -> dict:
        """Upload a brand logo image"""
        self.validate_image(file)
        
        content = await file.read()
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        unique_filename = self._generate_unique_filename(file.filename or "logo.jpg")
        file_path = self.upload_dir / "brands" / unique_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        relative_path = file_path.relative_to(self.upload_dir)
        url = f"/uploads/{relative_path}"
        
        return {
            "filename": unique_filename,
            "url": url,
            "size": len(content),
            "content_type": file.content_type
        }
    
    async def upload_category_image(self, file: UploadFile) -> dict:
        """Upload a category image"""
        self.validate_image(file)
        
        content = await file.read()
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        unique_filename = self._generate_unique_filename(file.filename or "category.jpg")
        file_path = self.upload_dir / "categories" / unique_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        relative_path = file_path.relative_to(self.upload_dir)
        url = f"/uploads/{relative_path}"
        
        return {
            "filename": unique_filename,
            "url": url,
            "size": len(content),
            "content_type": file.content_type
        }
    
    async def upload_multiple_images(
        self,
        files: List[UploadFile],
        product_id: Optional[str] = None
    ) -> List[dict]:
        """
        Upload multiple images
        
        Args:
            files: List of uploaded files
            product_id: Optional product ID
            
        Returns:
            List of upload results
        """
        results = []
        for file in files:
            try:
                result = await self.upload_product_image(file, product_id)
                results.append(result)
            except HTTPException as e:
                results.append({
                    "filename": file.filename,
                    "error": e.detail
                })
        
        return results
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file
        
        Args:
            file_path: Relative path to file
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get file information
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Dict with file info or None if not found
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                stat = full_path.stat()
                return {
                    "filename": full_path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime)
                }
            return None
        except Exception:
            return None


# TODO: Implement S3/MinIO integration
class S3UploadService:
    """
    Service for uploading files to S3/MinIO
    
    This is a placeholder for future implementation.
    """
    
    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None):
        """
        Initialize S3 upload service
        
        Args:
            bucket_name: S3 bucket name
            endpoint_url: Optional endpoint URL (for MinIO)
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        # TODO: Initialize boto3 client
    
    async def upload_file(self, file: UploadFile, key: str) -> str:
        """Upload file to S3 and return URL"""
        # TODO: Implement S3 upload
        raise NotImplementedError("S3 upload not yet implemented")
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        # TODO: Implement S3 delete
        raise NotImplementedError("S3 delete not yet implemented")
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for file access"""
        # TODO: Implement presigned URL generation
        raise NotImplementedError("Presigned URL not yet implemented")
