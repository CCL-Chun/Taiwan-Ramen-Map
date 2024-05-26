#!/bin/bash

URL="https://ramentaiwan.info/health"
RESPONSE=$(curl --write-out "%{http_code}\n" --silent --output /dev/null "$URL")

if [ "$RESPONSE" -ne 200 ]; then
    aws sns publish --topic-arn arn:aws:sns:ap-northeast-1:590183938508:Ramen-Map-healthCheck --message "RamenMap Flask app is down!"
fi

#if [ "$RESPONSE" -eq 200 ]; then
#    echo "Fine"
#fi
