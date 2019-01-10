#!/usr/bin/env python3
#
# (C) 2018 Yoichi Tanibayashi
#
import RPi.GPIO as GPIO
import threading
import queue
import time

import click

from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
logger = getLogger(__name__)
logger.setLevel(DEBUG)
handler = StreamHandler()
handler.setLevel(DEBUG)
handler_fmt = Formatter('%(asctime)s %(levelname)s %(name)s.%(funcName)s> %(message)s',
                        datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False

class Led:
    '''Primitive LED class
    '''
    def __init__(self, pin):
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('')
        if pin == 0:
            return None

        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)

        self.off()

    def __enter__(self):
        self.logger.debug('')
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.logger.debug('%s, %s, %s', ex_type, ex_value, trace)
        self.off()
        
    def switch(self, sw_on):
        self.logger.debug('')
        if sw_on:
            self.on()
        else:
            self.off()
            
    def on(self):
        self.logger.debug('')
        GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        self.logger.debug('')
        GPIO.output(self.pin, GPIO.LOW)

class BlinkLed(Led):
    '''LED class

    support blink
    '''
    def __init__(self, pin):
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('pin=%d', pin)
        
        self.pin     = pin

        self.on_sec  = None
        self.off_sec = None
        self.tmr     = None
        
        super().__init__(self.pin)

    def blink_start(self, on_sec, off_sec):
        self.logger.debug('on_sec=%d, off_sec=%d', on_sec, off_sec)
        
        self.on_sec  = on_sec
        self.off_sec = off_sec

        self.off()

        self.blink_on()

    def off(self):
        self.logger.debug('')

        if self.tmr:
            self.tmr.cancel()
        super().off()

    def blink_on(self):
        self.logger.debug('')

        self.tmr = threading.Timer(self.on_sec,  self.blink_off)
        super().on()
        self.tmr.start()

    def blink_off(self):
        self.logger.debug('')

        self.tmr = threading.Timer(self.off_sec, self.blink_on)
        super().off()
        self.tmr.start()
        
def app(pin, debug):
    logger.debug('pin=%d', pin)

    bl = BlinkLed(pin)
    for s in [0.01, 0.015, 0.02, 0.03, 0.05]:
        print(s)
        bl.blink_start(s, s)
        time.sleep(4)
    bl.off()

    time.sleep(2)

    with BlinkLed(pin) as bl:
        for s in [1, 2]:
            print(s)
            bl.blink_start(s, s)
            time.sleep(4)

    time.sleep(2)

    led = Led(pin)
    led.on()
    time.sleep(1.0)
    led.off()

    time.sleep(2)

    with Led(pin) as l:
        l.on()
        time.sleep(1)
        l.off()

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, default=0)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    '''Led class sample program

Arguments:

    <pin>
    GPIO pin (BCM)
    '''
    logger.setLevel(INFO)
    if debug:
        logger.setLevel(DEBUG)

    setup_GPIO()
    try:
        app(pin, debug)
    finally:
        cleanup_GPIO()

def setup_GPIO():
    logger.debug('')

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

def cleanup_GPIO():
    logger.debug('')

    GPIO.cleanup()

if __name__ == '__main__':
    main()
