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

import os, sys, socket, string, random, base64, inspect

# import colorama
try:
    import colorama

    colorama.init();
    colored = True
except:
    colored = False

# import email
try:
    import smtplib
    from email.mime.text import MIMEText

    email = True
except:
    email = False

# encryption tools
try:
    import hashlib
    from Crypto.Cipher import AES
    from Crypto import Random

    encryption = True
except:
    encryption = False

# colors
COLOR_DICT = {
    'COLOR.GREEN': colorama.Fore.GREEN if colored else '',
    'COLOR.RED': colorama.Fore.RED if colored else '',
    'COLOR.YELLOW': colorama.Fore.YELLOW if colored else ''
}


# check and return graph url
def UrlGraph(string):
    if string[0:8] == 'graph://':
        return string
    else:
        return ''


# check and return file url
def UrlFile(string):
    if string[0:7] == 'file://':
        return string
    else:
        return ''


# time to str
def strtime(t):
    if t < 10:
        return '0' + str(t)
    else:
        return str(t)


# log with 't>' and color features
def log(*msg):
    if colored: sys.stdout.write(colorama.Style.BRIGHT)
    sys.stdout.write('t> ')

    reset = False
    for m in msg:
        if isinstance(m, basestring) and m in COLOR_DICT:
            if colored: sys.stdout.write(COLOR_DICT[m])
            reset = True
        else:
            try:
                sys.stdout.write(str(m))
            except:
                try:
                    sys.stdout.write(unicode(m))
                except Exception as e:
                    if hasattr(m, '__class__') and 'Commit' in str(m.__class__):
                        sys.stdout.write(m.name)
                    sys.stdout.write(' ! exception log: ' + repr(e))


            if reset and colored: sys.stdout.write(colorama.Fore.RESET)
            reset = False
            sys.stdout.write(' ')

    sys.stdout.write('\n')
    if colored:
        sys.stdout.write(colorama.Fore.RESET + colorama.Back.RESET + colorama.Style.RESET_ALL)


# log without 't>' and colors
def log_simple(*msg):
    if colored: sys.stdout.write(colorama.Style.BRIGHT)
    for m in msg:
        sys.stdout.write(str(m))
        sys.stdout.write(' ')
    sys.stdout.write('\n')
    if colored:
        sys.stdout.write(colorama.Fore.RESET + colorama.Back.RESET + colorama.Style.RESET_ALL)


# log line by line with color mapping
def log_lines(msg, insertTab=True):
    lines = msg.split('\n')
    for c in xrange(len(lines)):
        s = '\t' if insertTab else ''

        if colored:
            if c % 2 == 0:
                s += colorama.Fore.GREEN + lines[c]
            else:
                s += colorama.Fore.CYAN + lines[c]
            s += colorama.Style.RESET_ALL
        else:
            s += lines[c]
        s += '\n'
        sys.stdout.write(s)
    if colored:
        sys.stdout.write(colorama.Fore.RESET + colorama.Back.RESET + colorama.Style.RESET_ALL)


# log python exception
def log_exception(e):
    lines = e.split('\n')

    for l in lines[3:-2]:  # skip testarium traceback stuff
        if colored:
            if l[0:6] == '  File':
                l = l.replace('line', 'line' + colorama.Fore.YELLOW)
                l = l.replace(' in ', colorama.Style.RESET_ALL + ' in ' + colorama.Fore.YELLOW + colorama.Style.BRIGHT)
                l += colorama.Style.RESET_ALL
            else:
                l = colorama.Style.BRIGHT + colorama.Fore.RED + l + colorama.Style.RESET_ALL
        sys.stdout.write(l + '\n')


# create dir
def create_dir(d, ex=False):
    try:
        os.mkdir(d)
        return False
    except:
        if ex:
            log('Error:', d, ' is not empty, exit')
            return True


def try_del(dict_, key):
    try:
        del dict_[key]
    except:
        pass


def try_get(dict_, key, default=None):
    try:
        return dict_[key]
    except:
        return default


# --- E-Mail tools -------------------------------------------------------------
def makehtml(body):
    # css style
    s = '<html><head><style> .even {background: #EEE;} .odd {background: #FFF;} ' \
        'h1 {font-size:150%;} td {padding: 5px 10px;} </style></head>'
    s += '<body>\n'
    s += body
    s += '\n</body></html>'

    # f = open('tmp.html', 'w')
    # f.write(s)
    return s


# format commits to email
def commits2html(header, results):
    # header text
    s = '<h1>' + header + '</h1><br/>'
    if len(results) == 0: return s + 'No commits'

    # body
    body = ''
    trueCols = []
    count = 0
    for c in results:
        if not c[0]: body += '<tr>Totally broken experiment</tr>'; continue
        cols, out = c[0].Print()
        body += '<tr style="' + ('background:#EEE;' if count % 2 == 0 else '') + (
            'color:#A00' if not out else '') + '">'
        if not out:
            out = [c[0].name, 'failed commit', c[0].desc['params']]
        else:
            trueCols = cols
        for o in out: body += '<td>' + str(o) + '</td>'
        body += '</tr>'
        count += 1

    # header
    s += '<table><tbody>'
    s += '<tr>'
    for h in trueCols: s += '<th>' + str(h) + '</th>'
    s += '</tr>'
    s += body
    s += '</tbody></table>'
    s += '<br/><br/>'
    return s


# Support func for ProxySMTP
def recvline(sock):
    stop = 0
    line = ''
    while True:
        i = sock.recv(1)
        if i == '\n': stop = 1
        line += i
        if stop == 1:
            break
    return line


# SMTP over Proxy
class ProxySMTP(smtplib.SMTP):
    def __init__(self, host='', port=0, p_address='', p_port=0, local_hostname=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """Initialize a new instance.

        If specified, `host' is the name of the remote host to which to
        connect.  If specified, `port' specifies the port to which to connect.
        By default, smtplib.SMTP_PORT is used.  An SMTPConnectError is raised
        if the specified `host' doesn't respond correctly.  If specified,
        `local_hostname` is used as the FQDN of the local host.  By default,
        the local hostname is found using socket.getfqdn().

        """
        self.p_address = p_address
        self.p_port = p_port

        self.timeout = timeout
        self.esmtp_features = {}
        self.default_port = smtplib.SMTP_PORT
        if host:
            (code, msg) = self.connect(host, port)
            if code != 220:
                raise Exception("Proxy connection failed: code: " + str(code) + ' ' + str(msg))
        if local_hostname is not None:
            self.local_hostname = local_hostname
        else:
            # RFC 2821 says we should use the fqdn in the EHLO/HELO verb, and
            # if that can't be calculated, that we should use a domain literal
            # instead (essentially an encoded IP address like [A.B.C.D]).
            fqdn = socket.getfqdn()
            if '.' in fqdn:
                self.local_hostname = fqdn
            else:
                # We can't find an fqdn hostname, so use a domain literal
                addr = '127.0.0.1'
                try:
                    addr = socket.gethostbyname(socket.gethostname())
                except socket.gaierror:
                    pass
                self.local_hostname = '[%s]' % addr
        smtplib.SMTP.__init__(self)

    def _get_socket(self, port, host, timeout):
        # This makes it simpler for SMTP_SSL to use the SMTP connect code
        # and just alter the socket connection bit.
        if self.debuglevel > 0: print>> stderr, 'connect:', (host, port)
        new_socket = socket.create_connection((self.p_address, self.p_port), timeout)
        new_socket.sendall("CONNECT {0}:{1} HTTP/1.1\r\n\r\n".format(port, host))
        for x in xrange(2): recvline(new_socket)
        return new_socket


# send email
def send_email(whom, username, password, subject, text, smtp_host='smtp.gmail.com', smtp_port=587, proxy='',
               porta=8080):
    if not email: log('COLOR.RED', "Can't import smtplib or email, can't send an email")

    msg = MIMEText(text, 'html')
    msg['Subject'] = subject
    msg['To'] = whom

    log('Using', smtp_host, 'and', smtp_port, 'port')
    if proxy:
        log('Using proxy:', proxy, porta)
        s = ProxySMTP('smtp.gmail.com', smtp_port, proxy, porta)
    else:
        s = smtplib.SMTP('smtp.gmail.com', smtp_port)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(username, password)

    s.sendmail(username, [whom], msg.as_string())
    s.quit()


# --- Encryption / Decryption --------------------------------------------------
class TestariumCipherAES:
    def key_generator(self, size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(size))

    def error_and_exit(self):
        log('COLOR.RED',
            'Please, install hashlib and pycrypto to use encrytion (need to store passwords and other important info)')
        exit(-1010)

    def __init__(self):
        if not encryption: self.error_and_exit()

        self.bs = 256
        self.key = None
        keyfile = os.path.expanduser('~') + '/testarium.key'
        if os.path.exists(keyfile):
            self.key = str()
            self.key = open(keyfile, 'rb').read()

        if not self.key:
            key = self.key_generator(256)
            self.key = hashlib.sha256(key.encode()).digest()
            open(keyfile, 'wb').write(self.key)
            os.chmod(keyfile, 0500)
            log('Cipher AES: Testarium keyfile created:', 'COLOR.GREEN', keyfile)

    def encrypt(self, raw):
        if not encryption: self.error_and_exit()

        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        if not encryption: self.error_and_exit()

        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        if not encryption: self.error_and_exit()
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]
