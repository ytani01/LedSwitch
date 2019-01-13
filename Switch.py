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

class SwitchTimer:
    def __init__(self, loop_interval, timeout=[0.7, 1, 3, 5]):
        self.loop_interval = loop_interval
        self.timeout = timeout
        self.stop()

    def start(self):
        self.tick   = 0
        self.tout_i = 0

    def stop(self):
        self.tick   = -1
        self.tout_i = -1

    def timeout_check(self):
        timer_sec = self.tick * self.loop_interval
        tout_sec  = self.timeout[self.tout_i]
        self.tick += 1
        return (timer_sec > tout_sec)

    def is_alive(self):
        return (self.tick >= 0)

    def inc_timeout(self):
        self.tout_i += 1
        if self.tout_i >= len(self.timeout):
            self.stop()

class SwitchWatcher(threading.Thread):
    ONOFF = ['ON', 'OFF']
    
    def __init__(self, pin, interval=0.02, timeout=[0.7, 1, 3, 5]):
        '''
        tout[0]  timeout(sec) for multi-click
        tout[1:] timeouts(sec) for long-press (long-long-press ..)
        '''
        self.logger = logger.getChild(__class__.__name__)
        self.logger.debug('pin=%d', pin)

        self.pin = pin
        self.loop_interval = interval
        self.timeout = timeout
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.event = queue.Queue()
        self.timer = SwitchTimer(self.loop_interval, self.timeout)
        
        self.val       = 1.0
        self.prev_val3 = __class__.ONOFF.index('OFF')
        self.on_count  = 0

        super().__init__()

    def event_put(self, event_name, tout_i, val, on_count):
        event = {
            'name'   : event_name,
            'tout_i' : tout_i,
            'value'  : __class__.ONOFF[val],
            'count'  : on_count	}
        
        self.event.put(event)

    def event_get(self):
        return self.event.get()

    def run(self):
        self.logger.debug('start')
        
        while True:
            t1 = time.time()			# ロスタイム計算用
            new_val = GPIO.input(self.pin)

            # XXX ここまでやる必要はあるか？
            self.val = new_val * 0.5 + self.val * 0.5

            if self.val > 0.7:
                val3 = 1	# off
                if self.timer.tout_i != 0:
                    self.on_count = 0
                if self.timer.tout_i >= 1:
                    self.timer.stop()
                    
            if self.val < 0.3:
                val3 = 0	# on
                
            if val3 != self.prev_val3:
                self.logger.debug('val3=%d', val3)

                if val3 == 0:	# pressed
                    self.on_count += 1
                    if self.on_count == 1:
                        self.timer.start()
                        
                    self.event_put('pressed',
                                   self.timer.tout_i, val3, self.on_count)

                if val3 == 1:	# released
                    self.event_put('released',
                                   self.timer.tout_i, val3, self.on_count)
                    
                self.prev_val3 = val3

            if self.timer.is_alive():
                if self.timer.timeout_check():
                    self.logger.debug('timer.tout_i = %d', self.timer.tout_i)
                    self.logger.debug('  on_count = %d', self.on_count)
                    self.logger.debug('  val3     = %d', val3)
                        
                    self.event_put('timer',
                                   self.timer.tout_i, val3, self.on_count)

                    #self.on_count = 0
                    self.timer.inc_timeout()
                
            t_loss = time.time() - t1			# ロスタイム計算
            time.sleep(self.loop_interval - t_loss)

class Switch:
    '''Primitive Switch class
    '''
    SW_BOUNCE_MSEC = 150
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
            self.event_edge = GPIO.FALLING
            self.ON = GPIO.LOW
        else:
            self.pud = GPIO.PUD_DOWN
            self.event_dege = GPIO.RISING
            self.ON = GPIO.HIGH

        self.callback = {}
        for c in __class__.ACTION:
            self.callback[c] = None

        self.on = False
        self.on_count = 0
        self.on_start = 0
        self.on_sec = 0
        self.prev_sec = 0
        self.prev_val = -1

        self.tmr = threading.Timer(0, self.cbk_timer)
        
        self.enable()
        
    def enable(self):
        self.logger.debug('')
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.pud)
        GPIO.add_event_detect(self.pin, GPIO.BOTH,
                              callback=self.handle,
                              bouncetime=5)

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
        now_sec = time.time()
        val = GPIO.input(pin)

        while val == self.prev_val:
            self.logger.debug('val == prev_val? .. ignore')
            if val != self.ON:
                self.prev_val = val
                return
            val = GPIO.input(pin)
            self.logger.debug('val=%d', val)
            #return

        if (now_sec - self.prev_sec) * 1000 < __class__.SW_BOUNCE_MSEC:
            return
        self.prev_sec = now_sec

        if pin != self.pin:
            self.logger.warning('pin=%d not equal to self.pin=%d ??', pin, self.pin)
            return
        
        self.logger.debug('%d === pin=%d, val=%d', now_sec * 1000 % 10000, pin, val)

        self.prev_val = val

        if val != self.ON:
            self.logger.debug('OFF')
            return

        if not self.tmr.is_alive():
            self.tmr = threading.Timer(__class__.LONG_PUSH_MSEC/1000, self.cbk_timer)
            self.tmr.start()
            self.logger.debug('tmr start')
        else:
            self.logger.debug('tmr=%s:%s', self.tmr, self.tmr.is_alive())

        self.on_count += 1
        if self.on_count == 1:
            self.on_start = now_sec

        self.logger.debug('on_count=%d', self.on_count)

    def cbk_timer(self):
        now_sec = time.time()
        val = GPIO.input(self.pin)

        self.on       = (val == self.ON)
        self.on_sec   = now_sec - self.on_start
        self.logger.debug('%d ---', now_sec * 1000 % 10000)
        self.logger.debug('val=%d', val)
        self.logger.debug('self.on=%s', self.on)
        self.logger.debug('self.on_count=%d', self.on_count)
        self.logger.debug('self.on_sec=%.3f', self.on_sec)

        if self.on:
            self.logger.debug('* long[%d]', self.on_count)
        else:
            self.logger.debug('* click[%d]', self.on_count)
        
        self.on_count = 0
        self.on_sec   = 0
                
def app(pin, debug):
    logger.debug('pin=%d', pin)

    #sw = SwitchWatcher(pin, tout=[0.7])
    sw = SwitchWatcher(pin)
    sw.start()

    while True:
        event = sw.event_get()
        print('!!! %-8s %d %-3s %d' % (event['name'],
                                       event['tout_i'],
                                       event['value'],
                                       event['count']))
        time.sleep(0.1)

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
