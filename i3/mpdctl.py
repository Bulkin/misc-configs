#!/usr/bin/env python

#import traceback
import functools
import sys
import time

def retry(fun, count=3):
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except Exception as e:
            print('MPDWrapper disconnected', e, file=sys.stderr)
            for i in range(count):
                try:
                    self.enabled = False
                    self.connect()
                    break
                except Exception as e:
                    print('MPDWrapper connection failed', e, file=sys.stderr)
                    time.sleep(self.client.timeout)
            if self.enabled:
                return wrapper(self, *args, **kwargs)
            else:
                return 'MPD disabled'
    return wrapper


class MPDWrapper:
    def __init__(self, host='/var/lib/mpd/socket', port=None):
        try:
            self.addr = (host, port)
            self.connect()
        except Exception as e:
            print(e, file=sys.stderr)
            #traceback.print_tb(e.__traceback__)
            self.enabled = False

    def connect(self):
        from mpd import MPDClient
        self.client = MPDClient()
        self.client.timeout = 0.7
        self.client.connect(*self.addr)
        self.enabled = True
        self.retry_count = 3

    @retry
    def current_song(self):
        if not self.enabled: return 'MPD: disabled'
        song = self.client.currentsong()
        status = self.client.status()

        if {'artist', 'title'} <= song.keys():
            song_fmt = '{} - {}'.format(song['artist'], song['title'])
        else:
            song_fmt = song['file']

        if not 'volume' in status:
            status['volume'] = 'n/a'

        if song:
            elapsed = '{}:{:02}'.format(int(float(status['elapsed'])) // 60,
                                        int(float(status['elapsed'])) % 60)
            duration = '{}:{:02}'.format(int(float(status['duration'])) // 60,
                                         int(float(status['duration'])) % 60)
            return '{} | {}/{} | {}%'.format(song_fmt,
                                             elapsed,
                                             duration,
                                             status['volume'])
        else:
            return 'Stopped {}%'.format(status['volume'])

    @staticmethod
    def test():
        mpc = MPDWrapper()
        print(mpc.client.status())
        print(mpc.client.currentsong())
        print(mpc.client.config())
        print(mpc.current_song())


if __name__ == '__main__':
    command = sys.argv[1]
    mpd = MPDWrapper()
    try:
        getattr(mpd.client, command)()
    except Exception as e:
        print('Tried command {} -- {}'.format(command, e))
