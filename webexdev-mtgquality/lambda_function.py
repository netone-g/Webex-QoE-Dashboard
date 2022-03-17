import json
import os
import logging
import decimal
import base64
import urllib.request
import urllib.parse
import boto3
from botocore.exceptions import ClientError
from urllib import error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ['AWS_DEFAULT_REGION']

def lambda_handler(event, context):
    logging.info(event)

    SecretReturn = json.loads(get_secret(os.environ['SECRETMANAGER_NAME'], REGION))
    Token = json.loads(get_secret(os.environ['SECRETMANAGER_TOKEN_NAME'], REGION))
    
    hostEmail = SecretReturn['hostEmail']
    CLIENT_ID = SecretReturn['CLIENT_ID']
    CLIENT_SECRET = SecretReturn['CLIENT_SECRET']
    ACCESS_TOKEN = Token['ACCESS_TOKEN']
    REFRESH_TOKEN = Token['REFRESH_TOKEN']

    latest_token = json.loads(oauth(ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET))
    
    put_secret(os.environ['SECRETMANAGER_TOKEN_NAME'], latest_token['access_token'], latest_token['refresh_token'])
    
    try:
        mtg_res = get_meetings(ACCESS_TOKEN, hostEmail)
        active_meetingid = mtg_res['items'][0]['id']
        
        qual_res = get_meeting_quality(ACCESS_TOKEN, active_meetingid)
        logging.info("get_meeting_quality: {}".format(json.dumps(qual_res, indent=4, ensure_ascii=False)))
        qual_res = qual_res['items']
        
        for i, item in enumerate(qual_res):
            payload = {
                "meetingid": qual_res[i]['meetingInstanceId'],
                "useremail": qual_res[i]['webexUserEmail'],
                "jointime": qual_res[i]['joinTime'],
                "leavetime": qual_res[i]['leaveTime'],
                "serverregion": qual_res[i]['serverRegion'],
                "items": json.loads(json.dumps(qual_res[i]), parse_float=decimal.Decimal)
            }
            db_response = write_dynamodb(payload, os.environ['DYNAMODB_TABLENAME'])
            if db_response['ResponseMetadata']['HTTPStatusCode'] == 200:
                logging.info("DB Input Success.")
            else:
                logging.info("DB Input Failed.")
    except Exception as e:
        logger.error(f'{e}')
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def oauth(access_token: str, refresh_token: str, client_id: str, client_secret: str):
    url = "https://webexapis.com/v1/access_token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Bearer " + access_token
    }
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    
    data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data, headers)
    
    try:
        with urllib.request.urlopen(req) as f:
            update_token_result = f.read().decode("utf-8")
        logging.info("update_token_result: {}".format(update_token_result))
    except error.HTTPError as e:
        update_token_result = "null"
        logging.error(e)
        logging.error('Error:Could NOT UPDATE Token')
    return update_token_result

def get_meetings(token: str, hostEmail: str):
    meetingType = "meeting"
    state = "inProgress"
    hostEmail = hostEmail
    
    url = "https://webexapis.com/v1/meetings" + "?meetingType=" + meetingType + "&state=" + state + "&hostEmail=" + hostEmail
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer " + token
    }
    req = urllib.request.Request(url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as f:
        result = json.load(f)

    return result

def get_meeting_quality(token: str, id: str):
    url = "https://analytics.webexapis.com/v1/meeting/qualities" + "?meetingId=" + id
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer " + token
    }
    req = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.urlopen(req) as f:
        result = json.load(f)

    return result

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


def put_secret(secret_name: str, access_token: str, refresh_token: str):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )

    response = client.put_secret_value(
        SecretId=secret_name,
        SecretString='{"ACCESS_TOKEN":"' + access_token + '",' + '"REFRESH_TOKEN":"' + refresh_token + '"}',
    )
    return response

def write_dynamodb(message: dict, tablename: str):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(tablename)
  
    response = table.put_item(
        Item=message
    )
    return response
