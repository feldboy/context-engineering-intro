"""
Create sample Q&A PDFs for testing the document analysis agent
"""
import asyncio
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def create_sample_questions_pdf():
    """Create a sample questions PDF for testing"""
    filename = "uploads/sample_questions.pdf"
    
    # Ensure uploads directory exists
    Path("uploads").mkdir(exist_ok=True)
    
    # Create a simple PDF with questions
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "LEGAL EXAMINATION QUESTIONS")
    
    # Questions
    c.setFont("Helvetica", 12)
    y = height - 150
    questions = [
        "Question 1: What is the case number for this civil complaint?",
        "",
        "Question 2: Who is the plaintiff in this case?",
        "",
        "Question 3: What is the name of the defendant?",
        "",
        "Question 4: In which court is this case being filed?",
        "",
        "Question 5: What is the amount of damages being sought?",
        "",
        "Question 6: What was the date of the original contract?",
        "",
        "Question 7: What is the attorney's state bar number?",
        "",
        "Question 8: What county is this case filed in?",
        "",
        "Question 9: What type of legal action is this?",
        "",
        "Question 10: What was the scheduled delivery date mentioned in the contract?",
    ]
    
    for line in questions:
        c.drawString(100, y, line)
        y -= 20
        if y < 100:  # Start new page if needed
            c.showPage()
            y = height - 100
    
    c.save()
    print(f"Created questions document: {filename}")
    return filename

def create_sample_answers_pdf():
    """Create a sample answers PDF for testing"""
    filename = "uploads/sample_answers.pdf"
    
    # Ensure uploads directory exists
    Path("uploads").mkdir(exist_ok=True)
    
    # Create a simple PDF with answers
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "LEGAL EXAMINATION ANSWERS")
    
    # Answers
    c.setFont("Helvetica", 12)
    y = height - 150
    answers = [
        "Answer 1: The case number is CIV-2024-123456",
        "",
        "Answer 2: The plaintiff is John Smith",
        "",
        "Answer 3: The defendant is ABC Corporation",
        "",
        "Answer 4: The case is filed in Superior Court of California",
        "",
        "Answer 5: The damages sought are $50,000 plus costs and attorney fees",
        "",
        "Answer 6: The contract was signed on March 15, 2024",
        "",
        "Answer 7: The attorney's state bar number is 123456",
        "",
        "Answer 8: The case is filed in Los Angeles County",
        "",
        "Answer 9: This is a breach of contract action",
        "",
        "Answer 10: The scheduled delivery date was April 30, 2024",
    ]
    
    for line in answers:
        c.drawString(100, y, line)
        y -= 20
        if y < 100:  # Start new page if needed
            c.showPage()
            y = height - 100
    
    c.save()
    print(f"Created answers document: {filename}")
    return filename

if __name__ == "__main__":
    print("🚀 Creating Sample Q&A PDFs for Testing")
    print("=" * 50)
    
    # Create sample documents
    questions_pdf = create_sample_questions_pdf()
    answers_pdf = create_sample_answers_pdf()
    
    print("\n✅ Sample documents created successfully!")
    print(f"📄 Questions PDF: {questions_pdf}")
    print(f"📄 Answers PDF: {answers_pdf}")
    print("\nYou can now upload these PDFs to the frontend to test the Q&A matching functionality.")
