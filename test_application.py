#!/usr/bin/env python3
"""
Test script to verify both backend and frontend are working correctly
"""
import requests
import time
import json

def test_backend():
    """Test backend API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🔧 Testing Backend API...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health endpoint: Working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health endpoint: Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint: Error - {e}")
        return False
    
    # Test documents endpoint
    try:
        response = requests.get(f"{base_url}/api/documents")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Documents endpoint: Working")
            print(f"   Found {data.get('total_count', 0)} documents")
        else:
            print(f"❌ Documents endpoint: Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Documents endpoint: Error - {e}")
        return False
    
    return True

def test_frontend():
    """Test frontend accessibility"""
    frontend_url = "http://localhost:3000"
    
    print("\n🎨 Testing Frontend...")
    
    try:
        response = requests.get(frontend_url)
        if response.status_code == 200:
            if "Document Analysis Agent" in response.text:
                print("✅ Frontend: Loading correctly")
                print("   Title found in HTML")
            else:
                print("✅ Frontend: Accessible but title not found")
                print("   This is normal for React apps that load content dynamically")
        else:
            print(f"❌ Frontend: Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend: Error - {e}")
        return False
    
    return True

def test_file_upload():
    """Test file upload functionality"""
    base_url = "http://localhost:8000"
    
    print("\n📄 Testing File Upload...")
    
    # Test with a sample file if it exists
    sample_files = [
        "uploads/sample_questions.pdf",
        "uploads/sample_legal_complaint.pdf"
    ]
    
    for sample_file in sample_files:
        try:
            with open(sample_file, 'rb') as f:
                files = {'file': f}
                data = {
                    'extraction_schema': json.dumps({
                        "schema_name": "test_upload",
                        "fields": {
                            "content": {
                                "type": "string", 
                                "description": "Document content"
                            }
                        }
                    })
                }
                
                response = requests.post(f"{base_url}/api/documents/upload", 
                                       files=files, data=data)
                
                if response.status_code == 200:
                    print(f"✅ File upload: Working with {sample_file}")
                    result = response.json()
                    print(f"   Document ID: {result.get('document_id', 'N/A')}")
                    return True
                else:
                    print(f"⚠️  File upload: Failed with {sample_file} - Status {response.status_code}")
                    print(f"   Response: {response.text}")
        except FileNotFoundError:
            print(f"⚠️  Sample file not found: {sample_file}")
            continue
        except Exception as e:
            print(f"❌ File upload error with {sample_file}: {e}")
            continue
    
    print("❌ No sample files available for upload testing")
    return False

def main():
    """Run all tests"""
    print("🚀 Testing Document Analysis Application")
    print("=" * 50)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    upload_ok = test_file_upload()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Backend API: {'✅ Working' if backend_ok else '❌ Failed'}")
    print(f"   Frontend:    {'✅ Working' if frontend_ok else '❌ Failed'}")
    print(f"   File Upload: {'✅ Working' if upload_ok else '❌ Failed'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 Application is working! You can now:")
        print("   • Access frontend at: http://localhost:3000")
        print("   • Access backend at: http://localhost:8000")
        print("   • View API docs at: http://localhost:8000/docs")
        
        if upload_ok:
            print("   • Upload PDF files for analysis")
        else:
            print("   ⚠️  File upload may have issues - check sample files")
    else:
        print("\n❌ Some components are not working properly")

if __name__ == "__main__":
    main()
