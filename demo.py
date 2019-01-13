#!/usr/bin/env python3

import RPi.GPIO as GPIO
from Led import Led
from Switch import SwitchWatcher
import time

PIN_LED    = 26
PIN_SWITCH = 20

def demo():
    sw = SwitchWatcher(PIN_SWITCH, timeout=[0.7, 1, 4, 7, 10])
    sw.start()

    with Led(PIN_LED) as led:
        while True:
            event = sw.event_get()
            if event['name'] == 'pressed':
                led.on()
            if event['name'] == 'released':
                led.off()
            if event['name'] == 'timer':
                if event['tout_i'] == 0 and event['value'] == 'OFF':
                    for i in range(event['count']):
                        led.on()
                        time.sleep(0.5)
                        led.off()
                        time.sleep(0.5)
                        
                if event['tout_i'] == 1:
                    led.off()
                    led.blink(0.2, 0.2)
                if event['tout_i'] == 2:
                    led.off()
                    led.blink(0.1, 0.1)
                if event['tout_i'] == 3:
                    led.off()
                    led.blink(0.05, 0.05)
                if event['tout_i'] == 4:
                    led.off()

def setup_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

def cleanup_GPIO():
    GPIO.cleanup()

def main():
    setup_GPIO()
    try:
        demo()
    finally:
        cleanup_GPIO()

if __name__ == '__main__':
    main()
