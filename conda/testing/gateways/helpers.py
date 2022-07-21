import json
import os
from fnmatch import fnmatch
from pathlib import Path


def populate_s3_server(endpoint, bucket_name, data_directory):
    # prepare the s3 connection for our minio instance
    import boto3
    from botocore.client import Config

    # Make the minio bucket public first
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-bucket-policies.html#set-a-bucket-policy
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    bucket_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AddPerm",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                }
            ],
        }
    )
    client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)

    # Minio has to start with an empty directory; once available,
    # we can import all channel files by "uploading" them
    for current, _, files in os.walk(data_directory):
        for f in files:
            path = Path(current, f)
            key = path.relative_to(data_directory)
            client.upload_file(str(path), bucket_name, str(key), ExtraArgs={"ACL": "public-read"})
