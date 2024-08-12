# SKA Rucio Extended Client

[[_TOC_]]

## Overview

The Rucio extended client builds upon the core functionality provided by the base Rucio client. Additional functionality 
includes:

- Hierarchical data management (uploads and downloads)

## Install

In the following sections it is assumed that the user is authenticating with the Rucio datalake via OIDC.

The recommended method is to use a docker container.

### Running natively

To run the extended client natively the user must first install the base rucio client package. This can be done via pip:

```bash
eng@ubuntu:~/SKAO$ python3 -m pip install rucio[clients]
```

Following this, they must create a [Rucio configuration file](https://gitlab.com/ska-telescope/src/ska-rucio-client/-/blob/master/etc/rucio/rucio.cfg.ska.j2)
as `/opt/rucio/etc/rucio.cfg`, taking care to set the authentication parameters:

```
rucio_host = https://path/to/rucio/host
auth_host = https://path/to/auth/host
auth_type = oidc
account = <account_name>
```

The extended client package can be then be installed natively by a local pip install:

```bash
eng@ubuntu:~/SKAO$ git clone https://gitlab.com/ska-telescope/src/ska-rucio-extended-client.git && cd ska-rucio-extended-client
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ export PYTHONWARNINGS="ignore:Unverified HTTPS request" && export LANG="en_US.UTF-8"
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ python3 -m pip install .
```

### Running in Docker (build locally)

A Dockerfile is provided to build an image (Makefile target included) with the necessary packages pre-installed:

```bash
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ make image
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ docker run -it --rm -e PYTHONWARNINGS="ignore:Unverified HTTPS request" -e LANG="en_US.UTF-8" -e RUCIO_CFG_ACCOUNT=$ACCOUNT rucio-extended-client:`cat BASE_RUCIO_CLIENT_TAG`
```

### Running in Docker (pull image from remote)

A pre-built image for this package is available at the container registry [here](https://gitlab.com/ska-telescope/src/ska-rucio-extended-client/container_registry). Simply substitute in the name and tag like so:

```bash
eng@ubuntu:~$ docker run -it --rm -e PYTHONWARNINGS="ignore:Unverified HTTPS request" -e LANG="en_US.UTF-8" -e RUCIO_CFG_ACCOUNT=$ACCOUNT registry.gitlab.com/ska-telescope/src/ska-rucio-extended-client:release-1.29.0
```

### Local development (containerised via pip w/ symlinks)

For development, create a new `devel` container with the source from the host volume mounted in, e.g. for a path `/home/eng/SKAO/ska-rucio-extended-client`:

```bash
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ make image-devel
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ docker run -it --rm -e PYTHONWARNINGS="ignore:Unverified HTTPS request" -e LANG="en_US.UTF-8" -e RUCIO_CFG_ACCOUNT=$ACCOUNT -v /home/eng/SKAO/ska-rucio-extended-client:/opt/rucio-extended-client rucio-extended-client:`cat BASE_RUCIO_CLIENT_TAG`-devel
```

If you want to attach to an existing Rucio **development** environment i.e. the one instantiated with `docker-compose`, remember to attach the extended client to the corresponding docker network and copy the `rucio.cfg` from the development client container to the extended client container.

## Usage

Extended client commands are available as an alias of `rucio-extended`, e.g. 

```bash
$ rucio-extended --help
```

### Commands

#### directory

The `directory` command has the following nested subcommands:

- `rucio-extended directory upload`: upload a multi-level directory
- `rucio-extended directory download`: download a multi-level directory (previously uploaded with `rucio-extended directory upload`)

##### upload

Uploading a directory can proceed via two methods: `native` and `metadata`. This is configurable by changing `hierarchy.METHOD` in `/etc/config.ini`.

The native method uses Rucio native datatypes to represent the directory structure, but is not well supported within Rucio where bottlenecks are encountered for heavily nested directories. See (here)[https://github.com/rucio/rucio/issues/6049]. 
 
The metadata method uses file metadata to store the directory structure. This is the default.

###### Example

```bash
eng@ubuntu:~/SKAO/ska-rucio-extended-client$ tree dummy_directory
../test/1/
├── d1
│    ├── d1_d1
│    │     └── d1_d1_f1
│    ├── d1_f1
│          └── d1_f2
├── d2
│    └── d2_d1
│          └── d2_d1_f1
├── d3
│    └── d3_f1
├── d4
│    └── d4_d1
├── d5
├── f1
└── f2
```

```bash
[user@f5945aba3d52 rucio-extended-client]$ rucio-extended directory upload --lifetime=76200 --rse STFC_STORM --scope hierarchy_tests -d dummy_directory -n test_upload

Plan Description
================

0: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload', 'lifetime': 76200}
1: (create_collections) RUN function DIDClient.add_dataset.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload__root', 'lifetime': 76200}
2: (create_attachments) RUN function DIDClient.add_datasets_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload__root'}]}]}
3: (upload_files) RUN function UploadClient.upload.rucio.client.uploadclient with parameters {'items': [{'path': 'dummy_directory/f2', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.f2', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload__root', 'register_after_upload': True}, {'path': '../test/1/f1', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.f1', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload__root', 'register_after_upload': True}]}
4: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d4', 'lifetime': 76200}
5: (create_attachments) RUN function DIDClient.add_containers_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d4'}]}]}
6: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d4.d4_d1', 'lifetime': 76200}
7: (create_attachments) RUN function DIDClient.add_containers_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d4', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d4.d4_d1'}]}]}
8: (create_collections) RUN function DIDClient.add_dataset.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d3', 'lifetime': 76200}
9: (create_attachments) RUN function DIDClient.add_datasets_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d3'}]}]}
10: (upload_files) RUN function UploadClient.upload.rucio.client.uploadclient with parameters {'items': [{'path': 'dummy_directory/d3/d3_f1', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.d3.d3_f1', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload.d3', 'register_after_upload': True}]}
11: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d1', 'lifetime': 76200}
12: (create_collections) RUN function DIDClient.add_dataset.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d1__root', 'lifetime': 76200}
13: (create_attachments) RUN function DIDClient.add_datasets_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d1', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d1__root'}]}]}
14: (create_attachments) RUN function DIDClient.add_containers_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d1'}]}]}
15: (upload_files) RUN function UploadClient.upload.rucio.client.uploadclient with parameters {'items': [{'path': 'dummy_directory/d1/d1_f2', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.d1.d1_f2', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload.d1__root', 'register_after_upload': True}, {'path': '../test/1/d1/d1_f1', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.d1.d1_f1', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload.d1__root', 'register_after_upload': True}]}
16: (create_collections) RUN function DIDClient.add_dataset.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d1.d1_d1', 'lifetime': 76200}
17: (create_attachments) RUN function DIDClient.add_datasets_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d1', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d1.d1_d1'}]}]}
18: (upload_files) RUN function UploadClient.upload.rucio.client.uploadclient with parameters {'items': [{'path': 'dummy_directory/d1/d1_d1/d1_d1_f1', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.d1.d1_d1.d1_d1_f1', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload.d1.d1_d1', 'register_after_upload': True}]}
19: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d5', 'lifetime': 76200}
20: (create_attachments) RUN function DIDClient.add_containers_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d5'}]}]}
21: (create_collections) RUN function DIDClient.add_container.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d2', 'lifetime': 76200}
22: (create_attachments) RUN function DIDClient.add_containers_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d2'}]}]}
23: (create_collections) RUN function DIDClient.add_dataset.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload.d2.d2_d1', 'lifetime': 76200}
24: (create_attachments) RUN function DIDClient.add_datasets_to_containers.rucio.client.didclient with parameters {'attachments': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d2', 'dids': [{'scope': 'hierarchy_tests', 'name': 'test_upload.d2.d2_d1'}]}]}
25: (upload_files) RUN function UploadClient.upload.rucio.client.uploadclient with parameters {'items': [{'path': 'dummy_directory/d2/d2_d1/d2_d1_f1', 'rse': 'STFC_STORM', 'did_scope': 'hierarchy_tests', 'did_name': 'test_upload.d2.d2_d1.d2_d1_f1', 'dataset_scope': 'hierarchy_tests', 'dataset_name': 'test_upload.d2.d2_d1', 'register_after_upload': True}]}
26: (add_metadata) RUN function DIDClient.set_metadata.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload', 'key': 'dir_checksum', 'value': 'd699da7005d41868c6e43f9190f243f0'}
27: (add_metadata) RUN function DIDClient.set_metadata.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload', 'key': 'root_suffix', 'value': '__root'}
28: (add_metadata) RUN function DIDClient.set_metadata.rucio.client.didclient with parameters {'scope': 'hierarchy_tests', 'name': 'test_upload', 'key': 'path_delimiter', 'value': '.'}

2022-09-30 16:08:12,855 [root]       plan  INFO 629	Running plan
2022-09-30 16:08:13,600 [root] uploadclient  INFO 629	Preparing upload for file f2
2022-09-30 16:08:13,901 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:14,434 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/9c/6f/test_upload.f2.rucio.upload
2022-09-30 16:08:14,633 [root] uploadclient  INFO 629	Successfully uploaded file f2
2022-09-30 16:08:15,020 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:15,098 [root] uploadclient  INFO 629	Preparing upload for file f1
2022-09-30 16:08:15,352 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:15,843 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/0d/4e/test_upload.f1.rucio.upload
2022-09-30 16:08:16,043 [root] uploadclient  INFO 629	Successfully uploaded file f1
2022-09-30 16:08:16,373 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:16,864 [root] uploadclient  INFO 629	Preparing upload for file d3_f1
2022-09-30 16:08:17,149 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:17,672 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/8d/03/test_upload.d3.d3_f1.rucio.upload
2022-09-30 16:08:17,908 [root] uploadclient  INFO 629	Successfully uploaded file d3_f1
2022-09-30 16:08:18,281 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:18,662 [root] uploadclient  INFO 629	Preparing upload for file d1_f2
2022-09-30 16:08:18,929 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:19,471 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/81/4c/test_upload.d1.d1_f2.rucio.upload
2022-09-30 16:08:19,701 [root] uploadclient  INFO 629	Successfully uploaded file d1_f2
2022-09-30 16:08:20,065 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:20,135 [root] uploadclient  INFO 629	Preparing upload for file d1_f1
2022-09-30 16:08:20,418 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:20,935 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/e4/0c/test_upload.d1.d1_f1.rucio.upload
2022-09-30 16:08:21,155 [root] uploadclient  INFO 629	Successfully uploaded file d1_f1
2022-09-30 16:08:21,448 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:21,683 [root] uploadclient  INFO 629	Preparing upload for file d1_d1_f1
2022-09-30 16:08:21,943 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:22,474 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/fe/a2/test_upload.d1.d1_d1.d1_d1_f1.rucio.upload
2022-09-30 16:08:22,702 [root] uploadclient  INFO 629	Successfully uploaded file d1_d1_f1
2022-09-30 16:08:23,048 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:23,530 [root] uploadclient  INFO 629	Preparing upload for file d2_d1_f1
2022-09-30 16:08:23,810 [root] uploadclient  INFO 629	Trying upload with https to STFC_STORM
2022-09-30 16:08:24,290 [root] uploadclient  INFO 629	Successful upload of temporary file. https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/1f/08/test_upload.d2.d2_d1.d2_d1_f1.rucio.upload
2022-09-30 16:08:24,500 [root] uploadclient  INFO 629	Successfully uploaded file d2_d1_f1
2022-09-30 16:08:24,843 [root] uploadclient  INFO 629	Successfully added replica in Rucio catalogue at STFC_STORM
2022-09-30 16:08:25,065 [root]       plan  INFO 629	Reached end of plan
```

###### Known issues and workarounds

If a bulk file upload step fails with the exception `NotAllFilesUploaded` it is necessary to run the dumped plan again until the exception changes to `NoFilesUploaded`. After this, increment the `current_step_number` by 1 to continue.

##### download

Downloading a directory can proceed via two methods: `native` and `metadata`. This is configurable by changing `hierarchy.METHOD` in `/etc/config.ini`.

The native method uses Rucio native datatypes to represent the directory structure, but is not well supported within Rucio where bottlenecks are encountered for heavily nested directories. See (here)[https://github.com/rucio/rucio/issues/6049]. 
 
The metadata method uses file metadata to store the directory structure. This is the default.

###### Example

```bash
[user@f5945aba3d52 rucio-extended-client]$ rucio-extended directory download --name test_upload --scope hierarchy_tests
2022-09-30 16:09:05,310 [root]       plan  INFO 636	root_suffix found in metadata (__root)
2022-09-30 16:09:05,310 [root]       plan  INFO 636	path_delimiter found in metadata (.)

Tree
====

hierarchy_tests:test_upload
├── hierarchy_tests:test_upload.d1
│   ├── hierarchy_tests:test_upload.d1.d1_d1
│   │   └── hierarchy_tests:test_upload.d1.d1_d1.d1_d1_f1
│   └── hierarchy_tests:test_upload.d1__root
│       ├── hierarchy_tests:test_upload.d1.d1_f1
│       └── hierarchy_tests:test_upload.d1.d1_f2
├── hierarchy_tests:test_upload.d2
│   └── hierarchy_tests:test_upload.d2.d2_d1
│       └── hierarchy_tests:test_upload.d2.d2_d1.d2_d1_f1
├── hierarchy_tests:test_upload.d3
│   └── hierarchy_tests:test_upload.d3.d3_f1
├── hierarchy_tests:test_upload.d4
│   └── hierarchy_tests:test_upload.d4.d4_d1
├── hierarchy_tests:test_upload.d5
└── hierarchy_tests:test_upload__root
    ├── hierarchy_tests:test_upload.f1
    └── hierarchy_tests:test_upload.f2


Plan Description
================

0: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
1: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
2: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.d2.d2_d1.d2_d1_f1', 'base_dir': 'test_upload/d2/d2_d1', 'no_subdir': True}]}
3: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/d2/d2_d1/test_upload.d2.d2_d1.d2_d1_f1', 'dst': 'test_upload/d2/d2_d1/d2_d1_f1'}
4: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
5: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.d1.d1_d1.d1_d1_f1', 'base_dir': 'test_upload/d1/d1_d1', 'no_subdir': True}]}
6: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/d1/d1_d1/test_upload.d1.d1_d1.d1_d1_f1', 'dst': 'test_upload/d1/d1_d1/d1_d1_f1'}
7: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
8: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.d1.d1_f1', 'base_dir': 'test_upload/d1', 'no_subdir': True}]}
9: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/d1/test_upload.d1.d1_f1', 'dst': 'test_upload/d1/d1_f1'}
10: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
11: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.d1.d1_f2', 'base_dir': 'test_upload/d1', 'no_subdir': True}]}
12: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/d1/test_upload.d1.d1_f2', 'dst': 'test_upload/d1/d1_f2'}
13: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
14: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.d3.d3_f1', 'base_dir': 'test_upload/d3', 'no_subdir': True}]}
15: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/d3/test_upload.d3.d3_f1', 'dst': 'test_upload/d3/d3_f1'}
16: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
17: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
18: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.f1', 'base_dir': 'test_upload', 'no_subdir': True}]}
19: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/test_upload.f1', 'dst': 'test_upload/f1'}
20: (create_directories) RUN function PosixPath.mkdir.pathlib with parameters {'parents': True, 'exist_ok': True}
21: (download_files) RUN function DownloadClient.download_dids.rucio.client.downloadclient with parameters {'items': [{'did': 'hierarchy_tests:test_upload.f2', 'base_dir': 'test_upload', 'no_subdir': True}]}
22: (rename_files) RUN function module.rename.posix with parameters {'src': 'test_upload/test_upload.f2', 'dst': 'test_upload/f2'}

2022-09-30 16:09:06,430 [root]       plan  INFO 636	Running plan
2022-09-30 16:09:06,431 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:06,735 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:06,735 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:06,735 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.d2.d2_d1.d2_d1_f1
2022-09-30 16:09:06,934 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.d2.d2_d1.d2_d1_f1 
2022-09-30 16:09:06,966 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/1f/08/test_upload.d2.d2_d1.d2_d1_f1
2022-09-30 16:09:07,261 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.d2.d2_d1.d2_d1_f1 successfully downloaded. 9.000 B in 0.16 seconds = 0.0 MBps
2022-09-30 16:09:07,261 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:07,468 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:07,468 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:07,469 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.d1.d1_d1.d1_d1_f1
2022-09-30 16:09:07,469 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.d1.d1_d1.d1_d1_f1 
2022-09-30 16:09:07,470 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/fe/a2/test_upload.d1.d1_d1.d1_d1_f1
2022-09-30 16:09:07,757 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.d1.d1_d1.d1_d1_f1 successfully downloaded. 9.000 B in 0.16 seconds = 0.0 MBps
2022-09-30 16:09:07,757 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:07,991 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:07,992 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:07,992 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.d1.d1_f1
2022-09-30 16:09:07,992 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.d1.d1_f1 
2022-09-30 16:09:07,993 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/e4/0c/test_upload.d1.d1_f1
2022-09-30 16:09:08,266 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.d1.d1_f1 successfully downloaded. 6.000 B in 0.15 seconds = 0.0 MBps
2022-09-30 16:09:08,266 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:08,463 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:08,463 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:08,463 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.d1.d1_f2
2022-09-30 16:09:08,463 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.d1.d1_f2 
2022-09-30 16:09:08,464 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/81/4c/test_upload.d1.d1_f2
2022-09-30 16:09:08,739 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.d1.d1_f2 successfully downloaded. 6.000 B in 0.15 seconds = 0.0 MBps
2022-09-30 16:09:08,740 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:08,945 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:08,945 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:08,945 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.d3.d3_f1
2022-09-30 16:09:08,945 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.d3.d3_f1 
2022-09-30 16:09:08,946 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/8d/03/test_upload.d3.d3_f1
2022-09-30 16:09:09,252 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.d3.d3_f1 successfully downloaded. 6.000 B in 0.15 seconds = 0.0 MBps
2022-09-30 16:09:09,252 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:09,461 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:09,461 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:09,461 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.f1
2022-09-30 16:09:09,462 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.f1 
2022-09-30 16:09:09,462 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/0d/4e/test_upload.f1
2022-09-30 16:09:09,784 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.f1 successfully downloaded. 3.000 B in 0.16 seconds = 0.0 MBps
2022-09-30 16:09:09,785 [root] downloadclient  INFO 636	Processing 1 item(s) for input
2022-09-30 16:09:10,088 [root] downloadclient  INFO 636	No preferred protocol impl in rucio.cfg: No section: 'download'
2022-09-30 16:09:10,088 [root] downloadclient  INFO 636	Using main thread to download 1 file(s)
2022-09-30 16:09:10,088 [root] downloadclient  INFO 636	Preparing download of hierarchy_tests:test_upload.f2
2022-09-30 16:09:10,088 [root] downloadclient  INFO 636	Trying to download with https and timeout of 360s from STFC_STORM: hierarchy_tests:test_upload.f2 
2022-09-30 16:09:10,089 [root] downloadclient  INFO 636	Using PFN: https://srcdev.skatelescope.org:443/storm/sa/test_rse/dev/deterministic/hierarchy_tests/9c/6f/test_upload.f2
2022-09-30 16:09:10,373 [root] downloadclient  INFO 636	File hierarchy_tests:test_upload.f2 successfully downloaded. 3.000 B in 0.15 seconds = 0.0 MBps
2022-09-30 16:09:10,373 [root]       plan  INFO 636	Reached end of plan
2022-09-30 16:09:10,517 [root] rucio-download-directory  INFO 636	dir_checksum found in metadata, verifying checksum
2022-09-30 16:09:10,519 [root] rucio-download-directory  INFO 636	Checksum verification passed
```
