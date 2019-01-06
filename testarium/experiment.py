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
import gc
import json
import time
import threading
import collections
import itertools as it
from utils import *
import kernel
try:
    import setproctitle
    setproctitle_enabled = True
except ImportError:
    setproctitle_enabled = False
    raise ImportError('setproctitle is not installed: pip install setproctitle')


class Experiment:
    def __init__(self, testarium):
        self.testarium = testarium
        self.user_run = None
        self.user_score = None
        self.sendmail = False

    # decorator: user run function
    # run function must take 1 param with path to json config
    # and return error code (or 0)
    def set_run(self, func):
        self.user_run = func

    # decorator: user score function must take an commit directory
    # and return a dict (eg. {'score':1.0, 'some':0.5})
    # (it will be kept in Commit.Description).
    # 'score' key is strongly required
    def set_score(self, func):
        self.user_score = func

    def _send_mail(self, text):
        if not self.sendmail: return False

        c = self.testarium.config
        try:
            mailto = try_get(c, 'mail.address')
            if not mailto:
                log('COLOR.RED', 'No email settings are present, see "' + sys.argv[0] + ' mail -h"')
                return False
            account = try_get(c, 'mail.account')
            passwd = TestariumCipherAES().decrypt(try_get(c, 'mail.password'))
            smtp_server = try_get(c, 'mail.smtp.server')
            smtp_port = try_get(c, 'mail.smtp.port')
            proxy_server = try_get(c, 'mail.proxy.server')
            proxy_port = try_get(c, 'mail.proxy.port')

            log('Sending email to:', mailto)
            send_email(mailto, account, passwd, 'Testarium: ' + self.testarium.name, text,
                       smtp_server, smtp_port, proxy=proxy_server, porta=proxy_port)
        except Exception, e:
            log('COLOR.RED', 'Error: sending mail failed:', str(e))
            return False

        return True

    def set_send_mail(self, send):
        self.sendmail = send

    # --- Advanced experiment run with params search
    def search(self, config, comment, new_params, branch_name, dry_run=False):

        # check newParams for variants number
        max_variants = 1
        for key in new_params:
            if hasattr(new_params[key], '__iter__'):  # object is iterable
                variants = len(new_params[key])
                if max_variants < variants:
                    max_variants = variants

        # start simple run(), if here is 1 variant
        if max_variants == 1:
            # convert to dict without values like lists
            begin_time = time.time()
            new_params = {key: (new_params[key][0] if hasattr(new_params[key], '__iter__')
                                else new_params[key]) for key in new_params}
            result = self.run(config, comment, new_params, branch_name, dry_run)
            duration = time.time() - begin_time

            # check experiment duration and make decision about mail sending
            autotime = try_get(self.testarium.config, 'mail.autoreport.time', -1)
            self.sendmail = True if duration > autotime >= 0 else self.sendmail
            self._send_mail(makehtml(commits2html('Experiment report', [result])))  # send report mail to user if need

        # perform search
        else:
            # convert to dict with all the list values
            new_params = {key: (new_params[key] if hasattr(new_params[key], '__iter__') else [new_params[key]]) for key
                          in
                          new_params}

            # combine params
            var_names = sorted(new_params)
            combinations = [collections.OrderedDict(zip(var_names, prod)) for prod in
                            it.product(*(new_params[varName] for varName in var_names))]

            # init vars
            results = []
            count = 0
            fault = 0
            begin_time = time.time()
            best_commit = kernel.Commit()  # not inited commit with the worst score

            # main loop
            for comb in combinations:
                log_simple('\n\n----------------------------------------------')
                log('Starting experiment: ', count + 1, '/', len(combinations))

                result = self.run(config, comment, comb, branch_name, dry_run)
                if result[1]:
                    if best_commit < result[0]:
                        best_commit = result[0]
                else:
                    fault += 1
                results.append(result)
                count += 1

            # print best result and information
            log_simple('\n\n==============================================')
            log('Search completed. Best commit:')
            if best_commit:
                log('COLOR.GREEN', best_commit)
            else:
                log('No best commit')

            # fault
            if fault > 0: log('COLOR.RED', 'Fault commits: ' + str(fault) + ' / ' + str(count))

            # mail
            duration = time.time() - begin_time
            autotime = try_get(self.testarium.config, 'mail.autoreport.time', -1)
            self.sendmail = True if duration > autotime >= 0 else self.sendmail
            body = commits2html('Best experiment', [(best_commit, True)]) + \
                   commits2html('All the experiment reports', results)
            text = makehtml(body)
            self._send_mail(text)  # send report mail to user if need

    # --- Execute user defined function and catch exceptions and check return value
    def exec_user_func(self, func, params, return_type, use_try=True):
        # use try
        if use_try:
            try:
                r = func(params)
            except MemoryError as e:
                log('Out of memory while', 'COLOR.YELLOW', func.__name__ + '():')
                log(e)
                log_simple()
                log_exception(traceback.format_exc())
                log_simple()
                log('Commit skipped')
                return None, False
            except Exception as e:
                log('Exception while', 'COLOR.YELLOW', func.__name__ + '():')
                log(e)
                log_simple()
                log_exception(traceback.format_exc())
                log_simple()
                log('Commit skipped')
                return None, False
        # not use try
        else:
            r = self.func(params)

        # check: r is returnType
        if not type(r) is return_type:
            log('COLOR.RED', 'Error: Return value of', 'COLOR.YELLOW', func.__name__ + '()', \
                'COLOR.RED', 'must be', 'COLOR.YELLOW', return_type.__name__, 'COLOR.RED', \
                '(but', 'COLOR.YELLOW', type(r).__name__, 'COLOR.RED', 'is given)')
            log('Commit skipped')
            return r, False

        # alright, ok
        return r, True

    # remove commit if dry run
    def remove_commit(self, c, dry_run):
        # check dry run and commit correct
        if not dry_run or c is None:
            return

        # check duration, skip if duration is long
        duration = time.time() - c.begin_time
        max_dur = self.testarium.config.get('dry_run.max_duration', 300)
        if duration > max_dur:
            c.RemoveDryRun()
            log()
            log('COLOR.GREEN', c.name, 'COLOR.GREEN',
                'duration %0.0fs is too long for dry-run,' % duration, 'COLOR.GREEN', 'commit saved!')
            return

        # remove otherwise
        try:
            c.Delete()
            log()
            log('COLOR.YELLOW', c.name, 'COLOR.YELLOW', 'was removed due to dry-run')
        except OSError as e:
            log()
            log('COLOR.YELLOW', c.name,
                'COLOR.RED', 'dry-run is enabled, but it is not possible to delete commit directory.\n'
                             'Did you forget close file descriptor inside of commit directory? \nSee error below:')
            # log(traceback.format_exc())
            log(e)

    # run one experiment
    def run(self, config, comment, new_params, branch_name, dry_run=True):
        c, result = None, False

        # get title of process
        title = ''
        if setproctitle_enabled:
            title = setproctitle.getproctitle()

        # check if user Run function defined
        if self.user_run is None:
            log('COLOR.RED', 'Error: User Run function is not described. Use decorator @Experiment.set_run to set it')
            return c, result

        # check if user Score function defined
        if self.user_score is None:
            log('COLOR.RED',
                'Error: User Score function is not described. Use decorator @Experiment.set_score to set it')
            return c, result

        # check commit removing after run and warning it
        timer = None
        dry_run_dur = self.testarium.config.get('dry_run.max_duration', 300)
        if dry_run:
            log('COLOR.YELLOW', 'Commit removing if run is less %0.0fs, ' % dry_run_dur +
                                'use CTRL+C to proper commit removing!')

        # form config with newParams
        config = collections.OrderedDict(config)
        for key in new_params:
            if key not in config:
                log('COLOR.YELLOW', 'Warning:', "new key '" + key + "' is not in config")
            config[key] = new_params[key]

        # we use double try to close all file descriptors inside of run & score
        try:
            try:
                # prepare commit and store it into testarium
                c = self.testarium.NewCommit(config, branch_name=branch_name, dry_run=dry_run)
                config_path = c.GetConfigPath()
                if config_path is None:
                    raise Exception("Something wrong with new commit path in Experiment.run()")
                c.desc['params'] = str(new_params)

                # start timer to disable dry-run
                if dry_run:
                    def disable_dry():
                        log()
                        log('COLOR.GREEN', 'Dry-run disabled due to duration')
                        c.RemoveDryRun()
                    timer = threading.Timer(dry_run_dur, disable_dry)
                    timer.start()

                # comment
                c.desc['comment'] = comment
                if len(new_params) > 0:
                    c.desc['comment'] = (c.desc['comment'] + ' ' if c.desc['comment'] else '') + json.dumps(new_params)

                # log output
                log('New commit:', c.name, '[' + c.branch.name + ']')
                if len(new_params) > 0:
                    log('Config =', str(new_params))

                # change process title
                if setproctitle_enabled:
                    new_title = '[testarium:' + c.name + '] ' + title
                    setproctitle.setproctitle(new_title)

                # run and score
                result = self._run_body(c)

            # grab CTRL + C
            except KeyboardInterrupt as e:
                raise e

        except KeyboardInterrupt as e:
            raise e

        finally:
            # remove commit if dry-run and CTRL+C
            self.remove_commit(c, dry_run)
            if timer is not None:
                timer.cancel()

        # change back process title
        if setproctitle_enabled:
            setproctitle.setproctitle(title)
        return c, result

    # Body of experiment run
    def _run_body(self, c):
        c.begin_time = time.time()

        # --- RUN section
        r, ok = self.exec_user_func(self.user_run, c, int)
        gc.collect()
        if not ok:
            return False

        # errors check
        if r < 0:
            log('COLOR.RED', 'Error: experiment error code =', r)
            log('Commit skipped')
            return False

        # duration
        duration = time.time() - c.begin_time

        # --- SCORE and DESC section
        desc, ok = self.exec_user_func(self.user_score, c, dict)
        gc.collect()
        if not ok:
            return False

        # form commit description
        c.desc['duration'] = duration
        c.desc.update(desc)

        # save commit with the new description
        c.Save()

        # print results
        log(c)
        return True
