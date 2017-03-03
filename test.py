# -*- coding: UTF-8 -*-
# import requests
#
# params = {'leftTicketDTO.train_date':'2017-03-03',
#           'leftTicketDTO.from_station':'HBB', 'leftTicketDTO.to_station':'KMM',
#           'purpose_codes':'ADULT'}
# #
# # r = requests.get('https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date='+'2017-03-03'
# #                  +'&leftTicketDTO.from_station='+'SHH'+'&leftTicketDTO.to_station='+'KMM'
# #                  +'&purpose_codes=ADULT', verify=False)
# r = requests.get('https://kyfw.12306.cn/otn/leftTicket/query',params=params,verify=False)
# print r.content


import random
from time import sleep
from Queue import Queue, Empty
import threading
import time

lock = threading.Lock()
MAX_THREADS = 2
q = Queue()
count = 0

# 锁以外的io
def io_process(x):
    pass

# 需要被锁的操作
def shared_resource_process(x):
    pass

def func():
    global q, count
    while True:
        time.sleep(0.1)
        try:
            x = q.get(False)
        except Empty:
            break
        io_process(x)
        if lock.acquire():
            shared_resource_process(x)
            print '%s is processing %r' %(threading.currentThread().getName(), x)
            count += 1
            q.task_done()  # 这一行不加 有时候主程序不能结束
            lock.release()

def main():
    global q
    for i in range(40):
        q.put(i)

    threads = []
    for i in range(MAX_THREADS):
        threads.append(threading.Thread(target=func))

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print 'multi-thread done.'
    print count == 40

if __name__ == '__main__':
    main()