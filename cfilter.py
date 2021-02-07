from cuckoo.filter import ScalableCuckooFilter
import os
import pickle
import signal
from functools import partial
import sys
import zerorpc
import itertools
import systemd.daemon

configpath = "config.ini"
class cfilter():
    def __init__(self, file = "filter.pkl", initial_capacity=1000000, error_rate=0.000001, bucket_size=6):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.bucket_size = bucket_size
        self.cuckoo = ScalableCuckooFilter(self.initial_capacity, self.error_rate, self.bucket_size)
        self.cuckoofile = file
        if os.path.exists(self.cuckoofile):
            with open(self.cuckoofile, "rb") as f:
                self.cuckoo.filters = pickle.load(f)
        self.save()
    def isexist(self, pid, page = 0):
        filterkey = "%s.%s" % (pid, page)
        return self.cuckoo.contains(filterkey)
    def insert(self, pid, page = 0):
        filterkey = "%s.%s" % (pid, page)
        return self.cuckoo.insert(filterkey)
    def clear(self):
        self.cuckoo.__init__(self.initial_capacity, self.error_rate, self.bucket_size)
        self.save()
    def delete(self, pid, page = 0):
        filterkey = "%s.%s" % (pid, page)
        return self.cuckoo.delete(filterkey)
    def __del__(self):
        self.save()
    def save(self):
        with open(self.cuckoofile, "wb") as f:
            pickle.dump(self.cuckoo.filters,f,0)


if __name__ == '__main__':
    from configparser import ConfigParser
    config = ConfigParser()
    config.read(configpath,encoding="utf-8")
    inscfilter = cfilter(config["cuckoo"]["file"], config["cuckoo"].getint("initial_capacity"), config["cuckoo"].getfloat("error_rate"), config["cuckoo"].getint("bucket_size"))
    s = zerorpc.Server(inscfilter, heartbeat=None)
    s.bind("tcp://0.0.0.0:" + config["cuckoo"]["port"])
    def exitx():
        old_int_hnd.cancel()
        zerorpc.gevent.signal(signal.SIGINT, partial(sys.exit, signal.SIGINT))
        old_term_hnd.cancel()
        zerorpc.gevent.signal(signal.SIGTERM, partial(sys.exit, signal.SIGTERM))
        s.stop()
        zerorpc.gevent.sleep(1)
        s.close()
        inscfilter.save()
        sys.exit(0)
    
    old_int_hnd = zerorpc.gevent.signal(signal.SIGINT, exitx)
    old_term_hnd = zerorpc.gevent.signal(signal.SIGTERM, exitx)
    
    try:
        zerorpc.gevent.spawn(s.run)
        systemd.daemon.notify(systemd.daemon.Notification.READY)
        for c in itertools.count(1):
            zerorpc.gevent.sleep(60)
            inscfilter.save()
    except KeyboardInterrupt:
        print("Received a request to terminate the server by KeyboardInterrupt!")
        exitx()