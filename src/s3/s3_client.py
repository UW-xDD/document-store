from os import environ
from boto3 import Session

session = Session(aws_access_key_id=environ['S3_ACCESS_KEY'], aws_secret_access_key=environ['S3_SECRET_KEY'])
s3 = session.client("s3", endpoint_url=environ['S3_HOST'], region_name='us-east-1')

def get_presigned_url(bucket: str, path: str):
    """ Return a temporary public URL for read access to an object in a private S3 bucket """
    return s3.generate_presigned_url('get_object', Params={'Bucket':bucket, 'Key':path})

def object_exists(bucket: str, path: str):
    """ Check whether an S3 object exists using `boto3.head_object`"""
    try:
        s3.head_object(Bucket=bucket, Key=path)
        return True
    except:
        return False

def get_object_body(bucket: str, path: str):
    """ Return the body of the s3 object in the given bucket at the given path """
    return s3.get_object(Bucket=bucket, Key=path).get('Body')

def put_object(bucket: str, path: str, body):
    """ Put an s3 object in the given bucket at the given path """
    return s3.put_object(Bucket=bucket, Key=path, Body=body)

def delete_object(bucket: str, path: str):
    """ Delete an object from S3 """
    s3.delete_object(Bucket=bucket, Key=path)
