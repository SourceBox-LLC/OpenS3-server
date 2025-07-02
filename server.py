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
import json
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
from fastapi.middleware.cors import CORSMiddleware
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

# Add CORS middleware to allow cross-origin requests from the GUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify the exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Security configuration
# Use environment variables from .env file
security = HTTPBasic()
# Support both OpenAthena-style and direct environment variables
USERNAME = os.getenv("OPENS3_ACCESS_KEY", os.getenv("S3_USERNAME", "admin"))  # Try OpenAthena var first, then S3, then default
PASSWORD = os.getenv("OPENS3_SECRET_KEY", os.getenv("S3_PASSWORD", "password"))  # Try OpenAthena var first, then S3, then default

# Print credentials for debugging
print(f"Using authentication credentials: {USERNAME} / {PASSWORD}")
print(f"Environment variables checked: OPENS3_ACCESS_KEY, S3_USERNAME, OPENS3_SECRET_KEY, S3_PASSWORD")

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
    bucket_path = get_bucket_path(bucket_name)
    
    # Handle objects in subdirectories
    # object_key could be like "dir1/dir2/file.txt"
    return os.path.join(bucket_path, object_key)

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
    print(f"DEBUG: Checking if object exists at: {object_path}")
    
    # Ensure any parent directories in the path exist
    parent_dir = os.path.dirname(object_path)
    if not os.path.exists(parent_dir):
        print(f"DEBUG: Parent directory does not exist: {parent_dir}")
        return False
        
    # Check if the object file exists
    exists = os.path.exists(object_path) and os.path.isfile(object_path)
    print(f"DEBUG: Object {'exists' if exists else 'does not exist'} at {object_path}")
    return exists

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

@app.head("/buckets/{bucket_name}")
async def head_bucket(bucket_name: str, username: str = Depends(verify_credentials)):
    """Check if a bucket exists
    
    Similar to the S3 HeadBucket operation. Checks if a bucket exists and if
    the caller has permission to access it.
    
    Args:
        bucket_name: The name of the bucket to check
        username: The authenticated username (from dependency)
        
    Returns:
        An empty response with 200 OK status if the bucket exists
        
    Raises:
        HTTPException: 404 if bucket doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    # If we got here, the bucket exists and the user has permission to access it
    return {"message": f"Bucket {bucket_name} exists"}

@app.delete("/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str, force: bool = Query(False, description="Force deletion of the bucket even if it contains objects"), username: str = Depends(verify_credentials)):
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
    
    # Check if bucket contains any objects (excluding metadata files and directory markers)
    has_objects = False
    for filename in os.listdir(bucket_path):
        # Skip metadata files and directory markers when checking if bucket is empty
        if not filename.endswith('.metadata') and not filename.endswith('.directory'):
            has_objects = True
            break
    
    if has_objects and not force:
        raise HTTPException(
            status_code=409, 
            detail=f"Bucket {bucket_name} cannot be deleted because it still contains objects. Delete all objects from the bucket first before attempting to delete the bucket, or use force=true."
        )
        
    # If force is True, recursively delete all contents
    if force:
        import shutil
        # Instead of deleting individual files, use shutil.rmtree for the entire bucket
        try:
            for item in os.listdir(bucket_path):
                item_path = os.path.join(bucket_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        except Exception as e:
            print(f"Warning: Error during forced cleanup: {e}")
    
    # Delete all files in the bucket (including metadata files)
    for filename in os.listdir(bucket_path):
        file_path = os.path.join(bucket_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    # Delete the bucket directory
    os.rmdir(bucket_path)
    return {"message": f"Bucket {bucket_name} deleted successfully", "force_applied": force}

# ============================================================================
# DIRECTORY OPERATIONS
# ============================================================================

@app.post("/buckets/{bucket_name}/directories", status_code=201)
async def create_directory(
    bucket_name: str, 
    directory_path: str = Query(..., description="Path for the directory to create (should end with '/')."),
    username: str = Depends(verify_credentials)
):
    """Create a directory in a bucket
    
    Creates a directory marker in the bucket. In S3's flat namespace, this is
    implemented by creating an empty file with a trailing slash in the name.
    
    Args:
        bucket_name: The target bucket name
        directory_path: The path for the directory (should end with '/')
        username: The authenticated username (from dependency)
        
    Returns:
        Directory creation confirmation with 201 Created status
        
    Raises:
        HTTPException: 404 if bucket doesn't exist
    """
    # Verify bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(status_code=404, detail=f"Bucket {bucket_name} not found")
    
    # Ensure the path ends with a slash
    if not directory_path.endswith('/'):
        directory_path += '/'
    
    # Create the directory path
    bucket_path = get_bucket_path(bucket_name)
    dir_parts = directory_path.strip('/').split('/')
    
    current_path = bucket_path
    for part in dir_parts:
        if part:
            current_path = os.path.join(current_path, part)
            if not os.path.exists(current_path):
                os.makedirs(current_path, exist_ok=True)
    
    # Create a directory marker file to indicate this is a directory
    marker_file = os.path.join(bucket_path, directory_path, ".directory")
    os.makedirs(os.path.dirname(marker_file), exist_ok=True)
    
    with open(marker_file, 'w') as f:
        pass  # Create an empty file as directory marker
    
    now = datetime.now().isoformat()
    
    return {
        "message": f"Directory '{directory_path}' created successfully in bucket '{bucket_name}'",
        "directory": directory_path,
        "creation_date": now
    }

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
    
    # Check if this is an S3-style directory marker (object key with trailing slash and empty content)
    is_directory_marker = object_key.endswith('/')
    
    # Save the file to the filesystem
    try:
        # Handle S3-style directory marker
        if is_directory_marker:
            # For S3-style directory markers, we need to create the directory structure
            # Extract the directory path - for a key with trailing slash, this is the entire key
            dir_path = os.path.join(get_bucket_path(bucket_name), object_key.rstrip('/'))
            
            # Create the directory structure
            os.makedirs(dir_path, exist_ok=True)
            
            # Create a .directory marker file in the directory
            directory_marker_path = os.path.join(dir_path, ".directory")
            with open(directory_marker_path, "w") as f:
                f.write(f"S3-style directory marker created on {datetime.now()}")
            
            # For S3 compatibility, we don't create an actual file for directory markers
            # Instead, we'll use the directory_marker_path as the object_path for metadata purposes
            object_path = directory_marker_path
            print(f"DEBUG: Created S3-style directory marker at '{dir_path}'")
            
            # Skip the file creation step since this is a directory marker
            
            print(f"DEBUG: Successfully created S3-style directory marker '{object_key}' in bucket '{bucket_name}'")
        else:
            # Regular file object
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
    
    # Function to walk through directory and find all objects
    def scan_directory(current_path, current_prefix=""):
        items = os.listdir(current_path)
        for item_name in items:
            item_path = os.path.join(current_path, item_name)
            
            # Skip metadata sidecar files
            if item_name.endswith('.metadata'):
                print(f"DEBUG: Skipping metadata file: {item_name}")
                continue
            
            # Skip .directory marker files (internal use)
            if item_name == '.directory':
                print(f"DEBUG: Skipping directory marker file")
                continue
            
            # For files, add them to the objects list
            if os.path.isfile(item_path):
                # Build the relative key path
                key = item_name if not current_prefix else f"{current_prefix}{item_name}"
                
                # Filter by prefix if provided
                if prefix and not key.startswith(prefix):
                    print(f"DEBUG: Skipping file not matching prefix '{prefix}': {key}")
                    continue
                
                # Get metadata from filesystem
                last_modified = datetime.fromtimestamp(os.path.getmtime(item_path))
                size = os.path.getsize(item_path)
                
                print(f"DEBUG: Adding file to results: {key}")
                
                # Create object metadata
                objects.append(Object(
                    key=key,
                    size=size,
                    last_modified=last_modified
                ))
            
            # For directories, traverse into them unless they're hidden
            elif os.path.isdir(item_path) and not item_name.startswith('.'):
                # Build new prefix for this directory
                dir_prefix = f"{current_prefix}{item_name}/"
                
                # If a prefix filter is specified and this directory doesn't match, skip it
                if prefix and not dir_prefix.startswith(prefix) and not prefix.startswith(dir_prefix):
                    print(f"DEBUG: Skipping directory not matching prefix '{prefix}': {dir_prefix}")
                    continue
                
                print(f"DEBUG: Scanning subdirectory: {dir_prefix}")
                
                # Recursively scan the subdirectory
                scan_directory(item_path, dir_prefix)
    
    # Start scanning from the bucket root
    scan_directory(bucket_path)
    
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

@app.get("/buckets/{bucket_name}/object")
async def download_object_query(
    bucket_name: str, 
    object_key: str = Query(..., description="The key (path) of the object to download"),
    username: str = Depends(verify_credentials)
):
    """Download an object from a bucket using query parameters
    
    Similar to the S3 GetObject operation but uses query parameters to handle keys with slashes.
    Returns the contents of an object as a file download with the appropriate content disposition headers.
    
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

@app.delete("/buckets/{bucket_name}/objects")
async def delete_object(
    bucket_name: str, 
    object_key: str = Query(..., description="The key (path) of the object to delete"),
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
    port = 8001  # Changed port to avoid conflict with OpenAthena
    print(f"Starting Local S3 server on http://0.0.0.0:{port}")
    print(f"API documentation available at http://localhost:{port}/docs")
    print(f"Storage location: {BASE_DIR}")
    
    # Start the server with uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
