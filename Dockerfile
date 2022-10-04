ARG BASE_RUCIO_CLIENT_IMAGE
ARG BASE_RUCIO_CLIENT_TAG

FROM $BASE_RUCIO_CLIENT_IMAGE:$BASE_RUCIO_CLIENT_TAG

USER root

COPY . /opt/rucio-extended-client

RUN cd /opt/rucio-extended-client && python3 -m pip install .

USER user

ENTRYPOINT ["/bin/bash"]
