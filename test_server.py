import unittest
import json
import requests
import os
import shutil
from fastapi.testclient import TestClient
import uvicorn
import subprocess
import time
import threading
from server import app, BASE_DIR

# Use the requests library to test the API
BASE_URL = "http://localhost:8000"

# Authentication credentials
AUTH = ("admin", "password")

class TestLocalS3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread for testing
        cls.server_thread = threading.Thread(target=cls.run_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give the server a moment to start
        time.sleep(2)
    
    @classmethod
    def run_server(cls):
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
        
    def setUp(self):
        # Clean up the storage directory before each test
        if os.path.exists(BASE_DIR):
            for bucket in os.listdir(BASE_DIR):
                bucket_path = os.path.join(BASE_DIR, bucket)
                if os.path.isdir(bucket_path):
                    shutil.rmtree(bucket_path)
    
    def test_create_bucket(self):
        response = requests.post(f"{BASE_URL}/buckets", json={"name": "test-bucket"}, auth=AUTH)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "Bucket test-bucket created successfully")
    
    def test_list_buckets(self):
        # Create a bucket first
        requests.post(f"{BASE_URL}/buckets", json={"name": "list-test-bucket"}, auth=AUTH)
        
        # List buckets
        response = requests.get(f"{BASE_URL}/buckets", auth=AUTH)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("buckets", data)
        self.assertTrue(isinstance(data["buckets"], list))
        
        # Check if our bucket is in the list
        bucket_names = [bucket["name"] for bucket in data["buckets"]]
        self.assertIn("list-test-bucket", bucket_names)
    
    def test_upload_object(self):
        # Create a bucket first
        requests.post(f"{BASE_URL}/buckets", json={"name": "upload-bucket"}, auth=AUTH)
        
        # Upload a file
        files = {"file": ("test.txt", "Hello World")}
        response = requests.post(f"{BASE_URL}/buckets/upload-bucket/objects", files=files, auth=AUTH)
        self.assertEqual(response.status_code, 201)
        self.assertIn("key", response.json())
        self.assertEqual(response.json()["key"], "test.txt")
    
    def test_list_objects(self):
        # Create a bucket and upload an object
        requests.post(f"{BASE_URL}/buckets", json={"name": "list-objects-bucket"}, auth=AUTH)
        files = {"file": ("list.txt", "Hello List")}
        requests.post(f"{BASE_URL}/buckets/list-objects-bucket/objects", files=files, auth=AUTH)
        
        # List objects
        response = requests.get(f"{BASE_URL}/buckets/list-objects-bucket/objects", auth=AUTH)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("objects", data)
        
        # Check if our file is in the list
        object_keys = [obj["key"] for obj in data["objects"]]
        self.assertIn("list.txt", object_keys)
    
    def test_download_object(self):
        # Create bucket and upload file
        requests.post(f"{BASE_URL}/buckets", json={"name": "download-bucket"}, auth=AUTH)
        files = {"file": ("download.txt", "Download Me")}
        requests.post(f"{BASE_URL}/buckets/download-bucket/objects", files=files, auth=AUTH)
        
        # Download the file
        response = requests.get(f"{BASE_URL}/buckets/download-bucket/objects/download.txt", auth=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Download Me")
    
    def test_delete_object(self):
        # Create bucket and upload file
        requests.post(f"{BASE_URL}/buckets", json={"name": "delete-object-bucket"}, auth=AUTH)
        files = {"file": ("delete.txt", "Delete Me")}
        requests.post(f"{BASE_URL}/buckets/delete-object-bucket/objects", files=files, auth=AUTH)
        
        # Delete the object
        response = requests.delete(f"{BASE_URL}/buckets/delete-object-bucket/objects/delete.txt", auth=AUTH)
        self.assertEqual(response.status_code, 200)
        
        # Verify it's gone
        response = requests.get(f"{BASE_URL}/buckets/delete-object-bucket/objects", auth=AUTH)
        data = response.json()
        object_keys = [obj["key"] for obj in data["objects"]]
        self.assertNotIn("delete.txt", object_keys)
    
    def test_delete_bucket(self):
        # Create a bucket
        requests.post(f"{BASE_URL}/buckets", json={"name": "delete-bucket"}, auth=AUTH)
        
        # Delete the bucket
        response = requests.delete(f"{BASE_URL}/buckets/delete-bucket", auth=AUTH)
        self.assertEqual(response.status_code, 200)
        
        # Verify it's gone
        response = requests.get(f"{BASE_URL}/buckets", auth=AUTH)
        data = response.json()
        bucket_names = [bucket["name"] for bucket in data["buckets"]]
        self.assertNotIn("delete-bucket", bucket_names)

if __name__ == "__main__":
    unittest.main()
