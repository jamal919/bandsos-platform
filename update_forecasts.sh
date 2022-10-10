#!/bin/bash
while :
do
    echo '*********************************'
    echo '* '`date`' *'
    echo '*********************************'
    python update_forecasts.py
    echo
    sleep 10800
done
