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

import datetime, time, json, numpy as np
import os, operator, shutil, collections
from utils import *
import coderepos, filedb

CONFIG_COMMIT_DIRECTORY = 'testarium.commitDirectory'

# ------------------------------------------------------------------------------
'''
	Common - store common params and working routines
'''


class Common:
    def __init__(self):
        self.root = None
        self.best_score_max = False
        self.commit_print_func = [None]
        self.commit_cmp_func = [None]
        self.allow_remove_commits = False


# ------------------------------------------------------------------------------
''' 
	Config contains a json config of experiment
	(parameters and other) 
'''


class Config(collections.OrderedDict):
    def __init__(self, *arg, **kw):
        self._init = True
        super(Config, self).__init__(*arg, **kw)

    def Print(self, useKeys=[]):
        if not useKeys: return self
        return {c: self[c] for c in self if c in useKeys}

    def __str__(self, useKeys=[]):
        msg = ''
        c = self.Print(useKeys)
        if not c: return 'No config' + (' with key filter ' + str(useKeys) if useKeys else '')

        maxSpaces = max([len(x) for x in c]) + 1
        for key in sorted(c.iterkeys()):
            if key == CONFIG_COMMIT_DIRECTORY: continue
            val = c[key]
            msg += key + ' ' * (maxSpaces - len(key)) + ': ' + str(val) + '\n'

        # delete unnecessary '\n'
        if msg and msg[len(msg) - 1] == '\n': msg = msg[0:len(msg) - 1]
        return msg

    def Difference(self, other_config, useKeys=[]):
        a = self
        b = other_config

        keys = set(a) | set(b)
        diff = dict()
        for key in keys:
            if not key in useKeys: continue
            if key == CONFIG_COMMIT_DIRECTORY: continue
            if key in useKeys or not useKeys:
                try:
                    aval = a[key]
                except:
                    aval = None

                try:
                    bval = b[key]
                except:
                    bval = None

                if aval <> bval: diff[key] = (aval, bval)
        return diff

    def StrDifference(self, other_config, aName, bName, useKeys=[]):
        diff = self.Difference(other_config, useKeys)
        if len(diff) == 0: return 'No configs difference' + \
                                  (' with key filter ' + str(useKeys) if len(useKeys) > 0 else '')

        s = ''
        maxSpaces = max([len(x) for x in diff]) + 1
        for key in sorted(diff.iterkeys()):
            val = diff[key]
            s += key + ' ' * (maxSpaces - len(key)) + ': ' + aName + ' = ' + str(val[0])
            s += ' ' * maxSpaces + ': ' + bName + ' = ' + str(val[1])
            s += '\n'

        # delete unnecessary '\n'
        if s and s[len(s) - 1] == '\n': s = s[0:len(s) - 1]
        return s


# ------------------------------------------------------------------------------
''' 
	Description contains a json desc 
	(score, time, comment and other) 
	after commit evaluation 
'''


class Description(collections.OrderedDict):
    def __init__(self, *arg, **kw):
        self._init = True
        super(Description, self).__init__(*arg, **kw)

    def Score(self):
        return self.desc['score']


# ------------------------------------------------------------------------------
''' 
	Commit consists of Config and Description
'''

class Commit:
    def __init__(self):
        self.config = Config()
        self.desc = Description()
        self.dir = ''
        self.name = 'none'
        self.common = Common()
        self._init = False
        self.meta = filedb.MetaDataBase()
        self.filedb = filedb.FileDataBase()
        self.branch = None

    def __nonzero__(self):
        return self._init

    def __cmp__(self, other):
        # user compare
        if not self.common.commit_cmp_func is None:
            if not self.common.commit_cmp_func[0] is None:
                return self.common.commit_cmp_func[0](self, other)

            if self._init:
                if self.common.best_score_max:
                    if self.desc['score'] > other.desc['score']:
                        return 1;
                    elif self.desc['score'] < other.desc['score']:
                        return -1;
                    else:
                        return 0
                else:
                    if self.desc['score'] > other.desc['score']:
                        return -1;
                    elif self.desc['score'] < other.desc['score']:
                        return 1;
                    else:
                        return 0
            else:
                return -1 if not self.common.best_score_max else 1

    def GenerateName(self):
        d = datetime.datetime.now()
        self.name = strtime(d.year) + strtime(d.month) + strtime(d.day) + \
                    '.' + strtime(d.hour) + strtime(d.minute) + strtime(d.second)
        self.SetName(self.name)
        return self.name

    def SetName(self, name):
        self.name = name
        self.desc['name'] = name

    def SetCommon(self, common):
        self.common = common

    def SetBranch(self, branch):
        self.branch = branch
        self.desc['branch'] = branch.name
        self.filedb = branch.filedb
        self.meta.SetFileDB(self.filedb)

    def SetConfig(self, c):
        self.config = collections.OrderedDict(c)

    def GetConfigPath(self):
        if self.dir != '':
            return self.dir + '/config.json'
        else:
            return None

    def __str__(self):
        if not self._init: return 'No init'
        cols, out = self.Print()
        if len(cols) != len(out): return 'Wrong cols or out afer Description.Print()'

        msg = ''
        nohead = ['name', 'comment', '']
        for i, c in enumerate(cols):
            if out[i] != '': msg += ('\t> ' if i != 0 else '') + ('' if c in nohead else c + ': ') + out[i] + ' '

        return msg

    def SkipUrls(self, cols, out):
        new = [c for c in zip(cols, out) if not UrlGraph(c[1]) and not UrlFile(c[1])]
        return zip(*new)

    def Print(self, skipUserPrint=False, web=False):
        if not self._init: return [], []

        # user print func
        if not self.common.commit_print_func is None and not skipUserPrint:
            if not self.common.commit_print_func[0] is None:
                if web:
                    try: cols, out = self.common.commit_print_func[0](self)
                    except:
                        cols, out = [], []

                    if not 'config' in cols:
                        cols.append('config')
                        out.append('file://storage/' + self.dir + '/config.json')
                    if not 'desc' in cols:
                        cols.append('desc')
                        out.append('file://storage/' + self.dir + '/desc.json')
                    if not 'fafr' in cols and os.path.exists(self.dir+'/fafr.txt'):
                        cols.append('fafr')
                        out.append('graph://storage/' + self.dir + '/fafr.txt')
                    return cols, out
                else:
                    return self.SkipUrls(*self.common.commit_print_func[0](self))

        try:
            name = self.desc['name']
        except:
            name = 'none'
        try:
            score = str("%0.5f" % float(self.desc['score']))
        except:
            score = 'none'
        try:
            time = str("%0.2f" % float(self.desc['duration']))
        except:
            time = ''
        try:
            comment = self.desc['comment']
        except:
            comment = ''

        # make much pretty commits have sub name (eg. 20140506.120001003)
        if len(name) > 15: name = name[:15] + ' ' + name[15:]

        cols = ['name', 'score', 'time', 'comment']
        out = [name, score, time, comment]

        # if web interface used
        if web:
            cols.append('fafr')
            out.append('graph://storage/' + self.dir + '/fafr.txt')

            cols.append('config')
            out.append('file://storage/' + self.dir + '/config.json')

            cols.append('desc')
            out.append('file://storage/' + self.dir + '/desc.json')

        return cols, out

    def MakeGraph(self, fname, points, xAxisName, yAxisName):

        if isinstance(points, list):
            points = np.array(points)

        if isinstance(points, np.ndarray):
            if len(points.shape) == 1:
                x = t = np.arange(len(points))
                y = points
            elif points.shape[1] == 1:
                x = t = np.arange(len(points))
                y = points
            elif points.shape[1] == 2:
                x = t = points[:, 0]
                y = points[:, 1]
            elif points.shape[1] == 3:
                x = points[:, 0]
                y = points[:, 1]
                t = points[:, 2]
            else:
                log('COLOR.RED', 'MakeGraph: Unsupported points dim')
                return -1

        else:
            log('COLOR.RED', 'Unsupported points type, supported only list and np.array')
            return -1

        path = self.dir + '/' + fname
        data = [{'x': float(x[i]), 'y': float(y[i]), 't': float(t[i])} for i, v in enumerate(x)]
        j = json.dumps({'xAxis': xAxisName, 'yAxis': yAxisName, 'data': data})
        try: open(path, 'w').write(j)
        except: log("MakeGraph: Can't save: " + path)

        return 'graph://storage/' + path

    def MakeLink(self, link_dir='../last'):
        # link commit dir to 'last'
        try:
            os.unlink(link_dir)  # unlink previous link
        except:
            pass
        os.symlink(os.path.abspath(self.dir), link_dir)

    def Load(self, dir):
        self._init = False
        self.dir = dir

        # desc
        try:
            self.desc = json.load(open(self.dir + '/desc.json'), object_pairs_hook=Description)
        except:
            raise Exception("Can't load commit description: " + dir)

        # config
        try:
            self.config = json.load(open(self.dir + '/config.json'), object_pairs_hook=Config)
        except:
            raise Exception("Can't load commit config: " + dir)

        # file db
        self.meta.LoadMeta(self.dir + '/filedb.meta.json')

        # common
        self.name = self.desc['name']
        self._init = True

    def Save(self, dir='', configOnly=False):
        self._init = False
        if dir:
            self.dir = dir
        else:
            if not dir and not self.dir: raise Exception('dir is not set in commit')
            dir = self.dir

        try:
            # dir
            self.config[CONFIG_COMMIT_DIRECTORY] = dir
            create_dir(dir)

            # config
            config_str = json.dumps(self.config, indent=2, ensure_ascii=False).encode('utf-8')
            open(self.dir + '/config.json', 'w').write(config_str)
            if configOnly: return

            # Encoder to save numpy to desc
            class NumpyEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    else:
                        return super(NumpyEncoder, self).default(obj)

            # desc
            json.dump(self.desc, open(self.dir + '/desc.json', 'w'), indent=2, cls=NumpyEncoder)

            # file db
            self.branch.filedb.SaveFiles(self.dir + '/../filedb.json')
            self.meta.SaveMeta(self.dir + '/filedb.meta.json')
        except Exception as e:
            raise Exception("Can't save the commit: " + dir + ", " + str(e))
        self._init = True


# ------------------------------------------------------------------------------
'''
	Branch keeps commits and is associated with subtask
'''


class Branch:
    def __init__(self):
        self._init = True
        self.name = 'default'
        self.config_path = 'config/config.json'
        self.commits = dict()
        self.common = Common()
        self.filedb = filedb.FileDataBase()

    def NewCommit(self, config):
        commit = Commit()
        commit.GenerateName()

        # check if commit with this name exists
        count = 1
        dir = self.common.root + '/' + self.name
        while os.path.exists(dir + '/' + commit.name):
            sub = str('%0.3i' % count)
            commit.SetName(commit.GenerateName() + sub)
            count += 1

        commit.SetConfig(config)
        commit.SetBranch(self)
        commit.SetCommon(self.common)

        # file db
        self.filedb.ResetShuffle()
        self.filedb.LoadFiles(dir + '/filedb.json')

        self.commits[commit.name] = commit
        return commit

    def Load(self, dir, loadCommits):
        self._init = False
        self.dir = dir

        # load branch description
        path = dir + '/branch.json'
        try:
            j = json.loads(open(path, 'r').read())
        except:
            raise Exception('No branch description: ' + path)

        self.name = j['name']
        self.config_path = j['config_path']

        if not loadCommits: return

        # scan for commit dirs
        subdirs = [d for d in os.listdir(dir) if os.path.isdir(dir + '/' + d)]

        # load commits
        removed = 0
        for d in subdirs:
            if d in self.commits:
                continue

            commit = Commit()
            commit.SetBranch(self)
            commit.SetCommon(self.common)

            # file db
            self.filedb.LoadFiles(dir + '/filedb.json')

            try:
                commit.Load(dir + '/' + d)
            except:
                if self.common.allow_remove_commits:
                    try:
                        shutil.rmtree(dir + '/' + d)
                    except:
                        log("Can't remove:", dir + '/' + d)
                    else:
                        log('Commit removed:', dir + '/' + d)
                        removed += 1
            else:
                self.commits[commit.name] = commit

        if removed > 0: log('Total removed commits:', removed)
        self._init = True

    def Save(self, saveCommits):
        dir = self.common.root + '/' + self.name
        create_dir(dir)

        # save branch info
        desc = dict()
        desc['name'] = self.name
        desc['config_path'] = self.config_path

        path = dir + '/branch.json'
        try:
            json.dump(desc, open(path, 'w'), indent=2)
        except:
            raise Exception("Can't save the branch description: " + path)

        if not saveCommits: return

        # save commits
        for c in self.commits:
            self.commits[c].Save(dir + '/' + self.commits[c].name)


# ------------------------------------------------------------------------------
'''
	Testarium - manage the commits
'''


class Testarium:
    def best_score_is_max(self):
        self.common.best_score_max = True

    def best_score_is_min(self):
        self.common.best_score_max = False

    def set_print(self, func):
        self.common.commit_print_func[0] = func  # use list because we want to save the pointer

    def set_compare(self, func):
        self.common.commit_cmp_func[0] = func  # use list because we want to save the pointer

    def __init__(self, rootdir='.testarium', loadCommits=False):
        # init root, branches, coderepos and try to preload testarium
        self.config = dict()
        self.root = rootdir
        self.branches = dict()
        self.coderepos = coderepos.CodeRepos()
        self.common = Common()
        self.common.root = rootdir
        try:
            self.Load(loadCommits, silent=True)
        except:
            log('Testarium loading failed. It will be new configurated setup')

        # git / mercurial repository init
        if self.ReadConfig('coderepos.use', True) == True:
            if os.path.exists('.hg') or os.path.exists('../.hg') or os.path.exists('../../.hg'):
                self.coderepos = coderepos.Mercurial()
            else:
                self.coderepos = coderepos.Git()

        # Load failed, reinit testarium
        if not self._init:
            if not colored: log("Do 'easy_install colorama' to color testarium logs")
            self._init = False
            self.name = os.path.basename(os.getcwd())
            self.SetRootDir(rootdir)

            self.ChangeBranch('default')
            self.Save(saveCommits=False)
            log('Testarium initialized. Project name:', 'COLOR.GREEN', self.name)
            self._init = True

    def ReadConfig(self, key, default):
        val = default
        try:
            val = self.config[key]
        except:
            pass
        return val

    def SetRootDir(self, dir):
        self.root = dir
        self.common.root = dir
        create_dir(self.root)

    def ChangeBranch(self, name, new=True):
        if name in self.branches:
            self.activeBranch = self.branches[name]
        elif new:
            b = Branch()
            b.name = name
            b.common = self.common
            b.Save(saveCommits=False)
            self.branches[name] = b
            self.activeBranch = b
        else:
            return

        # coderepos change branch
        self.coderepos.changebranch(name)

    # Return active branch
    def ActiveBranch(self):
        return self.activeBranch

    # Add new commit to active branch
    def NewCommit(self, config):
        commit = self.activeBranch.NewCommit(config)
        path = self.root + '/' + self.activeBranch.name + '/' + commit.name
        commit.Save(path, configOnly=True)

        # coderepos commit
        comment = ''
        try:
            comment = ' ' + commit.desc['comment']
        except:
            pass
        self.coderepos.commit(commit.name, comment)

        return commit

    # Select commits by branch and name/position/keyword
    def SelectCommits(self, branch_name, name, N):
        # select specified branch
        if branch_name:
            if branch_name in self.branches:
                branch = self.LoadBranch(self.branches[branch_name].name, silent=True)
            else:
                log('COLOR.RED', 'Error: no such branch:', branch_name)
                return
        # select active branch
        else:
            branch = self.LoadActiveBranch(silent=True)

        # commits
        commits = branch.commits
        #sort_keys = sorted([k for k in commits], reverse=True)
        sort_keys = sorted(commits.keys(), reverse=True)
        if not sort_keys: log('No commits in this branch:', branch.name); return

        # -----------------------------------------------
        # print only one commit
        if name:
            # replace last to 0
            if name == 'last': name = '0'

            # print the best commit
            if name == 'best':
                if N > 0: sort_keys = sort_keys[0:N]
                commits_list = [commits[k] for k in sort_keys]
                return [max(commits_list)]

            # -----------------------------------------------
            # take commit by number
            try:
                number = int(name)
            except:
                pass
            else:
                # check number bounds
                error = False
                if number < 0:
                    if abs(number) > len(sort_keys): error = True
                else:
                    if number >= len(sort_keys): error = True
                if error: log('COLOR.RED', 'Error: incorrect commit number:', number, '/', len(sort_keys)); return

                # print
                return [commits[sort_keys[number]]]

            # -----------------------------------------------
            # take commit by name
            # check for name as date, eg. 20140503.121100
            error = False
            try:
                if name[8] == '.':
                    try:
                        float(name)
                    except:
                        error = True
                    else:
                        # check if commit is exist
                        if name in commits:
                            return [commits[name]]
                        else:
                            log('COLOR.RED', 'Error: no commit found:', name)
            except:
                error = True

            if error: log('COLOR.RED', 'Error: incorrect commit name:', name)

        # -----------------------------------------------
        # print N commits
        else:
            if N == -1: N = None
            return [commits[c] for c in sort_keys[0:N]]

    # Where commit selector (expressions for desc and config to select commit)
    def Where(self, conditions):
        # commits = self.AllCommits()
        commits = self.activeBranch.commits

        sort_keys = sorted([k for k in commits], reverse=True)
        if not sort_keys: return None
        cond = ''.join(conditions)
        cond = cond.replace("['", "[", 1).replace("']", "]", 1).replace("[", "['", 1).replace("]", "']", 1)
        print cond

        # where
        error = ''
        out_commits = []
        for k in sort_keys:
            c = commits[k].config
            d = commits[k].desc

            show = False
            try:
                exec 'if ' + cond + ': show = True';
            except Exception as e:
                error += str(e) + '; '

            if show: out_commits.append(commits[k])
        return out_commits, error

    # Remove bad commits while load
    def RemoveBrokenCommitsAndLoad(self):
        self.common.allow_remove_commits = True
        self.Load(True)
        self.common.allow_remove_commits = False

    # Load branches and commits
    # if loadCommits == False than branch descriptions will be loaded only
    def Load(self, loadCommits, silent=False):
        self._init = False
        j = self.LoadTestariumOnly()

        # load branches and commits if need
        subdirs = [d for d in os.listdir(self.root) if os.path.isdir(self.root + '/' + d)]
        commitsCount = 0
        for d in subdirs:
            b = self.LoadBranch(d, silent=True, loadCommits=loadCommits)
            commitsCount += len(b.commits)
        self.activeBranch = self.branches[j['activeBranch']]

        self._init = True
        if not silent: log('Loaded', len(self.branches), 'branches and', commitsCount, 'commits')

    # Load Testarium class only
    def LoadTestariumOnly(self):
        # load testarium descrition
        path = self.root + '/testarium.json'
        try:
            self.config = json.loads(open(path, 'r').read())
        except:
            raise Exception('No testarium description: ' + path)
        self.name = self.config['name']
        self.activeBranch = None
        self.config = self.config
        return self.config

    # Load active branch only
    # if loadCommits == False than branch descriptions will be loaded only
    def LoadBranch(self, name, silent=False, loadCommits=True):
        b = self.branches[name] if name in self.branches else Branch()
        b.common = self.common
        b.Load(self.root + '/' + name, loadCommits=not b._init)
        self.branches[b.name] = b

        if not silent: log('Branch', name, 'has been loaded with', len(b.commits), 'commits')
        return b

    # Load active branch only
    # if loadCommits == False than branch descriptions will be loaded only
    def LoadActiveBranch(self, silent=False):
        b = self.LoadBranch(self.activeBranch.name, silent, loadCommits=True)
        self.activeBranch = b

        if not silent: log('Active branch has been loaded with', len(b.commits), 'commits')
        return b

    # All the commits from all the branches
    def AllCommits(self):
        all = dict()
        for b in self.branches:
            all.update(self.branches[b].commits)
        return all

    # Save branches and commits
    def Save(self, saveCommits):
        self.SaveTestariumOnly()

        # save branches and commits if need
        for b in self.branches:
            self.branches[b].Save(saveCommits)

        msg = 'and commits' if saveCommits else ' '
        log('All the branches' + msg + 'have been saved')

    def SaveTestariumOnly(self):
        create_dir(self.root)

        # save testarium info
        self.config['name'] = self.name
        self.config['activeBranch'] = self.activeBranch.name
        path = self.root + '/testarium.json'
        try:
            json.dump(self.config, open(path, 'w'), indent=2)
        except:
            raise Exception("Can't save the testarium: " + path)

    # Save branches and commits
    def SaveActiveBranch(self, saveCommits):
        self.SaveTestariumOnly()
        self.activeBranch.Save(saveCommits)
        log('Active branch has been saved')

    def DeleteCommit(self, commit):
        name = commit.name
        if commit.name in self.activeBranch.commits:
            shutil.rmtree(self.root + '/' + self.activeBranch.name + '/' + name)
            del self.activeBranch.commits[name]
            log('Commit', name, 'has been deleted from branch', self.activeBranch.name)
        else:
            log("Can't find commit", name, 'in branch', self.activeBranch.name)
