from importlib import import_module
import json
import logging
import os

from rucio.client.didclient import DIDClient
from rucio.client.uploadclient import UploadClient

from rucio_extended_client.common.exceptions import DataFormatError
from rucio_extended_client.api.step import Step


class Plan:
    def __init__(self):
        self.current_step_number = 0
        self.steps = []

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
            section_name, _, _ = step
            sections.add(section_name)
        return sections

    def append_step(self, section_name, fqn, arguments={}, is_done=False):
        self.steps.append(Step(section_name, fqn, arguments, is_done))

    def clear(self):
        logging.debug("Clearing current plan")
        self.steps = []
        self.current_step_number = 0

    def describe(self):
        print()
        print("Plan Description")
        print("================")
        print()
        for idx, step in enumerate(self.steps):
            section_name, fqn, arguments, is_done = (step.section_name, step.fqn, step.arguments, step.is_done)
            if not is_done:
                print("{}: ({}) RUN function {}.{}.{} with parameters {}".format(
                    idx, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__, arguments))
            else:
                print("{}: ({}) RAN function {}.{}.{} with parameters {}".format(
                    idx, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__, arguments))
        print()

    @classmethod
    def load(cls, path):
        logging.info("Loading plan from file {}".format(path))
        with open(path, 'r') as fi:
            inputs = json.load(fi)
        plan = cls()
        function_classes_to_objects = {}        # avoid instantiating duplicate classes of same type
        for step in inputs['steps']:
            module = import_module(step['function_module_name'])
            if step['function_class_name'] not in function_classes_to_objects:
                function_classes_to_objects[step['function_class_name']] = \
                    getattr(module, step['function_class_name'])()
            function_class_instance = function_classes_to_objects[step['function_class_name']]
            fqn = getattr(function_class_instance, step['function_name'])
            plan.append_step(step['section_name'], fqn, arguments=step['arguments'], is_done=step['is_done'])
        return plan

    def run(self, section_name=None, dry_run=False):
        logging.info("Running plan")
        for step in self.steps:
            try:
                self.run_next_step(section_name, dry_run)
            except Exception as e:
                logging.critical("Encountered exception running step {}: {}".format(self.current_step_number, repr(e)))
                exit()
            step.is_done = True

    def run_next_step(self, section_name=None, dry_run=False):
        if section_name:
            for idx, step in enumerate(self.steps[self.current_step_number:]):
                if step.section == section_name:
                    self.current_step_number += idx
                    break
        current_step = self.steps[self.current_step_number]

        section_name, fqn, arguments, is_done = \
            (current_step.section_name, current_step.fqn, current_step.arguments, current_step.is_done)
        logging.debug("{}: ({}) Running function {}.{}.{} with parameters {}".format(
            self.current_step_number, section_name, fqn.__self__.__class__.__name__, fqn.__name__, fqn.__module__,
            arguments))
        if not dry_run:
            fqn(**arguments)
        if self.current_step_number == self.max_step_number:
            logging.info("Reached end of plan")
            return
        self.current_step_number+=1

    def save(self, path):
        logging.info("Saving plan to file {}".format(path))
        step_output = []
        for step in self.steps:
            section_name, fqn, arguments, is_done = (step.section_name, step.fqn, step.arguments, step.is_done)
            step_output.append({
                'section_name': section_name,
                'function_name': fqn.__name__,
                'function_class_name': fqn.__self__.__class__.__name__,
                'function_module_name': fqn.__module__,
                'arguments': arguments,
                'is_done': is_done
            })
        output = {
            'current_step_number': self.current_step_number,
            'steps': step_output
        }
        with open(path, 'w') as fi:
            json.dump(output, fi, indent=2)


class UploadPlan(Plan):
    def __init__(self):
        super().__init__()

    @classmethod
    def make_from_directory(
            cls, root_directory, root_container_name, rse, scope, lifetime, root_suffix='__root', path_delimiter='.'):
        """
            Makes a new plan with steps created according to the following rules:
            - if directory only contains files -> dataset
            - if directory contains only folders or is empty -> container
            - if directory contains files and folders, root files will first be grouped into a dataset named with a
              suffix of root_suffix, with this dataset appended to the parent container
        """
        plan = cls()
        upload_client = UploadClient()
        did_client = DIDClient()
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
                        if idx == 0:  # set lifetime for the container corresponding to the root folder of the tree
                            plan.append_step("create_collections", fqn=did_client.add_container, arguments={
                                'scope': scope,
                                'name': container_name,
                                'lifetime': lifetime
                            })
                        else:
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
                        if idx == 0:  # set lifetime for the container corresponding to the root folder of the tree
                            plan.append_step("create_collections", fqn=did_client.add_container, arguments={
                                'scope': scope,
                                'name': container_name,
                                'lifetime': lifetime
                            })
                        else:
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
        except Exception as e:
            logging.critical("Encountered exception: {}".format(repr(e)))
            logging.critical("Dumping plan to file")
            plan.save("{}_upload.dump.json".format(root_directory))

        return plan


