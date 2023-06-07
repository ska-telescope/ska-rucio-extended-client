#!/usr/bin/env python

import argparse
import configparser
import logging
import os

from dirhash import dirhash
from rucio.client.didclient import DIDClient

from rucio_extended_client.common.exceptions import ArgumentError, ConfigError, UnknownMethod
from rucio_extended_client.api.plan import UploadPlanMetadata, UploadPlanNative, DownloadPlanMetadata, \
    DownloadPlanNative


class Directory:
    """ Class for adding Directory based operations. """
    def __init__(self):
        pass

    def add_to_argparse(self, subparsers):
        """ Add arguments to directory based operations to argparse"""
        directory_parser = subparsers.add_parser("directory")
        self.directory_parser_subparsers = directory_parser.add_subparsers(help="directory based operations",
                                                                           dest='subcommand')
        self._add_download_arguments()
        self._add_upload_arguments()

    def _add_download_arguments(self):
        download_parser = self.directory_parser_subparsers.add_parser("download")
        download_parser.add_argument('-c', help="path to configuration file", default="/usr/local/etc/config.ini",
                                        type=str)
        download_parser.add_argument('-o', help="overwrite existing directory if it exists", action='store_true')
        download_parser.add_argument('-p', help="path to download plan", type=str)
        download_parser.add_argument('-v', help="verbose?", action='store_true')
        download_parser.add_argument('--dry-run', help="dry run?", action='store_true')
        download_parser.add_argument('--name', help="name", type=str)
        download_parser.add_argument('--scope', help="scope", type=str)
        download_parser.add_argument('--skip-checksum', help="skip checksum?", action='store_true')

    def _add_upload_arguments(self):
        upload_parser = self.directory_parser_subparsers.add_parser("upload")
        upload_parser.add_argument('-c', help="path to configuration file", default="/usr/local/etc/config.ini",
                                      type=str)
        upload_parser.add_argument('-d', help="directory to upload", type=str)
        upload_parser.add_argument('-n', help="root container name of upload", type=str)
        upload_parser.add_argument('-p', help="path to upload plan", type=str)
        upload_parser.add_argument('-v', help="verbose?", action='store_true')
        upload_parser.add_argument('--dry-run', help="dry run?", action='store_true')
        upload_parser.add_argument('--lifetime', help="rule lifetime for root container", type=int, default=3600)
        upload_parser.add_argument('--rse', help="RSE to upload to", type=str)
        upload_parser.add_argument('--scope', help="scope", type=str)
        upload_parser.add_argument('--skip-checksum', help="skip checksum?", action='store_true')

    def download(self, args):
        """ Download directory. """
        if args.v:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s [%(name)s] %(module)10s %(levelname)5s %(process)d\t%(message)s")
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(name)s] %(module)10s %(levelname)5s %(process)d\t%(message)s")

        if not args.c or not os.path.isfile(args.c):
            raise ArgumentError("Configuration file has not been set or does not exist")

        if args.p:
            if not os.path.isfile(args.p):
                raise ArgumentError("Plan given but path does not exist")
        else:
            if not args.scope:
                raise ArgumentError("scope has not been set")
            if not args.name:
                raise ArgumentError("name has not been set")

        config = configparser.ConfigParser()
        config.read(args.c)
        try:
            metadata_plugin = config['general']['METADATA_PLUGIN']
            hierarchy_key = config['hierarchy']['METADATA_KEY']
            method = config['hierarchy']['METHOD'].lower()
            common_kwargs = {
                'hierarchy_key': hierarchy_key
            }
            if method == 'native':
                download_plan_cls = DownloadPlanNative
                download_plan_kwargs = {
                    'fallback_root_suffix': config['hierarchy.native']['ROOT_SUFFIX'],
                    'fallback_path_delimiter': config['hierarchy.native']['PATH_DELIMITER'],
                    **common_kwargs
                }
            elif method == 'metadata':
                download_plan_cls = DownloadPlanMetadata
                download_plan_kwargs = {
                    **common_kwargs
                }
            else:
                raise UnknownMethod("method {} is not understood".format(method))
        except KeyError as e:
            raise ConfigError("Key {} does not exist".format(e))

        # either load or make plan
        if args.p:
            plan = download_plan_cls.load(args.p)
        else:
            plan = download_plan_cls.make_plan_from_did(
                root_container_scope=args.scope, root_container_name=args.name, metadata_plugin=metadata_plugin,
                clobber=args.o, show_tree=True, **download_plan_kwargs)

        plan.describe()
        plan.run(dry_run=args.dry_run)

        # Verify directory checksum if requested.
        if not args.skip_checksum and not args.dry_run:
            # Get metadata of root container
            did_client = DIDClient()
            metadata = did_client.get_metadata(scope=args.scope, name=args.name, plugin=metadata_plugin)

            # Check for dir_checksum key
            if 'dir_checksum' in metadata[hierarchy_key]:
                logging.info("dir_checksum key found in metadata")
                dir_checksum = metadata[hierarchy_key]['dir_checksum']
                if dir_checksum is None:
                    logging.warning("dir_checksum is Nonetype, skipping checksum verification")
                else:
                    logging.info("verifying checksum")
                    this_dir_checksum = dirhash(args.name, algorithm='md5', empty_dirs=True)
                    try:
                        assert dir_checksum == this_dir_checksum
                    except AssertionError as e:
                        logging.critical("Checksum verification failed")
                        raise ChecksumVerificationError("Directory checksum does not match: {}!={}".format(
                            dir_checksum, this_dir_checksum))
                    logging.info("Checksum verification passed")
            else:
                logging.warning("dir_checksum not in container metadata, skipping checksum verification")

    def upload(self, args):
        """ Upload directory. """
        if args.v:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s [%(name)s] %(module)10s %(levelname)5s %(process)d\t%(message)s")
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(name)s] %(module)10s %(levelname)5s %(process)d\t%(message)s")

        if not args.c or not os.path.isfile(args.c):
            raise ArgumentError("Configuration file has not been set or does not exist")

        if args.p:
            if not os.path.isfile(args.p):
                raise ArgumentError("Plan given but path does not exist")
        elif args.d:
            if not args.lifetime:
                raise ArgumentError("lifetime has not been set")
            if not args.rse:
                raise ArgumentError("rse has not been set")
            if not args.scope:
                raise ArgumentError("scope has not been set")
            if not os.path.isdir(args.d):
                raise ArgumentError("Directory given but path does not exist")
            if not args.n:
                logging.info("No upload name set, using directory name {}".format(args.d))
                args.n = args.d
        else:
            raise ArgumentError("Neither a directory or plan has been specified")
            exit()

        config = configparser.ConfigParser()
        config.read(args.c)
        try:
            method = config['hierarchy']['METHOD'].lower()
            hierarchy_key = config['hierarchy']['METADATA_KEY']
            common_kwargs = {
                'hierarchy_key': hierarchy_key
            }
            if method == 'native':
                upload_plan_cls = UploadPlanNative
                upload_plan_kwargs = {
                    'root_suffix': config['hierarchy.native']['ROOT_SUFFIX'],
                    'path_delimiter': config['hierarchy.native']['PATH_DELIMITER'],
                    **common_kwargs
                }
            elif method == 'metadata':
                upload_plan_cls = UploadPlanMetadata
                upload_plan_kwargs = {
                    **common_kwargs
                }
            else:
                raise UnknownMethod("method {} is not understood".format(method))
        except KeyError as e:
            raise ConfigError("Key {} does not exist".format(e))

        # either load or make plan
        if args.d:
            plan = upload_plan_cls.make_plan_from_directory(args.d.rstrip('/'), args.n, rse=args.rse, scope=args.scope,
                                                            lifetime=args.lifetime, do_checksum=not args.skip_checksum,
                                                            **upload_plan_kwargs)
        elif args.p:
            plan = upload_plan_cls.load(args.p)

        plan.describe()
        plan.run(dry_run=args.dry_run)
