#!/usr/bin/env python3
"""
Local S3 - A local implementation of Amazon S3-like functionality using FastAPI

This module implements a simple S3-like service that runs locally, providing basic
object storage functionality (buckets, objects) with a RESTful API interface.

Main features:
- Create, list, and delete buckets
- Upload, download, list, and delete objects within buckets
- Simple HTTP Basic authentication
- Object metadata support
- Prefix-based object filtering
"""

# Standard library imports
import os
import shutil
from typing import List, Optional
from datetime import datetime
import secrets
import string

# Load environment variables
from dotenv import load_dotenv
load_dotenv()  # This will load variables from .env file

# Third-party imports
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Query, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Local S3", 
    description="A local implementation of Amazon S3-like functionality",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Security configuration
# Use environment variables from .env file
security = HTTPBasic()
USERNAME = os.getenv("USERNAME", "admin")  # Fallback to default if not set
PASSWORD = os.getenv("PASSWORD", "password")  # Fallback to default if not set

# Storage configuration
# This determines where bucket directories and object files will be stored
BASE_DIR = os.getenv("BASE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage"))
# Ensure the storage directory exists
os.makedirs(BASE_DIR, exist_ok=True)

# ============================================================================
# DATA MODELS
# ============================================================================

# Pydantic models for request and response validation

class Bucket(BaseModel):
    """Represents an S3 bucket with its metadata"""
    name: str  # The unique name of the bucket
    creation_date: datetime  # When the bucket was created

class Object(BaseModel):
    """Represents an S3 object with its metadata"""
    key: str  # The object's key (filename)
    size: int  # Size in bytes
    last_modified: datetime  # Last modification timestamp
    content_type: Optional[str] = None  # MIME type if available

class BucketList(BaseModel):
    """Response model for listing buckets"""
    buckets: List[Bucket]  # List of buckets

class ObjectList(BaseModel):
    """Response model for listing objects in a bucket"""
    objects: List[Object]  # List of objects
    
class BucketRequest(BaseModel):
    """Request model for creating a bucket"""
    name: str  # The desired bucket name

# ============================================================================
# AUTHENTICATION
# ============================================================================

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Authentication credentials
    
    This function is used as a dependency for routes that require authentication.
    It compares the provided credentials against the configured username and password
    using constant-time comparison to prevent timing attacks.
    
    Args:
        credentials: The HTTP Basic Auth credentials from the request
        
    Returns:
        The username if authentication is successful
        
    Raises:
        HTTPException: If credentials are invalid (401 Unauthorized)
    """
    # Use constant-time comparison to prevent timing attacks
    is_username_correct = secrets.compare_digest(credentials.username, USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, PASSWORD)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Invalid username or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Basic"},  # Prompt browser to show login dialog
        )
    return credentials.username

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_bucket_path(bucket_name: str) -> str:
    """Get the filesystem path for a bucket
    
    Args:
        bucket_name: The name of the bucket
        
    Returns:
        The absolute path to the bucket directory
    """
    return os.path.join(BASE_DIR, bucket_name)

def get_object_path(bucket_name: str, object_key: str) -> str:
    """Get the filesystem path for an object within a bucket
    
    Args:
        bucket_name: The name of the bucket containing the object
        object_key: The key (filename) of the object
        
    Returns:
        The absolute path to the object file
    """
    return os.path.join(get_bucket_path(bucket_name), object_key)

def bucket_exists(bucket_name: str) -> bool:
    """Check if a bucket exists
    
    Args:
        bucket_name: The name of the bucket to check
        
    Returns:
        True if the bucket exists, False otherwise
    """
    bucket_path = get_bucket_path(bucket_name)
    return os.path.exists(bucket_path) and os.path.isdir(bucket_path)

def object_exists(bucket_name: str, object_key: str) -> bool:
    """Check if an object exists within a bucket
    
    Args:
        bucket_name: The name of the bucket
        object_key: The key (filename) of the object
        
    Returns:
        True if the object exists in the bucket, False otherwise
    """
    object_path = get_object_path(bucket_name, object_key)
    return os.path.exists(object_path) and os.path.isfile(object_path)

# ============================================================================
# API ROUTES
# ============================================================================

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint that returns basic information about the service
    
    Returns:
        A welcome message
    """
    return {
        "message": "Welcome to Local S3 - A local implementation of Amazon S3-like functionality",
        "documentation": "/docs",
        "version": "1.0.0"
    }

# ============================================================================
# BUCKET OPERATIONS
# ============================================================================

@app.post("/buckets", status_code=201)
async def create_bucket(bucket: BucketRequest, username: str = Depends(verify_credentials)):
    """Create a new bucket
    
    Similar to the S3 CreateBucket operation. Creates a new directory on the filesystem
    to represent the bucket.
    
    Args:
        bucket: The bucket creation request containing the desired name
        username: The authenticated username (from dependency)
        
    Returns:
        A confirmation message with 201 Created status
        
    Raises:
        HTTPException: If the bucket already exists (409 Conflict)
    """
    bucket_path = get_bucket_path(bucket.name)
    
    # Check if bucket already exists
    if os.path.exists(bucket_path):
        raise HTTPException(
            status_code=409, 
            detail=f"Bucket '{bucket.name}' already exists. Choose a unique bucket name for creation."
        )
    
    # Create the bucket directory
    try:
        os.makedirs(bucket_path)
        print(f"DEBUG: Successfully created bucket directory for '{bucket.name}' at {bucket_path}")
        return {
            "message": f"Bucket '{bucket.name}' created successfully",
            "bucket": bucket.name,
            "creation_date": datetime.now().isoformat()
        }
    except PermissionError:
        print(f"ERROR: Permission denied when creating bucket '{bucket.name}' at {bucket_path}")
        raise HTTPException(
            status_code=500,
            detail=f"Permission denied: Cannot create bucket '{bucket.name}'. Please check storage directory permissions."
        )
    except Exception as e:
        print(f"ERROR: Failed to create bucket '{bucket.name}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create bucket '{bucket.name}': {str(e)}"
        )

@app.get("/buckets", response_model=BucketList)
async def list_buckets(username: str = Depends(verify_credentials)):
    """List all buckets
    
    Similar to the S3 ListBuckets operation. Returns a list of all buckets
    with their metadata.
    
    Args:
        username: The authenticated username (from dependency)
        
    Returns:
        A BucketList object containing all buckets and their metadata
    """
    buckets = []
    
    # Scan the storage directory for bucket directories
    for bucket_name in os.listdir(BASE_DIR):
        bucket_path = os.path.join(BASE_DIR, bucket_name)
        if os.path.isdir(bucket_path):
            # Get creation time from filesystem metadata
            creation_date = datetime.fromtimestamp(os.path.getctime(bucket_path))
            buckets.append(Bucket(name=bucket_name, creation_date=creation_date))
    
    return BucketList(buckets=buckets)

@app.delete("/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str, username: str = Depends(verify_credentials)):
    """Delete a bucket
    
    Similar to the S3 DeleteBucket operation. Deletes a bucket if it exists and is empty.
    In S3, you cannot delete a bucket that contains objects.
    
    Args:
        bucket_name: The name of the bucket to delete
        username: The authenticated username (from dependency)
        
    Returns:
        A confirmation message on successful deletion
        
    Raises:
        HTTPException: 404 if bucket doesn't exist, 409 if bucket is not empty
    """
    bucket_path = get_bucket_path(bucket_name)
    
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    # Check if bucket contains any objects (excluding metadata files)
    has_objects = False
    for filename in os.listdir(bucket_path):
        # Skip metadata files when checking if bucket is empty
        if not filename.endswith('.metadata'):
            has_objects = True
            break
    
    if has_objects:
        raise HTTPException(
            status_code=409, 
            detail=f"Bucket {bucket_name} cannot be deleted because it still contains objects. Delete all objects from the bucket first before attempting to delete the bucket."
        )
    
    # Delete all files in the bucket (including metadata files)
    for filename in os.listdir(bucket_path):
        file_path = os.path.join(bucket_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    # Delete the bucket directory
    os.rmdir(bucket_path)
    return {"message": f"Bucket {bucket_name} deleted successfully"}

# ============================================================================
# OBJECT OPERATIONS
# ============================================================================

@app.post("/buckets/{bucket_name}/objects", status_code=201)
async def upload_object(
    bucket_name: str, 
    file: UploadFile = File(...), 
    username: str = Depends(verify_credentials),
    content_type: Optional[str] = Header(None),
    json: Optional[str] = Form(None)
):
    """Upload an object to a bucket
    
    Similar to the S3 PutObject operation. Uploads a file to the specified bucket
    and stores it on the filesystem.
    
    Args:
        bucket_name: The target bucket name
        file: The uploaded file (from multipart/form-data)
        username: The authenticated username (from dependency)
        content_type: Optional content type header (will use file.content_type if not provided)
        json: Optional JSON string containing metadata and other parameters
        
    Returns:
        Object metadata with 201 Created status
        
    Raises:
        HTTPException: 404 if bucket doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    object_key = file.filename
    object_path = get_object_path(bucket_name, object_key)
    
    # Save the file to the filesystem
    try:
        with open(object_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"DEBUG: Successfully saved object '{object_key}' to bucket '{bucket_name}'")
    except Exception as e:
        print(f"DEBUG: Error saving object file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload '{object_key}' to bucket '{bucket_name}': {str(e)}"
        )
    
    # Get metadata from the saved file
    # In a real S3 implementation, this would be stored in a database or metadata file
    object_size = os.path.getsize(object_path)
    
    # Process metadata if provided
    metadata = {}
    if json:
        try:
            json_data = __import__('json').loads(json)
            if 'metadata' in json_data:
                metadata = json_data['metadata']
                
                # Save metadata to a sidecar file
                metadata_path = object_path + '.metadata'
                with open(metadata_path, 'w') as f:
                    __import__('json').dump(metadata, f)
                print(f"DEBUG: Successfully saved metadata for object '{object_key}' in bucket '{bucket_name}'")
        except json.JSONDecodeError as e:
            print(f"DEBUG: Invalid JSON metadata for object '{object_key}': {e}")
            # Don't fail the upload, just log the error and continue without metadata
        except Exception as e:
            print(f"DEBUG: Error processing metadata for '{object_key}': {e}")
            # Continue without metadata
    
    # Return metadata about the uploaded object
    return {
        "key": object_key,
        "size": object_size,
        "bucket": bucket_name,
        "content_type": content_type or file.content_type,
        "metadata": metadata
    }

@app.get("/buckets/{bucket_name}/objects", response_model=ObjectList)
async def list_objects(
    bucket_name: str, 
    prefix: Optional[str] = Query(None),
    username: str = Depends(verify_credentials)
):
    """List objects in a bucket
    
    Similar to the S3 ListObjects operation. Returns a list of objects in a bucket,
    optionally filtered by a prefix. This implements simple filtering which is useful
    for simulating directories in S3's flat namespace.
    
    Args:
        bucket_name: The bucket to list objects from
        prefix: Optional prefix to filter objects by
        username: The authenticated username (from dependency)
        
    Returns:
        An ObjectList containing metadata for all matching objects
        
    Raises:
        HTTPException: 404 if bucket doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    bucket_path = get_bucket_path(bucket_name)
    objects = []
    
    print(f"DEBUG: Listing objects in bucket '{bucket_name}' at path: {bucket_path}")
    
    # Check if the bucket directory exists
    if not os.path.exists(bucket_path):
        print(f"DEBUG: Bucket directory does not exist: {bucket_path}")
        # Still return a valid empty list but log the issue
        print(f"WARNING: Request to list objects in non-existent bucket path: {bucket_path}")
        return ObjectList(objects=[])
    
    # List all files in the bucket directory
    try:
        all_files = os.listdir(bucket_path)
        print(f"DEBUG: All files found: {all_files}")
    except Exception as e:
        print(f"DEBUG: Error listing files: {e}")
        return ObjectList(objects=[])
    
    # Scan the bucket directory for files
    for object_name in all_files:
        object_path = os.path.join(bucket_path, object_name)
        print(f"DEBUG: Processing file: {object_name} at {object_path}")
        
        # Skip metadata sidecar files
        if object_name.endswith('.metadata'):
            print(f"DEBUG: Skipping metadata file: {object_name}")
            continue
            
        # Filter by prefix if provided (simulates S3's directory-like structure)
        if prefix and not object_name.startswith(prefix):
            print(f"DEBUG: Skipping file not matching prefix '{prefix}': {object_name}")
            continue
            
        # Only include files, not directories
        if os.path.isfile(object_path):
            # Get metadata from filesystem
            last_modified = datetime.fromtimestamp(os.path.getmtime(object_path))
            size = os.path.getsize(object_path)
            
            # Create object metadata
            objects.append(Object(
                key=object_name,
                size=size,
                last_modified=last_modified
                # Note: We don't have stored content_type information
                # A real implementation would store this during upload
            ))
    
    return ObjectList(objects=objects)

@app.head("/buckets/{bucket_name}/objects/{object_key}")
async def head_object(
    bucket_name: str, 
    object_key: str,
    username: str = Depends(verify_credentials)
):
    """Get metadata for an object without downloading it
    
    Similar to the S3 HeadObject operation. Returns metadata about an object
    without downloading its contents.
    
    Args:
        bucket_name: The bucket containing the object
        object_key: The key (filename) of the object
        username: The authenticated username (from dependency)
        
    Returns:
        Object metadata
        
    Raises:
        HTTPException: 404 if bucket or object doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    # Verify object exists
    if not object_exists(bucket_name, object_key):
        raise HTTPException(status_code=404, detail=f"Object {object_key} not found")
    
    object_path = get_object_path(bucket_name, object_key)
    
    # Get basic metadata from the file
    try:
        print(f"DEBUG: Retrieving HEAD metadata for object '{object_key}' in bucket '{bucket_name}'")
        
        size = os.path.getsize(object_path)
        last_modified = datetime.fromtimestamp(os.path.getmtime(object_path)).isoformat()
        
        # Attempt to determine content type based on extension
        import mimetypes
        content_type = mimetypes.guess_type(object_path)[0] or "application/octet-stream"
        
        # Check for metadata file
        metadata = {}
        metadata_path = object_path + '.metadata'
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                print(f"DEBUG: Successfully loaded metadata for '{object_key}'")
            except Exception as e:
                print(f"DEBUG: Error reading metadata for HEAD request: {e}")
        
        # Return enhanced object metadata
        print(f"DEBUG: HEAD request for '{object_key}' completed successfully")
        return {
            "key": object_key,
            "size": size,
            "last_modified": last_modified,
            "content_type": content_type,
            "metadata": metadata,
            "etag": f"\"md5-{hash(object_key + str(size) + last_modified)}\""
        }
    except Exception as e:
        print(f"ERROR: Failed to get HEAD metadata for '{object_key}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metadata for object '{object_key}' in bucket '{bucket_name}': {str(e)}"
        )

@app.get("/buckets/{bucket_name}/objects/{object_key}/metadata")
async def get_object_metadata(
    bucket_name: str, 
    object_key: str,
    username: str = Depends(verify_credentials)
):
    """Get metadata for an object
    
    Returns the metadata associated with an object.
    
    Args:
        bucket_name: The bucket containing the object
        object_key: The key (filename) of the object
        username: The authenticated username (from dependency)
        
    Returns:
        Object metadata
        
    Raises:
        HTTPException: 404 if bucket or object doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    # Verify object exists
    if not object_exists(bucket_name, object_key):
        raise HTTPException(status_code=404, detail=f"Object {object_key} not found")
    
    object_path = get_object_path(bucket_name, object_key)
    metadata_path = object_path + '.metadata'
    
    # Check if metadata file exists
    metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            print(f"DEBUG: Invalid JSON in metadata file for '{object_key}': {e}")
            metadata = {"error": "Metadata file exists but contains invalid JSON format"}
        except Exception as e:
            print(f"DEBUG: Error reading metadata file for '{object_key}': {e}")
            metadata = {"error": f"Error accessing metadata: {str(e)}"}
    
    # Return metadata
    return {
        "metadata": metadata
    }

@app.get("/buckets/{bucket_name}/objects/{object_key}")
async def download_object(
    bucket_name: str, 
    object_key: str,
    username: str = Depends(verify_credentials)
):
    """Download an object from a bucket
    
    Similar to the S3 GetObject operation. Returns the contents of an object
    as a file download with the appropriate content disposition headers.
    
    Args:
        bucket_name: The bucket containing the object
        object_key: The key (filename) of the object to download
        username: The authenticated username (from dependency)
        
    Returns:
        FileResponse with the object's contents
        
    Raises:
        HTTPException: 404 if bucket or object doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found. Please ensure the bucket exists and try again.")
    
    object_path = get_object_path(bucket_name, object_key)
    
    # Verify object exists
    if not object_exists(bucket_name, object_key):
        raise HTTPException(status_code=404, detail=f"Object '{object_key}' not found in bucket '{bucket_name}'. Please ensure the object exists and try again.")
    
    # Return file as a download response with appropriate headers
    try:
        # Log download attempt
        print(f"DEBUG: Attempting to download object '{object_key}' from bucket '{bucket_name}'")
        
        # Check if file is readable before returning
        if not os.access(object_path, os.R_OK):
            raise PermissionError(f"Object file exists but is not readable: {object_path}")
            
        # FastAPI will automatically set Content-Type based on the file extension
        print(f"DEBUG: Successfully serving download for '{object_key}'")
        return FileResponse(path=object_path, filename=object_key)
    except Exception as e:
        print(f"ERROR: Failed to serve file '{object_key}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download object '{object_key}' from bucket '{bucket_name}': {str(e)}"
        )

@app.delete("/buckets/{bucket_name}/objects/{object_key}")
async def delete_object(
    bucket_name: str, 
    object_key: str,
    username: str = Depends(verify_credentials)
):
    """Delete an object from a bucket
    
    Similar to the S3 DeleteObject operation. Deletes an object if it exists.
    
    Args:
        bucket_name: The bucket containing the object
        object_key: The key (filename) of the object to delete
        username: The authenticated username (from dependency)
        
    Returns:
        A confirmation message on successful deletion
        
    Raises:
        HTTPException: 404 if bucket or object doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    object_path = get_object_path(bucket_name, object_key)
    
    # Verify object exists
    if not object_exists(bucket_name, object_key):
        raise HTTPException(
            status_code=404, 
            detail=f"Object '{object_key}' not found in bucket '{bucket_name}'. Please verify that both the object key and bucket name are correct."
        )
    
    # Delete metadata file if it exists
    metadata_path = object_path + '.metadata'
    if os.path.exists(metadata_path):
        try:
            os.remove(metadata_path)
            print(f"DEBUG: Deleted metadata file for object '{object_key}' in bucket '{bucket_name}'")
        except Exception as e:
            print(f"DEBUG: Error deleting metadata file: {e}")
    
    # Delete the object file from the filesystem
    os.remove(object_path)
    return {
        "message": f"Object '{object_key}' deleted successfully from bucket '{bucket_name}'", 
        "bucket": bucket_name,
        "key": object_key
    }

# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

# This block is executed when the script is run directly
if __name__ == "__main__":
    # Start the Uvicorn ASGI server
    # - host="0.0.0.0" makes the server accessible from any network interface
    # - port=8000 is the default FastAPI port
    # - reload=True enables auto-reloading when code changes (development mode)
    print(f"Starting Local S3 server on http://0.0.0.0:8000")
    print(f"API documentation available at http://localhost:8000/docs")
    print(f"Storage location: {BASE_DIR}")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
