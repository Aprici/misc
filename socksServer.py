#!/usr/bin/python
import socket
import SocketServer
import sys
import select
import struct

'''
    Socks5 Proxy Server
    by dechang.xu
'''

class Socks5Server(SocketServer.StreamRequestHandler):
    def handle_tcp(self, sock, remote):
        while True:
            r, w, e = select.select([sock, remote], [], [])
            if (sock in r and remote.send(sock.recv(4096)) <= 0) or (remote in r and sock.send(remote.recv(4096)) <= 0):
                break
    def handle(self):
        try:
            sock = self.connection
            sock.recv(262)
            sock.send('\x05\x00');
            data = self.rfile.read(4)
            mode = ord(data[1])
            addrtype = ord(data[3])
            if addrtype == 1:
                addr = socket.inet_ntoa(self.rfile.read(4))
            elif addrtype == 3:
                addr = self.rfile.read(ord(sock.recv(1)[0]))
            port = struct.unpack('>H', self.rfile.read(2))
            reply = '\x05\x00\x00\x01'
            try:
                if mode == 1:
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.connect((addr, port[0]))
                else:
                    reply = '\x05\x07\x00\x01'
                local = remote.getsockname()
                reply += socket.inet_aton(local[0]) + struct.pack('>H', local[1])
            except socket.error:
                reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
            sock.send(reply)
            if reply[1] == '\x00' and mode == 1:
                self.handle_tcp(sock, remote)
        except socket.error,e:
            print >>sys.stderr,'socket error',e
        except Exception,e:
            print >>sys.stderr,e

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise
        address = sys.argv[1].split(':')
        if len(address) > 2:
            raise
        if len(address) == 1:
            ip = '0.0.0.0'
            port = int(address[0])
        else:
            ip,port = address
            port = int(port)
    except:
        print >>sys.stderr, 'Usage:\n\n %s [ip:]port\n\nThis is socks5 proxy server\nby dechang.xu\n'%sys.argv[0]
        sys.exit(1)
    try:
        server = ThreadingTCPServer((ip,port), Socks5Server)
    except Exception,e:
        print >>sys.stderr, e
        sys.exit(1)
    try:
        print 'listening on %s:%s'%(ip,port)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
