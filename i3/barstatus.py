#!/usr/bin/env python

# Install python-mpd PySensors psutil

import datetime
import json
import psutil
import sensors
import sys
import threading
import time

from math import floor,ceil
from pathlib import Path
from subprocess import check_output

import mpdctl

statusbar_contents = {
    'time' : lambda: datetime.datetime.now().strftime('%a %d %b %H:%M:%S '),
}

slow_vals = {}
slow_funcs = []

def slow_thread_worker():
    while True:
        for f in slow_funcs:
            f()
        time.sleep(60)

def defmonitor(func=None, optional=False, slow=False):
    if func is None:
        return lambda f: defmonitor(f, optional, slow)
    name = func.__name__
    def wrapper(f):
        def checked_exec():
            try:
                if slow:
                    res = slow_vals[name]
                else:
                    res = f()
            except:
                if optional:
                    res = ''
                else:
                    res = f'{name}: ERR'
            return res
        return checked_exec

    def slow_wrapper(f):
        def checked_exec():
            try:
                res = f()
            except:
                if optional:
                    res = ''
                else:
                    res = f'{name}: ERR'
            slow_vals[name] = res
        return checked_exec

    statusbar_contents[name] = wrapper(func)
    if slow: slow_funcs.append(slow_wrapper(func))
    return func

@defmonitor
def load():
    vals = psutil.getloadavg()
    return ' '.join(['{:>5.2f}'] * len(vals)).format(*vals)

@defmonitor
def lm_sensors():
    from statistics import mean
    feature_labels = {'Tdie', 'fan2', 'Vcore', 'Icore',  # cpu
                      'SVI2_P_Core', 'SVI2_P_SoC',       # zenpower
                      'fan1', 'edge', 'power1', 'PPT' }  # gpu
    features = {}
    for chip in sensors.iter_detected_chips():
        for feature in chip:
            if (feature.label in feature_labels and
                not features.get(feature.label, 0)):
                features[feature.label] = feature.get_value()

    cpu_freqs = [ f[0] for f in psutil.cpu_freq(True) ]
    features['cpufreq_avg'] = mean(cpu_freqs) / 1000
    features['cpufreq_max'] = max(cpu_freqs) / 1000

    if 'Vcore' in features and 'Icore' in features:
        features['cpupow'] = features['Vcore'] * features['Icore']
    elif 'SVI2_P_Core' in features and 'SVI2_P_SoC' in features:
        features['cpupow'] = features['SVI2_P_Core'] + features['SVI2_P_SoC']
    else:
        features['cpupow'] = 0
    cpu = '{Tdie:.1f}°C {fan2:>4.0f}rpm {cpufreq_max:.2f}GHz {cpufreq_avg:.2f}GHz {cpupow:03.0f}w'.format(**features)
    gpu = '{edge:.0f}°C {fan1:.0f}rpm {PPT:>2.0f}w'.format(**features)
    return ' | '.join((cpu, gpu))

@defmonitor(optional=True, slow=False)
def controller_bat():
    path = Path('/sys/class/power_supply/')
    prefix = sorted(path.glob('ps-controller-battery-*'))[0]
    bat = int((prefix / 'capacity').read_text())
    return f'CBAT: {bat}%'

@defmonitor(optional=False, slow=True)
def mouse_bat():
    # TODO*: write to proper path (power_supply) in driver
    path = Path('/sys/module/razermouse/drivers/hid:razermouse')
    prefix = sorted(path.glob("*:*:*.*"))[0]
    bat = int((prefix / 'charge_level').read_text()) * 100 // 255
    charging = int((prefix / 'charge_status').read_text())
    # path = Path('/sys/class/power_supply/razermouse_battery_0')
    # bat = int((path / 'capacity').read_text())
    # charging = not (path / 'status').read_text().startswith('Discharging')
    warn = (charging and bat > 90) or (not charging and bat < 30)
    return {
        'full_text': f'MBAT: {bat}%',
        'color': '#bb55000' if warn else None,
    }

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
        # playerctl sometimes reports floats for some reason
        l = int(metadata['mpris:length'].split('.')[0]) // 1000000
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
    res = { 'name' : entry_func[0] }
    if type(entry_func[1]) is str:
        res['full_text'] = entry_func[1]
    else:
        res.update(entry_func[1])
    return res

def print_once():
    values = ((n, f()) for n, f in  statusbar_contents.items())
    entries = reversed([encode(f) for f in values if f[1]])
    print(json.dumps(list(entries)), ',', flush=True)

def stdin_worker():
    while txt := sys.stdin.read():
        ev = json.loads(txt)

def main():
    slow_thread = threading.Thread(target=slow_thread_worker)
    slow_thread.start()
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
