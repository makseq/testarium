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

# command: setup.py sdist & twine upload dist/*

from subprocess import STDOUT, CalledProcessError, check_output as run
from setuptools import setup

def get_version():
    # take version from git
    try:
        desc = run('git describe --long --tags --always --dirty', stderr=STDOUT, shell=True)
    except CalledProcessError as e:
        print "cmd: %s\nError %s: %s" % (e.cmd, e.returncode, e.output)
        exit(-101)

    # check if everything is commited
    if 'dirty' in desc:
        print 'Current git description: %sError: please commit your changes' % desc
        exit(-100)

    # create package version
    version = desc.lstrip('v').rstrip().replace('-', '.')
    version = '.'.join(version.split('.')[0:-1])
    print 'Version:', version
    return version


data_files = [

    ('testarium/web/templates', ['main.html']),

    ('testarium/web/static/fonts',
     ['FontAwesome.otf',
      'FontAwesome.ttf',
      'fontawesome-webfont.eot',
      'fontawesome-webfont.svg',
      'fontawesome-webfont.ttf',
      'fontawesome-webfont.woff',
      'fontawesome-webfont.woff2',
      'Gudea-Bold.otf',
      'Gudea-Bold.ttf',
      'Gudea-Italic.otf',
      'Gudea-Italic.ttf',
      'Gudea-Regular.otf',
      'Gudea-Regular.ttf']),

    ('testarium/web/static/images', ['back.jpg']),

    ('testarium/web/static/scripts',
     ['d3.linegraph.js',
      'd3.v3.min.js',
      'jquery-ui.min.js',
      'jsrender.min.js',
      'jquery.mousewheel.min.js',
      'main.js',
      'wavesurfer.min.js',
      'wavesurfer.regions.js',
      'wavesurfer.spectrogram.js']),

    ('testarium/web/static/styles',
     ['main.css',
      'd3.linegraph.css',
      'jquery-ui.min.css',
      'font-awesome.css']),

    ('testarium/web/static', ['favicon.ico'])

]

setup(name='testarium',
      url='http://testarium.makseq.com',
      description='Research tool to perform experiments and store results in the repository. More: http://testarium.makseq.com',
      author='Max Tkachenko, Danila Doroshin, Alexander Yamshinin',
      author_email='makseq@gmail.com',
      license='GNU GPLv3',
      version=get_version(),
      packages=['testarium', 'testarium/score', 'testarium/web'],
      install_requires=['numpy', 'flask', 'colorama', 'pycrypto', 'argcomplete'],
      include_package_data=True,
      zip_safe=False,
      keywords=['testing', 'logging', 'research', 'science', 'repository'],
      classifiers=[
          "Topic :: Scientific/Engineering",
          "Development Status :: 3 - Alpha",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Intended Audience :: Science/Research"
      ]
      )
