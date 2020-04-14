import json
import time
import boto3
def lambda_handler(event, context):
    # TODO implement
    print (event)
    otp_entered = str(event['otp'])
    time_c=int(time.time())
    #otp_entered = incoming_msg["otp"]
    face_id = event['face_id']
    #write code here to verify otp from dynamo db
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table2 = dynamodb.Table('DB2')
    table1 = dynamodb.Table('DB1')
    responses = table1.get_item(
        Key={
            'face_id':face_id
        }
    )
    
    #store in actual_otp
    actual_otp=str(responses['Item']['otp'])
    print ("OTP from DB "+actual_otp)
    expiration=responses['Item']['expiration_time']
    #also get person name
    responses = table2.get_item(
                        Key={
                            'face_id':face_id
                            }
                            )
    name=responses['Item']['name']
    phone=responses['Item']['phone_number']
    #name = "Mike"
    #actual_otp = "123"
    #if(otp_entered==actual_otp):
    if(otp_entered==actual_otp and time_c<expiration):
        #return success message
        response = {}
        response['approve']='yes'
        response['message'] = "Hello "+name+". Granted Access."
        print (response)
        print (json.dumps(response))
        return {
            'statusCode': 200,
            'body': response
        }
    else:
        response = {}
        response['approve']='no'
        response['message'] = "Wrong or expired OTP. Access Denied."
        print (response)
        print (json.dumps(response))
        return {
            'statusCode': 200,
            'body': response
        }
