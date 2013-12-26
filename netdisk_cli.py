'''
Command line tool of mcloud(netdisk)!
'''
from xml.dom import minidom
import httplib
import SocketServer
import time
import sys
import os

class NDError(Exception):pass
class Structure(object):pass
class SocketShell(SocketServer.BaseRequestHandler):
    def __init__(self,request, client_address, server):
        self.pip = Structure()
        self.pip.write     = lambda x: self.request.sendall(x)
        self.pip.read      = lambda x: self.request.recv(x)
        self.pip.readline  = lambda  : self.request.recv(1024)
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
    def setup(self):
        self.request.settimeout(60)
    def handle(self):
        s = shell(stdout = self.pip,
                  stderr = self.pip,
                  stdin  = self.pip)
        try:
            s.run()
        except:
            pass

class shell(object):
    def __init__(self,
                 stdout=sys.stdout,
                 stderr=sys.stderr,
                 stdin =sys.stdin):
        self.stdout = Structure()
        self.stderr = Structure()
        self.stdin  = Structure()
        self.stdout.write = stdout.write
        self.stderr.write = stderr.write
        self.stdin.read = stdin.read
        self.stdin.readline = stdin.readline
        self.stdout.writeline = lambda x: self.stdout.write('%s\n'%x)
        self.stderr.writeline = lambda x: self.stderr.write('%s\n'%x)
        self.logged = False
        self.COMMANDS = {}
        self.root = '00019700101000000001'
        for k in dir(self):
            if k[:4] != 'cmd_':continue
            cmd = k[4:]
            method = getattr(self, k)
            self.COMMANDS[cmd] = method
            for alias in getattr(method, "aliases", []):
                self.COMMANDS[alias] = self.COMMANDS[cmd]

    def login(self):
        self.stdout.write('PLEASE ENTER THE NUMBER: ')
        msisdn = self.stdin.readline().strip()
        try:
            msisdn = int(msisdn)
            if msisdn < 13000000000 or msisdn > 19000000000:
                return
        except ValueError:
            return
        msisdn = str(msisdn)
        d = disk(msisdn)
        try:
            userid = d.getUserInfo()
            t,f = d.getDiskInfo()
            r = float(t-f)/float(t)
        except NDError,e:
            self.stderr.writeline('\33[0m\33[31m%s\33[0m'%e)
            return
        self.disk = d
        self.msisdn = msisdn
        self.userid = userid
        self.log = lambda x:logging.info('%s:%s'%(self.msisdn,x))
        self.cwd = Structure()
        self.cwd.name  = '/'
        self.cwd.cid   = self.root
        self.cwd.layer = 0 
        self.summaryCatalogList = {self.cwd.cid:self.cwd.name}
        self.summaryContentList = {}
        self.currentCatalogList = {}
        self.currentContentList = {}
        self.history = [{}]
        self.prompt = ''
        info = 'User: %s/%s Total: %4.1fGB Free: %5iMB Used: %4.2f%%'%(self.msisdn,self.userid,t/1024,f,r*100)
        info = [ x for x in info ]
        info.insert(int(r*len(info)),'\33[30m\33[47m')
        info.append('\33[0m')
        info = ''.join(info)
        self.stdout.writeline('%s'%info)
        self.logged = True
        self.log('login')
        self.changeDir('/')

    def changeDir(self,cname):
        if cname == '':return True
        layer = self.cwd.layer
        if cname == '/':
            cid = self.root
            layer = 0
        elif cname == '..':
            if layer > 0:
                layer -= 1
                cid = self.history[layer]
            else:
                layer = 0
                cid = self.history[0]
            cname = self.summaryCatalogList[cid]
        elif cname in self.currentCatalogList:
            cid = self.currentCatalogList[cname].cid
            layer += 1
        elif not cname in self.currentCatalogList:
            self.stderr.writeline('\33[0m\33[31mCannot access "%s": No such Directory\33[0m'%cname)
            return False
        try:
            self.history[layer] = cid
        except IndexError:
            self.history.append(cid)
        try:
            getdisk = self.disk.getDisk(cid)
        except NDError,e:
            self.stderr.writeline('\33[0m\33[31m%s\33[0m'%e)
            return False
        self.currentCatalogList,self.currentContentList = getdisk
        for k in self.currentContentList.keys():
            self.summaryContentList[self.currentContentList[k].cid] = k
        for k in self.currentCatalogList.keys():
            self.summaryCatalogList[self.currentCatalogList[k].cid] = k
        self.cwd.name = cname
        self.cwd.cid = cid
        self.cwd.layer = layer
        self.prompt = ''
        for i in range(self.cwd.layer+1):
            self.prompt = '%s%s/' %(self.prompt,self.summaryCatalogList[self.history[i]])
        self.prompt = '\33[32m%s@MCloud\33[0m:%s> '%(self.msisdn,self.prompt[1:])
        return True

    def cmd_clear(self,params):self.stdout.write('\33[0;0H\33[2J')
    def cmd_pwd(self,params):self.stdout.writeline('%s'%self.prompt.split(':')[1][:-2])
    def cmd_exit(self,params):self.logged = False
    cmd_exit.aliases = ['logout','quit']
    def cmd__post(self,params):
        url   = params[0]
        s_xml = ' '.join(params[1:])
        try:
            r = self.disk._post(url,s_xml)
            for i in r:self.stdout.writeline(i)
        except Exception,e:
            self.stderr.writeline(e)
    def cmd__komanda(self,params):
        try:
            stdin,stdout_err = os.popen4(' '.join(params))
            self.stdout.write(stdout_err.read())
        except Exception,e:
            self.stderr.writeline(e)
    def cmd_cd(self,params):
        if len(params) == 0:params=['/']
        params = params[0].split('/')
        if not params[0]:self.changeDir('/')
        for p in params:
            if not self.changeDir(p):break

    def cmd_lsut(self,params):
        utls = self.disk.qryUploadTaskInfo()
        m = 0
        for l in utls:
            t,s,i,n = l
            t = '%s-%s-%s %s:%s'%(t[:4],t[4:6],t[6:8],t[8:10],t[10:12])
            self.stdout.writeline('%s%10i %-27s %s'%(t,s,i,n))
            m += s
        self.stdout.writeline('Total: %s MB'%str(m/1024/1024))

    def cmd_ls(self,params):
        for i in self.currentCatalogList:
            t = self.currentCatalogList[i].ctime
            t = '%s-%s-%s %s:%s'%(t[:4],t[4:6],t[6:8],t[8:10],t[10:12])
            self.stdout.writeline('%s %10s %s/'%(t,' ',i))
        for i in self.currentContentList:
            t = self.currentContentList[i].ctime
            t = '%s-%s-%s %s:%s'%(t[:4],t[4:6],t[6:8],t[8:10],t[10:12])
            self.stdout.writeline('%s %10i %s'%(t,self.currentContentList[i].size,i))
        
    def cmd_get(self,params):
        clist = params
        if len(clist) == 1 and clist[0] == '*':
            clist = self.currentContentList.keys()
        for c in clist:
            if not c in self.currentContentList:
                self.stderr.writeline('\33[31mCannot access "%s": No such File\33[0m'%c)
                continue
            cid = self.currentContentList[c].cid
            try:
                url = self.disk.downloadRequest(cid)
            except NDError,e:
                self.stderr.writeline('\33[31m%s\33[0m'%e)
                continue
            self.stdout.writeline('\33[4m\33[34m%s\33[0m'%url)

    def cmd__cid(self,params):
        clist = params
        if len(clist) == 1 and clist[0] == '*':
            clist = self.currentCatalogList.keys() + self.currentContentList.keys()
        for c in clist:
            if c in self.currentContentList:
                self.stdout.writeline('%s  %s'%(self.currentContentList[c].cid,c))
            elif c in self.currentCatalogList:
                self.stdout.writeline('%s  %s/'%(self.currentCatalogList[c].cid,c))
            else:
                self.stderr.writeline('\33[31mCannot access "%s": No such file or directory\33[0m'%c)

    def cmd_help(self,params):
        self.stdout.write('''\
\33[33mUsage:
     cd  [Directory]  -- Change the Current Working Directory
     ls               -- List Files and Directories
     get [Files]      -- Get the Url of File
     lsut             -- List Upload Tasks
     pwd              -- Print Name of Working Directory
     clear            -- Clear the Screen
     exit/quit/logout -- Exit the MCloud
\33[0m
''')
    def run(self):
        self.login()
        while self.logged:
            self.stdout.write('\33[100D%s'%self.prompt)
            cmdlist = [i.strip() for i in self.stdin.readline().split()]
            self.log(' '.join(cmdlist))
            if not cmdlist:continue
            idx = 0
            while idx < (len(cmdlist) - 1):
                if cmdlist[idx][0] in ["'", '"']:
                    cmdlist[idx] = cmdlist[idx] + " " + cmdlist.pop(idx+1)
                    if cmdlist[idx][0] != cmdlist[idx][-1]:continue
                    cmdlist[idx] = cmdlist[idx][1:-1]
                idx += 1
            cmd = cmdlist[0]
            params = cmdlist[1:]
            if not cmd in self.COMMANDS:cmd = 'help'
            try:
                self.COMMANDS[cmd](params)
            except Exception,e:
                self.stderr.writeline(e)

class disk(object):
    def __init__(self,msisdn):
        self.msisdn = msisdn

    def _buildXml(self,root,keys):
        dom = minidom.getDOMImplementation().createDocument(None,root,None)
        rootnode = dom.documentElement
        for k in keys:
            node = dom.createElement(k[0])
            try:
                node.appendChild(dom.createTextNode(str(k[1])))
            except IndexError:
                pass
            rootnode.appendChild(node)
        dom.appendChild(rootnode)
        return dom.toxml()
    
    def _post(self,url,s_xml):
        u = url.split('/')
        u.remove('')
        if u[0] == 'http:':
            host,port = u[1].split(':')
            path = '/' + '/'.join(u[2:])
        else:
            host,port = '192.168.120.10',8080
            path = url
        conn =  httplib.HTTPConnection(host, port)
        headers = { "Content-type": "text/xml","Content-Length": str(len(s_xml))}
        conn.request('POST',path,'',headers)
        conn.send(s_xml)
        response = conn.getresponse()
        http_status,http_reason = response.status,response.reason
        r_xml = response.read()
        conn.close()
        if http_status != 200:raise NDError('HTTP RESULT %s:%s'%(http_status,http_reason))
        dom = minidom.parseString(r_xml)
        result = dom.getElementsByTagName('result')[0]
        resultCode = result.getAttribute('resultCode')
        if resultCode != '0':raise NDError('%s:%s'%(resultCode,result.getAttribute('desc')))
        return r_xml,dom

    def getUserInfo(self):
        keys = [['MSISDN',self.msisdn],['type',0]]
        result = self._post('/richlifeApp/devapp/IUser',self._buildXml('getUserInfo',keys))[1]
        self.userid = result.getElementsByTagName('userID')[0].childNodes[0].data
        return self.userid

    def downloadRequest(self,cid):
        keys = [['appName','MCloud'   ],
                ['MSISDN',self.msisdn ],
                ['contentID',cid      ],
                ['OwnerMSISDN'        ],
                ['entryShareCatalogID']]
        result = self._post('/richlifeApp/devapp/IUploadAndDownload',self._buildXml('downloadRequest',keys))[1]
        return result.getElementsByTagName('String')[0].childNodes[0].data

    def getDiskInfo(self):
        keys = [['MSISDN',self.msisdn]]
        result = self._post('/richlifeApp/devapp/IUser',self._buildXml('getDiskInfo',keys))[1]
        freeDiskSize = int(result.getElementsByTagName('freeDiskSize')[0].childNodes[0].data)
        diskSize = int(result.getElementsByTagName('diskSize')[0].childNodes[0].data)
        return diskSize,freeDiskSize

    def qryUploadTaskInfo(self):
        keys = [['account',self.msisdn]]
        xm,result = self._post('/richlifeApp/devapp/IUploadAndDownload',self._buildXml('qryUploadTaskInfo',keys))
        tasklist = result.getElementsByTagName('uploadInfo')
        filelist = []
        for t in tasklist:
            cname = t.getElementsByTagName('ctnName'  )[0].childNodes[0].data.encode('utf-8')
            cid   = t.getElementsByTagName('taskID'   )[0].childNodes[0].data.encode('utf-8')
            ctime = t.getElementsByTagName('timeStamp')[0].childNodes[0].data.encode('utf-8')
            size  = t.getElementsByTagName('ctnSize'  )[0].childNodes[0].data.encode('utf-8')
            filelist.append((ctime,int(size),cid,cname))
        return filelist

    def delUploadTask(self,taskID,fileName=''):
        keys = [['account',self.msisdn],
                ['taskID',      taskID],
                ['fileName',  fileName]]
        xm=self._post('/richlifeApp/devapp/IUploadAndDownload',self._buildXml('delUploadTask',keys))[0]
        print xm
        
    def getDisk(self,catalogid):
        keys = [['MSISDN', self.msisdn ],
                ['catalogID',catalogid ],
                ['entryShareCatalogID' ],
                ['filterType',0        ],
                ['contentType'         ],
                ['catalogSortType',0   ],
                ['contentSortType',0   ],
                ['sortDirection',0     ],
                ['startNumber',-1      ],
                ['endNumber'           ],
                ['channelList'         ]]
        result = self._post('/richlifeApp/devapp/ICatalog',self._buildXml('getDisk',keys))[1]
        catalogList = result.getElementsByTagName('catalogInfo')
        cl = {}
        fl = {}
        for c in catalogList:
            cname = c.getElementsByTagName('catalogName'     )[0].childNodes[0].data.encode('utf-8')
            cid   = c.getElementsByTagName('catalogID'       )[0].childNodes[0].data.encode('utf-8')
            ctime = c.getElementsByTagName('updateTime'      )[0].childNodes[0].data.encode('utf-8')
            pcid  = c.getElementsByTagName('parentCatalogId' )[0].childNodes[0].data.encode('utf-8')
            ci = Structure()
            ci.cid,ci.pcid,ci.ctime = cid,pcid,ctime
            cl[cname] = ci
        contentList = result.getElementsByTagName('contentInfo')
        for c in contentList:
            cname = c.getElementsByTagName('contentName'     )[0].childNodes[0].data.encode('utf-8')
            cid   = c.getElementsByTagName('contentID'       )[0].childNodes[0].data.encode('utf-8')
            ctime = c.getElementsByTagName('updateTime'      )[0].childNodes[0].data.encode('utf-8')
            pcid  = c.getElementsByTagName('parentCatalogId' )[0].childNodes[0].data.encode('utf-8')
            size  = c.getElementsByTagName('contentSize'     )[0].childNodes[0].data.encode('utf-8')
            ci = Structure()
            ci.name,ci.cid,ci.pcid,ci.ctime,ci.size = cname,cid,pcid,ctime,int(size)
            fl[cname] = ci
        return cl,fl

if __name__ == '__main__':
    try:
        if not sys.argv[1] in ('shell','listen'):
            raise Exception
    except Exception:
        sys.stderr.write('''
Usage: %s [param]

    shell          -- Open NetDisk Shell
    listen [port]  -- Listen on TCP Port(default 23333)

'''%sys.argv[0].split('/')[-1])
        sys.exit(1)
    if sys.argv[1] == 'shell':
        s = shell(stdout = sys.stdout,
                  stderr = sys.stderr,
                  stdin  = sys.stdin)
        try:s.run()
        except:pass
    if sys.argv[1] == 'listen':
        class SocketTCP(SocketServer.ThreadingTCPServer):
            allow_reuse_address = True
        try:port = int(sys.argv[2])
        except:port = 23333
        try:SocketTCP(('',port), SocketShell).serve_forever()
        except:pass
