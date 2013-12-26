'''
Operation network interface
'''
import subprocess as sp

class IFException(Exception):pass

class interface(object):
    def __init__(self,name):
        self.name = name
    def __getattr__(self,name):
        if name == 'ip':
            cp = sp.Popen(['ip','addr','show',self.name],stdout=sp.PIPE,stderr=sp.PIPE)
            rc = cp.wait()
            so,se = cp.communicate()
            if rc != 0:
                raise IFException(se)
            so = so.split()
            try:
                return so[so.index('inet')+1]
            except ValueError:
                return None
        if name == 'ip6':
            cp = sp.Popen(['ip','addr','show',self.name],stdout=sp.PIPE,stderr=sp.PIPE)
            rc = cp.wait()
            so,se = cp.communicate()
            if rc != 0:
                raise IFException(se)
            so = so.split()
            try:
                return so[so.index('inet6')+1]
            except ValueError:
                return None
        if name == 'ether':
            cp = sp.Popen(['ip','addr','show',self.name],stdout=sp.PIPE,stderr=sp.PIPE)
            rc = cp.wait()
            so,se = cp.communicate()
            if rc != 0:
                raise IFException(se)
            so = so.split()
            try:
                return so[so.index('link/ether')+1]
            except ValueError:
                return None
        raise AttributeError("'interface' object has no attribute '%s'"%(name))
    def __setattr__(self,name,value):
        if name == 'name':
            object.__setattr__(self,name,value)
        elif name == 'ip':
            cp = sp.Popen(['ifconfig',self.name,value],stdout=sp.PIPE,stderr=sp.PIPE)
            rc = cp.wait()
            so,se = cp.communicate()
            if rc != 0:
                raise IFException(se)
        elif name == 'ether':
            cp = sp.Popen(['ifconfig',self.name,'hw','ether',value],stdout=sp.PIPE,stderr=sp.PIPE)
            rc = cp.wait()
            so,se = cp.communicate()
            if rc != 0:
                raise IFException(se)
        else:
            raise AttributeError("'interface' object has no attribute '%s'"%(name))
    def ping(self,ip):
        cp = sp.Popen(['ping','-c1','-I',self.name,ip],stdout=sp.PIPE,stderr=sp.PIPE)
        rc = cp.wait()
        if rc == 0:
            return True

