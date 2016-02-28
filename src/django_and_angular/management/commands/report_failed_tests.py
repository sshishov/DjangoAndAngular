import re
from git import Repo

from optparse import make_option

from xml.etree import cElementTree as ElementTree

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = 'Creates JIRA issues for every failed case for specified branch'
    result_file = 'nosetests.xml'
    failure_row_re = re.compile(r'\s*File\s"(.*)",\sline\s(.*),.*')

    option_list = BaseCommand.option_list + (
        make_option(
            '-b',
            '--branches',
            action='store',
            dest='branches',
            help='Affected branches',
        ),
        make_option(
            '-t',
            '--target-branch',
            action='store',
            dest='target_branch',
            help='Target branch',
        )
    )

    @staticmethod
    def parse_test_path(path):
        path, classname = path.rsplit('.', 1)
        path = path.replace('.', '/')
        return path, classname

    def handle(self, *args, **options):
        repo = Repo()
        try:
            branches = [repo.heads[x] for x in options['branches'].split(',')]
            target = repo.heads[options['target_branch']]
        except IndexError as e:
            return 'Cannot find branch with error "{0}"'.format(e)
        if target != repo.head.ref:
            return 'Current branch "{0}" does not match provided CircleCI branch "{1}"'.format(
                repo.head.ref, target
            )
        elif target not in branches:
            return 'Skipping check for branch "{0}"'.format(repo.head.ref)

        try:
            root = ElementTree.parse(self.result_file).getroot()
            if root.attrib['errors']:
                for testcase in root:
                    for failure in testcase:
                        print('Failure for {}'. format(testcase.attrib['name']))
                        path, classname = self.parse_test_path(testcase.attrib['classname'])
                        print path, classname
                        for (file_path, line_number) in re.findall(self.failure_row_re, failure.text):
                            if path in file_path:
                                print repo.git.blame('HEAD', file_path)
            else:
                return 'No errors'
        except IOError:
            return 'File "{0}" does not exist'.format(self.result_file)
