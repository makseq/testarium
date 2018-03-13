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

import json, time, traceback, sys, gc, collections, shutil, os
import itertools as it
from utils import *
import kernel


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

    def SetSendMail(self, send):
        self.sendmail = send

    # --- Advanced experiment run with params search
    def Search(self, config, comment, newParams, useTry, runAndRemove=False):

        # check newParams for variants number
        max_variants = 1
        for key in newParams:
            if hasattr(newParams[key], '__iter__'):  # object is iterable
                variants = len(newParams[key])
                if max_variants < variants:
                    max_variants = variants

        # start simple Run(), if here is 1 variant
        if max_variants == 1:
            # convert to dict without values like lists
            beginTime = time.time()
            newParams = {key: (newParams[key][0] if hasattr(newParams[key], '__iter__') else newParams[key]) for key in
                         newParams}
            result = self.Run(config, comment, newParams, useTry, runAndRemove)
            duration = time.time() - beginTime

            # check experiment duration and make decision about mail sending
            autotime = try_get(self.testarium.config, 'mail.autoreport.time', -1)
            if duration > autotime and autotime >= 0: self.sendmail = True
            self._send_mail(makehtml(commits2html('Experiment report', [result])))  # send report mail to user if need

        # perform search
        else:
            # convert to dict with all the list values
            newParams = {key: (newParams[key] if hasattr(newParams[key], '__iter__') else [newParams[key]]) for key in
                         newParams}

            # combine params
            varNames = sorted(newParams)
            combinations = [collections.OrderedDict(zip(varNames, prod)) for prod in
                            it.product(*(newParams[varName] for varName in varNames))]

            # init vars
            results = []
            count = 0
            fault = 0
            beginTime = time.time()
            best_commit = kernel.Commit()  # not inited commit with the worst score

            # main loop
            for comb in combinations:
                log_simple('\n\n----------------------------------------------')
                log('Starting experiment: ', count + 1, '/', len(combinations))

                result = self.Run(config, comment, comb, useTry, runAndRemove)
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
            duration = time.time() - beginTime
            autotime = try_get(self.testarium.config, 'mail.autoreport.time', -1)
            if duration > autotime and autotime >= 0: self.sendmail = True
            text = makehtml(
                commits2html('Best experiment', [(best_commit, True)]) + commits2html('All the experiment reports',
                                                                                      results))
            self._send_mail(text)  # send report mail to user if need

    # --- Execute user defined function and catch exceptions and check return value
    def ExecUserFunc(self, func, params, returnType, useTry=True):
        # use try
        if useTry:
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
        if not type(r) is returnType:
            log('COLOR.RED', 'Error: Return value of', 'COLOR.YELLOW', func.__name__ + '()', \
                'COLOR.RED', 'must be', 'COLOR.YELLOW', returnType.__name__, 'COLOR.RED', \
                '(but', 'COLOR.YELLOW', type(r).__name__, 'COLOR.RED', 'is given)')
            log('Commit skipped')
            return r, False

        # alright, ok
        return r, True

    # --- Simple experiment run
    def Run(self, config, comment, newParams, useTry, runAndRemove=True):
        '''
        Run experiment.
        :arg runAndRemove   True means fully remove commit from repository,
                            False is nothing to remove
        '''
        # check if user Run function defined
        if self.user_run is None:
            log('COLOR.RED', 'Error: User Run function is not described. Use decorator @Experiment.set_run to set it')
            return None, False

        # check if user Score function defined
        if self.user_score is None:
            log('COLOR.RED',
                'Error: User Score function is not described. Use decorator @Experiment.set_score to set it')
            return None, False

        # check commit removing after run and warning it
        if runAndRemove == True:
            log('COLOR.YELLOW', 'Commit will be removed!')


        # form config with newParams
        config = collections.OrderedDict(config)
        for key in newParams:
            if not key in config: log('COLOR.YELLOW', 'Warning:', "new key '" + key + "' is not in config")
            config[key] = newParams[key]

        # prepare commit and store it into testarium
        c = self.testarium.NewCommit(config)  # save commit to provide access to config as file
        config_path = c.GetConfigPath()
        if config_path is None: raise Exception("Something wrong with new commit path in Experiment.Run()")
        c.desc['params'] = str(newParams)

        # log output
        log('New commit:', c.name, '[' + c.branch.name + ']')
        if len(newParams) > 0: log('Config =', str(newParams))
        beginTime = time.time()

        # remove commit if need
        def removeCommit():
            # remove commit if need
            if runAndRemove == True:
                shutil.rmtree(c.dir, True)
                log('COLOR.YELLOW', c.name, 'was removed')

        # --- RUN section
        r, ok = self.ExecUserFunc(self.user_run, c, int)
        gc.collect()
        if not ok:
            removeCommit()
            return c, False

        # errors check
        if r < 0:
            log('COLOR.RED', 'Error: experiment error code =', r)
            log('Commit skipped')
            removeCommit()
            return c, False

        # duration
        duration = time.time() - beginTime

        # --- SCORE and DESC section
        desc, ok = self.ExecUserFunc(self.user_score, c, dict)
        gc.collect()
        if not ok:
            removeCommit()
            return c, False

        # form commit description
        for key in desc: c.desc[key] = desc[key]
        c.desc['duration'] = duration
        c.desc['comment'] = comment
        if len(newParams) > 0:
            c.desc['comment'] = (c.desc['comment'] + ' ' if c.desc['comment'] else '') + json.dumps(newParams)

        # resave commit with the new description
        c.Save()
        # print results
        log(c)

        removeCommit()
        return c, True
