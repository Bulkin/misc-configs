#!/bin/sh

DMENU=~/bin/dmenu_wrapper
WS=`i3-msg -t get_workspaces | jq '.[].name' | $DMENU -p workspace`
i3-msg workspace "$WS"
