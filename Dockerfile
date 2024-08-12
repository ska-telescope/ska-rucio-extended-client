ARG BASE_SKA_RUCIO_CLIENT_IMAGE
ARG BASE_SKA_RUCIO_CLIENT_TAG

FROM $BASE_SKA_RUCIO_CLIENT_IMAGE:$BASE_SKA_RUCIO_CLIENT_TAG

USER root

COPY . /opt/ska-rucio-extended-client

RUN cd /opt/ska-rucio-extended-client && python3 -m pip install .

USER user

ENTRYPOINT ["/bin/bash"]
