import unicodedata,re,datetime,json



# NULL处理
def trim(content):
    content = str(content).strip()

    if content.lower() == 'null' or content.lower() == 'none':
        return ''

    content = unicode(content)
    return content

# 统计长度
def length(content):

    content = trim(content)
    return len(content)


# 查找字符串
def isContains(content,keyword):


    content = trim(content)
    keyword = trim(keyword)

    if content.find(keyword) != -1:
        return True
    else:
        return False



# 是否为空
def isNull(content):

    if length(content) <= 0:
        return True
    else:
        return False


# 只保留数字
def digitalOnly(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return ''

    str2List = list(inputString)
    outputString = ''

    for item in str2List:

        if u'0' <= item <= u'9':
            outputString += item

    return outputString


# 只保留英文字母
def letterOnly(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return ''

    str2List = list(inputString)
    outputString = ''


    for item in str2List:

        if  item in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o',
                     'p','q','r','s','t','u','v','w','x','y','z','A','B','C','D','E','F','G',
                     'H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']:
            outputString += item

    return outputString


# 只保留中文
def chineseOnly(inputString):

    inputString =  trim(inputString)

    if length(inputString) == 0:
         return ''

    str2List        = list(inputString)
    outputString    = ''

    for item in str2List:

        if(u'\u4e00' <= item <= u'\u9fa5'):
            outputString += item

    return outputString



# 是否数字
def  isNum(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    result = re.match('[0-9]', inputString)

    if result:
        return True

    return False


# 转换成unicode，防止全角数据
def unicode(inputString):
    return unicodedata.normalize('NFKC',inputString)


# 是否中文
def isChinese(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    if  u'\u4e00' <= inputString <= u'\u9fa5' :
        return True

    return False


# 是否中文括弧
def isBrackets(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    if inputString in ['（','）']:
        return True


    return False


# 是否点
def isDot(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    if inputString in ['.']:
        return True


    return False


# 是否英文
def isLetter(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    if inputString in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']:
        return True

    return False


# 判断是否日期
def isDate(inputString):

    inputString = trim(inputString)

    if length(inputString) == 0:
        return False

    result = re.match('[0-9]{4}\-[0-3]{1}[0-9]{1}\-[0-9]{2}', inputString)
    
    if result:

        try:
            datetime.datetime.strptime(inputString, "%Y-%m-%d")
            return True
        except:
            return False

    else:
        return False


