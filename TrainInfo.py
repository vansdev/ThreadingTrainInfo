# -*- coding: UTF-8 -*-
'''
该module包含车次信息的 class TrainInfo
TrainInfo 维护一个 余票信息 的有序字典(为了按序打印)  元素形如  票类别 ：(余票数量, 票价)
'''

dict_template = {'z1' : None, 'z2' : None, 'wr' : None, 'wy' : None, 'zy' : None, 'zw' : None}

class TrainInfo(object):

    # 构造器 读取 app.py 中 从url得到的json中 解析出的数据 构造TrainInfo 实例
    def __init__(self, train_id, from_station, to_station, start_time, arrive_time, time_lapse):
        self._train_id = train_id
        self._from_station = from_station
        self._to_station = to_station
        self._start_time = start_time
        self._arrive_time = arrive_time
        self._time_lapse = time_lapse
        self._ticket_info = None

    def set_ticket_info(self, ticket_info):
        self._ticket_info = ticket_info

    # 判定该类票是否还有余票, num_str最终来自对json的解析
    def has_ticket(self,num_str):
        if num_str == u'--' or num_str == u'无': # json解析得到 '--' 或 '无' 说明无该种票或无余票
            return False
        else:
            return True

    # 返回该TrainInfo对应车次的所有信息  作为一个list返回 以供prettyTable打印
    def add_to_table(self):
        output = []
        output.append(self._train_id)
        output.append(self._from_station)
        output.append(self._to_station)
        output.append(self._start_time)
        output.append(self._arrive_time)
        output.append(self._time_lapse)
        # 以下处理余票数目 和 票价信息
        if self._ticket_info:
            for item in self._ticket_info.itervalues(): # item是一个tuple  形如(余票数目, 票价)
                                                        # 其中余票数目仍然是json解析得到的str形式 例如 '--' '有' '无' '12'
                if self.has_ticket(item[0]):
                    if item[0] and item[1]: # 这里 理论上不需要此判断 有票时 应该能从price_query 查询时得到相应票价
                                            # 但实际中 12306存在个别车次的个别座型 显示有票 而price_query的结果无该座型票价
                                            # item[1]为None 导致 unicode+None 出错 故加上这一判断
                        output.append(item[0] + '  ' + item[1]) # 有票 且 读取到票价  打印 余票数目 和 票价
                    else:
                        output.append(item[0]) # 上述个别座型 票价为None 只打印余票数目
                else:
                    output.append(item[0]) # 无票 打印 '--' 或 '无'
        return output

