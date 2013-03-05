# -*- coding: utf-8 -*- vim: set ts=4 sw=4 expandtab
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2013 Bellite.io                            ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the MIT style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

import os, sys, socket, json
from collections import OrderedDict
from functools import partial
import asyncore

class BelliteJsonRpcApi(object):
    def __init__(self, cred=None):
        self.connect(cred)

    def auth(self, token):
        return self._invoke('auth', [token])
    def version(self):
        return self._invoke('version')
    def ping(self):
        return self._invoke('ping')
    def respondsTo(self, selfId, cmd):
        return self._invoke('respondsTo', [selfId or 0, cmd])
    def perform(self, selfId, cmd, *args, **kw):
        if args and kw: raise ValueError("Cannot specify both positional and keyword arguments")
        if len(args)==1 and isinstance(args[0], (list, dict, tuple)):
            args = args[0]
        elif not args: args = None
        return self._invoke('perform', [selfId or 0, cmd, kw or args])
    def bindEvent(self, selfId=0, evtType='*', res=-1, ctx=None):
        return self._invoke('bindEvent', [selfId or 0, evtType, res, ctx])
    def unbindEvent(self, selfId=0, evtType=None):
        return self._invoke('unbindEvent', [selfId or 0, evtType])

    def findCredentials(self, cred=None):
        if cred is None:
            cred = os.environ.get('BELLITE_SERVER')
            if not cred:
                cred = '127.0.0.1:3099/bellite-demo-host';
                print >>sys.stderr, 'BELLITE_SERVER environment variable not found, using "'+cred+'"'
        elif not isinstance(cred, basestring):
            return cred
        try:
            host, token = cred.split('/', 2)
            host, port = host.split(':', 2)
            return dict(credentials=cred, token=token, host=host, port=int(port))
        except ValueError:
            return None

    def connect(self, cred):
        cred = self.findCredentials(cred)
        if cred is not None:
            f_ready = deferred()
            self.ready = f_ready.promise
            self._connect(cred, f_ready)
            return self.ready

    def _connect(self, cred, f_ready):
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))
    def _invoke(self, method, params=None):
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BelliteJsonRpc(BelliteJsonRpcApi):
    def __init__(self, cred=None, logging=False):
        self._resultMap = {}
        self._evtTypeMap = {}
        self._logging = bool(logging)
        BelliteJsonRpcApi.__init__(self, cred)

    def _notify(self, method, params=None):
        return self._sendJsonRpc(method, params)
    _nextMsgId = 100
    def _invoke(self, method, params=None):
        msgId = self._nextMsgId
        self._nextMsgId = msgId + 1
        res = self._newResult(msgId)
        if not self._sendJsonRpc(method, params, msgId):
            res.reject(Exception('Bellite client not connected'))
        return res.promise
    def _newResult(self, msgId):
        res = deferred()
        self._resultMap[msgId] = res
        return res
    def _sendJsonRpc(self, method, params=None, msgId=None, separators=(',',':')):
        msg = OrderedDict(jsonrpc="2.0")
        if msgId is not None: msg['id'] = msgId
        msg['method'] = method
        if params is not None: msg['params'] = params
        self.logSend(msg)
        return self._sendMessage(json.dumps(msg,separators=separators))
    def _sendMessage(self, msg):
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))

    def logSend(self, msg):
        if self._logging:
            print 'send ==> ', json.dumps(msg)
    def logRecv(self, msg):
        if self._logging:
            print 'recv <== ', json.dumps(msg)

    def _recvJsonRpc(self, msgList):
        for msg in msgList:
            try:
                msg = json.loads(msg)
                isCall = 'method' in msg
            except ValueError:
                continue
            self.logRecv(msg)
            try:
                if isCall: self.on_rpc_call(msg)
                else: self.on_rpc_response(msg)
            except Exception:
                sys.excepthook(*sys.exc_info())
    def on_rpc_call(self, msg):
        if msg.get('method') == 'event':
            args = msg['params']
            self.emit(args['evtType'], args)
    def on_rpc_response(self, msg):
        tgt = self._resultMap.pop(msg['id'], None)
        if tgt is None: return
        if 'error' in msg:
            tgt.reject(msg['error'])
        elif msg['result'][0]:
            tgt.reject(msg['result'])
        else:
            tgt.resolve(msg.get('result'))

    def on_connect(self, cred, f_ready):
        self.emit('connect')
        self.auth(cred['token']) \
            .then(f_ready.resolve, f_ready.reject) \
            .then(self.on_auth_succeeded, self.on_auth_failed)
    def on_auth_succeeded(self, msg):
        self.emit('auth', True, msg)
        self.emit('ready')
    def on_auth_failed(self, msg):
        self.emit('auth', False, msg)

    #~ micro event implementation ~~~~~~~~~~~~~~~~~~~~~~~

    def on(self, key, fn=None):
        def bindEvent(fn):
            self._evtTypeMap.setdefault(key, []).append(fn)
            return fn
        if fn is None: return bindEvent
        else: return bindEvent(fn)
    def emit(self, key, arg=NotImplemented, extra=NotImplemented):
        for fn in self._evtTypeMap.get(key, ()):
            try:
                if arg is NotImplemented:
                    fn(self)
                elif extra is NotImplemented:
                    fn(self, arg)
                else:
                    fn(self, arg, extra)
            except Exception:
                sys.excepthook(*sys.exc_info())

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Bellite(BelliteJsonRpc):
    timeout_conn = 0.5
    timeout_send = 0.01
    timeout_recv = 1e-6
    conn = None
    _buf = ''

    def _connect(self, cred, f_ready):
        self.conn = socket.create_connection((cred['host'], cred['port']), self.timeout_conn)
        if self.conn: self.on_connect(cred, f_ready)

    def addAsyncMap(self, map=None):
        if map is None:
            map = asyncore.socket_map
    def loop(self, timeout=0.5):
        asyncore.loop(timeout, True, {self:self}, 1)
        return self.isConnected()

    def _sendMessage(self, msg):
        if not self.isConnected():
            return False
        self.conn.settimeout(self.timeout_send)
        self.conn.sendall(msg+'\0')
        return True
    def isConnected(self):
        return self.conn is not None
    def close(self):
        conn = self.conn; del self.conn
        if conn is None: return False
        try: conn.shutdown(socket.SHUT_RDWR)
        except socket.error: pass
        self.emit('close')
        return True

    # asyncore compatible api
    def fileno(self): return self.conn.fileno()
    def readable(self): return True
    def handle_read_event(self):
        if not self.isConnected():
            return False
        buf = self._buf
        self.conn.settimeout(self.timeout_recv)
        try: 
            while True:
                part = self.conn.recv(4096)
                if not part:
                    self.close()
                    break
                else: buf += part
        except socket.timeout: pass

        buf = buf.split('\0')
        self._buf = buf.pop()
        self._recvJsonRpc(buf)
        return True
    def writable(self): return False
    def handle_write_event(self): pass
    def handle_expt_event(self): self.close()
    def handle_close(self): self.close()
    def handle_error(self): sys.excepthook(*sys.exc_info())

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Fate promise/future (micro) implementation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class PromiseApi(object):
    def always(self, fn): return self.then(fn, fn)
    def fail(self, failure): return self.then(None, failure)
    def done(self, success): return self.then(success, None)

class Promise(PromiseApi):
    def __init__(self, then):
        if then is not None: self.then = then
    promise = property(lambda self: self)

class Future(PromiseApi):
    def __init__(self, then, resolve=None, reject=None):
        self.promise = Promise(then)
        if resolve is not None: self.resolve = resolve
        if reject is not None: self.reject = reject
    then = property(lambda self: self.promise.then)
    def resolve(self, result=None): pass
    def reject(self, error=None): pass

def deferred():
    cb = []; answer = None
    def then(success=None, failure=None):
        cb.append((success, failure))
        if answer is not None: answer()
        return self.promise
    def resolve(result):
        while cb:
            success, failure = cb.pop()
            try:
                if success is not None:
                    res = success(result)
                    if res is not None:
                        result = res
            except Exception as err:
                if failure is not None:
                    res = failure(err)
                elif not cb:
                    sys.excepthook(*sys.exc_info())
                if res is None:
                    return reject(err)
                else: return reject(res)
        answer = partial(resolve, result)
    def reject(error):
        while cb:
            failure = cb.pop()[1]
            try:
                if failure is not None:
                    res = failure(error)
                    if res is not None:
                        error = res
            except Exception as err:
                res = err
                if not cb:
                    sys.excepthook(*sys.exc_info())
        answer = partial(reject, error)

    self = Future(then, resolve, reject)
    return self


