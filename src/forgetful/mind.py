import threading
import json
import time
from spoton.johny.connection import ConnectionFactory
from spoton.johny.logging import LoggingFactory
from spoton.johny.data import Sanitize
from spoton.johny.service import Service


class MindService(Service):
    DEFAULT_DB = 'default'
    DEFAULT_COL = 'default'
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_OID = '_id'
    DEFAULT_PORT = 27017
    FMT_UP = "mongodb://{username}:{password}@{host}:{port}"
    FMT_NUP = "mongodb://{host}:{port}"

    def __init__(self, pubs_subs={}, mongo_uri=None,
                 password=None, user=None, host=DEFAULT_HOST,
                 port=DEFAULT_PORT, default_db=DEFAULT_COL,
                 default_collection=DEFAULT_COL, log_info={}):

        log_info['logger_class'] = 'MindService'
        Service.__init__(log_info=log_info)
        self.logger = LoggingFactory.setup(log_info)

        uri_kargs = {
            'password': password,
            'user': user,
            'host': host,
            'port': port,
        }

        con_kargs = {
            'uri': mongo_uri,
            'default_db': default_db,
            'default_collection': default_collection,
        }

        if mongo_uri is None:
            if user is None or password is None:
                mongo_uri = self.FMT_NUP.format(**uri_kargs)
            else:
                mongo_uri = self.FMT_UP.format(**uri_kargs)

        self.mongo_conn = ConnectionFactory.create(**con_kargs)
        self.host = self.mongo_conn.host()
        self.port = self.mongo_conn.port()
        self.addr_s = "%s:%s" % (host, port)

        self.publishers = ConnectionFactory.create_pubs_subs(pubs_subs)

        self.out_queues = {}
        self.publishers = {}
        self.subscribers = {}

        for sub in self.publishers.values():
            for sub in self.publishers.subscribers():
                self.subscribers[sub.name()] = sub
                self.out_queues[sub.name()] = []

        self.out_qt = None
        self.in_qt = None
        self.keep_queue_master_alive = False

    def start_queue_masters(self, sleep_time=2.0):
        self.keep_queue_master_alive = True
        self.out_qt = threading.Thread(target=self.fn_out_queue_thread,
                                       args=(sleep_time, ))
        self.in_qt = threading.Thread(target=self.fn_in_queue_thread,
                                      args=(sleep_time, ))
        self.out_qt.start()
        self.in_qt.start()

    def stop_queue_masters(self, sleep_time=5.0):
        self.keep_queue_master_alive = False

    def fn_out_queue_thread(self, sleep_time):
        while self.keep_queue_master_alive:
            self.read_publisher_queues()
            time.sleep(sleep_time)

    def fn_in_queue_thread(self, sleep_time):
        while self.keep_queue_master_alive:
            self.clear_subscriber_queues()
            time.sleep(sleep_time)

    def read_publisher_queues(self):
        for name, pub in self.publishers.items():
            # trying to capture the name of the publisher
            def callback(self, msg, pub_name=name):
                self.handle(pub_name, msg)

            pub.read_messages(cnt=100, callback=callback)

    def clear_subscriber_queues(self):
        for name in self.out_queues:
            if len(self.out_queues[name]) == 0:
                continue

            queue = self.out_queues[name]
            msgs = []
            while len(queue) > 0:
                msgs.append(queue.pop(0))
            sub_con = self.subscribers[name]
            sub_con.send_messages(msgs)


    def insert(self, save_db, save_col, msg,
               check_id=True, oid=DEFAULT_OID):
        db = self.mongo_conn[save_db]
        col = db[save_col]

        failed_check = True
        if check_id and oid in msg:
            objs = [i for i in col.find({'_id': msg[oid]}).limit(1)]
            failed_check = len(objs) == 0

        if failed_check:
            return True, col.insert_one(msg).inserted_id

        x = [i for i in col.find({'_id': msg['_id']}).limit(1)][0]
        return False, x['_id']

    def handle(self, pub_name, msg):
        meta = self.publishers.get('pub_name', {})
        handle_kargs = {}
        handle_kargs['save_db'] = meta.get('save_db', self.DEFAULT_DB)
        handle_kargs['save_col'] = meta.get('save_col', self.DEFAULT_COL)
        handle_kargs['oid'] = meta.get('oid', self.DEFAULT_OID)
        handle_kargs['check_id'] = meta.get('check_id', True)
        del_id = meta.get('check_id', True)

        mongo_data = msg
        if isinstance(msg, str):
            try:
                mongo_data = json.loads(msg)
            except:
                mongo_data = {'data': mongo_data}

        Sanitize.untrusted_dict(msg)

        added, _id = self.insert(**handle_kargs)
        handle_kargs['id'] = _id
        handle_kargs['addr'] = self.addr_s
        f_lmsg = "Failed: Insert {id} into {addr}:({save_db}[{save_col}])"
        s_lmsg = "Success: Insert {id} into {addr}:({save_db}[{save_col}])"

        if added:
            self.logger.log(s_lmsg.format(**handle_kargs))
        else:
            self.logger.log(f_lmsg.format(**handle_kargs))

        if del_id and meta['oid'] in msg:
            del msg[meta['oid']]

        # add messages to out queues
        pub = self.publishers[pub_name]
        for sub in pub.subscribers():
            self.out_queues[sub.name()].append()

    def start_service(self):
        pass

    def setup_logging(self):
        pass

    @classmethod
    def parser(cls, toml_file):
        pass
