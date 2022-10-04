BASE_RUCIO_CLIENT_TAG:=`cat BASE_RUCIO_CLIENT_TAG`

image:
	docker build . -f Dockerfile --build-arg BASE_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/ska-rucio-client --build-arg BASE_RUCIO_CLIENT_TAG=$(BASE_RUCIO_CLIENT_TAG) --tag rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)

image-devel:
	docker build . -f Dockerfile.dev --build-arg BASE_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/ska-rucio-client \
	--build-arg BASE_RUCIO_CLIENT_TAG=$(BASE_RUCIO_CLIENT_TAG) --tag rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)-devel

image-test:
	docker build . -f Dockerfile.dev --build-arg BASE_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/ska-rucio-client \
	--build-arg BASE_RUCIO_CLIENT_TAG=$(BASE_RUCIO_CLIENT_TAG) --tag rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)-test

run-tests: image-test
	docker run --rm -t rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)-test /opt/rucio-extended-client/test/run_unittests.sh