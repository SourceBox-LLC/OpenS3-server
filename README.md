# Local S3

A Python implementation of an Amazon S3-like service that runs locally using FastAPI, perfect for development and testing environments.

## Table of Contents

- [Features](#features)
- [Why Local S3?](#why-local-s3)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Bucket Operations](#bucket-operations)
  - [Object Operations](#object-operations)
- [Programming Examples](#programming-examples)
  - [Python Examples](#python-examples)
  - [JavaScript/Node.js Examples](#javascriptnodejs-examples)
- [Development Guidelines](#development-guidelines)
- [Storage Structure](#storage-structure)
- [Testing](#testing)
- [Common Patterns and Best Practices](#common-patterns-and-best-practices)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [License](#license)

A Python implementation of an Amazon S3-like service that runs locally using FastAPI.

## Features

- **Bucket Operations**: Create, list, and delete buckets (similar to S3 buckets)
- **Object Operations**: Upload, download, list, and delete objects within buckets
- **Metadata Support**: Store and retrieve metadata associated with objects
- **Authentication**: Simple HTTP Basic authentication for API security
- **Filtering**: List objects with prefix filtering (similar to S3's prefix parameter)
- **REST API**: Fully RESTful API compatible with standard HTTP clients
- **Swagger Documentation**: Interactive API documentation via Swagger UI
- **Local Storage**: Files stored in a structured way on your local filesystem
- **Content Type Handling**: Proper handling of MIME types for uploaded and downloaded files

## Why Local S3?

Local S3 serves several important purposes for developers:

- **Development Environment**: Test S3-dependent applications without connecting to actual AWS services
- **Cost Efficient**: Avoid AWS costs during development and testing phases
- **Offline Development**: Work on S3-integrated applications without internet connectivity
- **Simplified Testing**: Run integration tests that require S3 functionality without mock objects
- **Learning Tool**: Understand how object storage works with a simplified implementation
- **Rapid Prototyping**: Quickly build and test applications that rely on object storage
- **CI/CD Integration**: Integrate into continuous integration pipelines without AWS credentials

## Requirements

- Python 3.7+ (tested with Python 3.8 and 3.9)
- FastAPI (0.95.0+)
- Uvicorn for ASGI server
- Pydantic for data validation
- Additional dependencies are listed in `requirements.txt`

## Installation

### Option 1: Standard Installation

1. Clone the repository or download the source code:
   ```bash
   git clone https://github.com/SourceBox-LLC/OpenS3-server.git
   cd OpenS3-server
   ```

2. Set up a virtual environment (recommended):
   ```bash
   # On Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   
   Note: If you encounter issues with the virtual environment, try deactivating any existing environment first with `deactivate`.

3. Install the required dependencies:
   ```bash
   # The -r flag is required when installing from a requirements file
   pip install -r requirements.txt
   ```
   
   Note: If you encounter pip installation issues, you can also try:
   ```bash
   python -m pip install -r requirements.txt
   ```

4. Run the setup script to configure authentication:
   ```bash
   python setup.py
   ```
   This will create a `.env` file with your custom username and password.

### Option 2: Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t local-s3 .
   ```

2. Create a `.env` file with your desired credentials (as outlined in Option 1, step 4)

3. Run the container with environment variables:
   ```bash
   # On Linux/macOS
   docker run -p 8000:8000 -v $(pwd)/storage:/app/storage --env-file .env local-s3
   
   # On Windows PowerShell
   docker run -p 8000:8000 -v ${PWD}/storage:/app/storage --env-file .env local-s3
   ```
   
   This mounts the local storage directory and passes your authentication credentials to the container.

## Getting Started

### Starting the Server

```bash
python server.py
```

The server will start at `http://0.0.0.0:8000` with the following output:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Interactive Documentation

Local S3 comes with built-in interactive documentation powered by Swagger UI:

- **Swagger UI**: Visit `http://localhost:8000/docs` in your browser
- **ReDoc**: Visit `http://localhost:8000/redoc` for an alternative documentation interface

### Authentication

All API endpoints are protected with HTTP Basic Authentication:

- **Default Username**: `admin`
- **Default Password**: `password`

You can modify these credentials by running the setup script:
```bash
python setup.py
```

This will create a `.env` file with your custom credentials. You can also manually create or edit the `.env` file following the format in `.env.example`.

### Configuration

The following configuration parameters can be set in the `.env` file:

- **USERNAME**: Username for HTTP Basic Authentication
- **PASSWORD**: Password for HTTP Basic Authentication
- **BASE_DIR**: Storage location for buckets and objects (default: `./storage`)

Other settings like Host/Port can be adjusted when running the server (default: `0.0.0.0:8000`)

### Storage Location

By default, all data is stored in the `storage` directory in the project root. Each bucket will be created as a subdirectory.

## API Reference

Local S3 provides a RESTful API that closely resembles the AWS S3 API structure, making it easy to switch between local development and production AWS environments.

### Authentication

All API endpoints require HTTP Basic Authentication. Include the following header with every request:

```
Authorization: Basic <base64-encoded-credentials>
```

Where `<base64-encoded-credentials>` is the Base64 encoding of `username:password`.

Most HTTP clients and libraries handle this automatically when you provide auth credentials.

### Bucket Operations

#### Create a Bucket

- **Endpoint**: `POST /buckets`
- **Auth Required**: Yes
- **Request Body**:
  ```json
  {
    "name": "my-bucket-name"
  }
  ```
- **Success Response**: `201 Created`
  ```json
  {
    "message": "Bucket my-bucket-name created successfully"
  }
  ```
- **Error Responses**:
  - `409 Conflict`: Bucket already exists
  - `401 Unauthorized`: Invalid credentials

#### List All Buckets

- **Endpoint**: `GET /buckets`
- **Auth Required**: Yes
- **Success Response**: `200 OK`
  ```json
  {
    "buckets": [
      {
        "name": "bucket1",
        "creation_date": "2023-04-01T12:00:00"
      },
      {
        "name": "bucket2",
        "creation_date": "2023-04-02T14:30:00"
      }
    ]
  }
  ```

#### Delete a Bucket

- **Endpoint**: `DELETE /buckets/{bucket_name}`
- **Auth Required**: Yes
- **URL Parameters**: 
  - `bucket_name`: Name of the bucket to delete
- **Success Response**: `200 OK`
  ```json
  {
    "message": "Bucket bucket1 deleted successfully"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Bucket does not exist
  - `409 Conflict`: Bucket is not empty
  - `401 Unauthorized`: Invalid credentials

### Object Operations

#### Upload an Object

- **Endpoint**: `POST /buckets/{bucket_name}/objects`
- **Auth Required**: Yes
- **URL Parameters**:
  - `bucket_name`: Target bucket for the upload
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: The file to upload
- **Headers** (optional):
  - `Content-Type`: The MIME type of the uploaded file
- **Success Response**: `201 Created`
  ```json
  {
    "key": "filename.txt",
    "size": 1024,
    "bucket": "my-bucket",
    "content_type": "text/plain"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Bucket does not exist
  - `401 Unauthorized`: Invalid credentials

#### List Objects in a Bucket

- **Endpoint**: `GET /buckets/{bucket_name}/objects`
- **Auth Required**: Yes
- **URL Parameters**:
  - `bucket_name`: Bucket to list objects from
- **Query Parameters** (optional):
  - `prefix`: Filter objects that start with this prefix
- **Success Response**: `200 OK`
  ```json
  {
    "objects": [
      {
        "key": "document.pdf",
        "size": 10240,
        "last_modified": "2023-04-10T09:15:00",
        "content_type": "application/pdf"
      },
      {
        "key": "image.jpg",
        "size": 5120,
        "last_modified": "2023-04-11T14:20:00",
        "content_type": "image/jpeg"
      }
    ]
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Bucket does not exist
  - `401 Unauthorized`: Invalid credentials

#### Download an Object

- **Endpoint**: `GET /buckets/{bucket_name}/objects/{object_key}`
- **Auth Required**: Yes
- **URL Parameters**:
  - `bucket_name`: Source bucket name
  - `object_key`: Object key/filename to download
- **Success Response**: `200 OK` with file contents as the response body
  - Response will include appropriate `Content-Type` and `Content-Disposition` headers
- **Error Responses**:
  - `404 Not Found`: Bucket or object does not exist
  - `401 Unauthorized`: Invalid credentials

#### Delete an Object

- **Endpoint**: `DELETE /buckets/{bucket_name}/objects/{object_key}`
- **Auth Required**: Yes
- **URL Parameters**:
  - `bucket_name`: Bucket containing the object
  - `object_key`: Object key/filename to delete
- **Success Response**: `200 OK`
  ```json
  {
    "message": "Object object_key deleted successfully from bucket bucket_name"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Bucket or object does not exist
  - `401 Unauthorized`: Invalid credentials

## Programming Examples

This section provides code examples for interacting with Local S3 in different programming languages.

### Command Line (cURL) Examples

#### Creating a bucket

```bash
curl -X 'POST' \
  'http://localhost:8000/buckets' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -u admin:password \
  -d '{"name": "mybucket"}'
```

#### Uploading a file

```bash
curl -X 'POST' \
  'http://localhost:8000/buckets/mybucket/objects' \
  -H 'accept: application/json' \
  -u admin:password \
  -F 'file=@/path/to/your/file.txt'
```

#### Listing objects in a bucket

```bash
curl -X 'GET' \
  'http://localhost:8000/buckets/mybucket/objects' \
  -H 'accept: application/json' \
  -u admin:password
```

#### Downloading an object

```bash
curl -X 'GET' \
  'http://localhost:8000/buckets/mybucket/objects/file.txt' \
  -u admin:password \
  --output downloaded_file.txt
```

#### Deleting an object

```bash
curl -X 'DELETE' \
  'http://localhost:8000/buckets/mybucket/objects/file.txt' \
  -u admin:password
```

### Python Examples

#### Complete Example with Requests

```python
import requests
from requests.auth import HTTPBasicAuth
import os

# Configuration
BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("admin", "password")

# Create a bucket
def create_bucket(bucket_name):
    response = requests.post(
        f"{BASE_URL}/buckets",
        json={"name": bucket_name},
        auth=AUTH
    )
    print(f"Create bucket response: {response.status_code}")
    return response.status_code == 201

# Upload a file
def upload_file(bucket_name, file_path):
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as file:
        files = {"file": (file_name, file)}
        response = requests.post(
            f"{BASE_URL}/buckets/{bucket_name}/objects",
            files=files,
            auth=AUTH
        )
    print(f"Upload response: {response.status_code}")
    return response.json() if response.status_code == 201 else None

# List objects in a bucket
def list_objects(bucket_name, prefix=None):
    params = {"prefix": prefix} if prefix else {}
    response = requests.get(
        f"{BASE_URL}/buckets/{bucket_name}/objects",
        params=params,
        auth=AUTH
    )
    if response.status_code == 200:
        return response.json()["objects"]
    return []

# Download an object
def download_object(bucket_name, object_key, output_path):
    response = requests.get(
        f"{BASE_URL}/buckets/{bucket_name}/objects/{object_key}",
        auth=AUTH,
        stream=True
    )
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

# Delete an object
def delete_object(bucket_name, object_key):
    response = requests.delete(
        f"{BASE_URL}/buckets/{bucket_name}/objects/{object_key}",
        auth=AUTH
    )
    return response.status_code == 200

# Usage example
if __name__ == "__main__":
    # Create a test bucket
    create_bucket("test-bucket")
    
    # Upload a file
    upload_info = upload_file("test-bucket", "./example.txt")
    print(f"Uploaded file: {upload_info}")
    
    # List all objects
    objects = list_objects("test-bucket")
    print(f"Objects in bucket: {objects}")
    
    # Download a file
    download_object("test-bucket", "example.txt", "./downloaded_example.txt")
    print("File downloaded successfully")
    
    # Delete the object
    delete_object("test-bucket", "example.txt")
    print("File deleted successfully")
```

### JavaScript/Node.js Examples

#### Complete Example with Axios

```javascript
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

// Configuration
const BASE_URL = 'http://localhost:8000';
const AUTH = {
  username: 'admin',
  password: 'password'
};

// Create a bucket
async function createBucket(bucketName) {
  try {
    const response = await axios.post(
      `${BASE_URL}/buckets`,
      { name: bucketName },
      { auth: AUTH }
    );
    console.log(`Create bucket response: ${response.status}`);
    return response.status === 201;
  } catch (error) {
    console.error('Error creating bucket:', error.message);
    return false;
  }
}

// Upload a file
async function uploadFile(bucketName, filePath) {
  try {
    const fileName = path.basename(filePath);
    const fileContent = fs.readFileSync(filePath);
    
    const formData = new FormData();
    formData.append('file', fileContent, fileName);
    
    const response = await axios.post(
      `${BASE_URL}/buckets/${bucketName}/objects`,
      formData,
      {
        auth: AUTH,
        headers: formData.getHeaders()
      }
    );
    
    console.log(`Upload response: ${response.status}`);
    return response.data;
  } catch (error) {
    console.error('Error uploading file:', error.message);
    return null;
  }
}

// List objects in a bucket
async function listObjects(bucketName, prefix = null) {
  try {
    const params = prefix ? { prefix } : {};
    const response = await axios.get(
      `${BASE_URL}/buckets/${bucketName}/objects`,
      {
        params,
        auth: AUTH
      }
    );
    
    return response.data.objects;
  } catch (error) {
    console.error('Error listing objects:', error.message);
    return [];
  }
}

// Download an object
async function downloadObject(bucketName, objectKey, outputPath) {
  try {
    const response = await axios.get(
      `${BASE_URL}/buckets/${bucketName}/objects/${objectKey}`,
      {
        auth: AUTH,
        responseType: 'stream'
      }
    );
    
    const writer = fs.createWriteStream(outputPath);
    response.data.pipe(writer);
    
    return new Promise((resolve, reject) => {
      writer.on('finish', resolve);
      writer.on('error', reject);
    });
  } catch (error) {
    console.error('Error downloading object:', error.message);
    return false;
  }
}

// Delete an object
async function deleteObject(bucketName, objectKey) {
  try {
    const response = await axios.delete(
      `${BASE_URL}/buckets/${bucketName}/objects/${objectKey}`,
      { auth: AUTH }
    );
    
    return response.status === 200;
  } catch (error) {
    console.error('Error deleting object:', error.message);
    return false;
  }
}

// Example usage
async function runExample() {
  // Create a test bucket
  await createBucket('js-test-bucket');
  
  // Upload a file
  const uploadInfo = await uploadFile('js-test-bucket', './example.txt');
  console.log('Uploaded file:', uploadInfo);
  
  // List all objects
  const objects = await listObjects('js-test-bucket');
  console.log('Objects in bucket:', objects);
  
  // Download a file
  await downloadObject('js-test-bucket', 'example.txt', './downloaded_example.txt');
  console.log('File downloaded successfully');
  
  // Delete the object
  await deleteObject('js-test-bucket', 'example.txt');
  console.log('File deleted successfully');
}

runExample().catch(console.error);
```

## Development Guidelines

### Architecture Overview

Local S3 follows a simple architecture pattern:

1. **FastAPI Application**: The main server component that handles HTTP requests
2. **Pydantic Models**: Data validation for requests and responses
3. **Storage Layer**: Simple filesystem operations for bucket and object management
4. **Authentication**: HTTP Basic Auth for securing endpoints

### Project Structure

```
/local-s3
  server.py          # Main server implementation with API endpoints
  test_server.py     # Test cases for the API
  requirements.txt   # Python dependencies
  /storage           # Root directory for stored buckets and objects
```

### Extending the Service

Here are some ways you might extend Local S3 for your needs:

1. **Custom Metadata**: Add support for custom metadata on objects
2. **Versioning**: Implement object versioning
3. **Role-based Access**: Enhance the security model
4. **Multipart Uploads**: Add support for large file uploads
5. **Lifecycle Policies**: Implement expiration and archiving rules

## Storage Structure

Files are stored locally in a directory structure that mimics S3:

```
/storage
  /bucket1
    file1.txt
    file2.jpg
  /bucket2
    file3.pdf
```

Each bucket is implemented as a directory, and each object is stored as a file within its bucket directory. Metadata is currently handled at the API level and derived from file system properties (creation time, size, etc.).

## Testing

Local S3 includes a test suite in `test_server.py` that verifies all major API functionality.

### Running Tests

```bash
python -m unittest test_server.py
```

The test suite:
- Starts the server in a separate thread
- Creates test buckets and objects
- Verifies all API operations work correctly
- Cleans up test data between tests

### Writing Additional Tests

To add new tests, extend the `TestLocalS3` class in `test_server.py`. Each test method should:

1. Set up any required test data
2. Execute the API operation being tested
3. Assert the expected behavior
4. Clean up any created resources (the `setUp` method will handle most of this)

## Common Patterns and Best Practices

### Working with Local S3

1. **Error Handling**: Always check response status codes when interacting with the API
2. **Bucket Naming**: Use consistent bucket naming conventions (e.g., all lowercase, no special characters)
3. **File Organization**: Organize objects with prefixes to simulate directories (e.g., `images/photo1.jpg`)
4. **Authentication**: Store credentials securely in environment variables
5. **Content Types**: Set appropriate content types when uploading files for proper handling when downloaded

### Migration to AWS S3

If you plan to eventually move from Local S3 to AWS S3:

1. Use libraries that abstract S3 operations (boto3 for Python, AWS SDK for JavaScript)
2. Implement a configuration toggle to switch between Local S3 and AWS S3
3. Use environment variables to configure endpoints and credentials
4. Consider using the same bucket naming conventions and object keys

## Troubleshooting

### Common Issues

#### Server Won't Start

- **Port Conflict**: The default port 8000 might be in use. Change the port in `server.py`.
- **Permission Issues**: Ensure you have write access to the storage directory.

#### Authentication Problems

- Verify you're using the correct credentials (default: admin/password)
- Check that you're properly encoding the Authorization header

#### Object Upload Fails

- Ensure the bucket exists before uploading
- Check file permissions
- Verify you're using the correct Content-Type for multipart form uploads

### Debugging

1. **Enable Verbose Logging**: Modify the server to increase log verbosity
2. **Check Storage Directory**: Examine the physical files to verify storage operations
3. **Use API Documentation**: The Swagger UI at `/docs` can help diagnose issues

## Limitations

This is a simplified implementation of S3 and does not include features like:

- **Versioning**: No support for multiple versions of the same object
- **Access Control Lists (ACLs)**: Limited to basic authentication, no fine-grained permissions
- **Cross-Origin Resource Sharing (CORS)**: No CORS support for browser access
- **Server-Side Encryption**: No encryption of stored objects
- **Multipart Uploads**: Limited to single-part uploads (file size constraints)
- **Website Hosting**: No static website hosting capabilities
- **Lifecycle Policies**: No automatic deletion or archiving
- **Transfer Acceleration**: No optimized upload/download speeds
- **Event Notifications**: No event hooks for object operations

## License

MIT

---

Developed as a lightweight local alternative to Amazon S3 for development and testing purposes.
