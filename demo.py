#!/usr/bin/env python3
#
# (c) 2019 Yoichi Tanibayashi

import RPi.GPIO as GPIO
from Led import Led
from Switch import Switch, SwitchListener
import time

PIN_LED    = 26
PIN_SWITCH = 20

class demo:
    def __init__(self, interval=0.02, timeout_sec=[0.7, 1, 4, 7, 10],
                 debug=False):

        self.sw = SwitchListener(PIN_SWITCH, self.sw_callback,
                                 interval, timeout_sec, debug)
        self.sw.start()

        self.led = Led(PIN_LED)

        self.active = True
        
    def main(self):
        while self.active:
            print('main>', time.time())
            time.sleep(1)
        self.led.off()

    def sw_callback(self, sw, event):
        sw.event_print(event)

        if event['name'] == 'pressed':
            self.led.on()
        if event['name'] == 'released':
            self.led.off()
        if event['name'] == 'timer':
            if event['timeout_idx'] == 0 and event['value'] == 'OFF':
                self.led.off()
                for i in range(event['count']):
                    time.sleep(0.4)
                    self.led.on()
                    time.sleep(0.4)
                    self.led.off()
            # 長押し
            if event['timeout_idx'] == 1:
                self.led.off()
                self.led.blink(0.2, 0.05)
            if event['timeout_idx'] == 2:
                self.led.off()
                self.led.blink(0.1, 0.05)
            if event['timeout_idx'] == 3:
                self.led.off()
                self.led.blink(0.05, 0.05)
            if event['timeout_idx'] == 4:
                self.led.off()
                self.active = False

def demofunc():
    sw = Switch(PIN_SWITCH, timeout_sec=[0.7, 1, 4, 7, 10], debug=True)
    sw.start()

    with Led(PIN_LED) as led:
        while True:
            event = sw.event_get()
            sw.event_print(event)
            if event['name'] == 'pressed':
                led.on()
            if event['name'] == 'released':
                led.off()
            if event['name'] == 'timer':
                if event['timeout_idx'] == 0 and event['value'] == 'OFF':
                    # クリック回数確定
                    led.off()
                    time.sleep(0.3)
                    for i in range(event['count']):
                        led.on()
                        time.sleep(0.4)
                        led.off()
                        time.sleep(0.4)

                # 長押し
                if event['timeout_idx'] == 1:
                    led.off()
                    led.blink(0.2, 0.05)
                if event['timeout_idx'] == 2:
                    led.off()
                    led.blink(0.1, 0.05)
                if event['timeout_idx'] == 3:
                    led.off()
                    led.blink(0.05, 0.05)
                if event['timeout_idx'] == 4:
                    led.off()
                    break

def setup_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

def cleanup_GPIO():
    GPIO.cleanup()

def main():
    setup_GPIO()
    try:
        demo().main()
        
        #demofunc()
    finally:
        cleanup_GPIO()

if __name__ == '__main__':
    main()
