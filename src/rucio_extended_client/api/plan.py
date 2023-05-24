from importlib import import_module
import json
import logging
import os
import pathlib
import shutil
import time
import typing
import uuid

from dirhash import dirhash
from rucio.client import client
from rucio.client.didclient import DIDClient
from rucio.client.downloadclient import DownloadClient
from rucio.client.ruleclient import RuleClient
from rucio.client.uploadclient import UploadClient
from treelib.exceptions import DuplicatedNodeIdError
from treelib import Node, Tree

from rucio_extended_client.common.exceptions import DataFormatError
from rucio_extended_client.api.step import Step


class Plan:
    def __init__(self, root_suffix: str = None, path_delimiter: str = None, hierarchy_key: str = None, **kwargs):
        """
        :param root_suffix: suffix to define that the file belongs to the base directory (native method only)
        :param path_delimiter: delimiter used to separate directories and files (native method only)
        :param hierarchy_key: metadata key holding description of how did fits into hierarchy (metadata method only)
        """
        self._current_step_number = 0
        self.steps = []
        self.root_suffix = root_suffix
        self.path_delimiter = path_delimiter
        self.hierarchy_key = hierarchy_key

    @property
    def current_step_number(self):
        return self._current_step_number

    @current_step_number.setter
    def current_step_number(self, new_current_step_number):
        self._current_step_number = new_current_step_number

    @property
    def max_step_number(self):
        return self.number_of_steps-1

    @property
    def number_of_steps(self):
        return len(self.steps)

    @property
    def sections(self):
        sections = set()
        for step in self.steps:
            sections.add(step.section_name)
        return sections

    def append_step(self, section_name: str, fqn: str, arguments: typing.Dict[typing.Any, typing.Any] = {},
                    is_done: bool = False) -> None:
        """ Append a step to the plan.

        :param section_name: section name to run next step from (will skip other sections in between)
        :param fqn: the fully qualified function name (package and class)
        :param arguments: arguments to the function
        :param is_done: flag for whether step is done
        """
        self.steps.append(Step(section_name, fqn, arguments, is_done))

    def clear(self) -> None:
        """ Clear the current plan. """
        logging.debug("Clearing current plan")
        self.steps = []
        self.current_step_number = 0

    def describe(self) -> None:
        """ Describe the current plan. """
        print()
        print("Plan Description")
        print("================")
        print()
        for idx, step in enumerate(self.steps):
            section_name, fqn, arguments, is_done = (step.section_name, step.fqn, step.arguments, step.is_done)
            if not is_done:
                if hasattr(step.fqn, '__self__'): # bound method
                    print("{}: ({}) RUN bound method {}.{}.{} with parameters {}".format(
                        idx, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__, arguments))
                else:
                    print("{}: ({}) RUN function {}.{} with parameters {}".format(
                        idx, section_name, fqn.__module__, fqn.__name__, arguments))
            else:
                if hasattr(step.fqn, '__self__'):  # bound method
                    print("{}: ({}) RAN bound method {}.{}.{} with parameters {}".format(
                        idx, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__, arguments))
                else:
                    print("{}: ({}) RAN function {}.{} with parameters {}".format(
                        idx, section_name, fqn.__module__, fqn.__name__, arguments))
        print()

    @classmethod
    def load(cls, path: str) -> None:
        """ Load plan from a hard copy.

        :param path: the path to load from
        """
        logging.info("Loading plan from file {}".format(path))
        with open(path, 'r') as fi:
            inputs = json.load(fi)
        plan = cls(**inputs)
        plan.current_step_number = inputs['current_step_number']
        function_classes_to_objects = {}        # avoid instantiating duplicate classes of same type
        for step in inputs['steps']:
            module = import_module(step['function_module_name'])
            if step['function_class_name']:     # bound method
                try:
                    if step['function_class_name'] not in function_classes_to_objects:
                        function_classes_to_objects[step['function_class_name']] = \
                        getattr(module, step['function_class_name'])()
                    function_class_instance = function_classes_to_objects[step['function_class_name']]
                    fqn = getattr(function_class_instance, step['function_name'])
                except AttributeError:          # bound method with no class, just module
                    fqn = getattr(module, step['function_name'])
            else:                               # unbound method (e.g. class)
                fqn = getattr(module, step['function_name'])
            plan.append_step(step['section_name'], fqn, arguments=step['arguments'], is_done=step['is_done'])
        return plan

    def run(self, section_name: str =None, dry_run: bool = False) -> typing.List[typing.Any]:
        """ Run the entire plan.

        :param section_name: section name to run next step from (will skip other sections in between)
        :param dry_run: don't actually do anything, just print
        """
        logging.info("Running plan")
        returns = []
        while True:
            try:
                returns.append(self.run_next_step(section_name, dry_run))
                if self.current_step_number > self.max_step_number:
                    logging.info("Reached end of plan")
                    return
            except (Exception, KeyboardInterrupt) as e:
                logging.critical("Encountered exception running step {}: {}".format(self.current_step_number, repr(e)))
                self.save("plan-dump.json")
                exit()
        return returns

    def run_next_step(self, section_name: str = None, dry_run: bool = False) -> typing.Any:
        """ Run the next step.

        :param section_name: section name to run next step from (will skip other sections in between)
        :param dry_run: don't actually do anything, just print
        """
        if section_name:
            for idx, step in enumerate(self.steps[self.current_step_number:]):
                if step.section == section_name:
                    self.current_step_number += idx
                    break
        current_step = self.steps[self.current_step_number]

        section_name, fqn, arguments, is_done = \
            (current_step.section_name, current_step.fqn, current_step.arguments, current_step.is_done)
        if hasattr(fqn, '__self__'):  # bound method
            logging.debug("{}: ({}) Running function {}.{}.{} with parameters {}".format(
                self.current_step_number, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__,
                arguments))
        else:
            logging.debug("{}: ({}) Running function {}.{} with parameters {}".format(
                self.current_step_number, section_name, fqn.__module__, fqn.__name__, arguments))
        if not dry_run:
            rtn = fqn(**arguments)
        else:
            rtn = None

        self.steps[self.current_step_number].is_done = True
        self.current_step_number += 1

        return rtn

    def save(self, path: str) -> None:
        """ Save a hard copy of the plan.

        :param path: the path to save to
        """
        logging.info("Saving plan to file {}".format(path))
        step_output = []
        for step in self.steps:
            section_name, fqn, arguments, is_done = (step.section_name, step.fqn, step.arguments, step.is_done)
            if hasattr(fqn, '__self__'):  # bound method
                step_output.append({
                    'section_name': section_name,
                    'function_name': fqn.__name__,
                    'function_class_name': fqn.__self__.__class__.__name__,
                    'function_module_name': fqn.__module__,
                    'arguments': arguments,
                    'is_done': is_done
                })
            else:
                step_output.append({
                    'section_name': section_name,
                    'function_name': fqn.__name__,
                    'function_class_name': None,
                    'function_module_name': fqn.__module__,
                    'arguments': arguments,
                    'is_done': is_done
                })
        output = {
            'current_step_number': self.current_step_number,
            'path_delimiter': self.path_delimiter,
            'hierarchy_key': self.hierarchy_key,
            'root_suffix': self.root_suffix,
            'steps': step_output
        }
        with open(path, 'w') as fi:
            json.dump(output, fi, indent=2)


class DownloadPlanMetadata(Plan):
    def __init__(self, hierarchy_key: str, **kwargs):
        """
        :param hierarchy_key: metadata key referencing hierarchical data
        """
        super().__init__(hierarchy_key)

    @classmethod
    def make_plan_from_did(
            cls, root_container_scope: str, root_container_name: str, hierarchy_key: str ='hierarchy',
            metadata_plugin: str = 'json', clobber: bool = True, show_tree: bool = True) -> typing.Type[Plan]:
        """ Makes a download plan given the DID of a root container and according to the rules of the UploadPlan.

        :param root_container_scope: the scope of the root container
        :param root_container_name: the name of the root container
        :param hierarchy_key: metadata key holding description of how did fits into hierarchy
        :param metadata_plugin: the Rucio metadata plugin to use
        :param clobber: overwrite existing directory if it exists
        :param show_tree: show the hierarchical tree when constructing the plan
        :return: a populated instance of DownloadPlan
        """
        did_client = DIDClient()
        download_client =DownloadClient()

        # Get metadata of root container
        metadata = did_client.get_metadata(
            scope=root_container_scope, name=root_container_name, plugin=metadata_plugin)

        # Check for necessary hierarchy keys in metadata, and get emptydirs_container_name, files_dataset_name, files
        # and emptydirs.
        try:
            assert hierarchy_key in metadata
            logging.info("hierarchnical key ({}) found in metadata".format(hierarchy_key))
            metadata_hierarchy = metadata[hierarchy_key]
            assert 'emptydirs_container_name' in metadata_hierarchy
            logging.info("emptydirs_container_name key found in metadata".format(hierarchy_key))
            emptydirs_container_name = metadata_hierarchy['emptydirs_container_name']
            assert 'files_dataset_name' in metadata_hierarchy
            logging.info("files_dataset_name key found in metadata".format(hierarchy_key))
            files_dataset_name = metadata_hierarchy['files_dataset_name']
            assert 'files' in metadata_hierarchy
            logging.info("files key found in metadata".format(hierarchy_key))
            files = metadata_hierarchy['files']
            assert 'emptydirs' in metadata_hierarchy
            logging.info("emptydirs key found in metadata".format(hierarchy_key))
            emptydirs = metadata_hierarchy['emptydirs']
        except AssertionError:
            logging.critical("Either the hierarchical key ({}), emptydirs_container_name or files_dataset_name was not "
                            "found in root container metadata. This may not be hierarchical data.")
            exit()

        # Get DID of nested .emptydirs container and .files dataset.
        content = did_client.list_content(scope=root_container_scope, name=root_container_name)
        did_emptydirs_container = None
        did_files_dataset = None
        for item in content:
            if emptydirs_container_name in item['name'] and 'CONTAINER' in item['type']:
                did_emptydirs_container = '{}:{}'.format(item['scope'], item['name'])
            if files_dataset_name in item['name'] and 'DATASET' in item['type']:
                did_files_dataset = '{}:{}'.format(item['scope'], item['name'])

        # Assert that we have the .emptydirs container and .files dataset.
        try:
            assert did_emptydirs_container is not None
            logging.info("Found did_emptydir_container ({})".format(did_emptydirs_container))
            assert did_files_dataset is not None
            logging.info("Found did_files_dataset ({})".format(did_files_dataset))
        except AssertionError:
            logging.warning("Could not find either .emptydirs or .files DIDs attached to root container")
            exit()

        plan = cls(hierarchy_key)

        # Add clobber step if set.
        if clobber:
            plan.append_step("overwrite_existing", fqn=shutil.rmtree, arguments={
                'path': root_container_name
            })

        # The directory structure is simply the set of directory names from [files] and [emptydirs]
        #
        dirnames = set()
        for fi in files:
            dirnames.add(os.path.dirname(fi['path']))
        for emptydir in emptydirs:
            dirnames.add(emptydir['path'])

        # Create tree, if requested
        if show_tree:
            tree = Tree()

            # Add directories as nodes first.
            for dirname in sorted(dirnames):
                if not os.path.dirname(dirname).rstrip('/'):
                    tree.create_node(dirname, dirname)
                else:
                    tree.create_node(dirname, dirname, parent=os.path.dirname(dirname))

            # Then add files.
            for fi in files:
                tree.create_node(fi['path'], fi['path'], parent=os.path.dirname(dirname))

            print()
            print("Tree")
            print("====")
            print()
            tree.show()

        # Create these directories.
        for dirname in dirnames:
            plan.append_step("create_directories", fqn=pathlib.Path(dirname).mkdir, arguments={
                'parents': True,
                'exist_ok': True
            })

        # Download files and rename.
        for fi in files:
            name = fi['name']
            path = fi['path']
            plan.append_step("download_files", fqn=download_client.download_dids, arguments={
                'items': [{
                    'did': '{}:{}'.format(root_container_scope, name),
                    'base_dir': os.path.dirname(path),
                    'no_subdir': True,
                    'transfer_timeout': 3600
                }],
            })
            plan.append_step("rename_files", fqn=os.rename, arguments={
                'src': os.path.join(os.path.dirname(path), name),
                'dst': os.path.join(path)
            })

        return plan

class DownloadPlanNative(Plan):
    def __init__(self, root_suffix: str, path_delimiter: str, **kwargs):
        """
        :param root_suffix: suffix to define that the file belongs to the base directory
        :param path_delimiter: delimiter used to separate directories and files
        """
        super().__init__(root_suffix, path_delimiter)

    def _add_steps_from_tree(
            self, tree: typing.Type[Tree], collections: typing.List[typing.Dict[typing.Any, typing.Any]],
            mock: bool = False) -> None:
        """ Add plan steps from a graph.

        :param tree: the tree of relationships between DIDs
        :param collections: a list of collections contained within the root container
        :param mock: only use for pytests (doesn't instantiate clients)
        """
        download_client = DownloadClient
        if not mock:
            download_client = download_client() # instantiate

        did_items = []
        for logical_path_segments in tree.paths_to_leaves():
            # remove segments w/ root_suffix and strip scope
            physical_path_segments = [
                segment.split(':')[1] for segment in logical_path_segments if self.root_suffix not in segment]

            # recover the original directory names by removing the previous segment as a substring from each segment
            # when iterating through the path list
            desired_physical_path_segments = [physical_path_segments[0]]
            for segment, segment_p1 in zip(physical_path_segments[:-1], physical_path_segments[1:]):
                desired_physical_path_segments.append(
                    segment_p1.replace('{}{}'.format(segment, self.path_delimiter), ""))

            is_dir = logical_path_segments[-1] in collections
            if is_dir:
                lfn = None
                path = os.path.join(*desired_physical_path_segments)
                filename = None
            else:
                lfn = logical_path_segments[-1]
                path = os.path.join(*desired_physical_path_segments[:-1])
                filename = desired_physical_path_segments[-1]

            # create directories
            self.append_step("create_directories", fqn=pathlib.Path(path).mkdir, arguments={
                'parents': True,
                'exist_ok': True
            })

            # download file and rename
            if lfn and filename:
                self.append_step("download_files", fqn=download_client.download_dids, arguments={
                    'items': [{
                        'did': lfn,
                        'base_dir': path,
                        'no_subdir': True,
                        'transfer_timeout': 3600
                    }]
                })
                self.append_step("rename_files", fqn=os.rename, arguments={
                    'src': os.path.join(path, lfn.split(':')[1]),
                    'dst': os.path.join(path, filename)
                })

    def _create_directed_graph(self, did_name: str, did_scope: str) \
            -> typing.Tuple[typing.Dict[str, str], typing.List[str], typing.List[typing.Dict[typing.Any, typing.Any]]]:
        """
        Create a directed graph representing the relationships between dids in a given container (did_scope:did_name).

        :param did_name: DID name
        :param did_scope: DID scope
        :return: a tuple consisting of the graph showing the relationships between dids, the roots of this graph and
        nested collections
        """
        # Create an instance of the rucio client & get a list of child containers and datasets.
        did_client = DIDClient()
        collections = did_client.list_dids(
            scope=did_scope,
            filters=[{
                'name': did_name
            }],
            did_type='collection',
            long=True,
            recursive=True)

        # Separate out collections into datasets and containers.
        datasets = []
        containers = []
        for collection in collections:
            if 'DATASET' in collection['did_type']:
                datasets.append('{}:{}'.format(collection['scope'], collection['name']))
            elif 'CONTAINER' in collection['did_type']:
                containers.append('{}:{}'.format(collection['scope'], collection['name']))

        # Create a list of the relationships between these collections.
        relationships = []
        for collection_did in datasets + containers:
            collection_scope, collection_name = collection_did.split(':')
            for parent_did in did_client.list_parent_dids(collection_scope, collection_name):
                parent_did_scope = parent_did['scope']
                parent_did_name = parent_did['name']
                relationships.append(
                    ('{}:{}'.format(parent_did_scope, parent_did_name),
                     '{}:{}'.format(collection_scope, collection_name))
                )

        # Create a list of all files in datasets and add relationships between files and datasets.
        for dataset in datasets:
            dataset_scope, dataset_name = dataset.split(':')
            for content in did_client.list_content(dataset_scope, dataset_name):
                file_scope = content['scope']
                file_name = content['name']
                relationships.append(
                    ('{}:{}'.format(dataset_scope, dataset_name),
                     '{}:{}'.format(file_scope, file_name))
                )

        # Build a directed graph with a list of all dids and children.
        graph = {name: set() for tup in relationships for name in tup}
        has_parent = {name: False for tup in relationships for name in tup}
        for parent, child in relationships:
            graph[parent].add(child)
            has_parent[child] = True

        # Get the roots of this graph i.e. nodes have no parents.
        roots = [name for name, parents in has_parent.items() if not parents]

        return (graph, roots, datasets + containers)

    def _traverse_graph(self, graph: typing.Dict[str, str], roots: typing.List[str]) -> typing.Dict[str, str]:
        """ Traverse a directed graph, creating a nested dictionary illustrating the relationships between elements.

        :param graph: graph showing the relationships between dids
        :param roots: the roots of the graph
        :return: a nested dictionary showing the hierarchy between elements of the graph
        """
        # Define a recursive function to traverse the graph.
        def traverse_graph_recursive(hierarchy, graph, names):
            for name in names:
                hierarchy[name] = traverse_graph_recursive({}, graph, graph[name])
            return hierarchy

        return traverse_graph_recursive({}, graph, roots)

    def _make_tree_from_graph(self, graph: typing.Dict[str, str], roots: typing.List[str]) -> typing.Type[Tree]:
        """ Make a tree from a graph.

        :param graph: graph showing the relationships between dids
        :param roots: the roots of the graph
        :return: an instance of Tree() formatted as per hierarchy
        """
        # Define function to recurse through the hierarchy and create nodes.
        def recurse_hierarchy(children, parent, tree):
            for did, children in children.items():
                if isinstance(children, dict):
                    if not parent:
                        tree.create_node(did, did)
                    else:
                        tree.create_node(did, did, parent=parent)
                    recurse_hierarchy(children, did, tree=tree)
            return tree

        tree = Tree()
        return recurse_hierarchy(self._traverse_graph(graph, roots), '', tree=tree)

    @classmethod
    def make_plan_from_did(
            cls, root_container_scope: str, root_container_name: str, hierarchy_key: str = 'hierarchy',
            fallback_root_suffix: str ='__root', fallback_path_delimiter: str ='.', metadata_plugin: str = 'json',
            clobber: bool = True, show_tree: bool = True) -> typing.Type[Plan]:
        """ Makes a download plan given the DID of a root container and according to the rules of the UploadPlan.

        :param root_container_scope: the scope of the root container
        :param root_container_name: the name of the root container
        :param hierarchy_key: metadata key holding description of how did fits into hierarchy
        :param fallback_root_suffix: fallback suffix to define that the file belongs to the base directory
        :param fallback_path_delimiter: fallback delimiter used to separate directories and files
        :param metadata_plugin: the Rucio metadata plugin to use
        :param clobber: overwrite existing directory if it exists
        :param show_tree: show the hierarchical tree when constructing the plan
        :return: a populated instance of DownloadPlan
        """
        did_client = DIDClient
        did_client = did_client()

        # Get metadata of root container
        metadata = did_client.get_metadata(
            scope=root_container_scope, name=root_container_name, plugin=metadata_plugin)

        # Check for necessary hierarchy keys in metadata, and get emptydirs_container_name, files_dataset_name, files
        # and emptydirs.
        try:
            assert hierarchy_key in metadata
            logging.info("hierarchnical key ({}) found in metadata".format(hierarchy_key))
            metadata_hierarchy = metadata[hierarchy_key]
        except AssertionError:
            logging.critical("The hierarchical key ({}) could not be found in root container metadata. This may not be "
                             "hierarchical data.")
            exit()

        # Check for root_suffix and path_delimiter keys, otherwise fallback to those in config
        if 'root_suffix' in metadata_hierarchy:
            logging.info("root_suffix found in metadata ({})".format(metadata_hierarchy['root_suffix']))
            root_suffix = metadata_hierarchy['root_suffix']
        else:
            logging.warning("root_suffix not in container metadata, falling back to config ({})".format(
                fallback_root_suffix))
            root_suffix = fallback_root_suffix

        if 'path_delimiter' in metadata_hierarchy:
            logging.info("path_delimiter found in metadata ({})".format(metadata_hierarchy['path_delimiter']))
            path_delimiter = metadata_hierarchy['path_delimiter']
        else:
            logging.warning("path_delimiter not in container metadata, falling back to config ({})".format(
                fallback_path_delimiter))
            path_delimiter = fallback_path_delimiter

        plan = cls(root_suffix, path_delimiter)

        # add clobber step if set
        if clobber:
            plan.append_step("overwrite_existing", fqn=shutil.rmtree, arguments={
                'path': root_container_name
            })

        try:
            graph, roots, collections = plan._create_directed_graph(root_container_name, root_container_scope)
            tree = plan._make_tree_from_graph(graph, roots)
            if show_tree:
                print()
                print("Tree")
                print("====")
                print()
                tree.show()
            plan._add_steps_from_tree(tree, collections)
        except Exception as e:
            logging.critical("Encountered exception: {}".format(repr(e)))
            exit()
        return plan


class UploadPlanMetadata(Plan):
    def __init__(self, hierarchy_key: str, **kwargs):
        """
        :param hierarchy_key: metadata key referencing hierarchical data
        """
        super().__init__(hierarchy_key)

    @classmethod
    def make_plan_from_directory(
            cls, root_directory: str, root_container_name: str, rse: str, scope: str, lifetime: int,
            hierarchy_key: str = 'hierarchy', mock: bool = False, do_checksum: bool = True) -> typing.Type[Plan]:
        """
        Makes a new plan with steps created according to the following rules:

        - the root container will have a dataset with prefix .files containing dids
        - the root container will have a collection with prefix .emptydirs containing datasets representing empty
          directories

        The root container itself is the source of the hierarchical layout where corresponding metadata is held under
        the [hierarchy_key] key. This is preferred to per-file metadata to avoid having to do multiple get_metadata()
        queries when downloading the data.

        :param root_directory: the directory to upload
        :param root_container_name: the name to use for the root container
        :param rse: the RSE to upload to
        :param scope: the scope to use for uploaded content
        :param lifetime: the lifetime of uploaded content
        :param hierarchy_key: metadata key holding description of how did fits into hierarchy
        :param mock: only use for pytests (doesn't instantiate clients)
        :param do_checksum: do directory checksum
        :return: a populated instance of UploadPlan
        """
        st = time.time()
        plan = cls(hierarchy_key)

        upload_client = UploadClient
        did_client = DIDClient
        rule_client = RuleClient
        if not mock:                         # instantiate
            upload_client = upload_client()
            did_client = did_client()
            rule_client = rule_client()
        try:
            # Create a root container to hold files dataset and empty directories container.
            logging.debug("Will create container {}".format(root_container_name))
            plan.append_step("create_root_container", fqn=did_client.add_container, arguments={
                'scope': scope,
                'name': root_container_name
            })
            files_dataset_name = "{}.files".format(root_container_name)
            logging.debug("Will create dataset {}".format(files_dataset_name))
            plan.append_step("create_files_dataset", fqn=did_client.add_dataset, arguments={
                'scope': scope,
                'name': files_dataset_name
            })
            emptydirs_container_name = "{}.emptydirs".format(root_container_name)
            logging.debug("Will create container {}".format(emptydirs_container_name))
            plan.append_step("create_emptydirs_container", fqn=did_client.add_container, arguments={
                'scope': scope,
                'name': emptydirs_container_name
            })

            # Attach these to the root container.
            plan.append_step("create_attachments", fqn=did_client.add_datasets_to_containers, arguments={
                'attachments': [
                    {
                        'scope': scope,
                        'name': root_container_name,
                        'dids': [
                            {
                                'scope': scope,
                                'name': files_dataset_name
                            }
                        ]
                    }
                ]
            })
            plan.append_step("create_attachments", fqn=did_client.add_containers_to_containers, arguments={
                'attachments': [
                    {
                        'scope': scope,
                        'name': root_container_name,
                        'dids': [
                            {
                                'scope': scope,
                                'name': emptydirs_container_name
                            }
                        ]
                    }
                ]
            })

            n_files = 0
            n_emptydir = 0
            root_container_hierarchy_files = []
            root_container_hierarchy_emptydirs = []
            for idx, (root, dirs, files) in enumerate(os.walk(root_directory, topdown=True)):
                logging.debug("Considering directory {}".format(root))
                if idx == 0 and not dirs:
                    raise DataFormatError("Parent directory is not a multi level directory")
                if files:
                    logging.debug("This directory contains files")

                    # Upload files and add to this dataset.
                    logging.debug("  Will add the following files to the {} dataset:".format(files_dataset_name))
                    items = []
                    for fi in files:
                        path = '/'.join([root_container_name] + \
                            os.path.join(root, fi).split(os.sep)[len(root_directory.split(os.sep)):])
                        name = str(uuid.uuid4())
                        logging.debug("  - {} as {}".format(os.path.join(root, fi), name))
                        items.append({
                            'path': os.path.join(root, fi),
                            'rse': rse,
                            'did_scope': scope,
                            'did_name': name,
                            'dataset_scope': scope,
                            'dataset_name': files_dataset_name,
                            'register_after_upload': True
                        })
                        root_container_hierarchy_files.append({
                            'path': path,
                            'name': name
                        })
                        n_files+=1
                    plan.append_step("upload_files", fqn=upload_client.upload, arguments={
                        'items': items
                    })
                elif not files and not dirs:
                    logging.debug("This directory is empty")

                    # Create dataset representing this empty dir.
                    path = '/'.join([root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])
                    emptydir_dataset_name = str(uuid.uuid4())
                    logging.debug("  Will create dataset representing {} as {}".format(path, emptydir_dataset_name))
                    plan.append_step("create_emptydir_dataset", fqn=did_client.add_dataset, arguments={
                        'scope': scope,
                        'name': emptydir_dataset_name
                    })

                    # Attach this to the .emptydirs container.
                    plan.append_step("create_attachments", fqn=did_client.add_datasets_to_containers, arguments={
                        'attachments': [
                            {
                                'scope': scope,
                                'name': emptydirs_container_name,
                                'dids': [
                                    {
                                        'scope': scope,
                                        'name': emptydir_dataset_name
                                    }
                                ]
                            }
                        ]
                    })

                    # Add metadata for these emptydirs
                    root_container_hierarchy_emptydirs.append({
                        'path': path,
                        'name': emptydir_dataset_name
                    })

                    n_emptydir+=1
                if idx == 0:
                    # Add a rule to root container only.
                    plan.append_step("add_root_container_rule", fqn=rule_client.add_replication_rule, arguments={
                        'dids': [{'scope': scope, 'name': root_container_name}],
                        'copies': 1,
                        'rse_expression': rse,
                        'lifetime': lifetime
                    })

            # Add metadata to root container.
            dir_checksum = None
            if do_checksum:
                dir_checksum = dirhash(root_directory, algorithm='md5', empty_dirs=True)
            plan.append_step("add_metadata", fqn=did_client.set_metadata_bulk, arguments={
                'scope': scope,
                'name': root_container_name,
                'meta': {
                    hierarchy_key: {
                        'upload_class': cls.__name__,
                        'dir_checksum': dir_checksum,
                        'n_files': n_files,
                        'n_emptydir': n_emptydir,
                        'files_dataset_name': files_dataset_name,
                        'emptydirs_container_name': emptydirs_container_name,
                        'files': root_container_hierarchy_files,
                        'emptydirs': root_container_hierarchy_emptydirs
                    }
                }
            })
        except Exception as e:
            logging.critical("Encountered exception: {}".format(repr(e)))
            exit()
        return plan

class UploadPlanNative(Plan):
    def __init__(self, root_suffix: str, path_delimiter: str, **kwargs):
        """
        :param root_suffix: suffix to define that the file belongs to the base directory
        :param path_delimiter: delimiter used to separate directories and files
        """
        super().__init__(root_suffix, path_delimiter)

    @classmethod
    def make_plan_from_directory(
            cls, root_directory: str, root_container_name: str, rse: str, scope: str, lifetime: int, hierarchy_key: str
            = 'hierarchy', root_suffix: str = '__root', path_delimiter: str = '.', mock: bool = False,
            do_checksum: bool = True) -> typing.Type[Plan]:
        """

        Makes a new plan with steps created according to the following rules:

        - if directory only contains files -> dataset
        - if directory contains only folders or is empty -> container
        - if directory contains files and folders, root files will first be grouped into a dataset named with a
          suffix of root_suffix, with this dataset appended to the parent container

        :param root_directory: the directory to upload
        :param root_container_name: the name to use for the root container
        :param rse: the RSE to upload to
        :param scope: the scope to use for uploaded content
        :param lifetime: the lifetime of uploaded content
        :param hierarchy_key: metadata key holding description of how did fits into hierarchy
        :param root_suffix: suffix to define that the file belongs to the base directory
        :param path_delimiter: delimiter used to separate directories and files
        :param mock: only use for pytests (doesn't instantiate clients)
        :param do_checksum: do directory checksum
        :return: a populated instance of UploadPlan
        """
        st = time.time()
        plan = cls(root_suffix, path_delimiter)

        upload_client = UploadClient
        did_client = DIDClient
        rule_client = RuleClient
        if not mock:                         # instantiate
            upload_client = upload_client()
            did_client = did_client()
            rule_client = rule_client()
        try:
            for idx, (root, dirs, files) in enumerate(os.walk(root_directory, topdown=True)):
                logging.debug("Considering directory {}".format(root))
                if idx == 0 and not dirs:
                    raise DataFormatError("Parent directory is not a multi level directory")
                for fi in files:
                    if root_suffix in fi:
                        raise DataFormatError("File ({}) contains root suffix ({})".format(
                            os.path.join(root, fi), root_suffix))
                parent_container_name = path_delimiter.join(
                    ([root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])[:-1])
                if files:
                    if dirs:
                        logging.debug("This directory contains files and directories")

                        # Create container for root directory.
                        container_name = path_delimiter.join(
                            [root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])
                        logging.debug("  Will create container with name {}".format(container_name))
                        plan.append_step("create_collections", fqn=did_client.add_container, arguments={
                            'scope': scope,
                            'name': container_name
                        })

                        # Create a dataset to hold the files at the root of this directory.
                        dataset_name = path_delimiter.join(
                            [root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):]) + root_suffix
                        logging.debug("  Will create dataset {}".format(dataset_name))
                        plan.append_step("create_collections", fqn=did_client.add_dataset, arguments={
                            'scope': scope,
                            'name': dataset_name
                        })

                        # Attach collections to parents.
                        logging.debug("  Will attach dataset {} to {} container".format(
                            dataset_name, container_name))
                        plan.append_step("create_attachments", fqn=did_client.add_datasets_to_containers, arguments={
                            'attachments': [
                                {
                                    'scope': scope,
                                    'name': container_name,
                                    'dids': [
                                        {
                                            'scope': scope,
                                            'name': dataset_name
                                        }
                                    ]
                                }
                            ]
                        })

                        if parent_container_name:
                            logging.debug("  Will attach container {} to {} container".format(
                                container_name, parent_container_name))
                            plan.append_step("create_attachments", fqn=did_client.add_containers_to_containers,
                                             arguments={
                                                 'attachments': [
                                                     {
                                                         'scope': scope,
                                                         'name': parent_container_name,
                                                         'dids': [
                                                             {
                                                                 'scope': scope,
                                                                 'name': container_name
                                                             }
                                                         ]
                                                     }
                                                 ]
                                             })

                        # Upload files and add to this dataset.
                        logging.debug("  Will add the following files to the {} dataset:".format(dataset_name))
                        items = []
                        for fi in files:
                            name = path_delimiter.join([root_container_name] + \
                                os.path.join(root, fi).split(os.sep)[len(root_directory.split(os.sep)):])
                            logging.debug("  - {} as {}".format(os.path.join(root, fi), name))
                            items.append({
                                'path': os.path.join(root, fi),
                                'rse': rse,
                                'did_scope': scope,
                                'did_name': name,
                                'dataset_scope': scope,
                                'dataset_name': dataset_name,
                                'register_after_upload': True
                            })
                        plan.append_step("upload_files", fqn=upload_client.upload, arguments={
                            'items': items
                        })
                    else:
                        logging.debug("This directory contains only files")

                        dataset_name = path_delimiter.join(
                            [root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])
                        logging.debug("  Will create dataset {}".format(dataset_name))
                        plan.append_step("create_collections", fqn=did_client.add_dataset, arguments={
                            'scope': scope,
                            'name': dataset_name
                        })

                        # Attach collections to parents.
                        if parent_container_name:
                            logging.debug("  Will attach dataset {} to {} container".format(
                                dataset_name, parent_container_name))
                            plan.append_step("create_attachments", fqn=did_client.add_datasets_to_containers,
                                             arguments={
                                                 'attachments': [
                                                     {
                                                         'scope': scope,
                                                         'name': parent_container_name,
                                                         'dids': [
                                                             {
                                                                 'scope': scope,
                                                                 'name': dataset_name
                                                             }
                                                         ]
                                                     }
                                                 ]
                                             })

                        logging.debug(
                            "  Will add the following files to the {} dataset:".format(dataset_name))
                        items = []
                        for fi in files:
                            name = path_delimiter.join([root_container_name] + \
                                os.path.join(root, fi).split(os.sep)[len(root_directory.split(os.sep)):])
                            logging.debug("  - {} as {}".format(os.path.join(root, fi), name))
                            items.append({
                                'path': os.path.join(root, fi),
                                'rse': rse,
                                'did_scope': scope,
                                'did_name': name,
                                'dataset_scope': scope,
                                'dataset_name': dataset_name,
                                'register_after_upload': True
                            })
                        plan.append_step("upload_files", fqn=upload_client.upload, arguments={
                            'items': items
                        })
                else:
                    if dirs:
                        logging.debug("This directory contains only directories")

                        # Create container for root directory.
                        container_name = path_delimiter.join(
                            [root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])
                        logging.debug("  Will create container with name {}".format(container_name))
                        plan.append_step("create_collections", fqn=did_client.add_container, arguments={
                            'scope': scope,
                            'name': container_name
                        })

                        # Attach collections to parents.
                        if parent_container_name:
                            logging.debug("  Will attach container {} to {} container".format(
                                container_name, parent_container_name))
                            plan.append_step("create_attachments", fqn=did_client.add_containers_to_containers,
                                             arguments={
                                                 'attachments': [
                                                     {
                                                         'scope': scope,
                                                         'name': parent_container_name,
                                                         'dids': [
                                                             {
                                                                 'scope': scope,
                                                                 'name': container_name
                                                             }
                                                         ]
                                                     }
                                                 ]
                                             })
                    else:
                        logging.debug("This directory is empty")

                        # Create container for root directory.
                        container_name = path_delimiter.join(
                            [root_container_name] + root.split(os.sep)[len(root_directory.split(os.sep)):])
                        logging.debug("  Will create container with name {}".format(container_name))
                        plan.append_step("create_collections", fqn=did_client.add_container, arguments={
                            'scope': scope,
                            'name': container_name
                        })

                        # Attach collections to parents.
                        if parent_container_name:
                            logging.debug("  Will attach container {} to {} container".format(
                                container_name, parent_container_name))
                            plan.append_step("create_attachments", fqn=did_client.add_containers_to_containers,
                                             arguments={
                                                 'attachments': [
                                                     {
                                                         'scope': scope,
                                                         'name': parent_container_name,
                                                         'dids': [
                                                             {
                                                                 'scope': scope,
                                                                 'name': container_name
                                                             }
                                                         ]
                                                     }
                                                 ]
                                             })

                if idx == 0:
                    # Add a rule to root container only.
                    plan.append_step("add_root_container_rule", fqn=rule_client.add_replication_rule, arguments={
                        'dids': [{'scope': scope, 'name': root_container_name}],
                        'copies': 1,
                        'rse_expression': rse,
                        'lifetime': lifetime
                    })

            # Add metadata to root container.
            dir_checksum = None
            if do_checksum:
                dir_checksum = dirhash(root_directory, algorithm='md5', empty_dirs=True)
            plan.append_step("add_metadata", fqn=did_client.set_metadata_bulk, arguments={
                'scope': scope,
                'name': root_container_name,
                'meta': {
                    hierarchy_key: {
                        'upload_class': cls.__name__,
                        'dir_checksum': dir_checksum,
                        'root_suffix': root_suffix,
                        'path_delimiter': path_delimiter
                    }
                }
            })
        except Exception as e:
            logging.critical("Encountered exception: {}".format(repr(e)))
            exit()
        return plan


