import hashlib
from typing import Union, Any
import logging

logger = logging.getLogger(__name__)


class HashUtils:
    """Utility functions for hashing."""
    
    @staticmethod
    def generate_hash(data: Union[str, bytes], algorithm: str = "md5") -> str:
        """
        Generate hash of data.
        
        Args:
            data: Data to hash (string or bytes)
            algorithm: Hash algorithm to use
            
        Returns:
            Hex digest of the hash
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def generate_cache_key(*args: Any, separator: str = "|") -> str:
        """
        Generate a cache key from multiple arguments.
        
        Args:
            *args: Arguments to include in the key
            separator: Separator between arguments
            
        Returns:
            MD5 hash of the combined arguments
        """
        # Convert all arguments to strings
        key_parts = [str(arg) for arg in args]
        
        # Join with separator
        key_string = separator.join(key_parts)
        
        # Generate MD5 hash
        return HashUtils.generate_hash(key_string, "md5")
    
    @staticmethod
    def verify_hash(data: Union[str, bytes], expected_hash: str, algorithm: str = "md5") -> bool:
        """
        Verify data against expected hash.
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm to use
            
        Returns:
            True if hash matches
        """
        actual_hash = HashUtils.generate_hash(data, algorithm)
        return actual_hash.lower() == expected_hash.lower()
    
    @staticmethod
    def get_text_hash(text: str) -> str:
        """
        Get MD5 hash of text content.
        
        Args:
            text: Text content to hash
            
        Returns:
            MD5 hash of the text
        """
        return HashUtils.generate_hash(text, "md5")
    
    @staticmethod
    def get_document_fingerprint(
        document_id: str, 
        schema_name: str, 
        process_full_document: bool = False,
        confidence_threshold: float = 0.9
    ) -> str:
        """
        Generate a fingerprint for document processing parameters.
        
        Args:
            document_id: Document identifier
            schema_name: Schema name
            process_full_document: Whether to process full document
            confidence_threshold: Confidence threshold
            
        Returns:
            MD5 hash fingerprint
        """
        return HashUtils.generate_cache_key(
            document_id,
            schema_name,
            process_full_document,
            confidence_threshold
        )
