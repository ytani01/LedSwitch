#!/usr/bin/env python3
#
# (c) 2019 Yoichi Tanibayashi

import RPi.GPIO as GPIO
from Led import Led
from Button import Button, ButtonListener
import time

PIN_LED    = 26
PIN_BUTTON = 20

class demo:
    def __init__(self, interval=0.02, timeout_sec=[0.7, 1, 4, 7, 10],
                 debug=False):

        self.sw = ButtonListener(PIN_BUTTON, self.sw_callback,
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
        event.print()

        if event.name == 'pressed':
            self.led.on()
        if event.name == 'released':
            self.led.off()
        if event.name == 'timer':
            if event.timeout_idx == 0 and event.value == 'OFF':
                self.led.off()
                for i in range(event.push_count):
                    time.sleep(0.4)
                    self.led.on()
                    time.sleep(0.4)
                    self.led.off()
            # 長押し
            if event.timeout_idx == 1:
                self.led.off()
                self.led.blink(0.2, 0.05)
            if event.timeout_idx == 2:
                self.led.off()
                self.led.blink(0.1, 0.05)
            if event.timeout_idx == 3:
                self.led.off()
                self.led.blink(0.05, 0.05)
            if event.timeout_idx == 4:
                self.led.off()
                self.active = False

def setup_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

def cleanup_GPIO():
    GPIO.cleanup()

def main():
    setup_GPIO()
    try:
        demo().main()
    finally:
        cleanup_GPIO()

if __name__ == '__main__':
    main()
