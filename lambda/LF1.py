import json
import base64
import boto3
import time
import math, random


import sys
sys.path.insert(1, '/opt')
import cv2

from random import randint

def get_visitor_photo(fragment_number):
    
    # get kinesis video endpoint
    client = boto3.client('kinesisvideo')
    response = client.get_data_endpoint(
        StreamName='ExampleStream',
        APIName='GET_MEDIA'
    )
    print("Kinesis Video response for endpoint ", response)
    endpoint = response.get('DataEndpoint', None)
    print("endpoint %s" % endpoint)
    stream_size = response['ResponseMetadata']['HTTPHeaders']['content-length']

    # use the above endpoint to fetch stream from the GET_MEDIA API of kinesis
    if endpoint is not None:
        client2 = boto3.client('kinesis-video-media', endpoint_url=endpoint)
        response = client2.get_media(
            StreamName='ExampleStream',
            StartSelector={
                'StartSelectorType': 'NOW',
            }
        )
        print("Response from GET_MEDIA ", response)
        
        # our S# Bucket
        s3 = boto3.client('s3')
        bucket = 'b1photobucket'
        
        
        uid = str(response['ResponseMetadata']['RequestId'])
        image_name = str(uid + ".jpg")
        
        name = str("/tmp/" + uid)
        video_path = str(name + ".webm")
        stream_processed = False #to check if stream has been processed so that we can return accordingly
        
        print('Going to try and get stream')
        # open a temp file as write in binary
        with open(video_path, 'wb') as f:
            while True:
                try:
                    stream = response['Payload'].read(1024*16384) # botocore.response.StreamingBody object of 16 MB read size
                except:
                    stream = None
                    
                if stream is None: #retry to read the fragment
                    continue
                else:
                    f.write(stream)
                    stream_processed = True
                    print("stream_processed")
                    
                    #------ REMOVE THIS AFTER TESTING --------
                    response = s3.upload_file(video_path, bucket, video_path)
                    print(response)
                    # --------------------
                    
                    #write the frame to a temp file
                    cap = cv2.VideoCapture(video_path)
                    ret, frame = cap.read()
                    print(frame)
                    image_path = str(name + ".jpg")
                    cv2.imwrite(image_path, frame)
                    
                    # upload the temp image to s3
                    s3.upload_file(image_path, bucket, image_name)
                    cap.release()
                    # s3.put_object(Bucket=bucket, Body=frame, Key=image_name, ContentType="image/jpeg")
                    print("Image Uploaded Successfully!")
                    
                    url = "https://" + str(bucket) + ".s3.amazonaws.com/" + image_name
                    print("URL of the image uploaded", url)
                    break
        
        if stream_processed:
            return url, image_name
        else:
            return None, None

def get_face_id_from_photo(photo_name):
    
    client=boto3.client('rekognition')
    collection_id='DoorFaceCollection'
    bucket = 'b1photobucket'
    
    response=client.index_faces(CollectionId=collection_id,
                                Image={'S3Object':{'Bucket':bucket,'Name':photo_name}},
                                ExternalImageId=photo_name,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])
    # print ('Results for ' + photo) 
    # print('Faces indexed:')
    print(response)
    face_ids = []
    for faceRecord in response['FaceRecords']:
      face_ids.append(faceRecord['Face']['FaceId'])

    if len(face_ids) >= 1:
        return face_ids[0]
    else:
        return None
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
    # print(event, context)
    # dynamodb = boto3.client('dynamodb')
    ses = boto3.client('ses')# What is this?
    print (" Triggered now ")
    for record in event['Records']:
        #Kinesis data is base64 encoded so decode here
        print(record)
        print("-------")
        payload=base64.b64decode(record["kinesis"]["data"])
        print("Decoded payload: " + str(payload))
        time_c=int(time.time()) # Current time
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1') # Table object
        table2 = dynamodb.Table('DB2')
        is_new_visitor = False
        face_search_response = json.loads(payload.decode('UTF-8')).get('FaceSearchResponse')
        if face_search_response:
            # Match
            face_search_resp = face_search_response[0]
            matched_faces_response = face_search_resp.get('MatchedFaces')
            if matched_faces_response:
                matched_faces_resp = matched_faces_response[0]
                face_obj = matched_faces_resp.get('Face')
                if face_obj:
                    face_id = face_obj.get('FaceId')
                    print ('Face id {0} found'.format(str(face_id)))
                    # Old visitor stuff here
                    #retrieve phone number and name, add new photo, store otp and send otp
                    response = table2.get_item(
                        Key={
                            'face_id':face_id
                            }
                            )
                    print (response)
                    user_name=response['Item']['name']
                    user_phone=response['Item']['phoneNumber']
                    input_information = json.loads(payload.decode('UTF-8')).get('InputInformation')
                    kinesis_video = input_information.get('KinesisVideo')
                    fragment_number = kinesis_video.get('FragmentNumber')
                    photo_link, photo_name = get_visitor_photo(str(fragment_number))
                    if photo_link is not None and photo_name is not None:
                        new_photo={
                            'object_key':photo_name,
                            'bucket':'b1photobucket',
                            'created_timestamp':time_c
                            }
                        response['Item']['photos'].append(new_photo)
                        r2=table2.delete_item(
                                Key={
                                    'face_id':face_id
                                }
                            )
                        table2.put_item(Item=response['Item'])
                        
                        
                    otp=generateOTP()
                    time_e=time_c+300# Storing otp with time expiration
                    table1 = dynamodb.Table('DB1')
                    table1.put_item(
                        Item={
                            'face_id': face_id,
                            'otp':otp,
                            'current_time': time_c,
                            'expiration_time':time_e
                        })
                    url = "s3://doorsecurityvisitorpagewp2/wp2.html?face_id="+str(face_id)
                    template="Hi "+str(user_name)+" .Welcome to our home. Your OTP is "+str(otp)+". Please go to the following page to gain access "+str(url)
                    client4 = boto3.client('sns')
                    response=client4.publish(PhoneNumber=user_phone,Message=template)
                else :
                        is_new_visitor = True
            else :
                is_new_visitor= True
            if is_new_visitor:
                # No match
                print ('The given face doesn\'t match any response.')
                input_information = json.loads(payload.decode('UTF-8')).get('InputInformation')
                kinesis_video = input_information.get('KinesisVideo')
                fragment_number = kinesis_video.get('FragmentNumber')
                photo_link, photo_name = get_visitor_photo(str(fragment_number))
                if photo_link is not None and photo_name is not None:
                    face_id = get_face_id_from_photo(photo_name)
                    approve_link="https://doorsecurityadminpagewp1.s3.amazonaws.com/wp1.html?face_id="+str(face_id)+"&photo_name="+str(photo_name)
                    template="Hi Abhay/Michelle. You have a new visitor at your door. Here is a link to their photo +  "+str(photo_link)+" .Here is a link to approve them "+str(approve_link) 
                    client5 = boto3.client('sns')
                    response=client5.publish(PhoneNumber="+17186665847",Message=template)
                #     if face_id:
                #         # send_photo_and_form_to_owner(ses, photo_link, face_id) #write this function
                #     else:
                #         # WHAT TO DO HERE? ie when no face_id was detected by rekognition
                # else:
        
        else :
            return
    return