#!/bin/bash

case `uname` in
    Darwin)
        # capstone
        brew install capstone
        ;;
    Linux)
        # capstone
        apt-get update
        apt-get install libcapstone3 libcapstone-dev -y --allow-unauthenticated
        ;;
    *)
          echo "Unsupported platform: `uname`" >&2
          exit 1
          ;;
esac
