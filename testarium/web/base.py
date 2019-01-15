"""
Testarium
Copyright (C) 2018 Maxim Tkachenko

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
from flask import *
import traceback as tb
import json  # it MUST be included after flask!
import logging

log = logging.getLogger()


# check english letters
def is_english(s):
    try: s.encode('ascii')
    except: return False
    else: return True


# answer for api
def answer(status=0, msg="", result=None):
    if status == 0 and not msg and result is None:
        status = -1000
        msg = "nothing happened"

    a = {"status": status, "msg": msg}
    a.update({'request': request.args})

    if result is not None: a.update({"result": result})
    return json.dumps(a, indent=2)


# make an answer as exception
class AnswerException(Exception):
    def __init__(self, status, msg='', result=None):
        self.status, self.msg, self.result = status, msg, result
        self.answer = answer(status, msg, result)
        Exception.__init__(self, self.answer)


# check absent list of arguments in request
def get_args(args):
    one = False
    if isinstance(args, str):
        args = [args]
        one = True

    absent_args = [a for a in args if a not in request.args]
    if absent_args:
        raise AnswerException(400, 'No argument in request: ' + ', '.join(absent_args))
    else:
        if one:
            return request.args[args[0]]
        else:
            return [request.args[a] for a in args]


# standard exception treatment for any api function
def exception_treatment(f):
    def exception_f(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except AnswerException, e:
            traceback = tb.format_exc()
            log.critical('\n\n--------------\n' + traceback + '--------------\n')

            if 'traceback' not in e.result:
                e.result['traceback'] = traceback
            if hasattr(exception_f, 'request_id') and not e.result['request_id']:
                e.result['request_id'] = exception_f.request_id
            return answer(e.status, e.msg, e.result)

        except Exception as e:
            traceback = tb.format_exc()
            log.critical('\n\n--------------\n' + traceback + '--------------\n')

            body = {'traceback': traceback}
            if hasattr(exception_f, 'request_id'):
                body['request_id'] = exception_f.request_id
            return answer(501, 'critical exception', body)

    exception_f.__name__ = f.__name__
    return exception_f
