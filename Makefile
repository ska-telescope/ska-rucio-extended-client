.ONESHELL:

BASE_RUCIO_CLIENT_TAG:=`cat BASE_RUCIO_CLIENT_TAG`

image:
	@docker build . -f Dockerfile --build-arg BASE_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/ska-rucio-client \
	--build-arg BASE_RUCIO_CLIENT_TAG=$(BASE_RUCIO_CLIENT_TAG) --tag rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)

image-devel:
	@docker build . -f Dockerfile.dev --build-arg BASE_RUCIO_CLIENT_IMAGE=registry.gitlab.com/ska-telescope/src/ska-rucio-client \
	--build-arg BASE_RUCIO_CLIENT_TAG=$(BASE_RUCIO_CLIENT_TAG) --tag rucio-extended-client:$(BASE_RUCIO_CLIENT_TAG)-devel