#!/usr/bin/env python3
#
# (C) 2018 Yoichi Tanibayashi
#
from Switch import SwitchListener, Switch

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
def init_logger(name, debug):
    l = logger.getChild(name)
    if debug:
        l.setLevel(DEBUG)
    else:
        l.setLevel(INFO)
    return l

class RotaryKey:
    '''
    stop(): Don't forget to call stop() when finished.

    callback function: cb_func(out_ch, cur_ch)
    '''
    
    CH_LIST = ' _-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    CH_BS   = '<BS>'
    CH_ENT  = '<ENT>'

    def __init__(self, pin_re, pin_sw, cb_func, chl=CH_LIST, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('pin_re:%s', pin_re)
        self.logger.debug('pin_sw:%d', pin_sw)
        self.logger.debug('chl   :%s', chl)

        self.pin_re  = pin_re
        self.pin_sw  = pin_sw
        self.cb_func = cb_func
        self.chl     = chl
        
        self.chl_len = len(self.chl)
        self.chl_i   = 0
        self.cur_ch  = self.CH_LIST[self.chl_i]
        self.out_ch  = ''

        self.rl = RotaryEncoderListener(self.pin_re, self.cb_re, debug=debug)
        self.sw = Switch(self.pin_sw, debug=debug)
        self.sl = SwitchListener([self.sw], self.cb_sw, debug=debug)

    def stop(self):
        self.logger.debug('')
        self.sl.stop()
        self.rl.stop()

    def cb_re(self, val):
        self.logger.debug('val=%d:%s', val, RotaryEncoder.val2str(val))
        self.chl_i += val
        self.chl_i %= self.chl_len
        self.cur_ch = self.chl[self.chl_i]
        self.logger.debug('chl_i:%d, cur_ch:%s', self.chl_i, self.cur_ch)

        self.cb_func('', self.cur_ch)

    def cb_sw(self, event):
        self.logger.debug('event=%s', event.name)

        if event.name == 'released':
            return
        
        if event.name == 'pressed':
            self.out_ch = self.cur_ch
            return

        # 'timer' event
        ll = event.longpress_level()
        cc = event.click_count()
        self.logger.debug('ll=%d', ll)
        self.logger.debug('cc=%d', cc)

        if ll > 0: # long pressed
            self.cb_func(self.CH_ENT, self.cur_ch)
            self.out_ch = ''
            return

        if cc > 1: # multi click
            self.cb_func(self.CH_BS, self.cur_ch)
            self.out_ch = ''
            return

        if cc == 1: # single click
            self.cb_func(self.out_ch, self.cur_ch)
            self.out_ch = ''

class RotaryEncoderListener(threading.Thread):
    '''
    stop(): Don't forget to call stop() when finished.

    callback function: cb_func(val) ... val: RotaryEncoder.CW|CCW
    '''
    
    def __init__(self, pin, cb_func, sw_loop_interval=0.002, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('pin:%s', pin)
        self.logger.debug('sw_loop_interval:%.4f', sw_loop_interval)

        if len(pin) != 2:
            return None

        self.pin              = pin
        self.cb_func          = cb_func
        self.sw_loop_interval = sw_loop_interval

        self.q                = queue.Queue()

        self.rotenc           = RotaryEncoder(self.pin, self.q,
                                              self.sw_loop_interval,
                                              debug)

        super().__init__(daemon=True)

        time.sleep(0.1)
        while not self.q.empty():
            self.logger.debug('ignore initail input: %s',
                              RotaryEncoder.val2str(self.q.get()))

        self.start()

    def run(self):
        self.logger.debug('start')
        while True:
            v = self.q.get()
            if v == RotaryEncoder.NULL:
                break
            self.cb_func(v)
        self.logger.debug('end')

    def stop(self):
        self.logger.debug('')
        self.q.put(RotaryEncoder.NULL)
        self.join()
        self.logger.debug('join()')

class RotaryEncoder:
    CW   = 1
    CCW  = -1
    NULL = 0

    @classmethod
    def val2str(cls, val):
        if val == cls.CW:
            return 'CW'
        if val == cls.CCW:
            return 'CCW'
        return ''

    def __init__(self, pin, valq, loop_interval, debug=False):
        '''
        @param pin			[pin1, pin2]
        @param valq			value queue
        @param loop_interval	sec
        @param debug		debug flag
        '''
    
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('pin:%s', pin)

        if len(pin) != 2:
            return None

        self.pin           = pin
        self.valq          = valq
        self.loop_interval = loop_interval

        self.switch = []
        for p in self.pin:
            sw = Switch(p, timeout_sec=[], debug=debug)
            self.switch.append(sw)
        
        self.stat = [-1, -1]
        self.sl   = SwitchListener(self.switch, self.cb, self.loop_interval,
                                   debug=debug)

    def cb(self, event):
        self.logger.debug('event.name:%s', event.name)
        
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

        self.logger.debug('stat=%s, v=%d:%s', self.stat, v, self.val2str(v))

        self.valq.put(v)

#####
class sample:
    def __init__(self, pin, debug):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('pin=%s', pin)

        self.pin_re    = pin[0:2]
        self.pin_sw    = pin[2]

        self.text      = ''

    def main(self, debug):
        print('### RotaryEncoderListener demo')

        self.rel = RotaryEncoderListener(self.pin_re, self.cb_re, debug=debug)
        self.sw  = Switch(self.pin_sw, debug=debug)
        self.sl  = SwitchListener([self.sw], self.cb_sw, debug=debug)
        self.start_sec = time.time()

        self.loop_flag = True
        while self.loop_flag:
            time.sleep(1)

        self.sl.stop()
        self.rel.stop()

        print('')
        print('### RotaryKey demo')
        self.rek = RotaryKey(self.pin_re, self.pin_sw, self.cb_rk, debug=debug)

        self.loop_flag = True
        while self.loop_flag:
            time.sleep(1)

        self.rek.stop()

        print('')
        print('### Finished')

    def cb_re(self, v):
        print('%.3f, ' % (time.time() - self.start_sec), end='')
        print('%s' % RotaryEncoder.val2str(v))

    def cb_sw(self, event):
        print('%.3f, ' % (time.time() - self.start_sec), end='')
        event.print()
        if event.name == 'timer' and event.timeout_idx == 1:
            print('long pressed: %d' % event.pin)
            self.loop_flag = False

    def cb_rk(self, out_ch, cur_ch):
        if out_ch != '':
            if out_ch == RotaryKey.CH_ENT:
                print('>%s<' % self.text) # enter
                if self.text == '': # finish
                    self.loop_flag = False
                    return
                self.text = ''

            elif out_ch == RotaryKey.CH_BS:
                self.text = self.text[:-1]

            else:       
                self.text += out_ch
                
        print('%s[%s]' % (self.text, cur_ch))

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='pin1 pin2 pin_sw', type=int, nargs=3)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    logger.setLevel(INFO)
    if debug:
        logger.setLevel(DEBUG)

    setup_GPIO()
    try:
        sample(pin, debug).main(debug)
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
