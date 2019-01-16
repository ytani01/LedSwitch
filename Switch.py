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
handler_fmt = Formatter(
    '%(asctime)s %(levelname)s %(name)s.%(funcName)s> %(message)s',
    datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False

class SwitchListener(threading.Thread):
    def __init__(self, pin, callback_func,
                 sw_loop_interval=0.02, timeout_sec=[0.7, 1, 3, 5, 7],
                 debug=False):

        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)
            
        self.pin           = pin
        self.callback_func = callback_func

        self.eventq        = queue.Queue()

        self.sw = []
        for p in pin:
            s = Switch(p, self.eventq, sw_loop_interval, timeout_sec, debug)
            self.sw.append(s)

        super().__init__(daemon=True)
        self.start()

    def run(self):
        while True:
            event = self.eventq.get()
            self.callback_func(self.sw, event)

class SwitchTimer:
    def __init__(self, loop_interval, timeout_sec=[0.7, 1, 3, 5, 7],
                 debug=False):
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

        self.loop_interval = loop_interval
        self.timeout_sec   = timeout_sec
        self.stop()

        self.logger.debug('loop_interval = %f', self.loop_interval)
        self.logger.debug('timeout_sec   = %s', self.timeout_sec)
        self.logger.debug('timeout_idx   = %d', self.timeout_idx)
        self.logger.debug('start_sec     = %f', self.start_sec)
            
    def start(self):
        if len(self.timeout_sec) == 0:
            self.logger.debug(len(self.timeout_sec))
            self.stop()
            return
        
        self.start_sec   = time.time()
        self.timeout_idx = 0

    def stop(self):
        self.start_sec   = -1
        self.timeout_idx = -1

    def is_alive(self):
        return (self.start_sec > 0)

    def is_expired(self):
        if not self.is_alive():
            return False
        
        timer_sec = time.time() - self.start_sec
        tout_sec  = self.timeout_sec[self.timeout_idx]
        return (timer_sec >= tout_sec)

    def next_timeout(self):
        self.timeout_idx += 1
        if self.timeout_idx >= len(self.timeout_sec):
            self.stop()

###
class SwitchEvent():
    def __init__(self, pin, name, timeout_idx, value, push_count, debug=False):
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

        self.logger.debug('pin=%d, name=%s', pin, name)

        self.pin         = pin
        self.name        = name
        self.timeout_idx = timeout_idx
        self.value       = value
        self.push_count  = push_count

    def print(self):
        print('pin: %d' % self.pin)
        print('  name       : %s' % self.name)
        print('  timeout_idx: %d' % self.timeout_idx)
        print('  value      : %s' % self.value)
        print('  push_count : %d' % self.push_count)

class Switch(threading.Thread):
    ON  = 0
    OFF = 1
    
    @classmethod
    def val2str(cls, val):
        if val == cls.ON:
            return 'ON'
        if val == cls.OFF:
            return 'OFF'
        return ''

    def __init__(self, pin, eventq,
                 loop_interval=0.02, timeout_sec=[0.7, 1, 3, 5, 7],
                 debug=False):
        '''
        timeout_sec[0]  timeout(sec) for multi-click
        timeout_sec[1:] timeouts(sec) for long-press (long-long-press ..)
        '''
        self.logger = logger.getChild(__class__.__name__)
        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)
            
        self.logger.debug('pin=%d', pin)

        self.pin           = pin
        self.event         = eventq
        self.loop_interval = loop_interval
        self.timeout_sec   = timeout_sec

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.timer = SwitchTimer(self.loop_interval, self.timeout_sec, debug)
        
        self.val        = 1.0
        self.prev_onoff = self.OFF
        self.push_count = 0

        super().__init__(daemon=True)
        self.start()

    def run(self):
        self.logger.debug('start')
        
        while True:
            t1 = time.time()			# ロスタイム計算用
            new_val = GPIO.input(self.pin)

            # XXX ここまでやる必要はあるか？
            self.val = new_val * 0.6 + self.val * 0.4
            onoff = self.prev_onoff
            if self.val > 0.7:
                onoff = self.OFF
            if self.val < 0.3:
                onoff = self.ON

            if onoff == self.OFF:
                idx = self.timer.timeout_idx
                if idx != 0:
                    self.push_count = 0
                if idx >= 1:
                    self.timer.stop()
                
            if onoff != self.prev_onoff:
                self.logger.debug('onoff=%d', onoff)

                if onoff == self.ON:	# pressed
                    self.push_count += 1
                    if self.push_count == 1:
                        self.timer.start()
                        
                    self.event.put(SwitchEvent(self.pin, 'pressed',
                                               self.timer.timeout_idx,
                                               onoff,
                                               self.push_count))

                if onoff == self.OFF:	# released
                    self.event.put(SwitchEvent(self.pin, 'released',
                                               self.timer.timeout_idx,
                                               onoff,
                                               self.push_count))
                    
                self.prev_onoff = onoff

            if self.timer.is_expired():
                self.logger.debug('timer.timeout_idx = %d',
                                  self.timer.timeout_idx)
                self.logger.debug('  push_count = %d', self.push_count)
                self.logger.debug('  onoff      = %d', onoff)
                        
                self.event.put(SwitchEvent(self.pin, 'timer',
                                           self.timer.timeout_idx,
                                           onoff,
                                           self.push_count))

                self.timer.next_timeout()
                
            t_loss = time.time() - t1			# ロスタイム計算
            t_sleep = self.loop_interval - t_loss
            if t_sleep > 0:
                time.sleep(self.loop_interval - t_loss)
                
#####
def cb(sw, event):
    event.print()

def app(pin, debug):
    if debug:
        logger.setLevel(DEBUG)
    else:
        logger.setLevel(INFO)
        
    logger.debug('pin=%s', pin)

    sw = SwitchListener(pin, cb, debug=debug)

    while True:
        time.sleep(1)

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('pin', metavar='<pin>', type=int, nargs=-1)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(pin, debug):
    if debug:
        logger.setLevel(DEBUG)
    else:
        logger.setLevel(INFO)

    if len(pin) == 0:
        logger.error('pin=%s', pin)
        return

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
