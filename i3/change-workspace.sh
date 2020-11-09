#!/bin/sh

DMENU=~/bin/dmenu_wrapper
WS=`i3-msg -t get_workspaces | jq '.[].name' | $DMENU -p workspace`
if [ "$1" = "" ]; then
    i3-msg workspace "$WS"
else
    i3-msg move container to workspace $WS
fi
