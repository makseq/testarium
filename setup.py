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

# pypi upload command: setup.py sdist & twine upload dist/*

import testarium as package
import setuptools

# advanced files
files = [
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

# read description
with open("README.md", "r") as fh:
    long_description = fh.read()

# read side packages
with open('requirements.txt') as f:
    required = f.read().splitlines()

# setuptools setup
setuptools.setup(name=package.__name__,
                 version=package.__version__,
                 author=package.__author__,
                 author_email=package.__email__,
                 description=package.__description__,
                 url=package.__url__,

                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 license='GNU GPLv3',

                 packages=setuptools.find_packages(),
                 install_requires=required,
                 include_package_data=True,
                 zip_safe=False,
                 keywords=['testing', 'logging', 'research', 'science', 'repository'],
                 classifiers=[
                     "Topic :: Scientific/Engineering",
                     "Development Status :: 3 - Alpha",
                     "Operating System :: OS Independent",
                     "Programming Language :: Python",
                     "Intended Audience :: Science/Research"
                 ])
