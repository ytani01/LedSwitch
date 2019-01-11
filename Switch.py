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

class Switch:
    '''Primitive Switch class
    '''
    SW_BOUNCE_MSEC = 10
    LONG_PUSH_MSEC = 500
    CLICK_INTERVAL = 200
    ACTION = ['push', 'long_push', 'release', 'click']
    
    def __init__(self, pin, pull_up=True):
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('pin=%d, pull_up=%s', pin, pull_up)

        self.pin = pin
        self.pull_up = pull_up
        
        if self.pull_up:
            self.pud = GPIO.PUD_UP
        else:
            self.pud = GPIO.PUD_DOWN

        self.callback = {}
        for c in __class__.ACTION:
            self.callback[c] = None

        self.on = False
        self.on_count = 0
        self.on_start = 0
        
        self.enable()
        
    def enable(self):
        self.logger.debug('')
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.pud)
        GPIO.add_event_detect(self.pin, GPIO.BOTH,
                              callback=self.handle,
                              bouncetime=__class__.SW_BOUNCE_MSEC)

    def disable(self):
        self.logger.debug('')
        GPIO.remove_event_detect(self.pin)

    def set_callback(self, action, callback):
        if action not in __class__.ACTION:
            return

        self.callback[action] = callback

    def __enter__(self):
        self.logger.debug('')
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.logger.debug('%s, %s, %s', ex_type, ex_value, trace)
        self.disable()
        
    def handle(self, pin):
        self.logger.debug('pin=%d', pin)
        if pin != self.pin:
            self.logger.warning('pin=%d not equal to self.pin=%d ??', pin, self.pin)
            return

        now_sec = time.time()
        
        val = GPIO.input(self.pin)
        self.logger.debug('val=%d', val)

        self.on = False
        if self.pull_up and val == GPIO.LOW:
            self.on = True
        if not self.pull_up and val == GPIO.HIGH:
            self.on = True
        self.logger.debug('self.on=%d', self.on)

        if self.on:
            self.on_count += 1
            if self.on_count == 1:
                self.on_start = now_sec
            self.on_sec = now_sec - self.on_start

        self.logger.debug('on_count=%d, on_sec=%f', self.on_count, self.on_sec)
                
def app(pin, debug):
    logger.debug('pin=%d', pin)

    sw = Switch(pin)

    while True:
        time.sleep(1)

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, nargs=1)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    '''Switch class sample program

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
