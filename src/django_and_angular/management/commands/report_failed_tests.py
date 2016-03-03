import re
from optparse import make_option
from xml.etree import cElementTree as ElementTree

from django.core.management.base import BaseCommand
from git import Repo
from jira import JIRA
from jira.exceptions import JIRAError


FAILURE_ROW_RE = re.compile(r'\s*File\s"(.*)",\sline\s(.*),.*')


class Command(BaseCommand):

    help = 'Creates JIRA issues for every failed case for specified branch'

    option_list = BaseCommand.option_list + (
        make_option(
            '--branches',
            action='store',
            dest='branches',
            help='Affected branches',
        ),
        make_option(
            '--target-branch',
            action='store',
            dest='target_branch',
            help='Target branch',
        ),
        make_option(
            '--issue-type',
            action='store',
            dest='issue_type',
            default='Bug',
            help='Issue type',
        ),
        make_option(
            '--project-key',
            action='store',
            dest='project_key',
            default='EZHOME',
            help='Project key',
        ),
        make_option(
            '--jira-server',
            action='store',
            dest='jira_server',
            help='JIRA server',
        ),
        make_option(
            '--jira-username',
            action='store',
            dest='jira_username',
            help='Username for JIRA account',
        ),
        make_option(
            '--jira-password',
            action='store',
            dest='jira_password',
            help='Password for JIRA account',
        ),
        make_option(
            '--test-results',
            action='store',
            dest='test_results',
            default='nosetests.xml',
            help='Location of test results',
        ),
    )

    def handle(self, *args, **options):
        self.issue_type = options['issue_type']
        self.project_key = options['project_key']
        self.jira_server = options['jira_server']
        self.jira_username = options['jira_username']
        self.jira_password = options['jira_password']
        test_results = options['test_results']

        self.repo = Repo()
        branches = []
        try:
            for branch in options['branches'].split(','):
                branches.append(self.repo.heads[branch])
        except IndexError:
            return 'Cannot find branch "{0}"'.format(branch)
        try:
            self.target_branch = self.repo.heads[options['target_branch']]
        except IndexError:
            return 'Cannot find branch "{0}"'.format(options['target_branch'])
        if self.target_branch != self.repo.head.ref:
            return (
                'Current branch "{0}" does not match '
                'provided CircleCI branch "{1}"'
                .format(self.repo.head.ref, self.target_branch)
            )
        elif self.target_branch not in branches:
            return 'Skipping check for branch "{0}"'.format(self.repo.head.ref)

        try:
            root = ElementTree.parse(test_results).getroot()
            if root.attrib['errors']:
                results = []
                for testcase in root:
                    if testcase:
                        results.append(self.handle_testcase(testcase))
                return '\n'.join(results)
            else:
                return 'No errors in tests'
        except IOError:
            return 'File "{0}" does not exist'.format(test_results)

    @staticmethod
    def parse_test_path(path):
        path, classname = path.rsplit('.', 1)
        path = path.replace('.', '/')
        return path, classname

    def handle_testcase(self, testcase):
        path, classname = self.parse_test_path(
            testcase.attrib['classname']
        )
        for (file_path, line_number) in re.findall(
                FAILURE_ROW_RE, testcase[0].text
        ):
            if path in file_path:
                # Finding the line of testcase definition
                authors = {}
                commit, line = self.repo.blame(
                    '-L/def {}/'.format(testcase.attrib['name']), file_path
                )[0]
                if commit.author not in authors:
                    authors['function'] = commit.author
                # Finding the line of failure
                commit, line = self.repo.blame(
                    '-L{0},{0}'.format(line_number), file_path
                )[0]
                if commit.author not in authors:
                    authors['failure'] = commit.author
                return self.handle_jira(
                    path=path,
                    authors=authors,
                    classname=classname,
                    testcase=testcase,
                )

    def handle_jira(self, path, authors, classname, testcase):
        try:
            jira = JIRA(
                server=self.jira_server,
                basic_auth=(
                    self.jira_username,
                    self.jira_password,
                )
            )
            summary = (
                'Fail: {path}:{classname}.{testcase}, '
                'branch: {branch}'.format(
                    path=path,
                    classname=classname,
                    testcase=testcase.attrib['name'],
                    branch=self.target_branch,
                )
            )
            open_issues = jira.search_issues(
                'summary ~ "{summary}" AND '
                'resolution=unresolved'.format(
                    summary=summary
                ),
                maxResults=1
            )
            if open_issues:
                # Update priority
                issue = open_issues[0]
                new_priority = '1'
                if int(issue.fields.priority.id) > 1:
                    new_priority = str(int(issue.fields.priority.id) - 1)
                issue.update(priority={'id': new_priority})
                return (
                    'Priority of issue "{issue}" '
                    'has been set to "{priority}"'.format(
                        issue=issue, priority=jira.priority(new_priority)
                    )
                )
            else:
                # Create issue
                assignee = jira.search_users(
                    user=authors['function'].email,
                    maxResults=1
                )
                issue_dict = dict(
                    project={'key': self.project_key},
                    summary=summary,
                    issuetype={'name': self.issue_type},
                    priority={'id': jira.priorities()[-1].id},
                    description='Description here',
                )
                if assignee:
                    issue_dict['assignee'] = {'name': assignee[0].name}
                new_issue = jira.create_issue(fields=issue_dict)
                return 'New issue "{0}" has been created'.format(new_issue)
        except JIRAError as e:
            return 'JIRA ERROR: {}'.format(e.text)
