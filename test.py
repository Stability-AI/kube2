import boto3

client = boto3.client('eks')
client.list_clusters()
