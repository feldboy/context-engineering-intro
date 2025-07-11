## FEATURE:

AI-Powered Document Analysis Agent: PDF to Structured Data Extraction
This feature involves the development of a core AI agent, the DocAnalysisAgent, within the Pre-Settlement Funding CRM. Its primary function is to read uploaded PDF legal documents (e.g., Civil Complaints, Retainer Agreements), and based on a user-provided example format (a target JSON schema), accurately extract the required information and populate the schema. This will automate a significant portion of the data entry for the "Case Information Gathering & Verification" workflow stage. Accuracy and verifiability are the highest priorities.
## EXAMPLES:

This section is crucial to demonstrate the required input-to-output transformation. The system will take two inputs: the raw PDF document and a target "example" template. It must produce a filled-out JSON object that includes not only the extracted data but also metadata to support verification.
Input 1: Source Document (Hypothetical PDF named complaint_doe_v_acme.pdf)
Let's assume the PDF contains the following text on its first page:
SUPERIOR COURT OF CALIFORNIA, COUNTY OF SAN MATEO
Case Number: CIV-2024-1138
Filed: April 15, 2024
Jane Doe, an individual,
Plaintiff,
vs.
Acme Corporation, a Delaware corporation; and John Smith, an individual,
Defendants.
COMPLAINT FOR DAMAGES (Personal Injury - Motor Vehicle)
Plaintiff Jane Doe alleges the following based on the incident occurring on or about January 5, 2024...
Input 2: Example Template (The target JSON schema to be filled)
Generated json
{
  "case_number": null,
  "court_name": null,
  "filing_date": null,
  "plaintiff_name": null,
  "defendant_names": [],
  "case_type": null
}
Use code with caution.
Json
Generated Output (The desired result from the AI Agent)
The agent's output must be more than just the filled JSON. To meet the accuracy requirement, it must include the source text and a confidence score for each extracted field, allowing for human verification.
Generated json
{
  "extracted_data": {
    "case_number": {
      "value": "CIV-2024-1138",
      "source_text": "Case Number: CIV-2024-1138",
      "confidence_score": 0.99
    },
    "court_name": {
      "value": "Superior Court of California, County of San Mateo",
      "source_text": "SUPERIOR COURT OF CALIFORNIA, COUNTY OF SAN MATEO",
      "confidence_score": 0.98
    },
    "filing_date": {
      "value": "2024-04-15",
      "source_text": "Filed: April 15, 2024",
      "confidence_score": 0.99
    },
    "plaintiff_name": {
      "value": "Jane Doe",
      "source_text": "Jane Doe, an individual,\nPlaintiff,",
      "confidence_score": 0.95
    },
    "defendant_names": {
      "value": [
        "Acme Corporation",
        "John Smith"
      ],
      "source_text": "Acme Corporation, a Delaware corporation; and John Smith, an individual,\nDefendants.",
      "confidence_score": 0.96
    },
    "case_type": {
      "value": "Personal Injury - Motor Vehicle",
      "source_text": "COMPLAINT FOR DAMAGES (Personal Injury - Motor Vehicle)",
      "confidence_score": 0.97
    }
  },
  "processing_errors": [],
  "raw_text_md5": "a1b2c3d4e5f6..."
}

## DOCUMENTATION:

Internal Documentation (from our Master Plan):
[🧬 03-DATA-MODEL-SPECIFICATIONS.md]: The extracted data must align with the fields defined for the Plaintiffs and Cases collections in our MongoDB schema.
[🤖 05-AI-PROMPT-ENGINEERING-GUIDE.md]: The prompt strategies developed for this feature will be the cornerstone of this guide.
[🔌 04-SYSTEM-ARCHITECTURE.md]: This agent will be a core service within the backend/agents/ directory, triggered by an API endpoint in backend/api/ai_agents.py.
[🔒 09-SECURITY-COMPLIANCE-PLAN.md]: All data handling must comply with the policies for PII and sensitive case information.
External Documentation & Libraries:
PDF Text Extraction:
PyMuPDF (fitz) Docs: For extracting text, images, and metadata from text-based PDFs. This should be the first-pass tool.
Optical Character Recognition (OCR) for Scanned PDFs:
pytesseract Docs: A Python wrapper for Google's Tesseract-OCR Engine. This is the fallback for image-based PDFs.
Google Cloud Vision AI - Document AI: A more powerful, cloud-based alternative for higher accuracy OCR if needed.
LLM API for Extraction & Structuring:
deepseek API Documentation: Specifically, sections on "JSON Mode" for forcing structured output and the latest model capabilities (e.g., )
google gemini API Documentation: Specifically, sections on "JSON Mode" for forcing structured output and the latest model capabilities (e.g., )
anthropic API Documentation: Specifically, sections on "JSON Mode" for forcing structured output and the latest model capabilities (e.g., )


## OTHER CONSIDERATIONS:

The Two-PDF Problem (Text vs. Image): The implementation must handle both text-based and image-based (scanned) PDFs. The standard workflow should be:
Attempt to extract text directly using a library like PyMuPDF.
If the extracted text is minimal or gibberish, flag the PDF as likely scanned.
Run the PDF through an OCR process (e.g., pytesseract or a cloud vision API) to convert the images of pages into text.
Proceed with the extracted text from either step 1 or 3.
Human-in-the-Loop (HITL) is Non-Negotiable: Given the legal context, no data should be committed to the CRM without human verification. The UI for verification is as important as the extraction itself. It should display:
A side-by-side view of the PDF document and the form with the extracted data.
When a user clicks on a form field, it should highlight the source_text within the PDF view.
Fields with a confidence_score below a certain threshold (e.g., 0.90) must be visually flagged for mandatory review.
Advanced Prompt Engineering is Key: The prompt sent to the LLM is critical for accuracy. It should be structured meticulously:
Role-Playing: "You are an expert paralegal specializing in personal injury cases. Your task is to extract specific information from a legal document with extreme accuracy."
Context & Goal: "You will be given text from a legal document and a JSON schema. Your goal is to populate the JSON schema with information found only in the provided text. Do not infer or add information that is not present."
The Schema and Instructions: "Fill out the following JSON object. For each field, provide the extracted 'value', the exact 'source_text' from the document that justifies the value, and a 'confidence_score' from 0.0 to 1.0. If a value cannot be found, return null for 'value' and 'source_text' and a score of 0.0."
Provide the Target Schema (as a string) and the Document Text.
Handling Large Documents (Chunking): Legal documents can exceed an LLM's context window. The agent must implement a "chunking" strategy.
Break the document text into smaller, overlapping chunks (e.g., 4000 tokens each, with a 400-token overlap).
Process each chunk individually to find the required information.
Synthesize the results from all chunks, resolving duplicates and choosing the extraction with the highest confidence score.
Cost and Performance Management: LLM and OCR API calls can be expensive and slow.
For initial case intake, consider processing only the first 5-10 pages of a document, as this is where key information (parties, case number) usually resides.
Allow for a "full document processing" option that can be triggered manually by the user for deeper analysis.
Cache results. If the same document is uploaded again, return the previously processed data (based on a hash of the file).
Error Handling and "Not Found" Cases: The agent must be robust. If a field like "Case Number" is genuinely not in the document, it must not hallucinate a value. The null value in the output schema is critical for this. The system should handle this gracefully, not as an error, but as a valid result.
52.0s
