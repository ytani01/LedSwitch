#!/usr/bin/env python3
#
# (c) 2019 Yoichi Tanibayashi

import RPi.GPIO as GPIO
from Led import Led
from Switch import Switch, SwitchListener
import time
import click

class demo:
    def __init__(self, pin_led, pin_sw, debug=False):
        self.pin_led = pin_led
        self.pin_sw  = pin_sw

        self.long_press = [
            {'timeout':0.7, 'blink':{'on':1,    'off':0}},
            {'timeout':1,   'blink':{'on':0.2,  'off':0.04}},
            {'timeout':3,   'blink':{'on':0.1,  'off':0.04}},
            {'timeout':5,   'blink':{'on':0.04, 'off':0.04}},
            {'timeout':7,   'blink':{'on':0,    'off':0}}]

        self.timeout_sec = []
        for i in range(len(self.long_press)):
            self.timeout_sec.append(self.long_press[i]['timeout'])

        self.sw = SwitchListener([self.pin_sw], self.sw_callback,
                                 timeout_sec=self.timeout_sec, debug=debug)

        self.led = Led(self.pin_led)

        self.active = True
        
    def main(self):
        start_sec = time.time()
        while self.active:
            print('main> %.1f' % ((time.time() - start_sec)))
            time.sleep(1)
        self.led.off()

    def sw_callback(self, sw, event):
        event.print()

        if event.name == 'pressed':
            self.led.on()

        if event.name == 'released':
            self.led.off()

        if event.name == 'timer':
            idx = event.timeout_idx

            if idx == 0:		# マルチクリック回数確定
                if event.value == Switch.OFF:
                    self.led.off()
                    for i in range(event.push_count):
                        time.sleep(0.4)
                        self.led.on()
                        time.sleep(0.4)
                        self.led.off()

            if idx >= 1:		# 長押し
                if idx < len(self.long_press) - 1:
                    self.led.off()
                    self.led.blink(self.long_press[idx]['blink']['on'],
                                   self.long_press[idx]['blink']['off'])
                else:
                    self.led.off()
                    self.active = False

def setup_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

def cleanup_GPIO():
    GPIO.cleanup()

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--led',    '-l', 'pin_led', type=int, default=26,
              help='LED pin')
@click.option('--switch', '-s', 'pin_sw',  type=int, default=20,
              help='Switch pin')
def main(pin_led, pin_sw):
    setup_GPIO()
    try:
        demo(pin_led, pin_sw).main()
    finally:
        cleanup_GPIO()

if __name__ == '__main__':
    main()
