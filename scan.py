import cv2 # type: ignore
from pyzbar import pyzbar # type: ignore
from time import sleep
import requests # type: ignore
import json
import pathlib
import logging
from datetime import datetime
import pytz # type: ignore
import os
import sys
import threading
import serial # type: ignore
import keyboard  # type: ignore
import gate
import magnet
import jsonTools
from gpiozero import CPUTemperature # type: ignore

# import Adafruit_GPIO.SPI as SPI # type: ignore
# import Adafruit_SSD1306 # type: ignore

import RPi.GPIO as GPIO # type: ignore

from PIL import Image # type: ignore
from PIL import ImageDraw # type: ignore
from PIL import ImageFont # type: ignore

#----- logger section -----
logging.basicConfig(filename='history.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

#region ---- variables section  -------------
conf = open(str(pathlib.Path().resolve()) + '/config.json')
config = json.loads(conf.read())
conf.close()

display_type = config['screen']['display_type']

if display_type == 'lcd.16x2':
    from Adafruit_CharLCD import Adafruit_CharLCD  # type: ignore

    cols = config['screen']['cols']
    lines = config['screen']['lines']
    rs = config['screen']['rs']
    en = config['screen']['en']
    d4 = config['screen']['d4']
    d5 = config['screen']['d5']
    d6 = config['screen']['d6']
    d7 = config['screen']['d7']
    backlight = config['screen']['backlight']

    disp = Adafruit_CharLCD(rs=rs, en=en, d4=d4, d5=d5, d6=d6, d7=d7,
                        cols=cols, lines=lines, backlight=backlight)
elif display_type == 'oled.128x32':
    from PIL import Image # type: ignore
    from PIL import ImageDraw # type: ignore
    from PIL import ImageFont # type: ignore
    import Adafruit_GPIO.SPI as SPI # type: ignore
    import Adafruit_SSD1306 # type: ignore
    RST = None     # on the PiOLED this pin isnt used
    # Note the following are only used with SPI:
    DC = 23
    SPI_PORT = 0
    SPI_DEVICE = 0

    # 128x32 display with hardware I2C:
    disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)
    disp.rotation = 2

    # Initialize library.
    disp.begin()

    # Clear display.
    disp.clear()
    disp.display()

    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    font = ImageFont.load_default()

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)



restraint = open('restraint.json')
restraint_list = json.loads(restraint.read())
restraint.close()

code = ''
code_hide = ''
settingsMode = False
settingsCode = ''
readyToConfig = False

code_hide_mark = config['screen']['code_hide_mark']
show_code = config['app']['show_code']
debugging = config['app']['debugging']
pwdRST = config['app']['pwdRST']
_settingsCode = config['app']['settingsCode']
tzone = config['app']['timezone']
demo = config['app']['demo']
rotate_display = config['app']['rotate']
openByCode = config['app']['openByCode']


screen_saver = 0
version_app = config['app']['version']
#api ------
url = config['api']['url']
api_valid_code = config['api']['api_valid_code']
api_codes_events = config['api']['api_codes_events']
usr = config['api']['usr']
namePlace = config['app']['NamePlace']
password = config['app']['pwd']
buzzer_pin = config['pi_pins']['buzzer']
display_type = config['screen']['display_type']
admin_sim = config['app']['admin_sim'].split(',')
apn = config['sim']['apn']
incoming_calls = config['sim']['incoming_calls']
sc_saver_time = config['screen']['sc_sever_time']

#decode and code verification
acc = 0
acc_code = 0
first_code = ''
last_capture = datetime.now()
settingsCode = ''
timestamp = ''
gsm_status = []
sendStatus = False


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(buzzer_pin,GPIO.OUT)
buzzer = GPIO.PWM(buzzer_pin, 1000)

#region Sim800L declaration
gsm = serial.Serial(port=config['sim']['serial_port'], 
                    baudrate=config['sim']['serial_baud'])



# Camera
cap = cv2.VideoCapture(0)

#endregion

# region ------------- Key pad gpio setup  ----------------------------
KEY_UP = 0 
KEY_DOWN = 1

MATRIX = config['keypad_matrix'][config['keypad_matrix']['default']]
ROWS = config['pi_pins']['keypad_rows']
COLS = config['pi_pins']['keypad_cols']

for pin in ROWS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

for pin in COLS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# endregion -----------------------------------------

#endregion

#region display ----------------------------

RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# 128x32 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

width = disp.width
height = disp.height
image = Image.new('1', (width, height))

font = ImageFont.load_default()

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

#endregion display -------------------

def initial():
    global sendStatus
    showVersion('ver. ' + version_app)
    sleep(1)

    # send module status  ---------------
    sendStatus = True
    signal_Status('Reboot')
    sleep(2)


def init_gsm():
    cmd = ''
    apn_usr = config['sim']['APN_USER']
    apn_pwd = config['sim']['APN_PWD']

    cmd = 'AT+CSTT="%s","%s","%s"\r' % (apn,apn_usr,apn_pwd)
    gsm.write(cmd.encode())
    sleep(2)
    
    cmd = 'AT+SAPBR=3,1,"Contype","GPRS"\r'
    gsm.write(cmd.encode())
    sleep(2)

    cmd = 'AT+SAPBR=3,1,"APN","%s"\r' % apn
    gsm.write(cmd.encode())
    sleep(1)

    cmd = 'AT+CMGF=1\r'
    gsm.write(cmd.encode())  # Select Message format as Text mode
    sleep(1)

    cmd = 'AT+CNMI=2,2,0,0,0\r'
    gsm.write(cmd.encode())  # New live SMS Message Indications
    sleep(1)

    # gsm.write('AT+CGATT?\r\n')
    # utime.sleep(1)

    if(not incoming_calls):
        cmd = 'AT+GSMBUSY=1\r'
        gsm.write(cmd.encode())
        sleep(1)

def signal_Status(titulo):
    cmd = ''
    global gsm_status
    gsm_status = []
    gsm_status.append({'Event':titulo})

    cmd = 'AT+CSQ\r'
    gsm.write(cmd.encode())
    sleep(0.7)

    cmd = 'AT+CBC\r'
    gsm.write(cmd.encode())
    sleep(0.7)

def showVersion(msg):
    clear()

    draw.text((0, 0),msg, font=font, fill=255)
    disp.image(image)
    disp.display()
    sleep(0.9)

    draw.text((0, 0),msg + '.', font=font, fill=255)
    disp.image(image)
    disp.display()
    sleep(0.9)

    draw.text((0, 0),msg + '..', font=font, fill=255)
    disp.image(image)
    disp.display()
    sleep(0.9)

    draw.text((0, 0),msg + '...', font=font, fill=255)
    disp.image(image)
    disp.display()
    sleep(0.9)

    draw.text((0, 0),msg + '....', font=font, fill=255)
    disp.image(image)
    disp.display()
    sleep(3)

def clear():
    if display_type == 'oled.128x32':
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        disp.image(image)
        disp.display()
    elif display_type == 'lcd.16x2':
        disp.clear()

def showMsg(msg1='',msg2=''):
    global screen_saver
    if display_type == 'lcd.16x2':
        clear()
        msg=''
        if (msg1 == 'headerControl'):
            msg1 = '* <-     # enter' 
            msg = f"{msg1:^16}" + '\n' + f"{msg2:^16}"
        else:
            msg = f"{msg1:^16}" + '\n' + f"{msg2:^16}"

        disp.message(msg)
    elif display_type == 'oled.128x32':
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        if (msg1 != ''):
            if (msg1 == 'headerControl'):
                space = 50 - 11 # 50 = screen length considering the font, 11 = '* <-# enter'
                draw.text((0, 2),f"{'* <-':<{space}}# enter", font=font, fill=255)
            else:
                draw.text((0, 2),f"{msg1:^50}", font=font, fill=255)

        if (msg2 != ''):
            draw.text((0, 16),f"{msg2:^40}", font=font, fill=255)
        
        disp.image(image)
        disp.display()

    screen_saver = 0


# region -------- Configuration  -------------------------------------

def changeSetting(value):
    global MATRIX
    global sendStatus
    applied = False

    # keypad  -----------------------------------
    if value == '00': # reboot
        printHeaderSettings()
        draw.text((1, 18), "Booting.. ", font=font, fill=255)
        disp.image(image)
        disp.display()
        sleep(3)
        restart()
        applied = True

    elif value == '01': # get Sim Info
        # getSimInfo()
        applied = True

    elif value == '02': # get timestamp
        # updTimestamp()
        applied = True

    elif value == '03': # get phone number
        sendStatus = True
        # getPhoneNum()
        applied = True

    elif value == '1': # set matrix for flex keypad
        MATRIX = config['keypad_matrix']['flex']
        applied = True

    elif value == '2': # set matrix for hard plastic keypad
        MATRIX = config['keypad_matrix']['hardPlastic']
        applied = True

    # debug -----------------------------------
    elif value == '10':  #debug true
        # jsonTools.updJson('u','config.json','app', 'debugging', True)
        applied = True

    elif value == '11': #debug false
        # jsonTools.updJson('u','config.json','app', 'debugging', False)
        applied = True

    return applied
    
# endregion


#----------------------------------------------
# msg: message to send
# type: to send Normal or write to memory to send later
#      n: Normal, w: Write to memory
# time: time to wait for assign message 
#---------------------------------------------


def sendSMS(msg, type = 'n', time = 1, trigger = 0):
    global admin_sim
    cmd = ''
    for i, item in enumerate(admin_sim):
        if debugging:
            print('sent msg to: ' + item)
        sleep(1)
        if type == 'n':
            cmd = 'AT+CMGS="' + item + '"\r'
            gsm.write(cmd.encode())
            sleep(time)
            cmd = str(msg) + "\r\x1A"
            gsm.write(cmd.encode())  # '\x1A' Enable to send SMS
            sleep(time)

        else: # write to memory
            cmd = 'AT+CMGW="' + item +  '"\r'
            gsm.write(cmd.encode())
            sleep(time)
            cmd = str(msg) + "\r\x1A"
            gsm.write(cmd.encode())
            sleep(time)

def isLocked(sim):
    locked = True
    for i, item in enumerate(restraint_list['user']):
        if len(item['sim']) == len(sim):
            if item['sim'] == sim:
                if item['status'] == 'unlock':
                    locked = False
                    break
        else:
            if len(item['sim']) < len(sim):
                if item['sim'] in sim:
                    if item['status'] == 'unlock':
                        locked = False
                        break
            else:
                if sim in item['sim']:
                    if item['status'] == 'unlock':
                        locked = False
                        break
    return locked

def isAnyAdmin(sim):
    admin = False
    for i, item in enumerate(restraint_list['user']):
        if len(item['sim']) == len(sim):
            if item['sim'] == sim:
                if item['role'] in ['admin','neighborAdmin']:
                    admin = True
                    break
        else:
            if len(item['sim']) < len(sim):
                if item['sim'] in sim:
                    if item['role'] in ['admin','neighborAdmin']:
                        admin = True
                        break
            else:
                if sim in item['sim']:
                    if item['role'] in ['admin','neighborAdmin']:
                        admin = True
                        break    
    return admin

def pkgListCodes():
    global codes
    global active_codes
    codes = ''
    for i, item in enumerate(active_codes['codes']):
        codes = codes + item['code'] + ','
    return codes


def updRestraintList():
    global restraint_list
    jaccess = open('restraint.json')
    restraint_list = json.loads(jaccess.read())
    jaccess.close()

def isAdmin(sim):
    admin = False
    for i, item in enumerate(restraint_list['user']):
        if len(item['sim']) == len(sim):
            if item['sim'] == sim:
                if item['role'] == 'admin':
                    admin = True
                    break
        else:
            if len(item['sim']) < len(sim):
                if item['sim'] in sim:
                    if item['role'] == 'admin':
                        admin = True
            else:
                if sim in item['sim']:
                    if item['role'] == 'admin':
                        admin = True    
    return admin


def signal_Status(titulo):
    global gsm_status
    gsm_status = []
    cmd = ''
    gsm_status.append({'Event':titulo})

    cmd = 'AT+CSQ\r'
    gsm.write(cmd.encode())
    sleep(0.7)
    cmd = 'AT+CBC\r'
    gsm.write(cmd.encode())
    sleep(0.7)

def str_to_bool(s):
    if s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False

def getBoardTemp():
    cpu = CPUTemperature()
    return "Temp: {:0.1f}".format(cpu.temperature)
def pkgListAccess():
    global access
    access = ''
    for i, item in enumerate(restraint_list['user']):
        if item['status'] == 'lock':
            print('pkgListCodes lock: ' + item['name'])
            access = access + item['name'] + '-[' + item['house'] + '],'
    return access

#---------------------------------------------
# file: json file name to read
# key:  key to read
# Desc: Convert Json file to text 
#--------------------------------------------
def txtJson(file, key):
    jsonObj = open(file, "r")
    json_list = json.loads(jsonObj.read())
    jsonObj.close()
   
    arr = []
    for i, item in enumerate(json_list[key]):
        arr.append({item['name'],item['house'],item['status']})
        # arr.append(item)

    if(len(arr) == 0):
        arr.append(file + ' empty')
    else:
        # sorting
        # for i,iitem in enumerate(arr):
        #     for j,jitem in enumerate(arr):
        #         if len(arr) > j + 1 :
        #             if arr[j]['house'] > arr[j + 1]['house']:
        #                 temp = arr[j]
        #                 arr[j] = arr[j + 1]
        #                 arr[j + 1] = temp

        arr_send = []
        pkg_size = 0
        total_size = 0
        for i,iitem in enumerate(arr):
            arr_send.append(iitem)
            pkg_size += len(str(iitem))

            if (1024 - pkg_size) <= 52:
                print('middle pkg size: ' + str(pkg_size))
                print('send middle pkg: ', arr_send)
                print('\n')
                total_size += pkg_size
                sendSMS(arr_send, 'n')
                sleep(10)
                pkg_size = 0
                arr_send.clear()
      

        if len(str(arr_send)) > 0 :
            total_size += pkg_size
            print('\n')
            print('last pkg size: ' + str(pkg_size))
            print('last pkg to send: ',arr_send)
            print('final size: ' + str(total_size))
            sendSMS(arr_send, 'n')
            sleep(10)

def softReset():
    showMsg('Rebooting')
    sleep(1)
    try:
        reset()
    except SystemExit:
        print('Error SystemExit')
        raise SystemExit
        
    except Exception as e:
        print('Error Exception: ', e)
        raise
    
    except:
        print('Error Fallback')
        # soft_reset()  from machine in micropython


def restart():
    clear()
    showMsg('Reiniciando..')
    cap.release()
    cv2.destroyAllWindows()
    os.execl(sys.executable, sys.executable, *sys.argv)

def stop():
    print('stop program')
    os._exit(1)

# ---  1 : by date, 2 : by duplicity
def cleanCodes(type, code):
    global rtc
    global active_codes
    active_codes = {"codes": []}

    now = datetime.now()
    jcodes = open('codes.json')
    code_list = json.loads(jcodes.read())
    jcodes.close()

    for i, item in enumerate(code_list['codes']):
        if type == 1:
            dtcode = datetime.fromisoformat(item['date']) # type: ignore

            if dtcode < now :
                if debugging:
                    print('Code deleted ----> ', item['code'])
            else:
                active_codes['codes'].append(item)

        elif type == 2:
            if code == item['code']:
                del code_list['codes'][i]
                f = open("codes.json", "w")
                json.dump(code_list, f)
                f.close()
                break
    f = open("codes.json", "w")
    json.dump(active_codes, f)
    f.close()
    showMsg("headerControl","Codigo: ")

def decode_qr(frame):
    #acc increment calling value
    global acc
    global acc_code
    global first_code
    global last_capture
    global screen_saver
    diff_time = 0

    # Decodifica los códigos QR en el frame
    decoded_objects = pyzbar.decode(frame)
    for obj in decoded_objects:
        # Extraer el texto del QR
        qr_data = obj.data.decode("utf-8")
        qr_type = obj.type

        #ignore duplicate verificartion for short time readings -----
        if qr_type == 'QRCODE':
            if first_code == qr_data:
                acc_code += 1
            else:
                acc_code = 1
                first_code = qr_data

            now = datetime.now()
            diff_time = (now - last_capture).seconds
        
        #end duplicate verification     ----------------------
            acc += 1

        # Imprimir el texto del QR y el tipo en la consola
            if diff_time > 15:
                GPIO.output(buzzer_pin,GPIO.HIGH)
                sleep(0.5)
                GPIO.output(buzzer_pin,GPIO.LOW)

                screen_saver = 0
                print("{}.- Data: '{}' | Time: '{}' | Acc-code: '{}' | Diff: '{}' "
                    .format(str(acc),f"{qr_data:^6}", datetime.now(pytz.timezone(tzone)), acc_code, str(diff_time)))
                
                activeCode(qr_data)

def activeCode(code):
    global last_capture
    last_capture = datetime.now()
    global screen_saver
    screen_saver = 0

    try:
        if code == 'gate':
            clear()
            showMsg('Bienvenido')
            gate.fullCycle(4)
            showMsg(namePlace)
            return True
        elif code == 'magnet':
            clear()
            showMsg('Bienvenido')
            magnet.fullCycle(4)
            showMsg(namePlace)
            return True
        elif code == 'boot':
            restart()
            return True
        
        elif code == 'stop':
            stop()
            return True
        
        curl = url + api_valid_code + code + '/' + usr
        res = requests.get(curl)
        code = ''

        if res.status_code == 200:
            clear()
            showMsg('Bienvenido')
            if(openByCode == 'gate'):
                gate.fullCycle(4)
            else:
                magnet.fullCycle(4)
                
            showMsg(namePlace)
            return True
        else:
            showMsg('Codigo','No valido')
            sleep(7)
            showMsg(namePlace)
            return False
        

    except requests.exceptions.RequestException as e:
        logger.error(e)
        return False

def screenSaver():
    global settingsMode
    global readyToConfig
    global settingsCode

    settingsCode = ''
    readyToConfig = False
    settingsMode = False
    clear()

def printHeader():
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((1,0), "* <-", font=font, fill=255)
    draw.text((75,0), '# enter', font=font, fill=255)
    disp.image(image)
    disp.display()

def printHeaderSettings():
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((1,0), "* <-", font=font, fill=255)
    draw.text((75,0), '# enter', font=font, fill=255)
    draw.text((1,9), 'config', font=font, fill=255)

def getLocalTimestamp():
    global timestamp
    tsf = ((str(timestamp[0:2]) + '-' + str(timestamp[3:5]) + '-' +
          str(timestamp[6:8]) + 'T' + str(timestamp[9:11]) + ':' +
          str(timestamp[12:14]) + ':' + str(timestamp[15:17])))
    return tsf

def PollKeypad():
    global ROWS
    global COLS
    global screen_saver
    global code
    global code_hide
    global code_hide_mark
    global settingsMode
    global readyToConfig
    global settingsCode
    while True:
        for r in ROWS:
            GPIO.output(r, GPIO.LOW)
            result = [GPIO.input(COLS[0]),GPIO.input(COLS[1]),GPIO.input(COLS[2]),GPIO.input(COLS[3])]
            if min(result) == 0:
                key = MATRIX[int(ROWS.index(r))][int(result.index(0))]
                GPIO.output(r, GPIO.HIGH) #manages key keept pressed
                if key != None:
                    screen_saver = 0
                    if key == '#':
                        # region code settings verification  --------------
                        if len(code) == 0 and settingsMode == True and readyToConfig == False:
                            printHeaderSettings()
                            code = code + key
                            code_hide = code_hide + code_hide_mark
                            draw.text((1, 18), "Pwd:  " + code_hide, font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            break
                        elif len(code) == 0 and settingsMode == True and readyToConfig == True:
                            printHeaderSettings()
                            code = code + key
                            code_hide = code_hide + code_hide_mark
                            draw.text((1, 18), "Code:  " + code, font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            break
                        elif len(code) == 0 and settingsMode == False:
                            code = code + key
                            code_hide = code_hide + code_hide_mark
                            draw.text((1, 18), "Code:  " + code, font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            break
                        elif code[0:1] == '#' and settingsMode == False:
                            if code[1:] == _settingsCode:
                                settingsMode = True
                                printHeaderSettings()
                                cmdLineTitle = "Pwd:                  "
                                draw.text((1, 18), cmdLineTitle, font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                settingsCode = ''
                                code = code_hide = ''
                                break
                        elif code[0:1] == '#' and settingsMode == True and readyToConfig == False:
                            if code[1:] == pwdRST :
                                readyToConfig = True
                                printHeaderSettings()
                                draw.text((1, 18), "Pwd: OK         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                sleep(3)
                                printHeaderSettings()
                                draw.text((1, 18), "Code:           ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                if debugging:
                                    # DisplayMsg('pwd ok',5)
                                    print('pwd ok')
                                code = code_hide = ''
                                settingsCode = ''
                                break
                            else:
                                printHeaderSettings()
                                draw.text((1, 18), "Pwd: Error         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                sleep(3)
                                printHeaderSettings()
                                draw.text((1, 18), "Pwd:         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                if debugging:
                                    # disable because not working ok
                                    # DisplayMsg('pwd error', 5)
                                    print('pwd error')
                                code = code_hide = ''
                                break
                        elif code[0:1] != '#' and settingsMode == True and readyToConfig == True:
                            if changeSetting(code):
                                draw.text((1, 10), "Applying", font=font, fill=255)
                                draw.text((3, 18), "code", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                sleep(4)
                                printHeaderSettings()
                                draw.text((3, 18), "Code: ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                code = code_hide = ''
                            else:
                                draw.rectangle((0,0,width,height), outline=0, fill=0)
                                draw.text((1, 10), "Not Applied", font=font, fill=255)
                                draw.text((3, 18), "code ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                sleep(4)
                                song('fail')
                                printHeaderSettings()
                                draw.text((3, 18), "Code: ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                code = code_hide = ''

                            break
                        elif code[0:1] == '#' and code[1:] == _settingsCode and settingsMode == True and readyToConfig == True:
                            printHeaderSettings()
                            draw.text((3, 18), "exit settings", font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            sleep(3)
                            printHeader()
                            draw.text((3, 18), "Codigo:           ", font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            code = code_hide = ''
                            settingsCode = ''
                            readyToConfig = False
                            settingsMode = False
                            break
                        elif len(code) > 0 and settingsMode == True and readyToConfig == False:
                            if code == pwdRST:
                                readyToConfig = True
                                printHeaderSettings()
                                draw.text((3, 18), "Pwd: OK         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                sleep(3)
                                printHeaderSettings()
                                draw.text((3, 18), "Code:           ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                if debugging:
                                    # disable because not working ok
                                    # DisplayMsg('pwd ok', 5)
                                    print('pwd ok')
                                code = code_hide = ''
                                settingsCode = ''
                                break
                            else:
                                printHeaderSettings()
                                draw.text((3, 18), "Pwd: Error         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                song('fail')
                                sleep(3)
                                printHeaderSettings()
                                draw.text((3, 18), "Pwd:         ", font=font, fill=255)
                                disp.image(image)
                                disp.display()
                                if debugging:
                                    # disable because not working ok
                                    # DisplayMsg('pwd error',4)
                                    print('pwd error')
                                code = code_hide = ''
                                break
                        # endregion -------------------------------------
                        
                        # incomplete code ---------------------
                        elif len(code) < 6 and code[0:1] != '#':
                            printHeader()
                            draw.text((3, 18), "Codigo incompleto    ", font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            # song('fail')
                            sleep(3)
                            printHeader()
                            draw.text((3, 18), "Codigo: {}             ".format(code), font=font, fill=255)
                            disp.image(image)
                            disp.display()
                            if debugging:
                                print('incomplete code')
                            break
                        # Just verify code ---------------------
                        elif len(code) > 5 and code[0:1] != '#':
                            activeCode(code)
                            code = code_hide = ''
                            break
                    elif key == '*':
                        if len(code) > 0:
                            code = code[0:-1]
                            code_hide = code_hide[0:-1]
                    else:
                        code = code + key
                        code_hide = code_hide + code_hide_mark
                
                    draw.rectangle((0,0,width,height), outline=0, fill=0)
                    draw.text((1,0), "* <-", font=font, fill=255)
                    draw.text((75,0), '# enter', font=font, fill=255)
                    if show_code:
                        draw.text((1, 18), "Codigo:  " + code, font=font, fill=255)
                    else:
                        draw.text((1, 18), "Codigo:  " + code_hide, font=font, fill=255)
                    
                    disp.image(image)
                    disp.display()

                    if debugging:
                        print("Codigo: " + code)
                
                    sleep(0.3)
            else:
                if screen_saver/1000 <= sc_saver_time:
                    screen_saver += 1
                    if screen_saver/1000 == sc_saver_time:
                        screenSaver()

            GPIO.output(r, GPIO.HIGH)

def simResponse():
    global gsm
    global debugging
    global screen_saver
    header = ''
    cmd = ''
    msg = ''
    response = ''
    global sendStatus  # used to collect more information from sim800L
                       # like CBC, CSQ values

    while True:
        #try:
        response = gsm.readline().decode('ascii').strip()

        if ',' in response:
            header = response.split(',')
        
        if debugging:
            if response:
                print('response: ',response)

        if 'ERROR' in response:
            print('simResponse,Error detected: ' + response)
        elif '+CREG:' in response:  # Get sim card status
            global simStatus
            # response = str(gsm.readline(), encoding).rstrip('\r\n')
            pos = response.index(':')
            simStatus = response[pos + 4: len(response)]
            if debugging:
                print('sim status --> ' + simStatus)
            return simStatus
        elif '+CCLK' in response:  # Get timestamp from GSM network
            global timestamp
            response = str(gsm.readline(), encoding).rstrip('\r\n') # type: ignore
            if debugging:
                print('sim status: ' + response)
            pos = response.index(':')
            timestamp = response[pos + 3: len(response) - 1]
            if debugging:
                print('GSM timestamp --> ' + timestamp)
                print(('Params --> ' ,timestamp[0:2],timestamp[3:5],
                        timestamp[6:8],timestamp[9:11],timestamp[12:14],
                        timestamp[15:17]))

                print('rtc_datetime --> ' + str(rtc.datetime()))

            rtc.datetime((int('20' + timestamp[0:2]), int(timestamp[3:5]),
                            int(timestamp[6:8]), 0, int(timestamp[9:11]),
                            int(timestamp[12:14]), int(timestamp[15:17]), 0))
            timestamplocal = timestamp.split(',')[0].split('/')
            tupleToday = (int(timestamplocal[0]), int(timestamplocal[1]), int(timestamplocal[2]))
            Today = timestamplocal[0] + '.' + timestamplocal[1] + '.' + timestamplocal[2]

        # SMS----------------------
        elif '+CMT:' in response:
            senderSim = header[0][header[0].index('"') + 1: -1]
            if(len(senderSim) >= 10):
                senderSim = senderSim[-10:]

            # Line to get SMS text
            response = gsm.readline().decode('ascii').strip()

            role = jsonTools.updJson('r', 'restraint.json','sim', senderSim,'',True,'role')
            # Check extrange sender----------------------------------
            if not jsonTools.updJson('r', 'restraint.json','sim', senderSim, '',False):
                timestamp = getLocalTimestamp()
                pkg = { "sim" : senderSim, "cmd" : response, "eventAt" : timestamp }
                jsonTools.updJson('c', 'extrange.json','events', pkg, '')

                #  --- send extrage info to admin  -------
                sendSMS('Extrange sim: ' + senderSim + ' \n,cmd: ' + response
                            + '\n, at: ' + timestamp )
                if debugging:
                    print('Extrange attempted')
                    showMsg('Extrange attempted')
                return
            
            # Check if user is lock  -------------------------------------
            # status = jsonTools.updJson('r', 'restraint.json','sim', senderSim,'',True,'status')
            # if status == 'lock' or status != 'unlock':
            if isLocked(senderSim):
                if debugging:
                    print('User locked')
                    showMsg('User locked')
                return

            if 'twilio' in response.lower():
                msg = response.split("-")
                lenght = len(response)
                index = response.find('-')
                msg = response[index + 2:lenght].split(',')
            else:
                msg = response.split(",")

            # receiving codes ------------------
            if msg[0].strip() == 'codigo':
                msg[3] = msg[3].rstrip('\r\n')
                msg[4] = msg[4].rstrip('\r\n')
                api_data = {"userId": msg[3], "date": msg[2],
                            "code": msg[1], "visitorSim": msg[4],
                            "codeId": msg[5]}
                jsonTools.updJson('c', 'codes.json','codes', api_data, '')
                cleanCodes(1, '')
                showMsg("headerControl","Codigo: " + msg[1])
                return
            
            elif msg[0].strip() == 'open':
                # if not demo:
                if debugging:
                    print('Abriendo', msg)
                
                showMsg('Bienvenido')
                if 'peatonal' in msg[1]:
                    magnet.fullCycle(4)
                elif 'vehicular' in msg[1]:
                    gate.fullCycle(4)
                showMsg(namePlace)

                response=''
        # region admin or neighborAdmin commands section -------------------------------------
            
            if isAnyAdmin(senderSim):
                if msg[0].strip() == 'newUser':
                    api_data = { "name": msg[1], "house": msg[2], "sim": msg[3],
                                    "status": "unlock","id": msg[4],"role": msg[5],
                                    "lockedAt": getLocalTimestamp()}
                    jsonTools.updJson('c', 'restraint.json','user', api_data, '')
                    return
                
                elif msg[0].strip() == 'updSim':
                    jsonTools.updJson('updSim', 'restraint.json','sim', msg[1],
                                        msg[2], False,'',getLocalTimestamp())
                    return

                elif msg[0].strip() == 'lock':
                    jsonTools.updJson('updStatus', 'restraint.json','sim', msg[3],
                                        'lock', False,'',getLocalTimestamp())
                    updRestraintList()
                    return
                
                elif msg[0].strip() == 'unlock':
                    jsonTools.updJson('updStatus','restraint.json','sim',msg[3],
                                        'unlock',False,'',getLocalTimestamp())
                    updRestraintList()
                    return
                
                elif msg[0].strip() == 'delete':
                    jsonTools.updJson('delete','restraint.json','id',msg[1],
                                        '',False,'',getLocalTimestamp())
                    updRestraintList()
                    return
                
                elif msg[0] == 'active_codes':
                    sendSMS('codes available --> ' + pkgListCodes())
                    return
                
            else:
                if debugging:
                    print('no privileges', msg)
            
        #endregion admin  -------------------------------------------------

        #region super admin ------------------------------------------
            if isAdmin(senderSim):
                if msg[0] == 'status':
                    if msg[1] == 'gral':
                        sendStatus = True
                        signal_Status('Status')

                    elif msg[1] == 'restraint':
                        txtJson('restraint.json','user')
                        # sendSMS('Hello','w',1,1)

                    elif msg[1] == 'extrange':
                        txtJson('extrange.json','events')
                    return

                elif msg[0] == 'rst':
                    softReset()
                    return

                # elif msg[0] == 'cfgCHG':
                #     oled1.fill(0)
                #     oled1.text(msg[2] + ' =', 2, 1)
                #     oled1.text(msg[3], 2, 14)
                #     oled1.show()
                #     sleep(4)
                    
                #     if(msg[3] == 'false' or msg[3] == 'true'):
                #         msg[3] = str_to_bool(msg[3])
                                
                #     jsonTools.updJson('u','config.json',msg[1], msg[2], msg[3])
                        
                #     if msg[2] == 'openByCode':
                #         openByCode = msg[3]

                #     if msg[2] == 'demo':
                #         demo = msg[3]

                    # if msg[2] == 'rotate':
                    #     rotate_display = msg[3]
                    #     i2c1 = I2C(1, scl=Pin(scl1), sda=Pin(sda1), freq=400000)
                    #     oled1 = SSD1306_I2C(WIDTH, HEIGHT, i2c1)
                    #     oled1.rotate(2)
                    
                    # if msg[2] == 'debugging':
                    #     debugging = msg[3]
                    #     if debugging:
                    #         tim25.init(freq=2, mode=Timer.PERIODIC, callback=tick25)
                    #     else:
                    #         tim25.deinit()

                    # if msg[1] == 'keypad_matrix':
                    #         MATRIX = config[msg[1]][msg[3]]

                    # if msg[2] == 'settingsCode':
                    #     _settingsCode = msg[3]
                    
                    # if msg[2] == 'pwdRST':
                    #     pwdRST = msg[3]

                    # ShowMainFrame()
                    # return    
        #endregion super andmin--------------------


        elif '+CSQ:' in response:
            print('Im here...')
            pos = response.index(':')
            # global response_return
            response_return = response[pos + 2: (pos + 2) + 2]
            if sendStatus:
                gsm_status.append({'CSQ': response_return})
            elif debugging:
                print('CSQ : ', response_return)

            # return (response_return)
        elif '+CBC:' in response:
            print('Im here...')
            pos = response.index(':')
            response_return = response[pos + 2: (pos + 2) + 9]

            if sendStatus:
                sendStatus = False
                gsm_status.append({'Local': datetime.now()})
                gsm_status.append({'CBC': response_return})
                pcbTemp = getBoardTemp()
                gsm_status.append({pcbTemp})
                gsm_status.append({'Demo': demo})
                gsm_status.append({'Rotate': rotate_display})
                gsm_status.append({'OpenByCode': openByCode})
                gsm_status.append({'cfgCode': _settingsCode})
                gsm_status.append({'pwdRST': pwdRST})

                #  --- send status  -------
                sendSMS(str(gsm_status) + '\n Codes: NA'
                        + '\n locked: ' + pkgListAccess())
            elif debugging:
                print('CBC : ', response_return)
        # return (response_return)
        elif '+CGREG:' in response:
            pos = response.index(':')
            response_return = response[pos + 4: (pos + 4) + 1]
            cgreg_status = response_return
        elif '+CNUM:' in response:
            if sendStatus:
                sendStatus = False
                sendSMS('Phone Num: ' + response)
        elif 'OVER-VOLTAGE' in response:  # 4.27v
            sendStatus = True
            showMsg('Temp high')
            if debugging:
                print('GSM Module Temperature high !')
            cmd = 'AT+CBC\r'
            gsm.write(cmd.encode())
        elif 'UNDER-VOLTAGE' in response:  # 3.48v
                sendStatus = True
                showMsg('Temp low')
                if debugging:
                    print('GSM Module Temperature low')
                cmd = 'AT+CBC\r'
                gsm.write(cmd.encode())
    # except NameError:
    #     print('Error -->', NameError)
    #     pass
    # if not debugging: 
    #     led25.value(0)
        # if screen_saver/1000 <= sc_saver_time:
        #     screen_saver += 1
        #     if screen_saver/1000 == sc_saver_time:
        #         screenSaver()

    # except gsm.serialException as err:
    #     print('gsm error: ', err)


def main():
    try:
        initial()
        init_gsm()
        sleep(2)
        clear()
        showMsg(namePlace)
    
        # catch keypas pressed
        thKeypad = threading.Thread(target=PollKeypad)

        #catch sim Response
        thSim = threading.Thread(target=simResponse)
        
        thKeypad.start()
        sleep(1)
        thSim.start()
        sleep(1)

        print('both threading have finished execution')

        while cap.isOpened():
            # Leer un frame de la cámara
            ret, frame = cap.read()
            if not ret:
                break

            # Decodificar QR en el frame
            frame = decode_qr(frame)

            # Salir con la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


    except KeyboardInterrupt:
        print('\nAdios.!')
        GPIO.cleanup()
        clear()

    except ValueError as errValue:
        print("Value Not valid, Try again...", errValue)

    except OSError:  # Open failed
        print('Error--> ', OSError)
        logger.error(OSError)
    except SystemExit as e:
        logger.error(e)
        os._exit()
    except sys as e:
        print('Exception: ', e)
    finally:
        # Liberar la cámara y cerrar todas las ventanas
        cap.release()
        cv2.destroyAllWindows()
        sys.exit()



if __name__ == "__main__":
    main()