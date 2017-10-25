
from . import Base as base
import datetime as date
import re


class DateFormat:

    def Tformat(self,inputDate):

        chs_arabic_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '零': '0', '〇': '0',
                          '○': '0', 'O': '0', '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
                          '元':'1','—':'1','０':'0'}
        chs_arabic = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
        digi_arabic = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        date_sign = ['年', '月', '日', '时', '分', '秒', '整', '下', '上', '中','凌','晨',
                     '午', '到', '/', '—', '－', '／', '/', '-', ':', '：']
        date_month = ['01', '02', '03', '04', '05',
                      '06', '07', '08', '09', '10', '11', '12']
        date_day = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15',
                    '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31']

        year    = None
        month   = None
        day     = None
        outDate = None


        OutputDate = str(inputDate).strip().replace(
            'NULL', '').replace('Null', '').replace('None','')
      
        # 判断时间是个正确时间，先正则时间格式，格式正确但是转时间戳后小于0的就返回空
        if base.isDate(OutputDate):
            try:
                timestamp = date.datetime.strptime(
                    OutputDate, "%Y-%m-%d").timestamp()
            except:
                return ''
            if timestamp < 0:
                return ''
            else:
                return OutputDate
        
        # 转换符号和字符
        str2List = list(OutputDate)
        outString = ''

        for index, val in enumerate(str2List):

            # 空数据
            if len(str(val).strip()) == 0:
                outString += val
                continue

            # 时间标记
            if val in date_sign:
                outString += val
                continue

            # 数字时间
            if val in digi_arabic:
                outString += val
                continue

            if val == '十':
                _previous_of_ten_index = index - 1
                _after_of_ten_index = index + 1
                _previous_of_ten = OutputDate[_previous_of_ten_index]
                _after_of_ten = OutputDate[_after_of_ten_index]

                ten = ''

                if _previous_of_ten in chs_arabic and _after_of_ten in chs_arabic:
                    ten = ''
                elif _previous_of_ten in chs_arabic and _after_of_ten not in chs_arabic:
                    ten = '0'
                elif _previous_of_ten not in chs_arabic and _after_of_ten in chs_arabic:
                    ten = '1'
                elif _previous_of_ten not in chs_arabic and _after_of_ten not in chs_arabic:
                    ten = '10'

                outString += ten
                continue

            # 中文数字转阿拉伯数字
            arabic_num = chs_arabic_map[val]
            if arabic_num is None:
                outString += val
            else:
                outString += arabic_num

        # 处理有时分秒的数据
        if outString.find(':') != -1 or outString.find('时') != -1:
            outString = re.split(" ", outString)
            if len(outString) > 1:
                outString = outString[0]
            else:
                if str(outString).find('日') != -1:
                    outString = re.split('日', outString[len(outString)-1])
                    outString = outString[0] + '日'
                else:
                    outString = outString[0]


        # 年-月-日   转换处理时间
        year = re.split("年", outString)
        month = re.split("月", outString)
        day = re.split("日", outString)

        if year.__len__() > 0:
            year = base.digitalOnly(year[0])

        if month.__len__() > 0:

            month = month[0]
            month = re.split("年", month)
            month = month[month.__len__()-1]
            if month.__len__() == 1:
                month = base.digitalOnly('0' + month)
            else:
                month = base.digitalOnly(month)

        if day.__len__() > 0:
            day = day[0]
            day = re.split("月", day)
            day = day[day.__len__()-1]
            if day.__len__() == 1:
                day = base.digitalOnly('0' + day)
            else:
                day = base.digitalOnly(day)

        outDate = year + '-' + month + '-' + day
        print(outDate)
        if base.isDate(outDate):
            return outDate

        # yyyy/MM/dd  MM/dd/yyyy   MM/dd/yy   转换处理时间
        chsDate = re.split("/", outString)

        if chsDate.__len__() == 3:
            part_01 = chsDate[0]
            part_02 = chsDate[1]
            part_03 = chsDate[2]


            # 第一部分
            if part_01.__len__() == 4:
                year = part_01

            if part_01.__len__() == 2:
                month = part_01

            if part_01.__len__() == 1:
                month = '0' + part_01

            # 第二部分
            if part_02.__len__() == 2:
                if part_02 in date_month and month is None:
                    month = part_02
                else:
                    day = part_02
            elif part_02.__len__() == 1:
                part_02 = '0' + part_02
                if part_02 in date_month and month is None:
                    month = part_02
                else:
                    day = part_02

            if part_03.__len__() == 4:
                year = part_03

            if part_03.__len__() == 2:
                if year is None:
                    year = '20' + part_03
                else:
                    day = part_03

            outDate = year + '-' + month + '-' + day


            if base.isDate(outDate):
                return outDate
            else:
                return ''

        else:
            return ''



if __name__ == '__main__':
    mm = DateFormat()
    print(mm.Tformat('1111-11-11'))
