# -*- coding: utf-8 -*- vim: set ts=4 sw=4 expandtab
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2012 Bellite.io                            ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the MIT style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

from distutils.core import setup

__version__ = '1.4.17'

setup(
    name='bellite', 
    version=__version__,
    license='MIT',
    author='Shane Holloway',
    author_email='shane@bellite.io',
    description='Deliver desktop applications on Mac OSX and Windows XP/7/8 using Bellite.io.',
    url='https://github.com/bellite/bellite-python',
    download_url='https://github.com/bellite/bellite-python.git',
    platforms=['win32', 'darwin', 'osx'],
    py_modules=['bellite'],

    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Operating System :: MacOS :: MacOS X',
        'Environment :: Web Environment',
        'Environment :: MacOS X :: Cocoa',
        'Operating System :: Microsoft :: Windows',
        'Environment :: Win32 (MS Windows)',
        'Topic :: Desktop Environment',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Development Status :: 4 - Beta'])


