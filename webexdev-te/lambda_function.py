import json
import logging
import os
import boto3
import base64
import urllib.request
import urllib.parse
import datetime
import decimal
import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger()
logger.setLevel(logging.INFO)
today = datetime.date.today()
str_today = today.strftime('%Y-%m-%d')
strjstnow = today.strftime("%Y-%m-%dT%H:%M:%S")
REGION = os.environ['AWS_DEFAULT_REGION']

def lambda_handler(event, context):
    if event.get("source") == "aws.events":
        SecretReturn = json.loads(
            get_secret(os.environ["SECRETMANAGER_NAME"], REGION))
        TE_OAUTHBEARER_TOKEN = SecretReturn["TE_OAUTHBEARER_TOKEN_V7"]
        mmp_res = get_te_mmp(TE_OAUTHBEARER_TOKEN)
        put_message_to_s3(json.dumps(mmp_res, indent=4), str_today)

        paths = mmp_res["net"]["pathVis"]
        put_message_to_s3(
            json.dumps(extract_nodes_and_links(paths), indent=4), "resource")
        logging.info(json.dumps(extract_nodes_and_links(paths)))

        wz_res = get_te_wz(TE_OAUTHBEARER_TOKEN)
        paths_wz = wz_res["net"]["pathVis"]
        put_message_to_s3(
            json.dumps(extract_nodes_and_links(paths_wz), indent=4), "resource-wz")
        logging.info(json.dumps(extract_nodes_and_links(paths_wz)))

        cb_res = get_te_cb(TE_OAUTHBEARER_TOKEN)
        paths_cb = cb_res["net"]["pathVis"]
        put_message_to_s3(
            json.dumps(extract_nodes_and_links(paths_cb), indent=4), "resource-cb")
        logging.info(json.dumps(extract_nodes_and_links(paths_cb)))

        mmp_net_res = get_te_mmp_net(TE_OAUTHBEARER_TOKEN)
        metrics = mmp_net_res['net']['metrics']
        logging.info("metrics: {}".format(json.dumps(metrics, indent=4, ensure_ascii=False)))
        http_web_res = get_te_http_web(TE_OAUTHBEARER_TOKEN)
        response = http_web_res['web']['httpServer']
        logging.info("response: {}".format(json.dumps(response, indent=4, ensure_ascii=False)))
        payload = {
            "datetime": strjstnow,
            "metrics": json.loads(json.dumps(metrics), parse_float=decimal.Decimal),
            "response": json.loads(json.dumps(response), parse_float=decimal.Decimal)
        }
        write_dynamodb(payload, os.environ['DYNAMODB_TABLENAME_PO'])
    else:
        logging.info("event: {}".format(json.dumps(event, indent=4, ensure_ascii=False)))
        agentName = []
        metric = []
        for item in event['alert']['agents']:
            agentName.append(str(item['agentName']))
            metric.append(item['metricsAtStart'])
        payload = {
            "datetime": strjstnow,
            "evnetid": event['eventId'],
            "type": event['alert']['type'],
            "agentName": agentName,
            "metric": metric,
            "ruleExpression": event['alert']['ruleExpression'],
            "items": event
        }
        write_dynamodb(payload, os.environ['DYNAMODB_TABLENAME'])
    return {
        "statusCode": 200,
        "body": json.dumps("Hello from Lambda!")
    }
def gen_network_graph(nodes: list, links: list):
    DG = nx.DiGraph()
    DG.add_nodes_from(nodes)
    DG.add_edges_from(links)
    DGdata = json_graph.node_link_data(DG)
    return DGdata


def extract_nodes_and_links(paths: list):
    d3_datasets = []
    for path in paths:
        for route in path["routes"]:
            nodes = []
            max_hops = route["hops"][-1]["hop"]
            for i in range(max_hops):
                nc = "inactive"
                for hop in route["hops"]:
                    rt = None
                    ip = None
                    nw = None
                    lc = None
                    if i + 1 == hop["hop"]:
                        nc = "active"
                        rt = hop["responseTime"] if "responseTime" in hop else None
                        ip = hop["ipAddress"] if "ipAddress" in hop else None
                        nw = hop["network"] if "network" in hop else None
                        lc = hop["location"] if "location" in hop else None
                        break
                nodes.append(
                    (i, {
                        "name": f"hop{i+1}",
                        "nc": nc,
                        "rt": rt,
                        "ip": ip,
                        "nw": nw,
                        "lc": lc
                    })
                )
            links = [(j, j + 1) for j in range(max_hops - 1) if j != max_hops - 1]
            d3_datasets.append(gen_network_graph(nodes, links))

    return d3_datasets


def get_secret(secret_name: str, region_name: str):
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        raise e
    else:
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
        else:
            secret = base64.b64decode(
                get_secret_value_response['SecretBinary'])
    return secret


def put_message_to_s3(bodycombine: str, d: str):
    filename = d + ".json"
    aclname = "private"
    s3 = boto3.client("s3")
    s3.put_object(Bucket=os.environ["S3_BUCKET_NAME"],
                  Key=filename, Body=bodycombine,
                  ACL=aclname)
    return True


def get_te_mmp(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_MMP"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result

def get_te_wz(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_WZ"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result

def get_te_cb(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_CD"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result

def get_te_http(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_HTTP"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result


def write_dynamodb(message: dict, tablename: str):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(tablename)
    table.put_item(
        Item=message
    )
    return


def get_te_mmp_net(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_MMP_NET"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result


def get_te_http_web(token: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token
    }
    url = os.environ["API_URL_HTTP_WEB"]
    req = urllib.request.Request(
        url, data={}, method="GET", headers=headers)
    with urllib.request.urlopen(req) as res:
        result = json.load(res)
    return result
