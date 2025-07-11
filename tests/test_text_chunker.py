import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.tools.text_chunker import TextChunker, TextChunk


class TestTextChunker:
    """Test text chunking functionality."""
    
    @pytest.fixture
    def text_chunker(self):
        """Create text chunker instance."""
        return TextChunker(max_tokens=100, overlap_tokens=20)
    
    def test_chunk_small_text(self, text_chunker):
        """Test chunking of small text that fits in one chunk."""
        text = "This is a small text that should fit in one chunk."
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == len(text)
    
    def test_chunk_large_text(self, text_chunker):
        """Test chunking of large text that needs multiple chunks."""
        # Create a large text that will require multiple chunks
        # With max_tokens=100, we need about 400+ characters 
        sentences = []
        for i in range(20):  # 20 sentences should be enough
            sentences.append(f"This is sentence number {i} with additional padding text." + " " * 10)
        
        text = " ".join(sentences)
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
    
    def test_chunk_with_legal_sections(self, text_chunker):
        """Test chunking with legal document sections."""
        text = """
        1. PARTIES
        
        Plaintiff Jane Doe is an individual residing in California.
        
        2. JURISDICTION AND VENUE
        
        This Court has jurisdiction over this matter.
        
        WHEREAS, the parties agree to the following terms.
        
        NOW THEREFORE, the parties agree as follows.
        
        COUNT I - NEGLIGENCE
        
        Plaintiff incorporates all previous allegations.
        """
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) >= 1
        # Should contain legal patterns
        combined_text = " ".join(chunk.text for chunk in chunks)
        assert "PARTIES" in combined_text
        assert "WHEREAS" in combined_text
        assert "COUNT I" in combined_text
    
    def test_chunk_empty_text(self, text_chunker):
        """Test chunking of empty text."""
        chunks = text_chunker.chunk_text("")
        assert len(chunks) == 0
        
        chunks = text_chunker.chunk_text("   ")
        assert len(chunks) == 0
    
    def test_chunk_overlap(self, text_chunker):
        """Test that chunks have proper overlap."""
        # Create text that will require chunking
        sentences = [f"This is sentence number {i}. " for i in range(20)]
        text = " ".join(sentences)
        
        chunks = text_chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]
                
                # There should be some overlap in the text
                # This is a simplified check
                assert current_chunk.end_index > next_chunk.start_index
    
    def test_split_by_legal_sections(self, text_chunker):
        """Test splitting text by legal document sections."""
        text = """
        Regular text here.
        
        1. FIRST SECTION
        Content of first section.
        
        2. SECOND SECTION
        Content of second section.
        
        WHEREAS, this is a whereas clause.
        
        NOW THEREFORE, this is a therefore clause.
        """
        
        sections = text_chunker._split_by_legal_sections(text)
        
        assert len(sections) > 1
        assert any("FIRST SECTION" in section for section in sections)
        assert any("WHEREAS" in section for section in sections)
    
    def test_split_into_sentences(self, text_chunker):
        """Test splitting text into sentences."""
        text = "This is the first sentence. This is the second sentence! Is this a question?"
        
        sentences = text_chunker._split_into_sentences(text)
        
        assert len(sentences) == 3
        assert "first sentence" in sentences[0]
        assert "second sentence" in sentences[1]
        assert "question" in sentences[2]
    
    def test_get_overlap_sentences(self, text_chunker):
        """Test getting overlap sentences."""
        sentences = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
            "Fourth sentence."
        ]
        
        overlap = text_chunker._get_overlap_sentences(sentences, 50)  # 50 token overlap
        
        assert len(overlap) > 0
        assert len(overlap) <= len(sentences)
        # Should get sentences from the end
        assert overlap[-1] == sentences[-1]
    
    def test_find_text_in_chunks(self, text_chunker):
        """Test finding text across chunks."""
        text = "This document contains a case number CIV-2024-1138 and other information."
        chunks = text_chunker.chunk_text(text)
        
        matches = text_chunker.find_text_in_chunks(chunks, "CIV-2024-1138")
        
        assert len(matches) == 1
        assert matches[0]["text"] == "CIV-2024-1138"
        assert matches[0]["chunk_index"] == 0
        assert "case number" in matches[0]["context"]
    
    def test_find_text_case_insensitive(self, text_chunker):
        """Test case-insensitive text finding."""
        text = "The PLAINTIFF filed a complaint."
        chunks = text_chunker.chunk_text(text)
        
        matches = text_chunker.find_text_in_chunks(chunks, "plaintiff")
        
        assert len(matches) == 1
        assert matches[0]["text"] == "PLAINTIFF"
    
    def test_get_context(self, text_chunker):
        """Test getting context around text match."""
        text = "This is a long document with important information in the middle that we want to extract."
        
        context = text_chunker._get_context(text, 30, 9, context_chars=10)  # "important"
        
        assert "important" in context
        assert len(context) > 9  # Should include context
        assert context.startswith("...") or context.startswith("This")
    
    def test_chunk_with_custom_tokens(self, text_chunker):
        """Test chunking with custom token limits."""
        text = "This is a test. " * 50  # Create text that will need chunking
        
        chunks = text_chunker.chunk_text(text, max_tokens=50)
        
        if len(chunks) > 1:
            # Each chunk should be approximately within the token limit
            for chunk in chunks:
                assert chunk.token_count <= 50
    
    def test_chunk_token_estimation(self, text_chunker):
        """Test token count estimation."""
        text = "This is a test sentence."
        estimated_tokens = len(text) // 4  # Rough estimation used in code
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].token_count == estimated_tokens
    
    def test_chunk_maintains_page_mapping(self, text_chunker):
        """Test that chunks maintain source page information."""
        text = "Sample text content."
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].source_pages == [1]  # Default to page 1
    
    def test_chunk_with_special_characters(self, text_chunker):
        """Test chunking text with special characters."""
        text = "This text has special characters: @#$%^&*()_+{}[]|\\:;\"'<>?,./"
        
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
    
    def test_chunk_preserves_legal_formatting(self, text_chunker):
        """Test that legal document formatting is preserved."""
        text = """
        SUPERIOR COURT OF CALIFORNIA
        COUNTY OF LOS ANGELES
        
        Case No. BC123456
        
        JANE DOE,
                    Plaintiff,
        v.
        
        JOHN SMITH,
                    Defendant.
        """
        
        chunks = text_chunker.chunk_text(text)
        
        # Should preserve the formatting
        combined_text = " ".join(chunk.text for chunk in chunks)
        assert "SUPERIOR COURT" in combined_text
        assert "Case No." in combined_text
        assert "Plaintiff" in combined_text
        assert "Defendant" in combined_text
