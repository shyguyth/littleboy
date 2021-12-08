from flask import Flask, request, make_response
import json
import cv2,os,time
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(5,GPIO.OUT)
from DHT_Python import dht22
instance = dht22.DHT22(pin=4)
from datetime import datetime

from glob import glob
from pyrebase import pyrebase

#config firebase
config = {'apiKey': "AIzaSyD42YspdSeyDl-1EL5M6cZAhJ2TLcSmXwQ",
  'authDomain': "raspberripi-7acbb.firebaseapp.com",
  'databaseURL': "https://raspberripi-7acbb-default-rtdb.asia-southeast1.firebasedatabase.app",
  'projectId': "raspberripi-7acbb",
  'storageBucket': "raspberripi-7acbb.appspot.com",
  'messagingSenderId': "911414191962",
  'appId': "1:911414191962:web:d9d71addcfae0a916b7563",
  'measurementId': "G-31123X5NZ2"}

firebase = pyrebase.initialize_app(config)
db = firebase.database()



app = Flask(__name__)
@app.route('/', methods=["POST"])




def webhook():
    #รับ intent จาก Dailogflow
    question_from_user = request.get_json(silent=True, force=True)
    #เรียกใช้ฟังก์ชันเพื่อแยกส่วนของuserinput
    answer_from_bot = generating_answer(question_from_user)
    
    #ตอบกลับไปที่ Dailogflow
    r = make_response(answer_from_bot)
    r.headers['Content-Type'] = 'application/json' #การตั้งค่าประเภทของข้อมูลที่จะตอบกลับไป
    return r

def generating_answer(question_from_user):
    #Print intent ที่รับมาจาก Dailogflow
    print(json.dumps(question_from_user, indent=4 ,ensure_ascii=False))
    #เก็บค่า ชื่อของ intent ที่รับมาจาก Dailogflow
    group_question_str = question_from_user["queryResult"]["intent"]["displayName"]
    
    if group_question_str == 'temp':
        answer_str = temp_room(question_from_user)
    elif group_question_str == 'humi':
        answer_str = humi_room(question_from_user)
    elif group_question_str == 'ledon':
        answer_str = led_on(question_from_user)
    elif group_question_str == 'ledoff':
        answer_str = led_off(question_from_user)
    elif group_question_str == 'จำนวนคน':
        answer_str = cam()
        answer_str += "\npreview picture(Y/N)"
        savepic()
    else: answer_str = answer_function
    
    #สร้างการแสดงของ dict 
    answer_from_bot = {"fulfillmentText": answer_str}
    
    
    #แปลงจาก dict ให้เป็น JSON
    answer_from_bot = json.dumps(answer_from_bot, indent=4)
    
    return answer_from_bot

        
def temp_room(respond_dict):
    answer_function = ""
    result= instance.read()
    while not result.is_valid():
        result= instance.read()
        temperature =round(result.temperature,2)
        print(temperature)
    else:
        temperature =round(result.temperature,2)
        answer_function = str(temperature)
    return answer_function+"°C ครับ"


def humi_room(respond_dict):
    answer_function = ""
    result= instance.read()
    while not result.is_valid():
        result= instance.read()
        humidity = round(result.humidity,2)
        print(humidity)
    else:
        humidity = round(result.humidity,2)
        answer_function = str(humidity)
    return answer_function+ "% ครับ"

def led_on(respond_dict):
    answer_function = ""
    GPIO.output(5,1)
    answer_function = "เปิดไฟแล้ว"
    return answer_function

def led_off(respond_dict):
    answer_function = ""
    GPIO.output(5,0)
    answer_function = "ปิดไฟแล้ว"
    return answer_function

def date():
    date = datetime.now()
    return date.strftime('%Y.%m.%d.%H.%M')

#นำรูปจากโฟลเดอร์ Allpicture มาหาจำนวนใบหน้า
def facedetect():
    face_cascade= cv2.CascadeClassifier('face-detect.html')
    for face in sorted(glob(os.path.join('Allpicture','*.jpg'))):
        img = cv2.imread(face)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        person = 1
        for x,y,w,h in faces:
            cv2.rectangle(img,(x,y),(x+w,y+h),(0,200,0),2)
            cv2.putText(img,f'person{person}',(x,y-10),cv2.FONT_HERSHEY_TRIPLEX,0.3,(0,200,0),1)
            person+=1
    cv2.putText(img,f'Total person: {person-1}',(20,20),cv2.FONT_HERSHEY_TRIPLEX,0.5,(50,200,0),2)
    cv2.imwrite(os.path.join('detectpic',os.path.split(face)[-1]),img) #เซฟรูปลงโฟลเดอร์ detectpic
    return person-1
        
def cam():
    cam = cv2.VideoCapture('rtsp://192.168.43.1:8080/h264_pcm.sdp') #ต่อกล้องแบบip camera
    while True:
        ret, frame = cam.read()
        frameresize = cv2.resize(frame,(1080//3,720//3))
        if not ret:
            print("failed")
            break
        k =cv2.waitKey(1)
        if k & 0xff  == ord('q'):
            break
        else:
            img_name ="{0}.jpg".format(date())
            filename = os.path.join('Allpicture',img_name)
            cv2.imwrite(filename,frameresize)  #เซฟรูปลงโฟลเดอร์Allpicture
            facedetect() #เรียกใช้ฟังชั่นเพื่อหาใบหน้า
            answer_function = str(facedetect())
            return answer_function + " คน" #ส่งคำตอบจำนวนใบหน้า

    cam.release()
    cam.destroyAllWindows()
        


#่รูปล่าสุดในโฟลเดอร์  
def newest(path):
    files = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in files]
    return max(paths, key=os.path.getctime)

 #เซฟรูปลงfirebase
def savepic():
    storage = firebase.storage()
    y =newest('detectpic')  #รูปล่าสุดในโฟลเดอร์detectpic 
    print(y)
    storage.child('image').put(y)
    url = storage.child("image").get_url(None)
    print(url)




if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port %d" % port)
    app.run(debug=False, port=port, host='0.0.0.0', threaded=True)


