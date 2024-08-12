BASE_SKA_RUCIO_CLIENT_TAG:=`cat BASE_SKA_RUCIO_CLIENT_TAG`

all: image image-devel image-test

image:
	docker build . -f Dockerfile --build-arg BASE_SKA_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/src-dm/ska-src-dm-da-rucio-client --build-arg BASE_SKA_RUCIO_CLIENT_TAG=$(BASE_SKA_RUCIO_CLIENT_TAG) --tag ska-rucio-extended-client:$(BASE_SKA_RUCIO_CLIENT_TAG)

image-devel:
	docker build . -f Dockerfile.dev --build-arg BASE_SKA_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/src-dm/ska-src-dm-da-rucio-client \
	--build-arg BASE_SKA_RUCIO_CLIENT_TAG=$(BASE_SKA_RUCIO_CLIENT_TAG) --tag ska-rucio-extended-client:$(BASE_SKA_RUCIO_CLIENT_TAG)-devel

image-test:
	docker build . -f Dockerfile.dev --build-arg BASE_SKA_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/src-dm/ska-src-dm-da-rucio-client \
	--build-arg BASE_SKA_RUCIO_CLIENT_TAG=$(BASE_SKA_RUCIO_CLIENT_TAG) --tag ska-rucio-extended-client:$(BASE_SKA_RUCIO_CLIENT_TAG)-test

run-tests: image-test
	docker run --rm -t ska-rucio-extended-client:$(BASE_SKA_RUCIO_CLIENT_TAG)-test /opt/ska-rucio-extended-client/test/run_unittests.sh