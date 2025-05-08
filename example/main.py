import requests
from requests.auth import HTTPBasicAuth
import os
from requests.exceptions import Timeout, ConnectionError, RequestException

REQUEST_TIMEOUT = 10  # Define the request timeout in seconds

print("program start")

# Configuration
BASE_URL = "http://10.0.0.204:8000"  # Raspberry Pi server IP
AUTH = HTTPBasicAuth("admin", "password")

# Create a bucket
def create_bucket(bucket_name):
    try:
        response = requests.post(
            f"{BASE_URL}/buckets",
            json={"name": bucket_name},
            auth=AUTH,
            timeout=REQUEST_TIMEOUT
        )
        print(f"Create bucket response: {response.status_code}")
        return response.status_code == 201
    except Timeout:
        print(f"Timeout error when creating bucket '{bucket_name}'")
    except ConnectionError:
        print(f"Connection error when creating bucket '{bucket_name}'")
    except RequestException as e:
        print(f"Error creating bucket '{bucket_name}': {e}")
    return False

# Upload a file
def upload_file(bucket_name, file_path):
    try:
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            files = {"file": (file_name, file)}
            response = requests.post(
                f"{BASE_URL}/buckets/{bucket_name}/objects",
                files=files,
                auth=AUTH,
                timeout=REQUEST_TIMEOUT
            )
        print(f"Upload response: {response.status_code}")
        return response.json() if response.status_code == 201 else None
    except Timeout:
        print(f"Timeout error when uploading '{file_path}' to bucket '{bucket_name}'")
    except ConnectionError:
        print(f"Connection error when uploading '{file_path}' to bucket '{bucket_name}'")
    except RequestException as e:
        print(f"Error uploading file to bucket '{bucket_name}': {e}")
    return None

# List objects in a bucket
def list_objects(bucket_name, prefix=None):
    try:
        params = {"prefix": prefix} if prefix else {}
        response = requests.get(
            f"{BASE_URL}/buckets/{bucket_name}/objects",
            params=params,
            auth=AUTH,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()["objects"]
        return []
    except Timeout:
        print(f"Timeout error when listing objects in bucket '{bucket_name}'")
    except ConnectionError:
        print(f"Connection error when listing objects in bucket '{bucket_name}'")
    except RequestException as e:
        print(f"Error listing objects in bucket '{bucket_name}': {e}")
    return []

# Download an object
def download_object(bucket_name, object_key, output_path):
    try:
        response = requests.get(
            f"{BASE_URL}/buckets/{bucket_name}/objects/{object_key}",
            auth=AUTH,
            stream=True,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Timeout:
        print(f"Timeout error when downloading '{object_key}' from bucket '{bucket_name}'")
    except ConnectionError:
        print(f"Connection error when downloading '{object_key}' from bucket '{bucket_name}'")
    except RequestException as e:
        print(f"Error downloading object '{object_key}' from bucket '{bucket_name}': {e}")
    return False

# Delete an object
def delete_object(bucket_name, object_key):
    try:
        response = requests.delete(
            f"{BASE_URL}/buckets/{bucket_name}/objects/{object_key}",
            auth=AUTH,
            timeout=REQUEST_TIMEOUT
        )
        return response.status_code == 200
    except Timeout:
        print(f"Timeout error when deleting '{object_key}' from bucket '{bucket_name}'")
    except ConnectionError:
        print(f"Connection error when deleting '{object_key}' from bucket '{bucket_name}'")
    except RequestException as e:
        print(f"Error deleting object '{object_key}' from bucket '{bucket_name}': {e}")
    return False

# Usage example
if __name__ == "__main__":
    try:
        print("Starting operations...")
        
        # Create a test bucket
        bucket_created = create_bucket("test-bucket")
        
        if bucket_created:
            print("Bucket created successfully. Proceeding with upload...")
            
            # Check if the example.txt file exists
            if os.path.exists("./example.txt"):
                # Upload a file
                upload_info = upload_file("test-bucket", "./example.txt")
                if upload_info:
                    print(f"Uploaded file: {upload_info}")
                    
                    # List all objects
                    objects = list_objects("test-bucket")
                    print(f"Objects in bucket: {objects}")
                    
                    if objects:
                        # Download a file
                        if download_object("test-bucket", "example.txt", "./downloaded_example.txt"):
                            print("File downloaded successfully")
                            
                            # Delete the object
                            if delete_object("test-bucket", "example.txt"):
                                print("File deleted successfully")
                            else:
                                print("Failed to delete the file")
                        else:
                            print("Failed to download the file")
                    else:
                        print("No objects found in bucket")
                else:
                    print("Failed to upload the file")
            else:
                print("Error: example.txt file not found. Please create this file first.")
        else:
            print("Bucket creation failed. Aborting further operations.")
            print("Is the server running at", BASE_URL, "?")
        
        print("Operations completed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")