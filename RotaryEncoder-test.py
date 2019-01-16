#!/usr/bin/env python3
#
# (C) 2018 Yoichi Tanibayashi
#
from Switch import SwitchListener

import RPi.GPIO as GPIO
import threading
import queue
import time

import click

from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
logger = getLogger(__name__)
logger.setLevel(INFO)
handler = StreamHandler()
handler.setLevel(DEBUG)
handler_fmt = Formatter(
    '%(asctime)s %(levelname)s %(name)s.%(funcName)s> %(message)s',
    datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False

class RotaryEncoder:
    def __init__(self, pin, cb_func, debug=False):
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('%s', pin)
        
        self.pin = pin
        self.cb_func = cb_func

        self.stat = ['', '']
        self.q = queue.Queue()

        self.sw = []
        for i in [0, 1]:
            self.sw.append(SwitchListener(self.pin[i], self.sw_cb,
                                          timeout_sec=[0], debug=debug))
            self.sw[i].start()

    def sw_cb(self, sw, event):
        if event.name == 'timer':
            return

        if event.pin == self.pin[0]:
            chg_i = 0
        else:
            chg_i = 1
            
        v = 0
        if self.stat[0] != self.stat[1]:
            if chg_i == 0:
                v = -1
            else:
                v = 1

        self.stat[chg_i] = event.value
                
        self.logger.debug('stat=%s, v=%d', self.stat, v)

        if self.stat[0] == self.stat[1]:
            self.q.put(v)

#
#
#
def cb(sw, event):
    if event.name == 'timer':
        return
    
    print('%d %s' % (event.pin, event.name))

def app(pin, debug):
    logger.debug('pin=%s', pin)

    rotenc = RotaryEncoder(pin, cb, debug)
                           
    while True:
        v = rotenc.q.get()
        print(v)
        time.sleep(1)

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', type=int, nargs=2)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
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
