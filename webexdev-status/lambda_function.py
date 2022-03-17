import json
import logging
import os
import boto3
import feedparser

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RSS_URL = 'https://status.webex.com/history.rss'

def lambda_handler(event, context):
    d = feedparser.parse(RSS_URL)
    for entry in d.entries:
        st_entry = entry.description
        target_be  = '<strong>'
        start_index = st_entry.find(target_be)
        target_af = '</strong>'
        end_index = st_entry.find(target_af)
        
        status = st_entry[start_index + len(target_be):end_index]
        res = {
            'title': entry.title,
            'URL': entry.link,
            'Status': status,
        }
        write_dynamodb(res, os.environ['DYNAMODB_TABLENAME'])
    return{
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

    
def write_dynamodb(message: dict, tablename: str):

    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(tablename)
  
    response = table.put_item(
        Item=message
    )
    return response
