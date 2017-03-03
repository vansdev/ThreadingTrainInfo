# -*- coding: UTF-8 -*-
import json
import threading
from collections import OrderedDict
from Queue import Queue, Empty
from time import clock
from warnings import filterwarnings

import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from prettytable import PrettyTable
from requests.packages import urllib3

from TrainInfo import TrainInfo
from my_tools import valid_date, get_station_code, build_query_url


global train_info_ordered_dict # 存储最终数据的有序字典  train_id:TrainInfo
count = 0
MAX_THREAD_NUM = 16
lock = threading.Lock() # 锁 控制线程对 有序字典 的写操作

# 用于获得 某 座型 在 price_query 的结果中(json解析得到的字典)对应的key 之后用得到的key查询票价
# 例如 一等座 在 price_query 返回的字典中 对应key 为 'M' 用'M'做key 可以查询一等座票价 然后加入余票信息字典
ticket_price_mapping = {'z1' : 'M', 'z2' : 'O', 'wr' : 'A4', 'wy' : 'A3', 'zy' : 'A1', 'zw' : 'WZ'}

# 构造train_list_raw 后续任务的基础
def get_list_raw(from_station_name, to_station_name, ride_date):
    # 将输入地名转换为站点代码
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

# 初始化  train_info_ordered_dict 该函数结束时  所有车次的信息(除票价外) 已经记录在 train_info_ordered_dict 中
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
# 线程中 网络I/O 部分的操作 得到某个车次的票价信息
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

# 线程中对共享数据  train_info_ordered_dict 的操作 更新某个车次的票价信息
def price_write_process(train, ticket_info):
    if train['controlled_train_flag'] == '0':
        global train_info_ordered_dict
        train_id = train['station_train_code']
        train_info_ordered_dict[train_id].set_ticket_info(ticket_info)

# 工作线程的工作函数
def t_ticket(train):
    global task_queue
    global count

    ticket_info = price_network_process(train)
    price_write_process(train, ticket_info)


# 线程控制器
def process_ticket_info_all(train_list_raw):


    futures = set()
    with ThreadPoolExecutor(multiprocessing.cpu_count() * 4) as executor:
        for train in train_list_raw:
            future = executor.submit(t_ticket, train)
            futures.add(future)

    try:
        for future in as_completed(futures):
            err = future.exception()
            if err is not None:
                raise err
    except KeyboardInterrupt:
        print 'Stopped by user.'



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

    filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning) # 不打印警告
    start = clock() #计时器

    if valid_date(ride_date):

        train_list_raw = get_list_raw(from_station_name, to_station_name, ride_date) # 构造train_list_raw
        init_result_ordered_dict(train_list_raw) # 用train_list_raw 构造 train_info_ordered_dict
        process_ticket_info_all(train_list_raw) # 为所有车次增加票价信息
        visualize() # 打印

    else:
        pass

    finish = clock()
    print 'total executing time: %d seconds.' % (finish - start)


if __name__ == '__main__':
    main()