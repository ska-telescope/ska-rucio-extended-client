#!/bin/bash

cd /opt/rucio-extended-client
python3.6 -m pytest -s test/unittests
