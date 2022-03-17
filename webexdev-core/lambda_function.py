import logging
import boto3
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import os
import json
import base64
import operator

logger = logging.getLogger()
logger.setLevel(logging.INFO)
JST = timezone(timedelta(hours=+9), 'JST')
now = datetime.now(JST)
before1h = now + timedelta(hours=-1)
before1h = before1h.strftime("%Y%m%d%H%M%S")
before1h_int = int(before1h)

before12h = now + timedelta(hours=-12)
before12h = before12h.strftime("%Y%m%d%H%M%S")
before12h_int = int(before12h)

before24h = now + timedelta(hours=-24)
before24h = before24h.strftime("%Y%m%d%H%M%S")
before24h_int = int(before24h)

now = datetime.now(JST).strftime("%Y/%m/%d %H:%M:%S")
now1 = datetime.now(JST).strftime("%Y%m%d%H%M%S")
now_comp = int(now1)


# Const(DynamoDB Table Names)
TWITTER = os.environ['DYNAMODB_TABLENAME_TWITTER']
MTGQA = os.environ['DYNAMODB_TABLENAME_MTGQA']
THOUSANDEYES = os.environ['DYNAMODB_TABLENAME_TEPOLLING']
WEBEX_RSS = os.environ['DYNAMODB_TABLENAME_STATUS']

REGION = os.environ['AWS_DEFAULT_REGION']

def lambda_handler(event, context):
    SecretReturn = json.loads(get_secret(os.environ['SECRETMANAGER_NAME'], REGION))
    USEREMAIL = SecretReturn['userEmail']
    
    mtgqa = '''
    <p>Analysis of home environment shows no signs of problems(Conect to WIFI)</p>
    '''
    mtgqa_table = mtgqa_score(USEREMAIL)

    # GENERATE RSS HTML SECTION
    rss_data = get_rss_data()

    # GENERATE TWITTER HTML SECTION
    twitter_data = get_twitter_data()

    # GET ALL COMMENT
    main_com = main_comment()
    quality_com = '''Analysis of home environment shows no signs of problems(Conect to WIFI)'''
    twitter_com = twitter_comment()
    rss_com = rss_comment()
    te_com = te_comment()

    # GET TOTAL SCORE
    score_alg = score_algorithm()
    img_pic = main_img()
    score = calc_total_score()

    cloudwatchURL = os.environ["CLOUDWATCH_URL"]

    wrapper = f'''
    <!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="180" >
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-giJF6kkoqNQ00vy+HMDP7azOuL0xtbfIcaT9wjKHr8RbDVddVHyTfAAsrekwKmP1" crossorigin="anonymous">
    <link rel ="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <link href="style.css" rel="stylesheet" type="text/css" media="all">
    <title>Webex QoE Dashboard</title>
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script type="text/javascript" src="d3.min.js"></script>
</head>
<body>
    <header class="header">
       <p>Webex QoE Dashboard</p>
    </header>
    <main>
        <div class="container-fluid">
            <div class="row">
                <div class="col-md-12">
                    <div class="row">
                        <div class="col-md-8">
                            <div class="row" style="padding-bottom: 25px;">
                                <div class="col-md-4">
                                    <h4><i class="fas fa-heartbeat"></i> Health Score</h4>
                                    <span class="score" style="border-bottom: 10px solid #0096D6; width: 280px;display: block;">{score}</span>
                                    <p><h6>Update:{now}</h6></p>
                                </div>
                                <div class="col-md-4">
                                    <div>
                                        <img src={img_pic}>
                                        {main_com}
                                        <p>◇Health Score Calculation Formula<br>100-(NegativeTweet×(-1)+Routing Infomation+RSS)<br>{score_alg}<br>(Routing Infomation and RSS is decrease per failure information)</p>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <h4><i class="fab fa-twitter"></i>User's Twitter reputation</h4>
                                    {twitter_com}
                                    <h4><i class="fas fa-route"></i>Internet Path Quality Assessment</h4>
                                    {te_com}
                                    <h4><i class="fas fa-rss"></i>Cisco Official Service Availability</h4>
                                    {rss_com}
                                    <h4><i class="fas fa-laptop-house"></i>User's Webex Quality Information</h4>
                                    {quality_com}
                                </div>
                            </div>
                            <div class="row mb-4">
                                <div class="col-md-12 route-info">
                                    <h4 class="wqms-subtitle"> <i class="fas fa-route"></i>Internet Path Quality Assessment</h4>
                                    <div id="te-metric-type-panel">
                                        <div class="btn-group" role="group" aria-label="Basic radio toggle button group">
                                            <input type="radio" class="btn-check" name="btnradio" data-name="mp" id="btnmmp" autocomplete="off" checked>
                                            <label class="btn btn-outline-light" for="btnmmp">Multimedia Platform</label>

                                            <input type="radio" class="btn-check" name="btnradio" data-name="wz" id="btnwz" autocomplete="off">
                                            <label class="btn btn-outline-light" for="btnwz">Web Zone</label>

                                            <input type="radio" class="btn-check" name="btnradio" data-name="cb" id="btncb" autocomplete="off">
                                            <label class="btn btn-outline-light" for="btncb">Collaboration Bridge</label>
                                        </div>
                                        
                                    </div>
                                    <div id="te-panel" class="te-control-panel"></div>
                                    <div id="topology1"></div>
                                    <script type="text/javascript" src="te-grap.js"></script>
                                </div>
                                <div class="col-md-12">
                                    <h4 id="te-detail"><i class="fas fa-info-circle"></i> Detail</h4>
                                    <div id="te-route-information-detail">
                                    <iframe id="inlineFrameExample" title="Inline Frame Example" width="100%" height="400" src="{cloudwatchURL}"></iframe>
                                    </div>
                                    <div class"data-source-info">
                                        <span class="sub-description">Data Source by ThousandEyes</span>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-12 p-4 quality-info">
                                <h4 class="wqms-subtitle"> <i class="fas fa-laptop-house"></i>User's Webex Quality Information</h4>
                                    <table class="table table_sticky">
                                        <thead>
                                          <tr>
                                            <th class="ml-4">Items</th>
                                            <th class="ml-4">AudioIn</th>
                                            <th class="ml-4">AudioOut</th>
                                            <th class="ml-4">VideoIn</th>
                                            <th class="ml-4">VideoOut</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                            {mtgqa}{now}{mtgqa_table}
                                        </tbody>
                                     </table>
                                    <div class"data-source-info">
                                        <span class="sub-description">Data source by Webex Meetings Quality API</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="col-md-12" style="padding: 0 40px;">
                            <h4 class="wqms-subtitle"> <i class="fas fa-rss"></i>Cisco Official Service Availability</h4>
                                <table class="table table_sticky">
                                    <thead>
                                      <tr>
                                        <th class="ml-4">Title</th>
                                        <th class="ml-4">Status</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                        {rss_data}
                                        <p>All location information<br>{now}</p>
                                    </tbody>
                                  </table>
                            </div>
                            <div class="col-md-12" style="padding: 40px;">
                            <h4 class="wqms-subtitle"> <i class="fab fa-twitter"></i>User Twitter reputation</h4>
                                <table class="table">
                                    <thead>
                                      <tr>
                                        <th class="ml-4">Twitter Comment(Latest 5)</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                        {twitter_data}
                                    </tbody>
                                  </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>
</body>
</html>
    '''

    put_message_to_s3(wrapper)
    return "ok"


def put_message_to_s3(bodycombine: str):
    filename = 'index.html'
    contentType = 'text/html'
    aclname = 'private'
    s3 = boto3.client('s3')
    s3.put_object(Bucket=os.environ["S3_BUCKET_NAME"],
                  Key=filename, Body=bodycombine,
                  ContentType=contentType, ACL=aclname)
    return True

def get_twitter_data():
    tw = _scan_record(TWITTER, before24h=before24h_int, now1=now_comp)
    dom = ''
    date_items_sort = sorted(tw, key=operator.itemgetter('datetime'), reverse=True)
    for item in date_items_sort:
        d = str(item['datetime'])
        d_str = d[0:4] + '-' + d[4:6] + '-' + d[6:8] + ' ' + d[8:10] + ':' + d[10:12] + ':' + d[12:14] + ' JST'
        t = item['text']
        s = item['Sentiment']
        if s == 'NEGATIVE':
            dom += f'<tr><td class="wqms-tw-td"><span class="wqms-date">{d_str}</span><br>{t}<br><span class="wqms-sen"><font color=yellow>{s}</font>(-1.0)</td></tr>'
        elif s == 'POSITIVE':
            dom += f'<tr><td class="wqms-tw-td"><span class="wqms-date">{d_str}</span><br>{t}<br><span class="wqms-sen"><font color=aqua>{s}</font>(+0.1)</td></tr>'
        else:
            dom += f'<tr><td class="wqms-tw-td"><span class="wqms-date">{d_str}</span><br>{t}<br><span class="wqms-sen">{s}(+0)</td></tr>'
    return dom


def calc_twitter_score():
    tw = _scan_record(TWITTER, before12h=before12h_int, now1=now_comp)
    sentiment_list = []
    dom = ''
    for data in tw['Items']:
        sentiment_list.append(data['Sentiment'])
        negative_count = int(sentiment_list.count("NEGATIVE"))
        positive_count = int(sentiment_list.count("POSITIVE"))
        dom = float(negative_count) * -2 + round(float(positive_count) * 0.1, 1)
    return dom


def get_rss_data():
    rss_data = _scan_record(WEBEX_RSS)
    count = int(rss_data['Count'])
    dom = ""
    for n in range(count):
        title = rss_data['Items'][n]['title']
        status = rss_data['Items'][n]['Status']
        dom += f'<tr><td>{title}</td><td>{status}</td></tr>'
    return dom


def calc_total_score():
    """ Calculation Total Score
    """
    total = 100.0 + calc_twitter_score() + calc_te_score() + calc_rss_score()
    return total

def score_algorithm():
    dom = ""
    twitter_score = calc_twitter_score()
    te_score = calc_te_score()
    rss_score = calc_rss_score()
    dom = f'<p>100 + ({twitter_score}) + ({te_score}) + ({rss_score})</p>'
    return dom

def main_img():
    score = calc_total_score()
    base = "/img/"
    if 85 <= score:
        return base + "hare.png"
    elif 75 <= score and score < 85:
        return base + "cloud.png"
    elif 65 <= score and score < 75:
        return base + "rain.png"
    else:
        return base + "str.png"


def calc_te_score():
    dom = ''
    te = _scan_record(THOUSANDEYES)
    for data in te['Items']:
        d = data['datetime']
        te_datetime_int = int(d[0:4] + d[5:7] + d[8:10] + d[11:13] + d[14:16] + d[17:19])
        if now_comp >= te_datetime_int and te_datetime_int >= before1h_int:
            dom = -10 + int(calc_te_score_detail())
            break
        else:
            dom = 0
    return dom

def calc_te_score_detail():
    te = _scan_record(THOUSANDEYES)
    dom = ''
    dom = 0
    for data in te['Items']:
        d = data['datetime']
        te_datetime_int = int(d[0:4] + d[5:7] + d[8:10] + d[11:13] + d[14:16] + d[17:19])
        if now_comp >= te_datetime_int and te_datetime_int >= before1h_int:
            metric_str = str(data['metric'])
            metric_split = int(metric_str[16:20])
            met_spl_point = float((metric_split - 400) / 10)
            if met_spl_point >= 1.0:
                dom = met_spl_point * -1
            else:
                dom = 0
    return dom

def main_comment():
    score = calc_total_score()
    if score >= 70:
        return '<p class="wqms-success">Webex seems to be working fine</p>'
    else:
        return '<p class="wqms-danger">Webex may not be working properly</p>'


def twitter_comment():
    score = calc_twitter_score()
    if score <= -20:
        return '<p class="wqms-danger">Twitter detects negative keywords about Webex</p>'
    else:
        return '<p class="wqms-success">The reception from Twitter has been good.</p>'


def rss_comment():
    """ Webex RSS Comment
    """
    rss_data = _scan_record(WEBEX_RSS)
    count = int(rss_data['Count'])
    if count >= 8:
        return '<p class="wqms-danger">Cisco has an announcement about Webex outage</p>'
    else:
        return '<p class="wqms-success">No Webex outage has been announced by Cisco</p>'


def calc_rss_score():
    """ Webex RSS Comment
    """
    rss_data = _scan_record(WEBEX_RSS)
    count = int(rss_data['Count'])
    if count >= 8:
        return -20
    else:
        return 0

def te_comment():
    count = calc_te_score()
    if count <= -20:
        return '<p class="wqms-danger">Analysis by ThousandEyes shows that the network Response Time is worse than usual</p>'
    else:
        return '<p class="wqms-success">No network problems as a result of the ThousandEyes analysis</p>'
        
def mtgqa_score(USEREMAIL: str):
    mtgqa_data = _scan_record(MTGQA)
    audioin_j = []
    for data in mtgqa_data['Items']:
        if data['useremail'] == USEREMAIL:
            audioin_data = data['items']['audioIn']
            audioout_data = data['items']['audioOut']
            videoin_data = data['items']['videoIn']
            videoout_data = data['items']['videoOut']
            for detail in audioin_data:
                audioin_j = int(detail['jitter'][0])
                audioin_p = int(detail['packetLoss'][0])
                audioin_l = int(detail['latency'][0])
                audioin_m = int(detail['mediaBitRate'][0])
            for detail in audioout_data:
                audioout_j = int(detail['jitter'][0])
                audioout_p = int(detail['packetLoss'][0])
                audioout_l = int(detail['latency'][0])
                audioout_m = int(detail['mediaBitRate'][0])
            for detail in videoin_data:
                videoin_j = int(detail['jitter'][0])
                videoin_p = int(detail['packetLoss'][0])
                videoin_l = int(detail['latency'][0])
                videoin_m = int(detail['mediaBitRate'][0])
            for detail in videoout_data:
                videoout_j = int(detail['jitter'][0])
                videoout_p = int(detail['packetLoss'][0])
                videoout_l = int(detail['latency'][0])
                videoout_m = int(detail['mediaBitRate'][0])
            return f'<tr><td>Jitter</td><td>{audioin_j}</td><td>{audioout_j}</td><td>{videoin_j}</td><td>{videoout_j}</td><tr><td>Latency</td><td>{audioin_l}</td><td>{audioout_l}</td><td>{videoin_l}</td><td>{videoout_l}</td></tr><tr><td>MediaBitRate(bps)</td><td>{audioin_m}</td><td>{audioout_m}</td><td>{videoin_m}</td><td>{videoout_m}</td></tr><tr><td>PacketLoss</td><td>{audioin_p}</td><td>{audioout_p}</td><td>{videoin_p}</td><td>{videoout_p}</td></tr>'

def _scan_record(table_name, before1h=None, before12h=None, before24h=None, now1=None, limit=None):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    if before1h is not None:
        options = {
            'FilterExpression': Key('datetime').between(before1h, now1)
        }
        return table.scan(**options)
    elif before12h is not None:
        options = {
            'FilterExpression': Key('datetime').between(before12h, now1)
        }
        return table.scan(**options)
    elif limit is not None:
        options = {
            'limit': limit
        }
        return table.scan(**options)
    elif before24h is not None:
        return table.scan(FilterExpression=Key('datetime').between(before24h, now1)).get('Items', [])[:5]
    else:
        return table.scan()


def _scan_record_forward(table_name, before6h=None, now1=None):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    queryData = table.query(
        FilterExpression=Key('datetime').between(before6h, now1),
        ScanIndexForward=False,
        Limit=5
    )
    return queryData

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

def decimal_default_proc(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
