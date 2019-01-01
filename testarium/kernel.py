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

import datetime, time, json, numpy as np
import os, operator, shutil, collections
import traceback
from utils import *
import coderepos
import filedb
import random
import codecs
import socket

CONFIG_COMMIT_DIRECTORY = 'testarium.commitDirectory'


# ------------------------------------------------------------------------------
class Common:
    """
    Common - store common params and working routines
    """
    def __init__(self):
        self.root = None
        self.best_score_max = False
        self.commit_print_func = [None]
        self.commit_cmp_func = [None]
        self.allow_remove_commits = ''


# ------------------------------------------------------------------------------
class Config(collections.OrderedDict):
    """ 
    Config contains a json config of experiment
    (parameters and other) 
    """

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
class Description(collections.OrderedDict):
    """ 
    Description contains a json desc 
    (score, time, comment and other) 
    after commit evaluation 
    """
    def __init__(self, *arg, **kw):
        super(Description, self).__init__(*arg, **kw)
        self._init = True
        self.setdefault('score', 0)

    def __getitem__(self, item):
        if item in self:
            return super(Description, self).__getitem__(item)
        else:
            return None


# ------------------------------------------------------------------------------
class Commit:
    """ 
    Commit consists of Config and Description
    """
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
        self.begin_time = None

    def __nonzero__(self):
        return self._init

    def __cmp__(self, other):
        # user compare
        if self.common.commit_cmp_func is not None:
            if not self.common.commit_cmp_func[0] is None:
                return self.common.commit_cmp_func[0](self, other)

            if self._init:
                if self.common.best_score_max:
                    if self.desc['score'] > other.desc['score']:
                        return 1
                    elif self.desc['score'] < other.desc['score']:
                        return -1
                    else:
                        return 0
                else:
                    if self.desc['score'] > other.desc['score']:
                        return -1
                    elif self.desc['score'] < other.desc['score']:
                        return 1
                    else:
                        return 0
            else:
                return -1 if not self.common.best_score_max else 1

    def __str__(self):
        if not self._init:
            return 'No init'

        cols, out = self.Print()
        if len(cols) != len(out):
            return 'Wrong cols or out after Description.Print()'

        msg = ''
        no_head = ['name', 'comment', '']
        for i, c in enumerate(cols):
            part = unicode(out[i])
            if part:
                msg += ('\t> ' if i != 0 else '') + ('' if c in no_head else c + ': ') + part + ' '

        return msg

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
        self.desc['score'] = float('-inf') if common.best_score_max else float('+inf')

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

    def GetDesc(self, key, format, default=''):
        return format % self.desc[key] if key in self.desc else default

    def SkipUrls(self, cols, out):
        new = [c for c in zip(cols, out) if not url_any(c[1])]
        return zip(*new)

    def Print(self, skipUserPrint=False, web=False):
        if not self._init: return [], []

        # user print func
        if self.common.commit_print_func is not None and not skipUserPrint:
            if not self.common.commit_print_func[0] is None:
                cols, out = self.common.commit_print_func[0](self)
                out = [unicode(o) for o in out]

                if web:
                    if 'config' not in cols:
                        cols.append('config')
                        out.append('file://storage/' + self.dir + '/config.json')
                    if 'desc' not in cols:
                        cols.append('desc')
                        out.append('file://storage/' + self.dir + '/desc.json')
                    if 'fafr' not in cols and os.path.exists(self.dir+'/fafr.txt'):
                        cols.append('fafr')
                        out.append('graph://storage/' + self.dir + '/fafr.txt')
                    return cols, out
                else:
                    return self.SkipUrls(cols, out)

        name = self.desc.get('name', 'none')
        score = str(self.desc['score']) if 'score' in self.desc else 'none'
        time = str('%0.2f' % float(self.desc['duration'])) if 'duration' in self.desc else ''
        comment = self.desc.get('comment', '')

        # make much pretty commits have sub name (eg. 20140506.120001003)
        name = (name[:15] + ' ' + name[15:]) if len(name) > 15 else name

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

    def MakeGraph(self, fname, points, xAxisName, yAxisName, graphName=None):

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

        # make json file for graph
        if graphName is not None:
            # make path from graphName autogenerated
            g_root = self.dir + '/graphics/'
            os.makedirs(g_root) if not os.path.exists(g_root) else ()
            path = g_root + graphName + '.json'
            # check
            if fname is not None and fname:
                log('COLOR.YELLOW', "! testarium warning: don't use graphName & fname together!")
        else:
            # use user prefered path
            path = self.dir + '/' + fname

        data = [{'x': float(x[i]), 'y': float(y[i]), 't': float(t[i])} for i, v in enumerate(x)]
        j = json.dumps({'xAxis': xAxisName, 'yAxis': yAxisName, 'data': data})
        try: open(path, 'w').write(j)
        except: log("MakeGraph: Can't save: " + path)

        # add to desc
        graphName = fname.split('.')[0] if graphName is None else graphName
        self.AddResources(graphName, path, 'graph')
        return path

    def MakeImage(self, name, path='', ext='.svg'):
        if not path:
            img_root = self.dir + '/images/'
            os.makedirs(img_root) if not os.path.exists(img_root) else ()
            path = img_root + name + ext

        self.AddResources(name, path, 'image')
        return path

    def AddResources(self, name, files_or_dirs, resource_type=''):
        # init
        if 'resources' not in self.desc:
            self.desc['resources'] = []

        # convert file to file list
        if not isinstance(files_or_dirs, list):
            files_or_dirs = [files_or_dirs]

        # add
        r = {"name": name, "paths": files_or_dirs, "type": resource_type}
        if r not in self.desc['resources']:  # check is it already exists?
            self.desc['resources'] += [r]

        # save changes
        self.Save()

    def GetResources(self, resource_type, unroll=True):
        result = []
        for r in self.desc.get('resources', []):
            if r.get('type', '') == resource_type:
                if unroll:
                    result += [{'name': r['name'], 'path': p} for p in r['paths']]
                else:
                    result += [{'name': r['name'], 'paths': r['paths']}]
        return result

    def PrintGraphics(self):
        graphs = self.GetResources('graph', unroll=True)
        names, paths = [], []
        for i in graphs:
            names += [i['name']]
            paths += ['graph://storage/' + i['path']]
        return names, paths

    def PrintImages(self):
        images = self.GetResources('image', unroll=True)
        names, paths = [], []
        for i in images:
            names += [i['name']]
            paths += ['image://storage/' + i['path']]
        return names, paths

    def RemoveDryRun(self):
        if 'dry_run' in self.desc:
            del self.desc['dry_run']
            self.Save()

    def Delete(self):
        # remove resources linked to this commit
        ok = True
        msg = ''
        if 'resources' in self.desc:
            for r in self.desc.get('resources', []):
                name, paths = r['name'], r['paths']
                for path in paths:
                    # skip resources inside of commit dir, it will be deleted anyway
                    if self.dir in path:
                        continue

                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.unlink(path)
                        log('resource removed: [' + name + ']', path)
                    except OSError as e:
                        if e.errno == 2:  # No such file - it's already removed
                            msg = 'resource not found: [' + name + '] ' + path
                        else:
                            ok = False
                            msg = 'resource removing error [' + name + '] ' + path + ': ' + str(e)

        # remove commit
        if ok:
            shutil.rmtree(self.dir)
        else:
            raise TestariumException("Can't remove commit: " + msg)

    def MakeLink(self, link_dir='../last'):
        # link commit dir to 'last'
        try:
            os.unlink(link_dir)  # unlink previous link
        except:
            pass
        os.symlink(os.path.abspath(self.dir), link_dir)

    def Load(self, d):
        self._init = False
        self.dir = d

        # desc
        try:
            with codecs.open(self.dir + '/desc.json', 'r', encoding='utf-8') as f:
                self.desc = json.load(f, object_pairs_hook=Description)
        except:
            raise TestariumException("Can't load commit description: " + d)

        # config
        try:
            self.config = json.load(open(self.dir + '/config.json'), object_pairs_hook=Config)
        except:
            raise TestariumException("Can't load commit config: " + d)

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
            if not dir and not self.dir:
                raise TestariumException('dir is not set in commit')
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
            with codecs.open(self.dir + '/desc.json', 'w', encoding='utf-8') as f:
                json.dump(self.desc, f, ensure_ascii=False, sort_keys=True, indent=2,
                          separators=(',', ': '), cls=NumpyEncoder)

            # file db
            self.branch.filedb.SaveFiles(self.dir + '/../filedb.json')
            self.meta.SaveMeta(self.dir + '/filedb.meta.json')
        except Exception as e:
            raise TestariumException("Can't save the commit: " + dir + ", " + str(e))
        self._init = True


# ------------------------------------------------------------------------------
class Branch:
    """        
    Branch keeps commits and is associated with subtask
    """
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
        d = self.common.root + '/' + self.name
        while os.path.exists(d + '/' + commit.name):
            sub = str('%0.3i' % count)
            commit.SetName(commit.GenerateName() + sub)
            count += 1

        commit.SetConfig(config)
        commit.SetBranch(self)
        commit.SetCommon(self.common)

        # file db
        self.filedb.ResetShuffle()
        self.filedb.LoadFiles(d + '/filedb.json')

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
            raise TestariumException('No branch description: ' + path)

        self.name = j['name']
        self.config_path = j['config_path']

        if not loadCommits: return

        # scan for commit dirs
        subdirs = [d for d in os.listdir(dir) if os.path.isdir(dir + '/' + d)]

        # load commits
        self.commits = {}
        removed = 0
        for d in subdirs:
            commit = Commit()
            commit.SetBranch(self)
            commit.SetCommon(self.common)

            # file db
            self.filedb.LoadFiles(dir + '/filedb.json')

            bad = False
            dry_run = False
            try:
                commit.Load(dir + '/' + d)
            except:
                bad = True
            else:
                self.commits[commit.name] = commit
                if 'dry_run' in commit.desc and commit.desc['dry_run']:
                    dry_run = True

            # remove commit
            if (bad or dry_run) and self.common.allow_remove_commits:
                # check is anything else in this directory?
                system_files = ['config.json', 'desc.json', 'filedb.meta.json']
                path = dir + '/' + d
                files = [f for f in os.listdir(path) if f not in system_files]

                if len(files) > 0 and self.common.allow_remove_commits != 'hard':
                    log("Broken commit," if bad else "Dry-run commit,", "but user files found (--hard to remove it):", dir + '/' + d)
                else:
                    try:
                        commit.Delete()
                        shutil.rmtree(path, ignore_errors=True)
                    except:
                        log("Can't remove:", dir + '/' + d)
                    else:
                        # remove commit from memory
                        if commit.name in self.commits:
                            del self.commits[commit.name]

                        log('Commit removed:', dir + '/' + d, '(dry-run)' if dry_run else '')
                        removed += 1

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
            raise TestariumException("Can't save the branch description: " + path)

        if not saveCommits: return

        # save commits
        for c in self.commits:
            self.commits[c].Save(dir + '/' + self.commits[c].name)


# ------------------------------------------------------------------------------
class Testarium:
    """
    Testarium - manage the commits
    """

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
        self.hostname = socket.gethostname()
        try:
            self.Load(loadCommits, silent=True)
        except Exception as e:
            log('Testarium loading failed. It will be new configurated setup')

        # git / mercurial repository init
        if self.ReadConfig('coderepos.use', True):
            if os.path.exists('.hg') or os.path.exists('../.hg') or os.path.exists('../../.hg'):
                self.coderepos = coderepos.Mercurial()
            elif os.path.exists('.git') or os.path.exists('../.git') or os.path.exists('../../.git'):
                self.coderepos = coderepos.Git()

        # Load failed, reinit testarium
        if not self._init:
            if not colored: log("Do 'easy_install colorama' to color testarium logs")
            self._init = False

            # generate name
            bad_names = ['research', 'work', 'test']
            self.name = os.path.basename(os.getcwd())
            self.name = os.path.basename(os.path.dirname(os.getcwd())) if self.name in bad_names else self.name
            self.name = 'T' if not self.name else self.name
            self.SetRootDir(rootdir)

            self.ChangeBranch('default')
            self.Save(saveCommits=False)
            log('Testarium initialized. Project name:', 'COLOR.GREEN', self.name)
            self._init = True

    def ReadConfig(self, key, default):
        return self.config.get(key, default)

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
        self.coderepos.change_branch(name)

    # Return active branch
    def ActiveBranch(self):
        return self.activeBranch

    # Add new commit to active branch
    def NewCommit(self, config, branch_name='', dry_run=False):
        branch = self.branches[branch_name] if branch_name else self.activeBranch
        commit = branch.NewCommit(config)
        commit.dry_run = dry_run
        path = self.root + '/' + branch.name + '/' + commit.name

        if dry_run:
            commit.desc['dry_run'] = True
        else:
            comment = ' ' + commit.desc.get('comment', '')
            repo_hash = self.coderepos.commit(commit.name, comment)  # commit in repository (git/hg)
            commit.desc['coderepos.commit_name'] = repo_hash

        # write to disk
        commit.Save(path, configOnly=True)
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
        sort_keys = sorted(commits.keys(), reverse=True)
        if not sort_keys:
            log('No commits in this branch:', branch.name)
            return

        # -----------------------------------------------
        # print only one commit
        if name:
            # replace last to 0
            if name == 'last' or name == 'head' or name == 'HEAD':
                name = '0'

            # print the best commit
            if name == 'best':
                if N > 0:
                    sort_keys = sort_keys[0:N]
                commits_list = [commits[k] for k in sort_keys]
                return [max(commits_list)]

            # -----------------------------------------------
            # take commit by number
            try:
                number = int(name)
                if number < 0:
                    raise TestariumException('Only positive numbers can be used')
            except:
                pass
            else:
                # check number bounds
                error = False
                if number < 0:
                    error = True if abs(number) > len(sort_keys) else error
                else:
                    error = True if number >= len(sort_keys) else error

                if error:
                    log('COLOR.RED', 'Error: incorrect commit number:', number, '/', len(sort_keys))
                    return

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
                exec 'if ' + cond + ': show = True'
            except Exception as e:
                error += str(e) + '; '

            if show: out_commits.append(commits[k])
        return out_commits, error

    # Remove bad commits while load
    def RemoveBrokenCommitsAndLoad(self, hard=False):
        self.common.allow_remove_commits = 'hard' if hard else 'soft'
        self.Load(True)
        self.common.allow_remove_commits = ''

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
        # self.SaveTestariumOnly()
        if not silent:
            log('Loaded', len(self.branches), 'branches and', commitsCount, 'commits')

    # Load Testarium class only
    def LoadTestariumOnly(self):
        # load testarium descrition
        path = self.root + '/testarium.json'
        try:
            self.config = json.loads(open(path, 'r').read())
        except:
            raise TestariumException('No testarium description: ' + path)
        self.name = self.config['name']
        self.activeBranch = None
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

        # choice background image by random
        if 'background' not in self.config:
            d = os.path.dirname(os.path.abspath(__file__)) + '/web/static/images'
            images = [f for f in os.listdir(d) if f.endswith('.jpg')]
            name = random.choice(images)
            self.config['background'] = 'static/images/' + name
            self.config['background.opacity'] = 0.7

        # dry run params
        if 'dry_run.max_duration' not in self.config:
            self.config['dry_run.max_duration'] = 300.0

        # dry run params
        if 'coderepos.use' not in self.config:
            self.config['coderepos.use'] = True

        path = self.root + '/testarium.json'
        try:
            json.dump(self.config, open(path, 'w'), indent=2)
        except:
            raise TestariumException("Can't save the testarium: " + path)

    # Save branches and commits
    def SaveActiveBranch(self, saveCommits):
        self.SaveTestariumOnly()
        self.activeBranch.Save(saveCommits)
        log('Active branch has been saved')

    def DeleteCommit(self, commit):
        name = commit.name
        try:
            commit.Delete()
            log('Commit', name, 'has been deleted')
        except Exception as e:
            log('COLOR.RED', 'Commit ' + name + ' can not be deleted:', traceback.format_exc())
