# -*- coding: utf-8 -*- vim: set ts=4 sw=4 expandtab
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2012 Bellite.io                            ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the MIT style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../..')))

import bellite
app = bellite.Bellite(logging=True)

@app.ready
def appReady(app):
    app.ping()
    app.version()
    app.perform(142, "echo", {"name":[None, True, 42, "value"]})

    app.bindEvent(118, "*")
    app.unbindEvent(118, "*")

    @app.on('testEvent')
    def onTestEvent(app, eobj):
        if eobj.get('evt'):
            app.perform(0, eobj['evt'])
        else: app.close()

    app.bindEvent(0, "testEvent", 42, {'testCtx': True})
    app.perform(0, "testEvent")

while app.loop(): pass

