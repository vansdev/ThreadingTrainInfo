# -*- coding: UTF-8 -*-
import arrow
import re

# arrow处理输入日期 只能看从今天起 预售三十天内的车次
def valid_date(input_date):
    span = arrow.utcnow().span('day', count=30)
    try:
        date = arrow.get(input_date)
    except Exception:
        print 'Please check input format of date, it should be sth like "2017-03-03".'
        exit(2)
    if span[0] <= date <= span[1]:
        return True
    else:
        print 'Tickets unavailable on this day.'
        return False


# re获得站点代码 例如 上海->SHH
def get_station_code(name, src):
    pattern = re.compile(name + r'\|([A-Z]{3})')
    return pattern.search(src).group(1)


# 用url体和查询参数构造查询url  理想情况下用requests的params可以直接达到一样的效果 不需要此函数
# 但实际发现本例 requests用params时不能正确返回数据(可能由于12306的ssl 不清楚) 只好写了这个函数...
def build_query_url(base, args): # base 和 args 为iterable 长度一致
    zip_list = zip(base, args) # zip_list 的 item 是tuple
    key_value_list = [] # 存储子串
    for item in zip_list:
        key_value_list.append(''.join(item))  # 每个查询参数构成的的形如 &key=value 子串
    return ''.join(key_value_list) # 连接所有子串 得到完整url