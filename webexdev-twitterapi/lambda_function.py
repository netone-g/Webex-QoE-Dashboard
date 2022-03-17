import boto3
import json
from requests_oauthlib import OAuth1Session
import logging
import time
import calendar
import os
import base64
from decimal import Decimal
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ['AWS_DEFAULT_REGION']
language_code = 'ja'

def lambda_handler(event, context):
    Token = json.loads(get_secret(os.environ['SECRETMANAGER_NAME'], REGION))
    API_KEY = Token['API_KEY']
    API_SECRET = Token['API_SECRET']
    TOKEN = Token['TWITTER_TOKEN']
    TOKEN_SECRET = Token['TWITTER_TOKEN_SECRET']

    research = research_text(API_KEY, API_SECRET, TOKEN, TOKEN_SECRET)
    for i in range(len(research)):
        text = research['statuses'][i]['text']
        created_at = research['statuses'][i]['created_at']
        time_utc = time.strptime(
            created_at, '%a %b %d %H:%M:%S +0000 %Y')
        unix_time = calendar.timegm(time_utc)
        time_local = time.localtime(unix_time)
        japan_time = time.strftime("%Y%m%d%H%M%S", time_local)
        real_time = int(japan_time)

        result = detect_sentiment(text, language_code)
        result_lan = detect_language(text)
        
        res = {
            'datetime': json.loads(json.dumps(real_time)),
            'text': json.loads(json.dumps(text)),
            'Sentiment': result['Sentiment'],
            'SentimentScore': result['SentimentScore'],
            'unixtime': unix_time,
            'language_code': result_lan
        }

        write_dynamodb(res, os.environ['DYNAMODB_TABLENAME'])
    return{
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def research_text(api_key: str, api_secret: str, token: str, token_secret: str):
    mytwitter = OAuth1Session(api_key, api_secret, token, token_secret)

    API_Plan_Standard = "https://api.twitter.com/1.1/search/tweets.json?q="
    how_many_get_data = 10
    what_type_result_data = "resent"
    search_keyword = "Webex"

    url = API_Plan_Standard + search_keyword + "&result_type=" + \
        what_type_result_data + "&count=" + str(how_many_get_data)
    response = mytwitter.get(url)
    response_data = json.loads(response.text)
    return response_data


def write_dynamodb(message: dict, tablename: str):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(tablename)

    response = table.put_item(
        Item=message
    )
    return response


def detect_sentiment(text: str, language_code: str):
    comprehend = boto3.client('comprehend')
    response = comprehend.detect_sentiment(
        Text=text, LanguageCode=language_code)
    return filter_dict(
        lambda k, v: k in ('Sentiment', 'SentimentScore'), response)

def detect_language(text: str):
    comprehend = boto3.client('comprehend')
    result = comprehend.detect_dominant_language(Text=text)
    item = json.loads(json.dumps(result['Languages']), parse_float=Decimal)
    return item
    
def filter_dict(f, d: dict):
    d = json.loads(json.dumps(d), parse_float=Decimal)
    return {k: v for k, v in d.items() if f(k, v)}

def get_secret(secret_name: str, region_name: str):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
    return secret
