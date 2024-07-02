import RPi.GPIO as GPIO # type: ignore
from time import sleep
import json

conf = open('config.json')
config = json.loads(conf.read())
angle = config['pi_pins']['gpio_servo_magnet_angle']
close_wait = config['pi_pins']['gpio_servo_magnet_delay']

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(config['pi_pins']['gpio_servo_magnet'],GPIO.OUT, initial=False)
pwm = GPIO.PWM(config['pi_pins']['gpio_servo_magnet'], 50)
pwm.start(0)


def Close():
    for degree in range(angle, 0, -10):
        pwm.ChangeDutyCycle(2.5 + 10 * degree / 180)
        sleep(0.03)
        pwm.ChangeDutyCycle(0)
        sleep(0.03)


def Open():
    for degree in range(0, angle, 10):
        pwm.ChangeDutyCycle(2.5 + 10 * degree / 180)
        sleep(0.03)
        pwm.ChangeDutyCycle(0)
        sleep(0.03)


def fullCycle(lapse):
    Open()
    sleep(lapse)
    Close()


if __name__ == "__main__":
    # run locally
    print('Hello running gate program locally..')
    #     Activate()
    #     servoSteps()

    while True:
        Open()
        sleep(5)
        Close()
        sleep(5)


