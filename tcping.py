#!/usr/bin/env python
'''
    by Dechang.Xu
'''
import sys
import socket
import time
import optparse 

usage = "usage: %prog [options] host:port"
parser = optparse.OptionParser(usage=usage)
parser.add_option('-c','--count',dest='count',type=int,default='4',help='stop after sending count requests, default 4')
parser.add_option('-w','--wait',dest='timeout',default=2.0,type=float,help='time to wait for a response, default 2(s)')
parser.add_option('-i','--interval',dest='interval',default=1.0,type=float,help='wait interval seconds between sending each request, default 1(s)')
options,args = parser.parse_args()
try:
    if len(args) > 1:raise
    address,port = args[0].split(':')
    port = int(port)
except Exception:
    parser.print_help()
    sys.exit(1)
total_time = 0
success = 0
failure = 0
maxvalue = 0
minvalue = options.timeout
for i in xrange(options.count):
    try:
        tcpclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpclient.settimeout(options.timeout)
        starttime = time.time()
        tcpclient.connect((address,port))
        tcpclient.close()
        rtt = time.time() - starttime
        total_time += rtt
        success += 1
        if rtt > maxvalue:maxvalue = rtt
        if rtt < minvalue:minvalue = rtt
        print 'Connect %s:%i seq=%i time=%1.3f ms' %(address,port,i+1,rtt*1000)
        if i+1 < options.count and rtt < 1:time.sleep(options.interval-rtt)
    except Exception as e:
        try:
            failure += 1
            tcpclient.close()
            rtt = time.time() - starttime
            print 'Connect %s:%i seq=%i %s' %(address,port,i+1,e)
            if rtt < 1:time.sleep(options.interval-rtt)
        except KeyboardInterrupt:
            break
    except KeyboardInterrupt:
        break

try:
    failure_ratio = float(failure)/float(success+failure)
except ZeroDivisionError:
    failure_ratio = 0
try:
    avg = total_time/success
except ZeroDivisionError:
    avg = 0
print '\n--- %s:%i tcping statistics ---' % (address,port)
print '%i connection, %i establish, %i%% lost' % ((success+failure),success,failure_ratio*100)
if success:
    print 'rtt min/avg/max = %1.3f/%1.3f/%1.3f ms' % (minvalue*1000,avg*1000,maxvalue*1000)

