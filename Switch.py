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
def init_logger(name, debug):
    l = logger.getChild(name)
    if debug:
        l.setLevel(DEBUG)
    else:
        l.setLevel(INFO)
    return l

class SwitchListener(threading.Thread):
    '''
    stop(): Dont't forget to call stop() when finished

    callback function: cb_func(event) ... event: SwitchEvent class
    '''

    def __init__(self, switch, cb_func, sw_loop_interval=0.02,
                 debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('sw_loop_interval:%.4f', sw_loop_interval)
            
        self.switch  = switch
        self.cb_func = cb_func

        self.eventq  = queue.Queue()

        self.sw = SwitchWatcher(self.switch, self.eventq, sw_loop_interval,
                                debug)

        super().__init__(daemon=True)
        self.start()

    def run(self):
        self.logger.debug('start')
        while True:
            event = self.eventq.get()
            if event == SwitchEvent.NULL:
                break
            self.cb_func(event)
        self.logger.debug('end')

    def stop(self):
        self.logger.debug('')
        self.sw.stop()
        self.eventq.put(SwitchEvent.NULL)
        self.join()
        self.logger.debug('join()')

class SwitchTimer:
    def __init__(self, timeout_sec=[0.7, 1, 3, 5, 7], debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('timeout_sec:%s', timeout_sec)

        self.timeout_sec = timeout_sec

        self.stop()
        self.logger.debug('timeout_idx:%d', self.timeout_idx)
        self.logger.debug('start_sec  :%f', self.start_sec)
            
    def start(self):
        self.logger.debug('')

        if len(self.timeout_sec) == 0:
            self.logger.debug('ignored')
            self.stop()
            return
        
        self.start_sec   = time.time()
        self.timeout_idx = 0

    def stop(self):
        self.logger.debug('')
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

class SwitchEvent:
    NULL = 0

    def __init__(self, pin, name, timeout_idx, value, push_count, debug=False):
        self.logger = init_logger(__class__.__name__, debug)

        self.logger.debug('pin=%d, name=%s', pin, name)

        self.pin         = pin
        self.name        = name
        self.timeout_idx = timeout_idx
        self.value       = value
        self.push_count  = push_count

    def click_count(self):
        self.logger.debug('')
        
        if self.name != 'timer':
            return 0

        if self.timeout_idx != 0:
            return 0

        if self.value == Switch.ON:
            return 0
        
        return self.push_count
    
    def longpress_level(self):
        self.logger.debug('')
        
        if self.name != 'timer':
            return 0
        if self.value == Switch.OFF:
            return 0

        return self.timeout_idx

    def print(self):
        print('pin: %d' % self.pin)
        print('  name       : %s' % self.name)
        print('  timeout_idx: %d' % self.timeout_idx)
        print('  value      : %s' % Switch.val2str(self.value))
        print('  push_count : %d' % self.push_count)

class Switch:
    '''
    timeout_sec[0]  timeout(sec) for multi-click
    timeout_sec[1:] timeouts(sec) for long-press (long-long-press ..)
    '''
        
    ON  = 0
    OFF = 1
    
    @classmethod
    def val2str(cls, val):
        if val == cls.ON:
            return 'ON'
        if val == cls.OFF:
            return 'OFF'
        return ''

    def __init__(self, pin, timeout_sec=[0.7, 1, 3, 5, 7], debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('pin         : %d', pin)
        self.logger.debug('timeout_sec : %s', timeout_sec)

        self.pin         = pin
        self.timeout_sec = timeout_sec

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        self.timer      = SwitchTimer(self.timeout_sec, debug=debug)
        self.val        = 1.0
        self.prev_onoff = self.OFF
        self.push_count = 0

    def get_onoff(self):
        new_val = GPIO.input(self.pin)

        # ここまでやる？
        self.val = new_val * 0.6 + self.val * 0.4

        onoff = self.prev_onoff
        if self.val > 0.7:
            onoff = Switch.OFF
        if self.val < 0.3:
            onoff = Switch.ON

        return onoff

class SwitchWatcher(threading.Thread):
    '''
    stop(): Don't forget to call stop() when finished
    '''

    def __init__(self, switch, eventq, loop_interval=0.02, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.logger.debug('loop_interval:%.4f', loop_interval)

        self.switch        = switch
        self.eventq        = eventq
        self.loop_interval = loop_interval

        self.loop_flag     = True
        super().__init__(daemon=True)
        self.start()

    def run(self):
        self.logger.debug('start')

        while self.loop_flag:
            t1 = time.time()			# ロスタイム計算用
            for sw in self.switch:
                onoff = sw.get_onoff()

                if onoff == sw.OFF:
                    idx = sw.timer.timeout_idx
                    if idx != 0:
                        sw.push_count = 0 # push_countクリア
                    if idx >= 1:
                        sw.timer.stop() # タイマーストップ

                if onoff != sw.prev_onoff:
                    self.logger.debug('onoff=%d:%s', onoff, sw.val2str(onoff))
                    sw.prev_onoff = onoff

                    if onoff == sw.ON: # pressed
                        sw.push_count += 1
                        if sw.push_count == 1:
                            sw.timer.start()

                        e = SwitchEvent(sw.pin, 'pressed',
                                        sw.timer.timeout_idx, onoff,
                                        sw.push_count)
                    else: # released
                        e = SwitchEvent(sw.pin, 'released',
                                        sw.timer.timeout_idx, onoff,
                                        sw.push_count)
                    self.eventq.put(e)

                while sw.timer.is_expired():
                    e = SwitchEvent(sw.pin, 'timer', sw.timer.timeout_idx,
                                    onoff, sw.push_count)
                    self.eventq.put(e)
                    sw.timer.next_timeout()
            
            t_loss = time.time() - t1	# ロスタイム計算
            t_sleep = self.loop_interval - t_loss
            if t_sleep > 0:
                time.sleep(self.loop_interval - t_loss)
            else:
                self.logger.warning('t_loss=%f', t_loss)

        self.logger.debug('end')

    def stop(self):
        self.logger.debug('')
        self.loop_flag = False
        self.join()
        self.logger.debug('join()')
                
#####
class app:
    def __init__(self, pin, debug=False):
        logger.setLevel(INFO)
        if debug:
            logger.setLevel(DEBUG)

        logger.debug('pin:%s', pin)

        self.pin = pin

        sw = []
        for p in pin:
            sw.append(Switch(p, debug=debug))

        sl = SwitchListener(sw, self.cb, debug=debug)

    def main(self):
        if len(self.pin) < 1:
            print('no pin')
            return
        
        print('Ready: pin=%s' % str(self.pin))
        while True:
            time.sleep(1)

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

    setup_GPIO()
    try:
        app(pin, debug=debug).main()
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
