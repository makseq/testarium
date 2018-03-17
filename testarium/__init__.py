#!/usr/bin/env python
'''
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
'''

import kernel, experiment as experiment_module
from utils import *
import sys, argparse, json, collections, copy, shutil

try: import numpy as np
except: pass

try: import web; webOk = True
except: webOk = False

version = '0.1'
testarium = kernel.Testarium()
experiment = experiment_module.Experiment(testarium)

def run(args):
    if args.config_path:
        config_path = args.config_path  # use user config
    else:
        config_path = testarium.activeBranch.config_path  # use default branch config

    # try to load main config
    config = collections.OrderedDict()
    try:
        config = json.loads(open(os.getcwd() + '/' + config_path, 'r').read(),
                            object_pairs_hook=collections.OrderedDict)
    except Exception, e:
        log('COLOR.RED', "Error: can't open config file:", config_path, '(' + str(e) + ')')
        return False

    # parser: c[param]=value; => (param, value)
    import re
    p = re.compile(ur'(c\[[\'|"]?([^\]|\'|"]+)[\'|"]?\]=([^;]*(?=;|)))')
    groups = re.findall(p, args.newParams)

    # apply newParams to dict c
    c = collections.OrderedDict()
    stop = False
    for g in groups:
        cmd = "c['" + g[1] + "'] = " + g[2]
        try:
            exec cmd
        except Exception, e:
            msg = str(e).replace(' (<string>, line 1)', '')
            log('COLOR.RED', msg + ':', 'COLOR.RED', '"' + cmd + '"')
            stop = True
    if stop: return False

    experiment.SetSendMail(args.mail)
    experiment.Search(config=config, comment=args.comment, newParams=c, useTry=True, runAndRemove=args.remove_after_run)
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
    testarium.RemoveBrokenCommitsAndLoad()


def delete(args):
    if args.conditions:
        testarium.Load(loadCommits=True, silent=True)
        out_commits, error = testarium.Where(args.conditions)

        if out_commits is None:
            log('No commits in this branch')
            returnur
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
                        shutil.rmtree(c.dir, True)
                        log(c.dir, 'was removed')

    else:
        if not args.name: log('Commit name is not specified'); return
        commit = testarium.SelectCommits(branch_name=args.branch, name=args.name, N=1)
        if commit: testarium.DeleteCommit(commit[0])


def differ(args):
    branchA = args.branchA if args.branchA else args.branch
    branchB = args.branchB if args.branchB else args.branch
    nameA = args.nameA
    nameB = args.nameB

    commitA = testarium.SelectCommits(branch_name=branchA, name=nameA, N=1)
    commitB = testarium.SelectCommits(branch_name=branchB, name=nameB, N=1)
    if commitA and commitB:
        commitA = commitA[0]
        commitB = commitB[0]
        nameA = 'last' if not nameA else nameA
        nameB = 'last' if not nameB else nameB

        l = max(len(nameA), len(nameB))
        log(nameA + ' ' * (l - len(nameA)) + ' :: ' + str(commitA))
        log(nameB + ' ' * (l - len(nameB)) + ' :: ' + str(commitB))
        print_diff(commitA, commitB, nameA, nameB, args.config_keys)


def print_diff(a, b, aName='A', bName='B', useKeys=[]):
    if a is None: log_lines('No ' + aName + ' to make difference'); return
    if b is None: log_lines('No ' + bName + ' to make difference'); return

    s = a.config.StrDifference(b.config, aName, bName, useKeys)
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
    if commits: print_commits(commits, args)


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
    if not webOk: log('Web server is disabled. Try to "easy_install flask"'); exit(-101)

    w = web.WebServer(testarium, experiment, args)
    w.Start(int(args.port), args.username, args.password)


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
        except Exception, e:
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
                            help='config path to use in the commit; using default branch config if option is empty')
    parser_run.add_argument('-m', '-c', default='', dest='comment', help='add comment to the commit')
    parser_run.add_argument('-p', default='', dest='newParams',
                            help='json dictionary, used instead of parameters in current config')
    parser_run.add_argument('-rm', default=False, dest='remove_after_run', action='store_true',
                            help='remove commit from repository after run')
    parser_run.add_argument('--mail', default=False, dest='mail', action='store_true', help='send report to mail')

    # branch
    parser_branch.add_argument('name', default='', nargs='?',
                               help='change branch to branche "name" (or create if need)')
    parser_branch.add_argument('config_path', default='', nargs='?',
                               help='set default branch config (using when change or create branch)')
    parser_branch.add_argument('--cfg', default='', dest='cfg_path', help='set default config for current the branch')

    # delete
    parser_delete.add_argument('name', default='', nargs='?',
                               help="name of commit. Use 'best' for the best scored commit. 0 is last, -1 is first commit")
    parser_delete.add_argument('--branch', default='', dest='branch',
                               help='name of branch, leave it empty to use active branch')
    parser_delete.add_argument('-p', default='', nargs='?', dest='conditions',
                              help="user conditions: 'c' - config dict, 'd' - description dict. "
                                   "Where proceeds all commits from all branches")


    # diff
    parser_differ.add_argument('nameA', default='best', nargs='?',
                               help="name of commit to diff to. Use 'best' for the best scored commit. 0 is last, -1 is first commit")
    parser_differ.add_argument('nameB', default='', nargs='?',
                               help="name of commit to diff with. Use 'best' for the best scored commit. 0 is last, -1 is first commit")
    parser_differ.add_argument('--branch', default='', dest='branch',
                               help='name of common branch to operate, stay it empty to use active branch')
    parser_differ.add_argument('--branchA', default='', dest='branchA', help='name of branch A to operate')
    parser_differ.add_argument('--branchB', default='', dest='branchB', help='name of branch B to operate')
    parser_differ.add_argument('-k', default=[], dest='config_keys', nargs='+',
                               help='config keys to use for check difference')

    # log
    parser_log.add_argument('name', default='', nargs='?',
                            help="name of commit to display. Use 'best' for the best scored commit. 0 is last, -1 is first commit")
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

    if len(sys.argv) == 1:
        args = parser.parse_args(['run'])
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
