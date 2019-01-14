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
logger.setLevel(INFO)
handler = StreamHandler()
handler.setLevel(DEBUG)
handler_fmt = Formatter('%(asctime)s %(levelname)s %(name)s.%(funcName)s> %(message)s',
                        datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False

class ButtonListener(threading.Thread):
    def __init__(self, pin, callback_func,
                 sw_loop_interval=0.02, timeout_sec=[0.7, 1, 3, 5],
                 debug=False):

        self.callback_func = callback_func
        self.sw = Button(pin, sw_loop_interval, timeout_sec, debug)
        self.sw.start()

        super().__init__(daemon=True)

    def run(self):
        while True:
            event = self.sw.event_get()
            self.callback_func(self.sw, event)

class ButtonTimer:
    def __init__(self, loop_interval, timeout_sec=[0.7, 1, 3, 5]):
        self.loop_interval = loop_interval
        self.timeout_sec   = timeout_sec
        self.stop()

    def start(self):
        self.start_sec   = time.time()
        self.timeout_idx = 0

    def stop(self):
        self.start_sec   = -1
        self.timeout_idx = -1

    def is_alive(self):
        return (self.start_sec > 0)

    def is_expired(self):
        timer_sec = time.time() - self.start_sec
        tout_sec  = self.timeout_sec[self.timeout_idx]
        return (timer_sec >= tout_sec)

    def next_timeout(self):
        self.timeout_idx += 1
        if self.timeout_idx >= len(self.timeout_sec):
            self.stop()

###
class ButtonEvent():
    def __init__(self, name, timeout_idx, value, push_count):
        self.name = name
        self.timeout_idx = timeout_idx
        self.value = value
        self.push_count = push_count

    def print(self):
        print('name: %s'  % self.name)
        print('  timeout_idx: %d' % self.timeout_idx)
        print('  value      : %s' % self.value)
        print('  push_count : %d' % self.push_count)

class Button(threading.Thread):
    ONOFF = ['ON', 'OFF']
    
    def __init__(self, pin, interval=0.02, timeout_sec=[0.7, 1, 3, 5],
                 debug=False):
        '''
        timeout_sec[0]  timeout(sec) for multi-click
        timeout_sec[1:] timeouts(sec) for long-press (long-long-press ..)
        '''
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            logger.setLevel(DEBUG)
        self.logger.debug('pin=%d', pin)

        self.pin = pin
        self.loop_interval = interval
        self.timeout_sec = timeout_sec
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.event = queue.Queue()
        self.timer = ButtonTimer(self.loop_interval, self.timeout_sec)
        
        self.val        = 1.0
        self.prev_val01 = __class__.ONOFF.index('OFF')
        self.push_count   = 0

        super().__init__(daemon=True)

    def event_put(self, event_name, timeout_idx, val, push_count):
        event = {
            'name'        : event_name,
            'timeout_idx' : timeout_idx,
            'value'       : self.value2str(val),
            'count'       : push_count	}
        
        self.event.put(event)

    def event_get(self):
        return self.event.get()

    def event_print(self, event):
        print('name: %s'  % event['name'])
        print('  timeout_idx: %d' % event['timeout_idx'])
        print('  value      : %s' % event['value'])
        print('  count      : %d' % event['count'])

    def value(self, text):
        try:
            return __class__.ONOFF.index(text)
        except ValueError:
            return -1

    def value2str(self, val):
        try:
            return __class__.ONOFF[val]
        except IndexError:
            return ''

    def run(self):
        self.logger.debug('start')
        
        while True:
            t1 = time.time()			# ロスタイム計算用
            new_val = GPIO.input(self.pin)

            # XXX ここまでやる必要はあるか？
            self.val = new_val * 0.5 + self.val * 0.5
            if self.val > 0.7:
                val01 = 1	# off
            if self.val < 0.3:
                val01 = 0	# on

            if val01 == self.value('OFF'):
                timeout_idx = self.timer.timeout_idx
                if timeout_idx != 0:
                    self.push_count = 0
                if timeout_idx >= 1:
                    self.timer.stop()
                
            if val01 != self.prev_val01:
                self.logger.debug('val01=%d', val01)

                if val01 == 0:	# pressed
                    self.push_count += 1
                    if self.push_count == 1:
                        self.timer.start()
                        
                    self.event.put(ButtonEvent('pressed',
                                               self.timer.timeout_idx,
                                               self.value2str(val01),
                                               self.push_count))

                if val01 == 1:	# released
                    self.event.put(ButtonEvent('released',
                                               self.timer.timeout_idx,
                                               self.value2str(val01),
                                               self.push_count))
                    
                self.prev_val01 = val01

            if self.timer.is_alive():
                if self.timer.is_expired():
                    self.logger.debug('timer.timeout_idx = %d',
                                      self.timer.timeout_idx)
                    self.logger.debug('  push_count  = %d', self.push_count)
                    self.logger.debug('  val01     = %d', val01)
                        
                    self.event.put(ButtonEvent('timer',
                                               self.timer.timeout_idx,
                                               self.value2str(val01),
                                               self.push_count))

                    self.timer.next_timeout()
                
            t_loss = time.time() - t1			# ロスタイム計算
            time.sleep(self.loop_interval - t_loss)
                
#
#
#
def cb(sw, event):
    event.print()

def app(pin, debug):
    logger.debug('pin=%d', pin)

    sw = ButtonListener(pin, cb, debug=debug)
    sw.start()
    while True:
        time.sleep(1)

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, nargs=1)
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
