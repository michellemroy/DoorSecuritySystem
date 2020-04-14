import json
import time
import math, random
import boto3
def generateOTP() : 
  
    # Declare a digits variable   
    # which stores all digits  
    digits = "0123456789"
    OTP = "" 
  
   # length of password can be chaged 
   # by changing value in range 
    for i in range(4) : 
        OTP += digits[math.floor(random.random() * 10)] 
  
    return OTP 
def lambda_handler(event, context):
    # TODO implement
    name = event["name"]
    phone = event['phone']
    face_id = event['face_id']
    photo_name = event['photo_name']
    url = "https://doorsecurityvisitorpagewp2.s3.amazonaws.com/wp2.html?face_id="+str(face_id)
    time_c=int(time.time())
    print (event)
    #write code here to enter name and phone into dynamo db
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table2 = dynamodb.Table('DB2')
    table1 = dynamodb.Table('DB1')
    table2.put_item(
            Item={
                'face_id': face_id,
                'name':name,
                'phone_number':phone,
                'photos':[{
                    'object_key':photo_name,
                    'bucket':'b1photobucket',
                    'created_timestamp':time_c
                }]
            })
    # Writing here to save otp in database
    otp=generateOTP()
    time_e=time_c+300# Storing otp with time expiration
    #table1 = dynamodb.Table('DB1')
    table1.put_item(
        Item={
            'face_id': face_id,
            'otp':otp,
            'current_time': time_c,
            'expiration_time':time_e
            })
    template="Hi "+str(name)+" .Welcome to our home. Your OTP is "+str(otp)+". Please go to the following page to gain access "+str(url)
    client4 = boto3.client('sns')
    response=client4.publish(PhoneNumber=phone,Message=template)
    #write code here to send sms to person with phone number
    #link to  otp page
    
    
    
    return {
            'statusCode': 200,
            'body': json.dumps("Hello from Lambda")
        }
