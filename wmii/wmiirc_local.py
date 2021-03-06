import os
from subprocess import check_output
from linecache import getline, checkcache

import wmiirc
from wmiirc import *

from mpdctl import MPDWrapper

mpd_controller = MPDWrapper()

background = '#333333'
floatbackground='#333333'

#wmii['font'] = '-xos4-terminus-medium-*-normal-*-16-*-*-*-*-*-*-*'
#wmii['font'] = 'xft:Terminus-12'
wmii['font'] = 'xft:xos4 Terminus-12'
wmii['normcolors'] = '#888888', '#222222', '#333333'
wmii['focuscolors'] = '#ffffff', '#285577', '#4c7899'
wmii['grabmod'] = keys.defs['mod']
wmii['border'] = 2

wmii.colrules = (
	('gimp', '15+70+15'),
	('9', '60+40'),
	('5', '80+20'),
        ('3', '70+30'),
	('2', '65+35'),
	('.*','50+50'),
)

wmii.tagrules = (
        ('krunner', '1+2+3+4+5+6+7+8+9'),
	('Plasma', '0'),
	('Konsole', '1'),
	('sakura', '1'),
	('gimp',   '~+gimp'),
	('opera', '2'),
	('Firefox', '2'),
	('emacs', '3'),
	('Pidgin', '5'),
	('Evolution', 'm'),
        ('kmail', 'm'),
	('Ktorrent', '6'),
	('pavucontrol', '9'),
	('ario', '9'),
	('qmpdclient', '9'),
	('MPlayer|VLC|Ark', '~'),
        ('MainWindow', '~')
)

def get_free_space(path):
	stats = os.statvfs(path)
	free_space = stats.f_bsize*stats.f_bavail/float(1024**3)
	return path + ': ' + '{:.1f}'.format(free_space) + 'G'

mem_cmd = ("free -mt | awk '/Mem/{mem=$3}/Swap/{swap=$3}END" +
           "{printf \"mem: %sM swap: %sM\", mem, swap}'")
cpu_cmd = ('sensors 2>/dev/null | awk \'{sub("+","")}/Tdie/{sys=$2} ' +
           '/fan2/{fan=$2}END{printf "%s %srpm",sys,fan}\'')
gpu_cmd = ('sensors 2>/dev/null | awk \'' +
           '{sub("+","")}' +
           '/fan1/{fan=$2}' +
           '/edge/{temp=$2}' +
           '/power1/{pow=$2}' +
           'END{printf "%s %srpm %03dw", temp, fan, pow}\'')


@defmonitor
def a_mpd(self):
        return mpd_controller.current_song()

@defmonitor
def c_mem(self):
        try:
                return check_output(mem_cmd, shell=True)
        except Exception as e:
                print(e)
                return 'ERR mem'
        
@defmonitor
def d_sensors(self):
        cpu_temps = check_output(cpu_cmd, shell=True)
        with open('/proc/cpuinfo') as f:
                freq_lines = (x for x in f.readlines() if 'MHz' in x)
                freqs = sorted(float(x.split()[3]) for x in freq_lines)

	return wmii.cache['normcolors'], '{} {}mhz'.format(cpu_temps, int(freqs[0]))

@defmonitor
def f_radeon(self):
        gpu_temps = check_output(gpu_cmd, shell=True)
        return wmii.cache['normcolors'], gpu_temps

@defmonitor
def afree(self):
	free_str = get_free_space('/') + ' ' + get_free_space('/home')
	return wmii.cache['normcolors'], free_str

@defmonitor
def time(self):
    return wmii.cache['normcolors'], datetime.datetime.now().strftime('%a %d %b %H:%M:%S')

@defmonitor
def load(self):
        checkcache("/proc/loadavg")
        avgs = ' '.join(getline("/proc/loadavg",1).split(' ')[:4])
        return wmii.cache['normcolors'], avgs

def toggle_all_tags():
        pass

keys.bind('main', (
	"MPD shortucts",
	('%(mod)s-F1', "Toggle playback",
	 lambda k: call('mpc', 'toggle', background=True)),
	('%(mod)s-F2', "Mute headphones",
	 lambda k: call('/home/bulkin/bin/pulse_mute', background=True)),
	('%(mod)s-p', "run",
	 lambda k: call('/home/bulkin/bin/menu_wrapper', background=True)),
	('%(mod)s-F3', "Increase volume",
	 lambda k: call('mpc', 'volume', '+5', background=True)),
	('%(mod)s-F4', "Decrease volume",
	 lambda k: call('mpc', 'volume', '-5',  background=True)),
	('%(mod)s-F5', "Next song",
	 lambda k: call('mpc', 'next', background=True)),
	('%(mod)s-F6', "Previous song",
	 lambda k: call('mpc', 'prev', background=True)),
	"Views",
	('%(mod)s-grave', "Move to view 0",
	 lambda k: tags.select(str(0))),
	"Misc",
	('%(mod)s-F8', "toggle cd tray",
	 lambda k: call('eject', '-T', '/dev/sr0', background=True)),
	('Print', "printscreen",
	 lambda k: call('spectacle', background=True)),
	('%(mod)s-Esc', "ksysguard",
	 lambda k: call('ksysguard', background=True)),
        ('%(mod)s-Mod1-h', "move to left screen",
         lambda k: call('swscreen', '0', background=True)),
        ('%(mod)s-Mod1-l', "move to right screen",
         lambda k: call('swscreen', '1', background=True))
))

