#!/usr/bin/env python
"""
Testarium
Copyright (C) 2014 Maxim Tkachenko

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import copy
import argparse
import collections

import kernel
import experiment as experiment_module
from .utils import *
from .version import get_git_version, get_short_version

# it's used for parameter grid search
try: import numpy as np
except ImportError: pass

try: import web; web_loaded = True
except Exception as e:
    log('Error while web module import:', e)
    web_loaded = False

__author__ = 'Max Tkachenko'
__email__ = 'makseq@gmail.com'
__url__ = 'http://testarium.makseq.com'
__version__ = get_short_version()
__git_version__ = get_git_version()
__description__ = 'Research tool to perform experiments and store results in the repository.' \
                  'More: http://testarium.makseq.com'

testarium = kernel.Testarium()
experiment = experiment_module.Experiment(testarium)


def run(args):
    if args.config_path in testarium.branches:  # user specified branch only
        config_path = testarium.branches[args.config_path].config_path
        branch_name = args.config_path

    elif args.config_path:
        config_path = args.config_path  # use user config file
        branch_name = testarium.activeBranch.name

    elif not args.config_path:  # empty config
        config_path = testarium.activeBranch.config_path  # use default branch config
        branch_name = testarium.activeBranch.name

    # try to load main config
    try:
        config = json.loads(open(os.getcwd() + '/' + config_path, 'r').read(),
                            object_pairs_hook=collections.OrderedDict)
    except Exception as e:
        log('COLOR.RED', "Error: can't open config file:", config_path, '(' + str(e) + ')')
        return False

    # parser: param=value; => (param, value)
    import re
    p = re.compile(ur'([^=|^;]+)?=([^;]*(?=;|))')
    groups = re.findall(p, args.newParams)

    # apply newParams to dict c
    c = collections.OrderedDict()
    stop = False
    for g in groups:
        cmd = "c['" + g[0].replace(' ', '').replace('\t', '') + "'] = " + g[1]
        try:
            exec cmd
        except Exception as e:
            msg = str(e).replace(' (<string>, line 1)', '')
            log('COLOR.RED', msg + ':', 'COLOR.RED', '"' + cmd + '"')
            stop = True
    if stop:
        return False

    # run experiments
    experiment.set_send_mail(args.mail)
    experiment.search(config=config, comment=args.comment, new_params=c, branch_name=branch_name, dry_run=args.dry_run)
    return True


def branch(args):
    # no branch name
    if not args.name:
        log('Active branch:', testarium.activeBranch.name)
        if args.cfg_path:
            log('Config path changed from', testarium.activeBranch.config_path, 'to', args.cfg_path)
            testarium.activeBranch.config_path = args.cfg_path
            testarium.SaveActiveBranch(saveCommits=False)
        else:
            log('Config:', testarium.activeBranch.config_path)
            log('Other branches:', *['"' + name + '"' for name in testarium.branches])

    else:
        # check english letters
        def incorrect_name(name):
            for ch in name:
                if not (ch.isalpha() or ch.isdigit() or ch in ['-', '_']):
                    return True
            return False

        if incorrect_name(args.name):
            log('COLOR.RED', "Incorrect branch name, use english letters, digits or ['-', '_']")
            exit(-1)

        testarium.ChangeBranch(args.name)
        log('Active branch changed to:', testarium.activeBranch.name)
        if args.config_path:
            log('Config set to:', args.config_path)
            testarium.activeBranch.config_path = args.config_path
        else:
            log('Config:', testarium.activeBranch.config_path)
        testarium.SaveActiveBranch(saveCommits=False)


def rescore(args):
    # get commit
    commits = testarium.SelectCommits(branch_name=args.branch, name=args.name, N=args.n)
    if not commits:
        log('No commits')
        return -1

    for commit in commits:
        # filter by file info
        if args.filter:
            filter = args.filter
            cond = filter.replace("['", "[").replace("']", "]").replace("[", "['").replace("]", "']")

            error = 'ok; '
            for _id in commit.meta.GetAllIds():
                f = commit.filedb.GetFile(_id)
                m = commit.meta.meta[_id]
                try:
                    exec 'if not (' + cond + '): del commit.meta.meta[_id]' in globals(), locals()
                except Exception as exception:
                    error += str(exception) + '; '
            msg = error
            log(msg)

        # rescore commit by user score
        old = copy.deepcopy(commit)
        if experiment.user_score:
            commit.desc.update(experiment.user_score(commit))
            commit.Save()
        log(old, '==>', commit)


def cleanup(args):
    testarium.RemoveBrokenCommitsAndLoad(hard=args.hard)


def delete(args):
    if args.conditions:
        testarium.Load(loadCommits=True, silent=True)
        out_commits, error = testarium.Where(args.conditions)

        if out_commits is None:
            log('No commits in this branch')
            return
        else:
            log('Found:', len(out_commits), 'commits')
            args.print_diff = args.print_config = False
            print_commits(out_commits, args)
            if error:
                log('COLOR.YELLOW', 'Warning: There was an error:', error)

            if len(out_commits) > 0:
                log('COLOR.YELLOW', 'Do you want to delete it from disk? [Y/n]:')
                if raw_input() == 'Y':
                    for c in out_commits:
                        c.Delete()
                        log(c.dir, 'was removed')

    else:
        if not args.name: log('Commit name is not specified'); return
        commit = testarium.SelectCommits(branch_name=args.branch, name=args.name, N=1)
        if commit: testarium.DeleteCommit(commit[0])


def differ(args):
    branch_a = args.branchA if args.branchA else args.branch
    branch_b = args.branchB if args.branchB else args.branch
    name_a = args.nameA
    name_b = args.nameB

    commit_a = testarium.SelectCommits(branch_name=branch_a, name=name_a, N=1)
    commit_b = testarium.SelectCommits(branch_name=branch_b, name=name_b, N=1)
    if commit_a and commit_b:
        commit_a = commit_a[0]
        commit_b = commit_b[0]
        name_a = 'last' if not name_a else name_a
        name_b = 'last' if not name_b else name_b

        l = max(len(name_a), len(name_b))
        log(name_a + ' ' * (l - len(name_a)) + ' :: ' + str(commit_a))
        log(name_b + ' ' * (l - len(name_b)) + ' :: ' + str(commit_b))
        print_diff(commit_a, commit_b, name_a, name_b, args.config_keys)


def print_diff(a, b, a_name='A', b_name='B', use_keys=[]):
    if a is None:
        log_lines('No ' + a_name + ' to make difference')
        return

    if b is None:
        log_lines('No ' + b_name + ' to make difference')
        return

    s = a.config.StrDifference(b.config, a_name, b_name, use_keys)
    log_lines(s)


def print_commits(commits, args):
    prev_commit = None
    best = max(commits) if commits else None
    for commit in reversed(commits):
        if best == commit and len(commits) > 1:
            log('COLOR.GREEN', commit)
        else:
            log(commit)

        if args.print_config:
            log_lines(commit.config.__str__(args.config_keys))
            log_simple('')  # print config

        if args.print_diff:
            print_diff(commit, prev_commit, 'this', 'prev', args.config_keys)
            log_simple('')  # print incremental diff

        prev_commit = commit


def logs(args):
    commits = testarium.SelectCommits(branch_name=args.branch, name=args.name, N=args.n)
    if commits:
        print_commits(commits, args)


def where(args):
    testarium.Load(loadCommits=True, silent=True)
    out_commits, error = testarium.Where(args.conditions)

    if out_commits is None:
        log('No commits in this branch')
        return
    else:
        log('Found:', len(out_commits), 'commits')
        print_commits(out_commits, args)
        if error:
            log('COLOR.YELLOW', 'Warning: There was an error:', error)


def webserver(args):
    if not web_loaded: log('Web server is disabled. Try to "easy_install flask"'); exit(-101)

    w = web.WebServer(testarium, experiment, args)
    w.start(int(args.port), args.username, args.password)


def mail(args):
    save = False
    account_ok = False
    reset = False
    saveauto = False
    c = testarium.config

    if args.account:
        c['mail.address'] = args.account[0]
        c['mail.account'] = args.account[1]
        c['mail.password'] = TestariumCipherAES().encrypt(args.account[2])
        save = True
        account_ok = True

    if args.smtp:
        c['mail.smtp.server'] = args.smtp[0]
        c['mail.smtp.port'] = int(args.smtp[1])
        save = True

    # use default smtp for gmail
    elif account_ok:
        if not try_get(c, 'mail.smtp.server'):
            c['mail.smtp.server'] = 'smtp.gmail.com'
            c['mail.smtp.port'] = 587
            save = True

    if args.proxy:
        c['mail.proxy.server'] = args.proxy[0]
        c['mail.proxy.port'] = int(args.proxy[1])
        save = True

    if args.reset:
        try_del(c, 'mail.address')
        try_del(c, 'mail.account')
        try_del(c, 'mail.password')
        try_del(c, 'mail.smtp.server')
        try_del(c, 'mail.smtp.port')
        try_del(c, 'mail.proxy.server')
        try_del(c, 'mail.proxy.port')
        save = True
        reset = True

    if args.time >= 0:
        c['mail.autoreport.time'] = int(args.time)
        saveauto = True
    if try_get(c, 'mail.autoreport.time') is None:
        c['mail.autoreport.time'] = int(360)
        saveauto = True

    if save or saveauto:
        testarium.SaveTestariumOnly()

    # --- print mail params
    try:
        log('Mailto:', c['mail.address'])
        log('Account:', c['mail.account'])
        log('Password:', len(TestariumCipherAES().decrypt(c['mail.password'])) * '*')
    except:
        log('COLOR.RED', 'No email account [or error occurred]')

    try:
        log('SMTP server:', c['mail.smtp.server'] + ':' + str(c['mail.smtp.port']))
    except:
        log('COLOR.RED', 'No SMTP server [or error occurred]')

    try:
        if c['mail.proxy.server']:
            log('HTTP proxy:', c['mail.proxy.server'] + ':' + str(c['mail.proxy.port']))
        else:
            raise 'No proxy server'
    except:
        log('No proxy [or error occurred]')

    autotime = c['mail.autoreport.time']
    if autotime > 0:
        log('Autoreports: send report if experiment duration >', autotime, 'sec')
    else:
        log('No autoreports [or error occurred]')

    # --- perform test
    if args.test or (save and not reset and try_get(c, 'mail.address')):
        try:
            log('Checking your mail settings')
            mailto = try_get(c, 'mail.address')
            account = try_get(c, 'mail.account')
            passwd = TestariumCipherAES().decrypt(try_get(c, 'mail.password'))
            smtp_server = try_get(c, 'mail.smtp.server')
            smtp_port = try_get(c, 'mail.smtp.port')
            proxy_server = try_get(c, 'mail.proxy.server')
            proxy_port = try_get(c, 'mail.proxy.port')

            log('Sending email to:', mailto)
            text = 'Your mail is working!'
            send_email(mailto, account, passwd, 'Testarium: ' + testarium.name, text,
                       smtp_server, smtp_port, proxy=proxy_server, porta=proxy_port)
        except Exception as e:
            log('COLOR.RED', 'Error: sending mail failed:', str(e))


def main():
    parser = argparse.ArgumentParser(description='Testarium is a tool for logging science experiments')
    parser.add_argument('--root', default='.testarium', dest='root', help='root directory of testarium (.testarium by default)')

    subparsers = parser.add_subparsers(title='subcommands')

    parser_run = subparsers.add_parser('run', help='run experiment')
    parser_branch = subparsers.add_parser('branch', help='operate with branches')
    parser_delete = subparsers.add_parser('del', help='delete commit')
    parser_rescore = subparsers.add_parser('rescore', help='run user scoring function for commits in the branch')
    parser_cleanup = subparsers.add_parser('cleanup', help='remove broken commits')
    parser_differ = subparsers.add_parser('diff', help='show difference between the commits')
    parser_log = subparsers.add_parser('log', help='show commits history')
    parser_where = subparsers.add_parser('where', help='show commits where user conditions are satisfied')
    parser_web = subparsers.add_parser('web', help='start web server')
    parser_mail = subparsers.add_parser('mail', help='mail settings')

    parser_run.set_defaults(func=run)
    parser_branch.set_defaults(func=branch)
    parser_delete.set_defaults(func=delete)
    parser_rescore.set_defaults(func=rescore)
    parser_cleanup.set_defaults(func=cleanup)
    parser_differ.set_defaults(func=differ)
    parser_log.set_defaults(func=logs)
    parser_where.set_defaults(func=where)
    parser_web.set_defaults(func=webserver)
    parser_mail.set_defaults(func=mail)

    # run
    parser_run.add_argument('config_path', default='', nargs='?',
                            help='[config path] or [branch name] to start experiment with. '
                                 'It will be used default branch config if option is empty')
    parser_run.add_argument('-m', '-c', default='', dest='comment', help='add comment to the commit')
    parser_run.add_argument('-p', default='', dest='newParams',
                            help='parameters to be replaced in config on the fly')
    parser_run.add_argument('-d', '--dry', default=False, dest='dry_run', action='store_true',
                            help='Dry run mode: do not repository (git, hg) commit and '
                                 'remove commit from repository after run. '
                                 'Dry run will be disabled for experiment more than 10 min')
    parser_run.add_argument('--mail', default=False, dest='mail', action='store_true', help='send report to mail')

    # branch
    parser_branch.add_argument('name', default='', nargs='?',
                               help='change branch to branche "name" (or create if need)')
    parser_branch.add_argument('config_path', default='', nargs='?',
                               help='set default branch config (using when change or create branch)')
    parser_branch.add_argument('--cfg', default='', dest='cfg_path', help='set default config for current the branch')

    # delete
    parser_delete.add_argument('name', default='', nargs='?',
                               help="name of commit. Use 'best' for the best scored commit. "
                                    "head or HEAD or last or 0 for the last commit")
    parser_delete.add_argument('--branch', default='', dest='branch',
                               help='name of branch, leave it empty to use active branch')
    parser_delete.add_argument('-p', default='', nargs='?', dest='conditions',
                               help="user conditions: 'c' - config dict, 'd' - description dict. "
                                    "Where proceeds all commits from all branches")

    # diff
    parser_differ.add_argument('nameA', default='best', nargs='?',
                               help="name of commit to diff to. Use 'best' for the best scored commit. "
                                    "0 is last, -1 is first commit")
    parser_differ.add_argument('nameB', default='', nargs='?',
                               help="name of commit to diff with. Use 'best' for the best scored commit. "
                                    "0 is last, -1 is first commit")
    parser_differ.add_argument('--branch', default='', dest='branch',
                               help='name of common branch to operate, stay it empty to use active branch')
    parser_differ.add_argument('--branchA', default='', dest='branchA', help='name of branch A to operate')
    parser_differ.add_argument('--branchB', default='', dest='branchB', help='name of branch B to operate')
    parser_differ.add_argument('-k', default=[], dest='config_keys', nargs='+',
                               help='config keys to use for check difference')

    # log
    parser_log.add_argument('name', default='', nargs='?',
                            help="name of commit to display. Use 'best' for the best scored commit. "
                                 "0 is last, -1 is first commit")
    parser_log.add_argument('-i', default=False, dest='print_diff', action='store_true',
                            help='print incremental difference between the commit configs')
    parser_log.add_argument('-c', default=False, dest='print_config', action='store_true', help='print configs')
    parser_log.add_argument('-k', default=[], dest='config_keys', nargs='+', help='config keys to show')
    parser_log.add_argument('-n', default=-1, dest='n', type=int, help='number of commits to display, -1 = all')
    parser_log.add_argument('--branch', default='', dest='branch',
                            help='name of branch to be shown, leave it empty to use active branch')

    # rescore
    parser_rescore.add_argument('name', default='', nargs='?',
                            help="name of commit. Use 'best' for the best scored commit. 0 is last, -1 is first commit")
    parser_rescore.add_argument('-n', default=1, dest='n', type=int, help='number of commits to rescore, -1 = all')
    parser_rescore.add_argument('--branch', default='', dest='branch',
                            help='name of branch to be shown, leave it empty to use active branch')
    parser_rescore.add_argument('-f', default='', dest='filter',
                            help='file filter to exclude scores with metadata from scoring')

    # where
    parser_where.add_argument('conditions', default='True', nargs='+',
                              help="user conditions: 'c' - config dict, 'd' - description dict. "
                                   "Where proceeds all commits from all branches")
    parser_where.add_argument('-i', default=False, dest='print_diff', action='store_true',
                              help='print incremental difference between the commit configs')
    parser_where.add_argument('-c', default=False, dest='print_config', action='store_true', help='print configs')
    parser_where.add_argument('-k', default=[], dest='config_keys', nargs='+', help='config keys to show')

    # web
    parser_web.add_argument('-p', default=1080, dest='port', help='port')
    parser_web.add_argument('-u', default='', dest='username', help='username for web interface')
    parser_web.add_argument('-s', default='', dest='password', help='password for username')
    parser_web.add_argument('-d', default=False, dest='debug', action="store_true",
                            help='debug mode for Flask (debug & reloader)')
    parser_web.add_argument('--no-open-tab', default=False, dest='no_open_tab', action="store_true",
                            help='do not open new tab in browser at webserver start')

    # mail
    parser_mail.add_argument('--account', default=None, dest='account', nargs=3, help='"whom@gmail.com username password", \
        recommend to create special email account to send reports\
        and do not endanger password from real account, because password will be kept in testarium config')
    parser_mail.add_argument('--smtp', default=None, dest='smtp', nargs=2,
                             help='"smtp_server smtp_port", by default here is gmail smtp (TLS)')
    parser_mail.add_argument('--proxy', default=None, dest='proxy', nargs=2,
                             help='proxy (http) for sending email, eg.: "192.168.10.1 8080"')
    parser_mail.add_argument('--auto', default=-1, dest='time',
                             help='send autoreports if experiment duration is higher specified time (in seconds), '
                                  'set -1 to disable it')
    parser_mail.add_argument('--test', default=False, dest='test', action='store_true', help='send testing email')
    parser_mail.add_argument('--reset', default=False, dest='reset', action='store_true',
                             help='reset mail settings (account, password and others)')

    parser_cleanup.add_argument('--hard', default=False, dest='hard', action='store_true',
                                help='hard cleanup will remove ALL commits without desc.json or with incorrect loading.'
                                     'By default soft cleanup is in use. Use hard cleanup very carefully!')

    # run by default
    if len(sys.argv) == 1:
        args = parser.parse_args(['run'])

    # user forget run
    elif sys.argv[1] not in subparsers._name_parser_map.keys():
        sys.argv.insert(1, 'run')
        args = parser.parse_args()

    # other subparsers
    else:
        args = parser.parse_args()

    if args.root != '.testarium':
        global testarium, experiment
        old = testarium.common
        testarium = kernel.Testarium(rootdir=args.root)
        testarium.common = old
        experiment.testarium = testarium
        log('Testarium root changed:', args.root)

    try:
        args.func(args)
    except KeyboardInterrupt:
        log('COLOR.RED', 'Stopped by user')
