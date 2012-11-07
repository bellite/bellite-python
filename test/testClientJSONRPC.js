/*-*- coding: utf-8 -*- vim: set ts=4 sw=4 expandtab
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2012 Bellite.io                            ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the MIT style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##*/

"use strict";
function createMockBelliteServer(ns) {
    var self = {
        server: require('net').createServer(),
        token: require('crypto').randomBytes(8).toString('hex'),
        shutdownTest: function() {
            self.shutdownTest = null;
            if (self.server)
                self.server.close();
            self.allConnections.forEach(function(conn){
                if (conn) conn.end() }) },
        allConnections: [] }

    self.server.on('listening', function () {
        var addr = this.address()
        self.env = addr.address+':'+addr.port+'/'+self.token
        process.env.BELLITE_SERVER = self.env
        ns.listening();
    })

    self.server.on('connection', function (conn) {
        self.allConnections.push(conn)
        conn.setEncoding("UTF-8");
        conn.setNoDelay(true);
        conn.setKeepAlive(true, 0);

        var api = {
            sendMessage: function(msg) {
                return conn.write(msg+'\0') },
            shutdown: function() { return conn.end() },
            fireEvent: function(evtType, selfId, evt, ctx) {
                return this.send('event', {evtType: evtType, selfId: selfId||0, evt:evt, ctx:ctx}) },
            send: function(method, params, id) {
                var msg = {jsonrpc: "2.0", id:id, method:method, params:params}
                return this.sendMessage(JSON.stringify(msg)) },
            answer: function(result, id) {
                if (id===undefined) return false;
                var msg = {jsonrpc: "2.0", id:id, result:result}
                return this.sendMessage(JSON.stringify(msg)) },
            error: function(error, id) {
                if (id===undefined) return false;
                var msg = {jsonrpc: "2.0", id:id, error:error}
                return this.sendMessage(JSON.stringify(msg)) },
            checkAuth: function(token) {
                clearTimeout(authTimeout);
                return this.authorized = (token == self.token) }
            },
            tgt = ns.connect(api),
            authTimeout = setTimeout(api.shutdown, 250);

        var connBuf='';
        conn.on('data', function(data) {
            data = (connBuf+data).split('\0')
            connBuf = data.pop()
            while (data.length) {
                var msg = data.shift();
                try { msg = JSON.parse(msg) }
                catch (err) { tgt.parse_error(err, msg); continue }
                if (msg.method!==undefined)
                    tgt.invoke(msg)
                else tgt.response(msg)
            } })
        conn.on('close', function() { tgt.conn_close() })
        conn.on('error', function(err) { tgt.conn_error(err) })
    })

    self.server.on('close', function() { 
        self.server = null; ns.server_close() })
    self.server.on('error', function(err) {
        ns.server_error(err) })

    self.server.listen(0, '127.0.0.1')
    return self;
}

//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

function testBelliteServer(opt, doneCallback) {
    opt.log = opt.log || {};
    function log(key, args) {
        var log=opt.log[key];
        if (!log) opt.log[key] = log = []
        var ea = Array.prototype.slice.call(arguments, 1);
        if (ea.length<2) ea = ea[0]===undefined ? 0 : ea[0];
        log.push(ea)
        return this }

    var rpc = {
        connect: function(api) {
            log('connect')
            this.api = api;
            this.evtCtx = {}
            return this },
        conn_close: function() { log('conn_close') },
        conn_error: function(err) { log('conn_error', err) },
        parse_error: function(err,msg) { log('parse_error', err, msg) },
        response: function(msg) { log('response', msg) },
        invoke: function(msg) {
            var pre = this.api.authorized ? 'meth_' : 'meth0_';
            var meth = this[pre+msg.method] || this.meth_unknown;
            log('invoke', pre+msg.method, msg.params)
            return meth.call(this, msg.params, msg)},

        meth_unknown: function(args, msg) {
            log('meth_unknown', msg.method, args)
            this.api.answer(["unknown method ", null], msg.id) },
        meth_ping: function(args, msg) {
            log('meth_ping', args)
            this.api.answer([null, true, "pong"], msg.id) },
        meth_version: function(args, msg) {
            log('meth_version', args)
            this.api.answer([null, {"server":"bellite", "version":"1.4.3", "platform":"node/test"}], msg.id) },

        meth0_ping: function(args, msg) { this.meth_ping(args, msg) },
        meth0_version: function(args, msg) { this.meth_version(args, msg) },
        meth0_auth: function(args, msg) {
            log('meth_auth', args)
            if (this.api.checkAuth(args[0])) {
                log('authorize', true)
                this.api.answer([null, true, "authorized"], msg.id)
            } else {
                log('authorize', false)
                this.api.error({code:401, message:"Unauthorized"}, msg.id)
                this.api.shutdown()
            } },

        meth_bindEvent: function(args, msg) {
            log('meth_bindEvent', args)
            this.evtCtx[args[1]] = args[3]
            this.api.answer([null, true], msg.id) },
        meth_unbindEvent: function(args, msg) {
            log('meth_unbindEvent', args)
            this.api.answer([null, true], msg.id) },
        meth_perform: function(args, msg) {
            log('meth_perform', args)
            var self=this, cmd=this['cmd_'+args[1]] || this.cmd_mock
            cmd.call(this, args, function(res) {
                self.api.answer([null, res], msg.id) }) },

        cmd_mock: function(args, answer) {
            answer([null, {'a mock':'result'}]) },
        cmd_testEvent: function(args, answer) {
            log('cmd_testEvent', args)
            answer([null, true, 'firingTestEvent'])
            var resp = 'dyn_'+require('crypto').randomBytes(4).toString('hex')
            this['cmd_'+resp] = this.dynamic_response
            this.api.fireEvent('testEvent', 0, resp, this.evtCtx.testEvent) },
        dynamic_response: function(args, answer) {
            log('dynamic_response', args)
            answer([null, true, 'awesome'])
            this.api.fireEvent('testEvent', 0, null, this.evtCtx.testEvent) }
    };

    var test = createMockBelliteServer({
        listening: function() {
            opt.execClient(spawnClient) },
        server_close: function() {},
        server_error: function(err) { log('server_error', err) },
        connect: function(api) {
            return Object.create(rpc).connect(api) }
    })

    function spawnClient(exec, args) {
        var cp = require('child_process'),
            proc = cp.spawn(exec, args, {stdio:'inherit'})
        proc.on('exit', function(code, signal) {
            log('process_exit', code, signal)
            done(code!==0 ? 'subprocess spawning error' : null) })
        return proc }

    function done(err) {
        clearTimeout(done.timer);
        if (test.shutdownTest) {
            test.shutdownTest()
            setTimeout(function() { doneCallback(err, opt.log, opt) }, 100)
        }}
    done.timer = setTimeout(function() {
        log('timeout'); done('timeout') }, opt.timeout || 2000)
}

//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

var assert=require('assert');

testBelliteServer({
    execClient: function(spawn) {
        spawn('python', [__dirname+'/_doBelliteTest.py'])
    },
    timeout: 2000,
}, function(err, log, opt) {
    try {
        assert.equal(err, null, "terminated with an error")

        assert.equal(log.connect.length, 1, "should connect exactly once")
        assert.equal(log.server_error, null, "should not experience server errors")
        assert.equal(log.conn_error, null, "should not experience connection errors")

        assert.equal(log.parse_error, null, "should not experience JSON parsing errors")
        assert.equal(log.response, null, "should not receive JSON-RPC 2.0 responses")

        assert.equal(log.meth_auth.length, 1, "should call auth exactly once")
        assert.deepEqual(log.authorize, [true], "should authorize successfully")

        assert.equal(log.meth_unknown, null, "should never call an unknown method")

        assert(log.meth_ping, [0], "should call ping once with no args")
        assert(log.meth_version, [0], "should call version once with no args")
        assert.equal(log.meth_perform.length, 3, "should call perform 3 times")
        assert.equal(log.meth_bindEvent.length, 2, "should call bindEvent 3 times")
        assert.equal(log.meth_unbindEvent.length, 1, "should call unbindEvent 2 times")

        assert.deepEqual(log.cmd_testEvent, [[0, 'testEvent', null]], "should call testEvent")
        assert.equal(log.dynamic_response.length, 1, "should call dynamic_response from event")

        console.log("All Bellite JSON-RPC protocol tests passed")
        process.exit(0) // success

    } catch(test_err) {
        console.log('\nBellite Mock Server Call Log:')
        console.log(log)
        console.log('\n')

        console.error(test_err.stack.split(/\n\s*/).slice(0,2).join('\n'))
        console.error(test_err)
        console.error()

        process.exit(1) // failure
    }
})
