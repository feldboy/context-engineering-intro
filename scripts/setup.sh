#!/bin/bash

# Document Analysis Agent Setup Script
# This script sets up the complete development environment

set -e

echo "🚀 Setting up Document Analysis Agent..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Check if Python 3.11+ is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Install system dependencies
install_system_deps() {
    print_info "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y \
            poppler-utils \
            tesseract-ocr \
            tesseract-ocr-eng \
            libgl1-mesa-glx \
            libglib2.0-0 \
            curl \
            git
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install poppler tesseract
        else
            print_warning "Homebrew not found. Please install manually:"
            print_info "  - Poppler: https://poppler.freedesktop.org/"
            print_info "  - Tesseract: https://tesseract-ocr.github.io/"
        fi
    else
        print_warning "Unsupported OS. Please install manually:"
        print_info "  - Poppler (for PDF processing)"
        print_info "  - Tesseract (for OCR)"
    fi
}

# Create virtual environment
create_venv() {
    print_info "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
}

# Activate virtual environment
activate_venv() {
    print_info "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_error "requirements.txt not found"
        return 1
    fi
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p uploads cache logs credentials
    touch credentials/.gitkeep
    
    print_success "Directories created"
}

# Setup environment variables
setup_env() {
    print_info "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Environment file created from template"
            print_warning "Please edit .env file with your API keys"
        else
            print_error ".env.example not found"
            return 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Install Node.js dependencies (if frontend exists)
install_frontend_deps() {
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        print_info "Installing frontend dependencies..."
        
        if command -v npm &> /dev/null; then
            cd frontend
            npm install
            cd ..
            print_success "Frontend dependencies installed"
        else
            print_warning "npm not found. Please install Node.js to set up frontend"
        fi
    else
        print_info "No frontend package.json found, skipping frontend setup"
    fi
}

# Run tests
run_tests() {
    print_info "Running tests..."
    
    if command -v pytest &> /dev/null; then
        pytest tests/ -v
        print_success "Tests completed"
    else
        print_warning "pytest not found, skipping tests"
    fi
}

# Setup database (if using Docker)
setup_database() {
    if [ -f "docker-compose.yml" ]; then
        print_info "Setting up database with Docker..."
        
        if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
            if command -v docker-compose &> /dev/null; then
                docker-compose up -d redis mongodb
            else
                docker compose up -d redis mongodb
            fi
            print_success "Database services started"
        else
            print_warning "Docker not found, skipping database setup"
        fi
    fi
}

# Main setup function
main() {
    echo "🔧 Document Analysis Agent Setup"
    echo "=================================="
    
    # Check prerequisites
    if ! check_python; then
        print_error "Python 3.11+ is required"
        exit 1
    fi
    
    # Install system dependencies
    install_system_deps
    
    # Create and activate virtual environment
    create_venv
    activate_venv
    
    # Install Python dependencies
    install_python_deps
    
    # Create directories
    create_directories
    
    # Setup environment
    setup_env
    
    # Install frontend dependencies
    install_frontend_deps
    
    # Setup database
    setup_database
    
    # Run tests
    run_tests
    
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "1. Edit .env file with your API keys"
    echo "2. Run: source venv/bin/activate"
    echo "3. Start the server: python main.py"
    echo "4. Visit: http://localhost:8000"
    echo ""
    echo "📚 Documentation:"
    echo "- API docs: http://localhost:8000/docs"
    echo "- README: ./README.md"
    echo ""
}

# Run main function
main "$@"
