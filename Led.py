#!/usr/bin/env python3
#
# (C) 2018 Yoichi Tanibayashi
#
import RPi.GPIO as GPIO
import threading
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

class SimpleLed:
    '''Primitive LED class
    '''
    def __init__(self, pin):
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('pin = %d', pin)

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

class Led(SimpleLed):
    '''LED class

    support blink

    IMPORTANT:
    don't forget to off() after blink()

    '''
    def __init__(self, pin):
        self.on_sec  = None
        self.off_sec = None
        self.tmr     = None
        super().__init__(pin)

        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('pin = %d', self.pin)

    def __exit__(self, ex_type, ex_value, trace):
        self.logger.debug('%s, %s, %s', ex_type, ex_value, trace)
        self.off()
        
    def blink(self, on_sec=0.5, off_sec=0.5):
        self.logger.debug('on_sec=%d, off_sec=%d', on_sec, off_sec)
        
        self.on_sec  = on_sec
        self.off_sec = off_sec

        self.off()

        self._blink_on()

    def off(self):
        self.logger.debug('')

        if self.tmr:
            self.tmr.cancel()
            self.tmr.join()
        super().off()

    def _blink_on(self):
        self.logger.debug('')

        self.tmr = threading.Timer(self.on_sec,  self._blink_off)
        super().on()
        self.tmr.start()

    def _blink_off(self):
        self.logger.debug('')

        self.tmr = threading.Timer(self.off_sec, self._blink_on)
        super().off()
        self.tmr.start()

def app(pin, debug):
    logger.debug('pin=%d', pin)

    l = Led(pin)
    l.on()
    time.sleep(1)
    l.off()
    time.sleep(1)
    
    for s in [0.02, 0.5]:
        print(s)
        l.blink(s, s)
        time.sleep(3)
    l.off()	# Important !

    with Led(pin) as led:
        led.on()
        time.sleep(1)
        led.off()
        time.sleep(1)

        for s in [0.02, 0.5]:
            print(s)
            led.blink(s, s)
            time.sleep(3)
    # In this case, off() is not necessary (off() is called auotmatically)

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, nargs=1)
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
