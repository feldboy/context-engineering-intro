import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    start_index: int
    end_index: int
    source_pages: List[int]
    chunk_index: int
    token_count: int


class TextChunker:
    """
    Smart text chunking for large documents with legal document awareness.
    """
    
    def __init__(self, max_tokens: int = 4000, overlap_tokens: int = 400):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        
        # Legal document patterns for intelligent chunking
        self.section_patterns = [
            r'^\s*\d+\.\s+',  # Numbered sections
            r'^\s*[A-Z]\.\s+',  # Lettered sections
            r'^\s*WHEREAS\s+',  # Whereas clauses
            r'^\s*NOW\s+THEREFORE\s+',  # Therefore clauses
            r'^\s*PARTIES\s*$',  # Parties section
            r'^\s*BACKGROUND\s*$',  # Background section
            r'^\s*CLAIMS?\s*$',  # Claims section
            r'^\s*COUNT\s+[IVX]+',  # Count sections (I, II, III, etc.)
            r'^\s*PRAYER\s+FOR\s+RELIEF\s*$',  # Prayer for relief
        ]
    
    def chunk_text(self, text: str, max_tokens: Optional[int] = None) -> List[TextChunk]:
        """
        Chunk text into overlapping segments with legal document awareness.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk (uses default if None)
            
        Returns:
            List of TextChunk objects
        """
        max_tokens = max_tokens or self.max_tokens
        
        if not text or not text.strip():
            return []
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(text) // 4
        
        # If text is small enough, return as single chunk
        if estimated_tokens <= max_tokens:
            return [TextChunk(
                text=text,
                start_index=0,
                end_index=len(text),
                source_pages=[1],  # Default to page 1
                chunk_index=0,
                token_count=estimated_tokens
            )]
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        # Create chunks
        chunks = []
        current_chunk = []
        current_tokens = 0
        start_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(sentence) // 4
            
            # If adding this sentence would exceed max tokens, create a chunk
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_index=start_index,
                    end_index=start_index + len(chunk_text),
                    source_pages=[1],  # Default to page 1, mapping to be improved
                    chunk_index=len(chunks),
                    token_count=current_tokens
                ))
                
                # Handle overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk, self.overlap_tokens)
                current_chunk = overlap_sentences
                current_tokens = sum(len(s) // 4 for s in overlap_sentences)
                start_index = start_index + len(chunk_text) - len(' '.join(overlap_sentences))
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add the last chunk if there's content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(TextChunk(
                text=chunk_text,
                start_index=start_index,
                end_index=start_index + len(chunk_text),
                source_pages=[1],  # Default to page 1, mapping to be improved
                chunk_index=len(chunks),
                token_count=current_tokens
            ))
        
        logger.info("Text chunked into %d chunks", len(chunks))
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences with legal document awareness.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Handle legal document patterns first
        sections = self._split_by_legal_sections(text)
        
        sentences = []
        for section in sections:
            # Split each section into sentences
            # Use regex to split on sentence boundaries
            sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
            section_sentences = re.split(sentence_pattern, section)
            
            # Clean up sentences
            section_sentences = [s.strip() for s in section_sentences if s.strip()]
            sentences.extend(section_sentences)
        
        return sentences
    
    def _split_by_legal_sections(self, text: str) -> List[str]:
        """
        Split text by legal document sections.
        
        Args:
            text: Text to split
            
        Returns:
            List of sections
        """
        lines = text.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            is_section_header = any(
                re.match(pattern, line.strip(), re.IGNORECASE) 
                for pattern in self.section_patterns
            )
            
            if is_section_header and current_section:
                # Start new section
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add the last section
        if current_section:
            sections.append('\n'.join(current_section))
        
        return sections
    
    def _get_overlap_sentences(self, sentences: List[str], overlap_tokens: int) -> List[str]:
        """
        Get sentences for overlap from the end of current chunk.
        
        Args:
            sentences: List of sentences
            overlap_tokens: Number of tokens to overlap
            
        Returns:
            List of sentences for overlap
        """
        overlap_sentences = []
        current_tokens = 0
        
        # Work backwards from the end
        for sentence in reversed(sentences):
            sentence_tokens = len(sentence) // 4
            if current_tokens + sentence_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        return overlap_sentences
    
    def find_text_in_chunks(self, chunks: List[TextChunk], search_text: str) -> List[Dict[str, Any]]:
        """
        Find text across chunks and return locations.
        
        Args:
            chunks: List of text chunks
            search_text: Text to search for
            
        Returns:
            List of matches with chunk and position information
        """
        matches = []
        
        for chunk in chunks:
            # Case-insensitive search
            chunk_text_lower = chunk.text.lower()
            search_text_lower = search_text.lower()
            
            start = 0
            while True:
                pos = chunk_text_lower.find(search_text_lower, start)
                if pos == -1:
                    break
                
                matches.append({
                    'chunk_index': chunk.chunk_index,
                    'position': pos,
                    'text': chunk.text[pos:pos + len(search_text)],
                    'context': self._get_context(chunk.text, pos, len(search_text)),
                    'source_pages': chunk.source_pages
                })
                
                start = pos + 1
        
        return matches
    
    def _get_context(self, text: str, pos: int, length: int, context_chars: int = 100) -> str:
        """
        Get context around a text match.
        
        Args:
            text: Full text
            pos: Position of match
            length: Length of match
            context_chars: Number of characters of context on each side
            
        Returns:
            Context string
        """
        start = max(0, pos - context_chars)
        end = min(len(text), pos + length + context_chars)
        
        context = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context
