/*-*- coding: utf-8 -*- vim: set ts=4 sw=4 expandtab
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2013 Bellite.io                            ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the MIT style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##*/

"use strict";
var test = require('./testClientJSONRPC.js');

test.testBelliteJSONRPC({
    debugLog: console.log,
    timeout: false,
    port: 3099,
    token: 'bellite-demo-host',

    execClient: function(spawn) {
        console.log('\n# Export environment varaible')
        console.log('set BELLITE_SERVER="'+process.env.BELLITE_SERVER+'"')

        console.log('\n# Run Belllite Client JSON-RPC')
        console.log('python "'+__dirname+'/_doBelliteTest.py'+'"')
    }
}, test.assetTestResults)

