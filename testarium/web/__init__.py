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

import flask, os, json, collections, copy, traceback, copy
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from functools import wraps
from flask import request, Response
import webbrowser, threading
import time


DEBUG = True
t = 'None'
e = 'None'


# answer for api
def answer(status=0, msg="", object=None):
    if status == 0 and not msg and object is None:
        status = -1000
        msg = "nothing happened"

    a = {"status": status, "msg": msg}
    a.update({'request': request.args})

    if not object is None: a.update({"result": object})
    return json.dumps(a, indent=2)

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


class WebServer:

    def __init__(self, testarium, experiment, args):
        self.app = Flask(__name__)
        self.app.config.from_object(__name__)
        self.args = args

        self.t = testarium
        self.t.Load(True)
        self.e = experiment
        global t, e
        t = self.t
        e = self.e
        self.auth_user = 'admin'
        self.auth_pass = ''

    def Start(self, port, auth_user, auth_pass):

        # -------------------------------------------------
        def check_auth(username, password):
            """This function is called to check if a username /
            password combination is valid.
            """
            time.sleep(2)
            if not auth_pass: return True
            return username == auth_user and password == auth_pass

        def requires_auth(f):
            if not auth_pass: return f  # do not use pass

            @wraps(f)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth or not check_auth(auth.username, auth.password):
                    return authenticate()
                return f(*args, **kwargs)
            return decorated

        # -----------------------------------------------
        @self.app.route('/static/<path:filename>')
        def send_static(path, filename):
            return flask.send_from_directory('static', filename)

        # -----------------------------------------------
        @self.app.route('/favicon.ico')
        def send_favicon():
            return flask.send_file('static/favicon.ico')

        # -----------------------------------------------
        @self.app.route('/storage/<path:filename>')
        def send_storage(filename):
            if os.path.exists(filename):
                workdir = os.getcwd()
                return flask.send_from_directory(workdir, filename)  # load file from root of project
            else:
                return flask.send_file(filename)  # load file with absolute path

        ###  API ###

        # -----------------------------------------------
        @self.app.route('/api/info')
        def API_info():
            t.Load(False)
            cfg = copy.deepcopy(t.config)
            try:
                del cfg['mail.password']
            except:
                pass

            res = {
                "config": cfg,
                "common": {
                    "root": t.common.root,
                    "best_score_max": t.common.best_score_max
                },
                "branches": [b.replace('.', '-') for b in t.branches],
                "active_branch": t.ActiveBranch().name
            }
            return answer(object=res)

        # -----------------------------------------------
        @self.app.route('/api/branches')
        def API_branches():
            t.Load(False)
            res = [b.replace('.', '-') for b in t.branches]
            return answer(object=res)

        # -----------------------------------------------
        @self.app.route('/api/branches/active')
        def API_branches_active():
            t.Load(False)
            return answer(object=t.ActiveBranch().name)

        # -----------------------------------------------
        @self.app.route('/api/branches/<branch_name>/commits')
        def API_branches_commits(branch_name):
            t.Load(True)
            if branch_name.replace('-', '.') in t.branches: branch_name = branch_name.replace('-', '.')
            if branch_name == '~': branch_name = t.ActiveBranch().name
            t.ChangeBranch(branch_name, new=False)

            number = 100
            commitName = ''
            if 'n' in request.args: number = int(request.args['n'])
            if 'name' in request.args: commitName = request.args['name']; number = -1

            # where
            if 'where' in request.args:
                where = request.args['where']
                commits, error = t.Where(where)

            # simple select
            else:
                commits = t.SelectCommits(branch_name, commitName, number)
                error = None

            printing = [c.Print(web=True) for c in commits]
            res = [collections.OrderedDict(zip(col, val)) for col, val in printing]

            status = 0
            msg = "ok"
            if error:
                status = -150
                msg = "There was error: '" + str(error) + "'"
            return answer(status=status, msg=msg, object=res)

        # -----------------------------------------------
        @self.app.route('/api/branches/<branch_name>/commits/<commit_name>')
        def API_commit(branch_name, commit_name):
            global e
            status = 0
            msg = "ok"
            res = None

            # get commit
            commit = t.SelectCommits(branch_name, commit_name, 1)
            if not commit: return answer(-151, 'no commit with this name ' + commit_name)
            commit = commit[0]

            # modify
            if 'op' in request.args and request.args['op']=='modify':
                if 'comment' in request.args:
                    commit.desc['comment'] = request.args['comment'] #.decode('utf-8')
                    commit.Save()
                    return answer(status=status, msg=msg, object=res)


            # filter by file info
            if 'filter' in request.args:
                filter = request.args['filter']
                cond = filter.replace("['", "[").replace("']", "]").replace("[", "['").replace("]", "']")
                commit = copy.deepcopy(commit)

                error = 'ok; '
                for _id in commit.meta.GetAllIds():
                    f = commit.filedb.GetFile(_id)
                    m = commit.meta.meta[_id]
                    try:
                        exec 'if not (' + cond + '): del commit.meta.meta[_id]' in globals(), locals()
                    except Exception as exception:
                        error += str(exception) + '; '
                msg = error

                # rescore commit by user score
                if e.user_score:
                    commit.desc.update(e.user_score(commit))

            # replace meta id to pathes
            meta = commit.meta.meta
            if 'replace_id' in request.args:
                new_meta = {}
                for _id in commit.meta.meta:
                    path = commit.filedb.GetPath(_id)
                    new_meta[path] = commit.meta.meta[_id]
                    value = commit.filedb.GetFile(_id)
                    new_meta[path].update(value)
                meta = new_meta

            if 'player' in request.args:
                media_files = [str(i)+'. '+commit.filedb.GetPath(f) + '\t' + str(meta[f]['probs']) + '<br/>'
                                '<audio controls preload="none" src=/storage/'+commit.filedb.GetPath(f)+'></audio><br/>'

                               for i,f in enumerate(meta)]
                out = '\n'.join(media_files)
                return out

            if 'desc_only' in request.args:
                res = {'desc': commit.desc}
            else:
                res = {'config': commit.config, 'desc': commit.desc, 'meta': meta}
            return answer(status=status, msg=msg, object=res)


        ### ROOT ###

        # -----------------------------------------------
        @self.app.route('/')
        @requires_auth
        def root():
            self.t.Load(False)
            self.t.ChangeBranch(self.t.activeBranch.name)

            number = 100
            name = ''

            try:
                number = int(request.args['n'])
            except:
                pass
            try:
                name = request.args['name']; number = -1
            except:
                pass

            commits = self.t.SelectCommits(t.activeBranch.name, name, number)
            return render_template('main.html', t=self.t)

        # -----------------------------------------------
        def open_page():  # open page with testarium in web browser
            try:
                url = 'http://localhost:'+str(port)
                webbrowser.open_new_tab(url)
                print 'Open in new tab:', url
            except:
                print "Can't open browser with new tab:", url
                pass

        if not self.args.no_open_tab:
            threading.Timer(2.0, open_page).start()

        self.app.run(port=port, host='0.0.0.0', use_reloader=False, debug=False)

