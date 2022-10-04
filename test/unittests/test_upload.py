import os

from rucio_extended_client.api.plan import UploadPlan

class TestUploadFolder:
    plan = UploadPlan.make_plan_from_directory(
        root_directory=os.path.join('test', 'data', 'dummy_directory'),
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
        self.plan.describe()

