#!/usr/bin/env python

# Install python-mpd PySensors psutil

import datetime
import json
import psutil
import sensors
import sys
import time

from math import floor,ceil
from subprocess import check_output

import mpdctl

statusbar_contents = {
    'time' : lambda: datetime.datetime.now().strftime('%a %d %b %H:%M:%S '),
}

def defmonitor(func):
    name = func.__name__
    def wrapper(f):
        def checked_exec():
            try:
                return f()
            except:
                return f'{name}: ERR'
        return checked_exec
    statusbar_contents[name] = wrapper(func)
    return func

def defmonitor_opt(func):
    def wrapper():
        try:
            return func()
        except:
            return ''
    return defmonitor(wrapper)

@defmonitor
def load():
    vals = psutil.getloadavg()
    return ' '.join(['{:>5.2f}'] * len(vals)).format(*vals)

@defmonitor
def lm_sensors():
    from statistics import mean
    feature_labels = {'Tdie', 'fan2', 'Vcore', 'Icore',  # cpu
                      'SVI2_P_Core', 'SVI2_P_SoC',       # zenpower
                      'fan1', 'edge', 'power1'}          # gpu
    features = {}
    for chip in sensors.iter_detected_chips():
        for feature in chip:
            if (feature.label in feature_labels and
                not features.get(feature.label, 0)):
                features[feature.label] = feature.get_value()

    cpu_freqs = [ f[0] for f in psutil.cpu_freq(True) ]
    features['cpufreq_avg'] = mean(cpu_freqs)
    features['cpufreq_max'] = max(cpu_freqs)

    if 'Vcore' in features and 'Icore' in features:
        features['cpupow'] = features['Vcore'] * features['Icore']
    elif 'SVI2_P_Core' in features and 'SVI2_P_SoC' in features:
        features['cpupow'] = features['SVI2_P_Core'] + features['SVI2_P_SoC']
    else:
        features['cpupow'] = 0
    cpu = '{Tdie:.1f}°C {fan2:>4.0f}rpm {cpufreq_max:.2f}GHz {cpufreq_avg:.2f}GHz {cpupow:03.0f}w'.format(**features)
    gpu = '{edge:.0f}°C {fan1:.0f}rpm {power1:.0f}w'.format(**features)
    return ' | '.join((cpu, gpu))

@defmonitor_opt
def controller_bat():
    path = '/sys/class/power_supply/sony_controller_battery_70:20:84:5d:1b:0e/capacity'
    with open(path) as f:
        return 'CBAT: {}%'.format(int(f.read()))

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

#@defmonitor
def mpd_status():
    return mpd.current_song()

def playerctl(cmd):
    return check_output(['playerctl',
                         '-i', 'firefox,chromium', # plasma-integration instead
                         cmd ],
                        text=True)

@defmonitor
def mpris2_playerctl():
    metadata = playerctl('metadata').split('\n')
    metadata = { e[1]: ' '.join(e[2:]) for entry in metadata
                 if (e := entry.split()) }
    vol = int(float(playerctl('volume')) * 100)
    res = ['']
    if 'xesam:artist' in metadata:
        res[-1] += metadata['xesam:artist'] + ' - '
    if 'xesam:title' in metadata:
        res[-1] += metadata['xesam:title']
    if 'mpris:length' in metadata:
        l = int(metadata['mpris:length']) // 1000000
        duration = f'{l//60}:{l%60:02}'
        pos = int(float(playerctl('position')))
        elapsed = f'{pos//60}:{pos%60:02}'
        res.append(f'{elapsed}/{duration}')
    else:
        res.append(playerctl('status')[:-1])

    vol = int(float(playerctl('volume')) * 100)
    res.append(f'{vol}%')

    return ' | '.join(res)

@defmonitor
def status_delay():
    t = time.time()
    return 'delay: {:.3f}s'.format(t - floor(t))

def encode(entry_func):
    return { 'name' : entry_func[0], 'full_text' : entry_func[1] }

def print_once():
    values = ((n, f()) for n, f in  statusbar_contents.items())
    entries = reversed([encode(f) for f in values if f[1]])
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
