#!/usr/bin/env python3
#
# (C) 2018 Yoichi Tanibayashi
#
import pigpio
import threading
import queue
import time

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
class SwitchListener:
    def __init__(self, debug=False):
        self.debug = debug
        self.logger = get_logger(self.__name__, self.debug)
        self.logger.debug('')

        super().__init__()

    def run(self):
        self.logger.debug('')
        
        while True:
            pass

    def _send_msg(self, msg):
        self.logger.debug('')

    def send(self, msg_type, msg_data):
        self.logger.debug('msg_type:%s, msg_data:%s', msg_type, msg_data)
        msg = {'type': msg_type, 'data':msg_data}
        _send_msg(msg)

    def end(self):
        self.logger.debug('')
        self.send_msg
        
        
#####
class Switch:
    ON      = 0
    OFF     = 1
    VAL2STR = ['ON', 'OFF']

    def __init__(self, pi, pin, debug=False):
        self.debug = debug
        self.logger = get_logger(__class__.__name__, self.debug)

        self.pi  = pi
        self.pin = pin
        self.logger.debug('pin = %s', self.pin)

        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)
        self.cb = self.pi.callback(self.pin, pigpio.EITHER_EDGE, self.cb_func)

        self.now_sec = time.time()

    def get(self):
        return self.pi.read(self.pin)

    def cb_func(self, pin, val, tick):
        self.logger.debug('pin=%d, val=%d, tick=%d', pin, val, tick)

        if time.time() - self.now_sec < 0.01:
            return
        
        self.now_sec = time.time()

        print('%d: %s' % (pin, self.VAL2STR[val]))

    def end(self):
        self.logger.debug('')
        cb.cancel()
        
        
#####
class app:
    def __init__(self, pi, pin, debug=False):
        self.debug = debug
        self.logger = get_logger(__class__.__name__, self.debug)
        self.logger.debug('pin=%s', str(pin))

        self.pi  = pi
        self.pin = pin

        sw = []
        for p in self.pin:
            sw.append(Switch(self.pi, p, debug=self.debug))

        #sl = SwitchListener(self.pi, sw, self.cb, debug=debug)

    def main(self):
        self.logger.debug('')
        
        if len(self.pin) < 1:
            print('no pin')
            return
        
        print('Ready: pin=%s' % str(self.pin))
        while True:
            print()
            time.sleep(3)

    def cb(self, event):
        event.print()

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, nargs=-1)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    logger.setLevel(INFO)
    if debug:
        logger.setLevel(DEBUG)

    logger.debug('pin=%s', pin)
    
    pi = pigpio.pi()
    try:
        app(pi, pin, debug=debug).main()
    finally:
        pi.stop()


if __name__ == '__main__':
    main()
