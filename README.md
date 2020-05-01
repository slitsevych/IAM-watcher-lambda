Re-factored script: 

- compatible with Python3 runtimes
- parsing S3 logs on SNS topic trigger
- sends richly formatted Slack notification 

Watch Cloudtrail for IAM events and post them to Slack.

Note the slack configuration at the top of lambda.py: it is advised to set environment variables in the Lambda directly
```
SNS_TOPIC = "arn:aws:sns...." # change me
SLACK_HOOK = "https://hooks.slack.com/services/<asdf>/<asdf>/<asdf>"  # change me
SLACK_CHANNEL = "general"  # change me
```
Script uses "requests" library which is not available in Lambda by default. 
It can be added manually: 
- git clone "repo" && cd "repo"
- cd ./deps/
- aws lambda publish-layer-version --layer-name requests \
      --description "requests package" \
      --zip-file fileb://../requests.zip \
      --compatible-runtimes python3.6


You'll need to configure SNS topic to allow Event Notifications from an S3 Bucket and IAM Role for the Lambda functions. More details on this matter in the following article:
https://aws.amazon.com/blogs/compute/fanout-s3-event-notifications-to-multiple-endpoints/ 

Use test-sns-notification-s3-event.json to trigger function in test mode:
- change TopicArn to match your SNS topic
- under "Message" look for {\"key\":\"CloudTrail/AWSLogs/1234567890/CloudTrail/us-east-1/1970/01/01/1234567890_CloudTrail_us-east-1_197001019T1005Z_2Iys7xENXi4MtQoU.json.gz\" and change to correct key containing IAM change (make some changes beforehand to create such file)
- "1234567890" is dummy AWS account ID, change with correct ID.s