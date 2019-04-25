#!/usr/bin/env python3
#
# (C) Yoichi Tanibayashi
#
import RPi.GPIO as GPIO
import time
import threading
import queue

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
class Switch1(threading.Thread):
    BOUNCE_TIME = 20 # msec
    EVENT_TOUT  = 0.5 # sec

    VAL         = ['ON', 'OFF', 'TIMEOUT']
    VAL_ON      = 0
    VAL_OFF     = 1
    VAL_TIMEOUT = 2
    
    STAT        = ['ON', 'OFF', 'HOLD']
    STAT_ON     = 0
    STAT_OFF    = 1
    STAT_HOLD   = 2
    
    def __init__(self, pin, bouncetime=BOUNCE_TIME, debug=False):
        self.debug = debug
        self.logger = get_logger(__class__.__name__, debug)
        self.logger.debug('pin : %d', pin)

        self.pin = pin

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.handle,
                              bouncetime=self.BOUNCE_TIME)

        self.q      = queue.Queue()
        self.eventq = queue.Queue()

        self.stat     = self.STAT_OFF

        self.t_on_start = 0

        super().__init__(daemon=True)

    def get_value(self):
        self.logger.debug('')
        val = GPIO.input(self.pin)

        return val

    def get_event(self):
        return self.eventq.get()

    def handle(self, pin):
        ts = time.time()
        v = self.get_value()
        self.logger.debug('%.3f:%d:%s', ts, pin, self.VAL[v])
        self.q.put([ts, v])

    def run(self):
        while True:
            try:
                [ts, v] = self.q.get(timeout=.5)
            except queue.Empty:
                # timeout
                ts = time.time()
                v  = self.VAL_TIMEOUT

            cur_val  = self.get_value()
            ev_out = False

            self.logger.debug('%d stat:%s v:%s cur_val:%s',
                              ts, self.STAT[self.stat], self.VAL[v], self.VAL[cur_val])

            prev_stat = self.stat
            if self.stat == self.STAT_ON:
                if v == self.VAL_ON:
                    pass
                elif v == self.VAL_OFF:
                    self.stat = self.STAT_OFF
                    ev_out = True
                elif v == self.VAL_TIMEOUT:
                    if cur_val == self.VAL_ON:
                        self.stat = self.STAT_HOLD
                        ev_out = True
                    elif cur_val == self.VAL_OFF:
                        self.stat = self.STAT_OFF
                        ev_out = True
                    else:
                        pass # error?
                else:
                    pass # error?

            elif self.stat == self.STAT_OFF:
                if v == self.VAL_ON:
                    self.stat = self.STAT_ON
                    self.on_start = time.time()
                    ev_out = True
                elif v == self.VAL_OFF:
                    pass
                elif v == self.VAL_TIMEOUT:
                    if cur_val == self.VAL_ON:
                        self.stat = self.STAT_ON
                        ev_out = True
                    elif cur_val == self.VAL_OFF:
                        pass
                    else:
                        pass # error?
                else:
                    pass # error?

            elif self.stat == self.STAT_HOLD:
                if v == self.VAL_ON:
                    self.stat = self.STAT_HOLD
                    ev_out = True
                elif v == self.VAL_OFF:
                    self.stat = self.STAT_OFF
                    ev_out = True
                elif v == self.VAL_TIMEOUT:
                    if cur_val == self.VAL_ON:
                        self.stat = self.STAT_HOLD
                        ev_out = True
                    elif cur_val == self.VAL_OFF:
                        self.stat = self.STAT_OFF
                        ev_out = True
                    else:
                        pass # error?
                else: # error?
                    pass

            if ev_out:
                if prev_stat != self.STAT_ON and self.stat == self.STAT_ON:
                    self.on_start = ts
                tm_on = ts - self.on_start
                event = {'ts': ts, 'tm_on': tm_on, 'val': self.stat}
                self.logger.debug('%.3f %s %.3f',
                                  event['ts'], self.STAT[event['val']], event['tm_on'])
                while self.eventq.full():
                    ev = self.get_event()
                    self.logger.warning('get and ignore event: %s', str(ev))
                    
                self.eventq.put(event)

    def end(self):
        self.logger.debug('')
        GPIO.remove_event_detect(self.pin)

    @classmethod
    def val2str(cls, val):
        return cls.VAL[val]


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
            self.sw.append(Switch1(p, debug=self.debug))


    def main(self):
        self.logger.debug('')

        self.sw[0].start()

        while True:
            ev = self.sw[0].get_event()
            print('%.3f %s %.3f' % (ev['ts'], Switch1.STAT[ev['val']], ev['tm_on']))


    def end(self):
        self.logger.debug('')
        for i in range(len(self.sw)):
            self.sw[i].end()
        GPIO.cleanup()


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
