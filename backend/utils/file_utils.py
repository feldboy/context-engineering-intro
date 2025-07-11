import os
import hashlib
import aiofiles
from typing import Optional, List
from pathlib import Path
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class FileUtils:
    """Utility functions for file handling."""
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = "md5") -> str:
        """
        Generate hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            Hex digest of the file hash
        """
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    async def get_file_hash_async(file_path: str, algorithm: str = "md5") -> str:
        """
        Generate hash of a file asynchronously.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            Hex digest of the file hash
        """
        hash_obj = hashlib.new(algorithm)
        
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def validate_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
        """
        Validate file type by extension.
        
        Args:
            file_path: Path to the file
            allowed_extensions: List of allowed extensions (without dots)
            
        Returns:
            True if file type is allowed
        """
        file_extension = Path(file_path).suffix.lower().lstrip('.')
        return file_extension in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
        """
        return Path(file_path).stat().st_size
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> None:
        """
        Ensure directory exists, create if it doesn't.
        
        Args:
            directory_path: Path to the directory
        """
        Path(directory_path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Create a safe filename by removing/replacing unsafe characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        safe_name = safe_name.strip('. ')
        
        # Ensure filename is not empty
        if not safe_name:
            safe_name = "unnamed_file"
        
        return safe_name
    
    @staticmethod
    def get_storage_path(document_id: str) -> Path:
        """
        Get the storage path for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Path to the document in storage
        """
        return Path(settings.pdf_storage_dir) / document_id
    
    @staticmethod
    def cleanup_old_files(directory: str, max_age_days: int = 30) -> int:
        """
        Clean up old files in a directory.
        
        Args:
            directory: Directory to clean
            max_age_days: Maximum age in days before deletion
            
        Returns:
            Number of files deleted
        """
        import time
        
        directory_path = Path(directory)
        if not directory_path.exists():
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        deleted_count = 0
        
        for file_path in directory_path.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info("Deleted old file: %s", file_path.name)
                    except Exception as e:
                        logger.warning("Failed to delete old file %s: %s", file_path.name, str(e))
        
        return deleted_count
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get comprehensive file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = path.stat()
        
        return {
            "name": path.name,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "extension": path.suffix.lower().lstrip('.'),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "absolute_path": str(path.absolute())
        }
