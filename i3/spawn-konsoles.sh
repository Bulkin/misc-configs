#!/bin/sh

i3-msg "append_layout ~/.config/i3/konsole-layout.json"
for i in `seq 4`; do
    konsole &
done
