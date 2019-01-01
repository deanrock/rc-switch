import time
import sys
import RPi.GPIO as GPIO

PIN = 18

if __name__ == '__main__':
    code = sys.argv[1]

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN, GPIO.OUT)

    for _ in range(8):
        toggle = 1
        for i in code:
            GPIO.output(PIN, toggle)
            toggle = not toggle

            if i == '1':
                time.sleep(0.00090)
            elif i == '0':
                time.sleep(0.00023)

        GPIO.output(PIN, 0)
        time.sleep(0.0087)

    GPIO.cleanup()
