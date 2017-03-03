# -*- coding: UTF-8 -*-

import json
import threading
from collections import OrderedDict
from Queue import Queue, Empty
from time import clock
from warnings import filterwarnings

import requests
from prettytable import PrettyTable
from requests.packages import urllib3

from TrainInfo import TrainInfo
from my_tools import valid_date, get_station_code, build_query_url


global train_info_ordered_dict
global task_queue
count = 0
MAX_THREAD_NUM = 16
lock = threading.Lock()

ticket_price_mapping = {'z1' : 'M', 'z2' : 'O', 'wr' : 'A4', 'wy' : 'A3', 'zy' : 'A1', 'zw' : 'WZ'}


def get_list_raw(from_station_name, to_station_name, ride_date):
    # 将输入地名转换为 余票查询所使用的 站点代码
    with open('station_name.data') as f:
        content = f.read()
        from_station_code = get_station_code(from_station_name, content)
        to_station_code = get_station_code(to_station_name, content)

    base_urls = ['https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date=',
                 '&leftTicketDTO.from_station=',
                 '&leftTicketDTO.to_station=',
                 '&purpose_codes=']
    args = (ride_date, from_station_code, to_station_code, 'ADULT')
    left_ticket_query_url = build_query_url(base_urls, args)

    try:
        r = requests.get(left_ticket_query_url, verify=False)
    except Exception:
        exit(1)
    src = r.content
    content = json.loads(src)
    data = content['data']
    train_list_raw = [x['queryLeftNewDTO'] for x in data]

    return train_list_raw

def init_result_ordered_dict(train_list_raw):
    global train_info_ordered_dict
    train_info_ordered_dict = OrderedDict()
    for train in train_list_raw:
        if train['controlled_train_flag'] == '0':  # 0代表正常车次    1为停运车次 不处理
            train_id = train['station_train_code']
            from_station_name = train['from_station_name']
            to_station_name = train['to_station_name']
            start_time = train['start_time']
            arrive_time = train['arrive_time']
            time_lapse = train['lishi']

            train_info_ordered_dict[train_id] = TrainInfo(train_id, from_station_name, to_station_name,
                                                          start_time, arrive_time, time_lapse)

def price_network_process(train):
    if train['controlled_train_flag'] == '0':
        train_no = train['train_no']
        seat_type = train['seat_types']
        from_station_no = train['from_station_no']
        to_station_no = train['to_station_no']
        raw_train_date = train['start_train_date']
        train_date = raw_train_date[0:4] + '-' + raw_train_date[4:6] + '-' + raw_train_date[6:]

        base_urls = ['https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=',
                     '&from_station_no=', '&to_station_no=', '&seat_types=', '&train_date=']
        args = (train_no, from_station_no, to_station_no, seat_type, train_date)
        price_query_url = build_query_url(base_urls, args)

        try:
            src = requests.get(price_query_url, verify=False).content
        except Exception:
            print 'fail to get the ticket info of train %s' %train_no
            return None
        content = json.loads(src)['data']
        ticket_info_dict = OrderedDict()

        ticket_info_dict['z1'] = (train['zy_num'], content.get(ticket_price_mapping['z1']))
        ticket_info_dict['z2'] = (train['ze_num'], content.get(ticket_price_mapping['z2']))
        ticket_info_dict['wr'] = (train['rw_num'], content.get(ticket_price_mapping['wr']))
        ticket_info_dict['wy'] = (train['yw_num'], content.get(ticket_price_mapping['wy']))
        ticket_info_dict['zy'] = (train['yz_num'], content.get(ticket_price_mapping['zy']))
        ticket_info_dict['zw'] = (train['wz_num'], content.get(ticket_price_mapping['zw']))

        return ticket_info_dict

    else:
        return None

def price_write_process(train, ticket_info):
    if train['controlled_train_flag'] == '0':
        global train_info_ordered_dict
        train_id = train['station_train_code']
        train_info_ordered_dict[train_id].set_ticket_info(ticket_info)

# 工作线程的工作函数
def t_ticket():
    global task_queue
    global count
    while True:
        try:
            train = task_queue.get(False)
        except Empty:
            break
        ticket_info = price_network_process(train)
        if lock.acquire():
            # print 'thread %s is writing' % threading.current_thread().getName()
            count += 1
            price_write_process(train, ticket_info)
            lock.release()

# 线程控制器
def process_ticket_info_all(train_list_raw):
    global task_queue
    task_queue = Queue()
    for train in train_list_raw:
        task_queue.put(train)
    threads = []

    # threads 列表的元素是线程 线程的方法是 t_ticket
    for i in range(MAX_THREAD_NUM):
        threads.append(threading.Thread(target=t_ticket))

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print 'Ticket info for all trains processed.'

# 用PrettyTable打印结果
def visualize():
    output = PrettyTable(['车次', '出发站', '到达站', '出发时刻', '到达时刻', '历时', '一等座', '二等座', '软卧', '硬卧', '硬座', '无座'])
    for item in train_info_ordered_dict.itervalues():
        output.add_row(item.add_to_table())
    print output

def main():
    from_station_name = raw_input('from: ')
    to_station_name = raw_input('to: ')
    ride_date = raw_input('date: ')

    filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
    start = clock()

    if valid_date(ride_date):

        train_list_raw = get_list_raw(from_station_name, to_station_name, ride_date)
        init_result_ordered_dict(train_list_raw)
        process_ticket_info_all(train_list_raw)
        visualize()

    else:
        pass

    finish = clock()
    print 'total executing time: %d seconds.' % (finish - start)


if __name__ == '__main__':
    main()