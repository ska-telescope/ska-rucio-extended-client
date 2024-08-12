#!/bin/bash

cd /opt/ska-rucio-extended-client
python3.6 -m pytest -s test/unittests
