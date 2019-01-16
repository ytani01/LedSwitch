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

class RotaryEncoderListener(threading.Thread):
    def __init__(self, pin, cb_func, sw_loop_interval=0.001, debug=False):
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

        self.logger.debug('pin=%s, interval=%f', pin, sw_loop_interval)

        self.pin = pin
        self.cb_func = cb_func
        self.sw_loop_interval = sw_loop_interval

        self.q = queue.Queue()

        self.rotenc = RotaryEncoder(self.pin, self.q, self.sw_loop_interval,
                                    debug)

        super().__init__(daemon=True)

        time.sleep(0.1)
        while not self.q.empty():
            self.logger.debug('ignore initail input: %s',
                              RotaryEncoder.val2str(self.q.get()))
                
        self.start()

    def run(self):
        while True:
            v = self.q.get()
            self.cb_func(v)

class RotaryEncoder:
    CW  = 1
    CCW = -1

    def __init__(self, pin, q, sw_loop_interval=0.001, debug=False):
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

        self.logger.debug('%s', pin)
        
        self.pin              = pin
        self.q                = q
        self.sw_loop_interval = sw_loop_interval

        self.stat = ['', '']
        
        self.sw = SwitchListener(self.pin, self.sw_cb, self.sw_loop_interval,
                                 timeout_sec=[],
                                 debug=debug)

    def sw_cb(self, sw, event):
        if event.name == 'timer':
            return

        if event.pin == self.pin[0]:
            pin_i = 0
        else:
            pin_i = 1
            
        self.stat[pin_i] = event.value

        if self.stat[0] != self.stat[1]:
            return

        if pin_i != 0:
            v = self.CW
        else:
            v = self.CCW
                
        self.logger.debug('stat=%s, v=%s', self.stat, self.val2str(v))

        self.q.put(v)

    @classmethod
    def val2str(cls, val):
        if val == cls.CW:
            return 'CW'
        if val == cls.CCW:
            return 'CCW'
        return ''

#####
class app:
    def __init__(self, pin, debug):
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

        self.logger.debug('pin=%s', pin)

        self.pin = pin

        self.rotenc = RotaryEncoderListener(self.pin, self.cb, debug=debug)

        self.start_sec = time.time()

    def main(self):
        print('Ready')
        while True:
            time.sleep(1)

    def cb(self, v):
        print('%.3f, %s' % (time.time() - self.start_sec,
                            RotaryEncoder.val2str(v)))

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', type=int, nargs=2)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    if debug:
        logger.setLevel(DEBUG)
    else:
        logger.setLevel(INFO)

    setup_GPIO()
    try:
        app(pin, debug).main()
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
