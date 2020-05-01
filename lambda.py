from __future__ import print_function
import urllib.request as urllib
import urllib.parse
import os
import json
import boto3
import requests
from io import BytesIO
from gzip import GzipFile

print('Loading function')

s3 = boto3.client('s3')

webhook_url = os.environ['SLACK_HOOK']
slack_channel = os.environ['SLACK_CHANNEL']

ACCEPT = ["iam.amazonaws.com"]
WATCHLIST_INFO = [
    "DeactivateMFADevice",
    "DeleteAccessKey",
    "DeleteAccountAlias",
    "DeleteAccountPasswordPolicy",
    "DeleteGroup",
    "DeleteGroupPolicy",
    "DeleteInstanceProfile",
    "DeleteLoginProfile",
    "DeleteOpenIDConnectProvider",
    "DeletePolicy",
    "DeletePolicyVersion",
    "DeleteRole",
    "DeleteRolePolicy",
    "DeleteSAMLProvider",
    "DeleteServerCertificate",
    "DeleteServiceSpecificCredential",
    "DeleteSigningCertificate",
    "DeleteSSHPublicKey",
    "DeleteUser",
    "DeleteUserPolicy",
    "DeleteVirtualMFADevice",
    "DetachGroupPolicy",
    "DetachRolePolicy",
    "DetachUserPolicy",
    "RemoveClientIDFromOpenIDConnectProvider",
    "RemoveRoleFromInstanceProfile",
    "RemoveUserFromGroup"
]
WATCHLIST_WARN = [
    "AddUserToGroup",
    "AttachGroupPolicy",
    "AttachRolePolicy",
    "AttachUserPolicy",
    "ChangePassword",
    "CreateAccessKey",
    "CreateAccountAlias",
    "CreateGroup",
    "CreateInstanceProfile",
    "CreateLoginProfile",
    "CreateOpenIDConnectProvider",
    "CreatePolicy",
    "CreatePolicyVersion",
    "CreateRole",
    "CreateSAMLProvider",
    "CreateServiceLinkedRole",
    "CreateServiceSpecificCredential",
    "CreateUser",
    "CreateVirtualMFADevice",
    "PutGroupPolicy",
    "PutRolePolicy",
    "PutUserPolicy",
    "UpdateAccessKey",
    "UpdateAccountPasswordPolicy",
    "UpdateAssumeRolePolicy",
    "UpdateGroup",
    "UpdateLoginProfile",
    "UpdateOpenIDConnectProviderThumbprint",
    "UpdateRoleDescription",
    "UpdateSAMLProvider",
    "UpdateServerCertificate",
    "UpdateServiceSpecificCredential",
    "UpdateSigningCertificate",
    "UpdateSSHPublicKey",
    "UpdateUser",
    "UploadServerCertificate",
    "UploadSigningCertificate",
    "UploadSSHPublicKey"
]
WATCHLIST_IGNORE = [
    "AddClientIDToOpenIDConnectProvider",
    "AddRoleToInstanceProfile",
    "EnableMFADevice",
    "GenerateCredentialReport",
    "GetAccessKeyLastUsed",
    "GetAccountAuthorizationDetails",
    "GetAccountPasswordPolicy",
    "GetAccountSummary",
    "GetContextKeysForCustomPolicy",
    "GetContextKeysForPrincipalPolicy",
    "GetCredentialReport",
    "GetGroup",
    "GetGroupPolicy",
    "GetInstanceProfile",
    "GetLoginProfile",
    "GetOpenIDConnectProvider",
    "GetPolicy",
    "GetPolicyVersion",
    "GetRole",
    "GetRolePolicy",
    "GetSAMLProvider",
    "GetServerCertificate",
    "GetSSHPublicKey",
    "GetUser",
    "GetUserPolicy",
    "ListAccessKeys",
    "ListAccountAliases",
    "ListAttachedGroupPolicies",
    "ListAttachedRolePolicies",
    "ListAttachedUserPolicies",
    "ListEntitiesForPolicy",
    "ListGroupPolicies",
    "ListGroups",
    "ListGroupsForUser",
    "ListInstanceProfiles",
    "ListInstanceProfilesForRole",
    "ListMFADevices",
    "ListOpenIDConnectProviders",
    "ListPolicies",
    "ListPolicyVersions",
    "ListRolePolicies",
    "ListRoles",
    "ListSAMLProviders",
    "ListServerCertificates",
    "ListServiceSpecificCredentials",
    "ListSigningCertificates",
    "ListSSHPublicKeys",
    "ListUserPolicies",
    "ListUsers",
    "ListVirtualMFADevices",
    "ResetServiceSpecificCredential",
    "ResyncMFADevice",
    "SetDefaultPolicyVersion",
    "SimulateCustomPolicy",
    "SimulatePrincipalPolicy"
]

WATCHLIST = WATCHLIST_INFO + WATCHLIST_WARN


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
            if record["eventSource"] in ACCEPT:
                if record["eventName"] not in WATCHLIST:
                    continue
                print("found IAM change in log " + key)
                arn = record["userIdentity"]["arn"]
                event = record["eventName"]
                color = "warning" if event in WATCHLIST_INFO else "danger"
                pretext = "`Alert level: Info` \n\n Event details:" if event in WATCHLIST_INFO else "`Alert level: Warning` \n Event details:"
                attachment = {
                    "fallback": "New incoming IAM Alert",
                    "color": "%s" % (color),
                    "pretext": "%s" % (pretext),
                    "text": "*User Identity* *`%s`* performed *`%s`*: " % (arn, event),
                    "fields": [
                        {   
                            "value": "*%s*: %s" % (k, v),
                            "short": False
                        } 
                        for k, v in record["requestParameters"].items()
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

