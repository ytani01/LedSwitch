#!/usr/bin/env python3
#
# (C) Yoichi Tanibayashi
#
import RPi.GPIO as GPIO
import time
import threading

import click
from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
logger = getLogger(__name__)
logger.setLevel(DEBUG)
console_handler = StreamHandler()
console_handler.setLevel(DEBUG)
handler_fmt = Formatter(
    '%(asctime)s %(levelname)s %(name)s.%(funcName)s()> %(message)s',
                        datefmt='%H:%M:%S')
console_handler.setFormatter(handler_fmt)
logger.addHandler(console_handler)
logger.propagate = False
def get_logger(name, debug=False):
    l = logger.getChild(name)
    if debug:
        l.setLevel(DEBUG)
    else:
        l.setLevel(INFO)

    return l

#####
class Switch1:
    ON  = 0
    OFF = 1
    BOUNCE_TIME = 2
    
    def __init__(self, pin, debug=False):
        self.debug = debug
        self.logger = get_logger(__class__.__name__, debug)
        self.logger.debug('pin : %d', pin)

        self.pin = pin

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.handle,
                              bouncetime=self.BOUNCE_TIME)

        self.prev_ms = 0
        self.ms = 0
        self.val = self.OFF

        self.sn = 0

    def get(self):
        self.logger.debug('')
        val = GPIO.input(self.pin)

        return val

    def handle(self, pin):
        self.sn += 1
        self.logger.debug('[%04d] pin=%d', self.sn, pin)

        ms = time.time() * 1000
        v = self.get()

        if v == self.val:
            print('![%04d] %6d: pin(%d): %s' %
                  (self.sn, ms - self.ms, pin, self.val2str(1 - v)))
        self.val = v
            
        print('[%04d] %6d: pin(%d): %s' %
              (self.sn, ms - self.ms, pin, self.val2str(self.val)))

        self.ms = ms

    def end(self):
        self.logger.debug('')
        GPIO.remove_event_detect(self.pin)

    @classmethod
    def val2str(cls, val):
        if val == cls.ON:
            return 'ON'
        if val == cls.OFF:
            return 'OFF'
        return ''


#####
class sample:
    def __init__(self, pins, debug=False):
        self.debug = debug
        self.logger = get_logger(__class__.__name__, self.debug)
        self.logger.debug('pins=%s', str(pins))

        self.pins = pins

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        self.sw = []
        for p in self.pins:
            self.sw.append(Switch1(p, self.debug))


    def main(self):
        self.logger.debug('')
        
        while True:
            #print(time.strftime('%Y/%m/%d(%a) %H:%M:%S'))
            #print(Switch1.val2str(self.sw[0].get()))
            time.sleep(1)
            

    def end(self):
        self.logger.debug('')
        for i in range(len(self.sw)):
            self.sw[i].end()
            
        GPIO.cleanup()
        

    # sample callback function
    def sample_cb_func(self, dev, code, value):
        self.logger.debug('')
        
        print('dev=%d, code=%d:%s, value=%d:%s' % (dev,
                                                   code, AbShutter.keycode2str(code),
                                                   value, AbShutter.val2str(value)))
        

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pins', type=int, nargs=-1)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pins, debug):
    logger.setLevel(INFO)
    if debug:
        logger.setLevel(DEBUG)

    logger.debug('pins=%s', str(pins))

    try:
        app = sample(pins, debug=debug)
        app.main()
    finally:
        app.end()
        print('END')

if __name__ == '__main__':
    main()
