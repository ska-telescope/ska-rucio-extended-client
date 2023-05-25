import tempfile

from rucio_extended_client.api.plan import UploadPlanNative

class TestUploadFolder:
    '''
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
    '''
    root = tempfile.TemporaryDirectory()
    d1 = tempfile.TemporaryDirectory(dir=root.name)
    d1_d1 = tempfile.TemporaryDirectory(dir=d1.name)
    d1_d1_f1 = tempfile.NamedTemporaryFile(dir=d1_d1.name)
    d1_f1 = tempfile.NamedTemporaryFile(dir=d1.name)
    d1_f2 = tempfile.NamedTemporaryFile(dir=d1.name)
    d2 = tempfile.TemporaryDirectory(dir=root.name)
    d2_d1 = tempfile.TemporaryDirectory(dir=d2.name)
    d2_d1_f1 = tempfile.NamedTemporaryFile(dir=d2_d1.name)
    d3 = tempfile.TemporaryDirectory(dir=root.name)
    d3_f1 = tempfile.NamedTemporaryFile(dir=d3.name)
    f1 = tempfile.NamedTemporaryFile(dir=root.name)
    f2 = tempfile.NamedTemporaryFile(dir=root.name)
    d4 = tempfile.TemporaryDirectory(dir=root.name)
    d4_d1 = tempfile.TemporaryDirectory(dir=d4.name)
    d5 = tempfile.TemporaryDirectory(dir=root.name)

    plan = UploadPlanNative.make_plan_from_directory(
        root_directory=root.name,
        root_container_name='test',
        rse='test_rse',
        scope='test_scope',
        lifetime=3600,
        root_suffix='__root',
        path_delimiter='.',
        mock=True
    )

    def test_upload_folder_add_steps(self):
        """ Checking addition of steps to plan. Do this by checking the number of steps per section. """
        for section in self.plan.sections:
            if section == 'create_collections':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 11
            elif section == 'create_attachments':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 10
            elif section == 'add_metadata':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 3


