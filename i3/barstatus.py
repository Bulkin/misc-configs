#!/usr/bin/env python

# Install python-mpd PySensors psutil

import datetime
import json
import psutil
import sensors
import sys
import time

from linecache import getline, checkcache
from math import floor,ceil

import mpdctl

statusbar_contents = {
    'time' : lambda: datetime.datetime.now().strftime('%a %d %b %H:%M:%S '),
}

def defmonitor(func):
    statusbar_contents[func.__name__] = func

@defmonitor
def load():
        checkcache("/proc/loadavg")
        avgs = ' '.join(getline("/proc/loadavg",1).split(' ')[:4])
        return avgs

@defmonitor
def lm_sensors():
    feature_labels = {'Tdie', 'fan2', 'Vcore', 'Icore',  # cpu
                      'fan1', 'edge', 'power1'}          # gpu
    features = {}
    for chip in sensors.iter_detected_chips():
        for feature in chip:
            if feature.label in feature_labels:
                features[feature.label] = feature.get_value()

    features['cpufreq'] = psutil.cpu_freq()[0] / 1000
    features['cpupow'] = features['Vcore'] * features['Icore']
    cpu = '{Tdie:.1f}°C {fan2:.0f}rpm {cpufreq:.1f}GHz {cpupow:02.0f}w'.format(**features)
    gpu = '{edge:.0f}°C {fan1:.0f}rpm {power1:.0f}w'.format(**features)
    return ' | '.join((cpu, gpu))

@defmonitor
def mem():
    return 'mem: {}M swap: {}M'.format(psutil.virtual_memory().used // 2**20,
                                       psutil.swap_memory().used // 2**20)

@defmonitor
def disk():
    partitions = ['/', '/home']
    free = [ psutil.disk_usage(p).free / 2**30 for p in partitions]
    return ' '.join(['{}: {:.1f}G'.format(k,v) for k,v in zip(partitions, free)])

mpd = mpdctl.MPDWrapper()

@defmonitor
def mpd_status():
    return mpd.current_song()

def encode(entry_func):
    return { 'name' : entry_func[0], 'full_text' : entry_func[1]() }

def print_once():
    entries = reversed([encode(f) for f in statusbar_contents.items()])
    print(json.dumps(list(entries)), ',', flush=True)

def main():
    print(sys.argv[0], file=sys.stderr)
    print('{ "version": 1 }')
    print('[')
    sensors.init()
    while True:
        cur_time = time.time()
        time.sleep(ceil(cur_time) - cur_time)
        print_once()

if __name__ == '__main__':
    main()
