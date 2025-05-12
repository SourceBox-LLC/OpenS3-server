# OpenS3 SDK

A boto3-like Python SDK for interacting with OpenS3, a local implementation of Amazon S3-like functionality.

## Installation

```bash
pip install opens3
```

## Usage

```python
import opens3

# Create a client with default credentials
s3 = opens3.client('s3', endpoint_url='http://localhost:8000')

# Create a client with custom credentials
s3 = opens3.client('s3', 
                  endpoint_url='http://localhost:8000',
                  aws_access_key_id='admin',
                  aws_secret_access_key='password')

# Create a bucket
s3.create_bucket(Bucket='my-bucket')

# List buckets
response = s3.list_buckets()
for bucket in response['Buckets']:
    print(f"Bucket: {bucket['Name']}, Created: {bucket['CreationDate']}")

# Upload an object
s3.put_object(
    Bucket='my-bucket',
    Key='hello.txt',
    Body=b'Hello World!'
)

# List objects
response = s3.list_objects_v2(Bucket='my-bucket')
for obj in response['Contents']:
    print(f"Object: {obj['Key']}, Size: {obj['Size']} bytes")

# Download an object
response = s3.get_object(Bucket='my-bucket', Key='hello.txt')
content = response['Body'].content
print(f"Content: {content.decode('utf-8')}")

# Upload a file
s3.upload_file('local_file.txt', 'my-bucket', 'remote_file.txt')

# Download a file
s3.download_file('my-bucket', 'remote_file.txt', 'downloaded_file.txt')

# Delete an object
s3.delete_object(Bucket='my-bucket', Key='hello.txt')

# Delete a bucket
s3.delete_bucket(Bucket='my-bucket')
```

## Compatibility with boto3

This SDK aims to provide a compatible interface with boto3 for the most common S3 operations.
It's designed to make it easy for developers to switch between AWS S3 and OpenS3 with minimal code changes.

## Features

* Bucket operations (create, list, delete)
* Object operations (put, get, list, delete)
* File upload and download helpers
* Prefix-based object filtering

## License

MIT