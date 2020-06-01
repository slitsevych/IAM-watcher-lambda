from __future__ import print_function
import urllib.request as urllib
import urllib.parse
import os
import re
import json
import yaml
import boto3
import requests
from io import BytesIO
from gzip import GzipFile

print('Loading function')

s3 = boto3.client('s3')
webhook_url = os.environ['SLACK_HOOK']
slack_channel = os.environ['SLACK_CHANNEL']

ACCEPT = ["iam.amazonaws.com"]

MATCH = (
    "^Add",
    "^Remove",
    "^Set",
    "^Delete",
    "^Deactivate",
    "^Detach",
    "^Upload",
    "^Update",
    "^Put",
    "^Create",
    "^Attach",
    "^Change"
    )

IGNORE = (
    "^List",
    "^Get",
    )

def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    bucket = message['Records'][0]['s3']['bucket']['name']
    key = message['Records'][0]['s3']['object']['key']
    try: 
        s3response = s3.get_object(Bucket=bucket, Key=key)
        bytestream = BytesIO(s3response['Body'].read())
        body = GzipFile(None, 'rb', fileobj=bytestream).read().decode('utf-8')
        j = json.loads(body)
        attachments = []
        for record in j["Records"]:
            match = re.compile('|'.join(MATCH))
            ignore = re.compile('|'.join(IGNORE))
            if record["eventSource"] in ACCEPT:
                for record_name in re.finditer(ignore, record["eventName"]):
                    continue
                for record_name in re.finditer(match, record["eventName"]): 
                    print("found IAM change in log " + key)
                    arn = record["userIdentity"]["arn"].split(':')[5]
                    request_params_json=json.dumps(record["requestParameters"], indent=4, sort_keys=True)
                    request_params=re.sub('["|[|\]|{|}]', '', re.sub('[\\\\]', '', re.sub('[,]', ', ', re.sub('[\n](\s\s\s)+', '\n', re.sub('[n](\s\s)+', '', request_params_json)))))
                    event = record["eventName"]
                    color = "#2eb886"
                    pretext = "*Event Time*: %s \n\n Event details:" % (record["eventTime"].replace('T', ' ').replace('Z', ' '))
                    attachment = {
                        "fallback": "New incoming IAM Alert",
                        "color": "%s" % (color),
                        "pretext": "%s" % (pretext),
                        "text": "*`%s`* --> *`%s`* \n\n " % (arn, event),
                        "fields": [
                            {   
                                "title": "Event Source",
                                "value": "%s" % (record["eventSource"]),
                                "short": True
                            },
                            {   
                                "title": "Account ID",
                                "value": "%s" % (record["userIdentity"]["accountId"]),
                                "short": True
                            },
                            {   
                                "title": "User",
                                "value": "%s" % (record["userIdentity"]["principalId"].split(':')[1]),
                                "short": True
                            },
                            {   
                                "title": "Event Name",
                                "value": "%s" % (record["eventName"]),
                                "short": True
                            },
                            {   
                                "title": "Request Parameters",
                                "value": "%s" % (request_params),
                                "short": False
                            }
                        ],
                        "mrkdwn_in": ["text", "pretext", "color", "fields", "title"]
                    }
                    attachments.append(attachment)
        if attachments:
            if len(attachments) > 20:
                print("warning! too many attachments")
            message = {
                "channel": slack_channel,
                "text": "<!channel>\n*New incoming IAM Alert*",
                "attachments": attachments
                      }
            try:
                response = requests.post(webhook_url, data=json.dumps(message), headers={'Content-Type': 'application/json'})
                print('Response: ' + str(response.text))
                print('Response code: ' + str(response.status_code))
                print('Message posted to channel "' + slack_channel + '"')
                
            except urllib.error.HTTPError as e:
                text=e.reason
                status=e.code
                message = f"""
                    Error sending message to Slack channel {slack_channel}
                    Reason: {text}
                    Status code: {status}
                    """
                print(message)
                raise error
                
            except urllib.error.URLError as e:
                print('Server connection failed: ' + str(e.reason))

        return s3response['ContentType']   

    except Exception as error:
        print(error)
        message = f"""
            Error getting object {key} from bucket {bucket}.
            """
        print(message)
        raise error