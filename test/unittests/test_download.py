from pytest_unordered import unordered

from rucio_extended_client.api.plan import DownloadPlanNative

class TestDownloadFolder:
    graph = {
        'hierarchy_tests:test_upload_1.d1': {'hierarchy_tests:test_upload_1.d1.d1_d1',
                                             'hierarchy_tests:test_upload_1.d1__root'},
        'hierarchy_tests:test_upload_1.d1.d1_d1': {'hierarchy_tests:test_upload_1.d1.d1_d1.d1_d1_f1'},
        'hierarchy_tests:test_upload_1.d1__root': {'hierarchy_tests:test_upload_1.d1.d1_f2',
                                                   'hierarchy_tests:test_upload_1.d1.d1_f1'},
        'hierarchy_tests:test_upload_1.d2': {'hierarchy_tests:test_upload_1.d2.d2_d1'},
        'hierarchy_tests:test_upload_1.d2.d2_d1': {'hierarchy_tests:test_upload_1.d2.d2_d1.d2_d1_f1'},
        'hierarchy_tests:test_upload_1': {'hierarchy_tests:test_upload_1.d4', 'hierarchy_tests:test_upload_1.d3',
                                          'hierarchy_tests:test_upload_1.d2', 'hierarchy_tests:test_upload_1__root',
                                          'hierarchy_tests:test_upload_1.d1', 'hierarchy_tests:test_upload_1.d5'},
        'hierarchy_tests:test_upload_1.d3': {'hierarchy_tests:test_upload_1.d3.d3_f1'},
        'hierarchy_tests:test_upload_1__root': {'hierarchy_tests:test_upload_1.f1', 'hierarchy_tests:test_upload_1.f2'},
        'hierarchy_tests:test_upload_1.d4': {'hierarchy_tests:test_upload_1.d4.d4_d1'},
        'hierarchy_tests:test_upload_1.d4.d4_d1': set(), 'hierarchy_tests:test_upload_1.d5': set(),
        'hierarchy_tests:test_upload_1.d1.d1_d1.d1_d1_f1': set(), 'hierarchy_tests:test_upload_1.d1.d1_f1': set(),
        'hierarchy_tests:test_upload_1.d1.d1_f2': set(), 'hierarchy_tests:test_upload_1.d2.d2_d1.d2_d1_f1': set(),
        'hierarchy_tests:test_upload_1.d3.d3_f1': set(), 'hierarchy_tests:test_upload_1.f1': set(),
        'hierarchy_tests:test_upload_1.f2': set()
    }

    roots = ['hierarchy_tests:test_upload_1']

    collections = [
        'hierarchy_tests:test_upload_1.d1.d1_d1',
        'hierarchy_tests:test_upload_1.d1__root',
        'hierarchy_tests:test_upload_1.d2.d2_d1',
        'hierarchy_tests:test_upload_1.d3',
        'hierarchy_tests:test_upload_1__root',
        'hierarchy_tests:test_upload_1.d1',
        'hierarchy_tests:test_upload_1.d2',
        'hierarchy_tests:test_upload_1.d4.d4_d1',
        'hierarchy_tests:test_upload_1.d4',
        'hierarchy_tests:test_upload_1.d5',
        'hierarchy_tests:test_upload_1'
    ]

    plan = DownloadPlanNative(root_suffix='__root', path_delimiter='.',)

    def test_download_folder_create_tree(self):
        """ Checking addition of steps to plan. Do this by checking the number of steps per section. """
        correct_tree = [
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d5'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d3', 'hierarchy_tests:test_upload_1.d3.d3_f1'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d4', 'hierarchy_tests:test_upload_1.d4.d4_d1'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1__root', 'hierarchy_tests:test_upload_1.f1'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1__root', 'hierarchy_tests:test_upload_1.f2'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d2', 'hierarchy_tests:test_upload_1.d2.d2_d1', 'hierarchy_tests:test_upload_1.d2.d2_d1.d2_d1_f1'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d1', 'hierarchy_tests:test_upload_1.d1__root', 'hierarchy_tests:test_upload_1.d1.d1_f1'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d1', 'hierarchy_tests:test_upload_1.d1__root', 'hierarchy_tests:test_upload_1.d1.d1_f2'],
            ['hierarchy_tests:test_upload_1', 'hierarchy_tests:test_upload_1.d1', 'hierarchy_tests:test_upload_1.d1.d1_d1', 'hierarchy_tests:test_upload_1.d1.d1_d1.d1_d1_f1']
        ]
        tree = self.plan._make_tree_from_graph(self.graph, self.roots).paths_to_leaves()
        assert correct_tree == unordered(tree)

    def test_download_folder_add_steps(self):
        """ Check addition of steps to plan. """
        tree = self.plan._make_tree_from_graph(self.graph, self.roots)
        self.plan._add_steps_from_tree(tree, self.collections, mock=True)

        for section in self.plan.sections:
            if section =='create_directories':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 9
            elif section =='download_files':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 7
            elif section =='rename_files':
                assert len([step for step in self.plan.steps if step.section_name == section]) == 7

