from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

import time
import json
import pymongo
import random
import jieba
import gc

from logging import INFO
from logging import Formatter
from logging.handlers import RotatingFileHandler
from logging import Logger

from multiprocessing import freeze_support
from snownlp import SnowNLP

try:
    from Analysis import Analysis
    print('ANALYSIS IMPORTED')
except:
    print('ANALYSIS NOT IMPORTED')

scrollNum:int=0
currentRank:int=0

#创建日志
def getLogger(filename='weiboloader.log') -> Logger:
    logger = Logger(filename.split('.')[0])
    logger.setLevel(level=INFO)
    maxsize=5*1024*1024
    handler=RotatingFileHandler(filename=filename,encoding='utf-8',maxBytes=maxsize)
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

#添加日志记录
def log(logger, info):
    logger.info(info)

#创建浏览器
def getBrowser():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    browser = webdriver.Chrome(chrome_options=chrome_options)
    browser.set_window_size(500, 700)
    wait = WebDriverWait(browser, 10)
    return wait,browser

#访问移动版微博（'https://m.weibo.cn/'）
def reachWeibo(wait,browser,logger):
    browser.get('https://m.weibo.cn/')
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.m-font-search'))
    )
    log(logger, 'REACH WEIBO')
    #进入搜索页面
    search = browser.find_element_by_css_selector('.m-font-search')
    search.click()
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input'))
    )

#获取热搜榜并保存
def hotRank(wait,browser,logger,hour:int=time.localtime().tm_hour) -> dict:
    reachWeibo(wait,browser,logger)
    # 进入热搜榜页面
    hotsearchs=browser.find_elements_by_css_selector('.m-text-cut')
    i=0
    for hotsearch in hotsearchs:
        if '微博热搜榜' in hotsearch.text:
            break
        i+=1
    hotsearchs[i].click()
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'.card'))
    )
    log(logger, 'REACH WEIBO HOT RANK PAGE')
    # 获取热搜榜
    texts=browser.find_elements_by_css_selector('.m-text-cut')
    hotList:list=[text.text for text in texts]
    log(logger,'FETCH HOTLIST WITH LENGTH: '+str(len(hotList)))
    rankDict:dict={str(i):hotList[i] for i in range(50)}
    riseDict:dict={str(i):text for text,i in zip(hotList[50:],range(len(hotList[50:])))}
    hot:dict={'rank':rankDict,'rise':riseDict,'hour':hour}
    log(logger, 'HOT RANK PARSED')
    #保存热搜榜
    colname:str=str(hour)+'#rank'
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    mongoClear(client,'weiboHotRanks',colname)
    mongoSave(client,hot,'weiboHotRanks',colname)
    client.close()
    log(logger, 'HOT RANK SAVED TO MONGODB')
    return hot

#获取指定话题的相关微博
def fetchTopic(wait,browser,logger,topic:str,rank:int=0,scrollnum:int=20,hour:int=time.localtime().tm_hour) -> dict:
    stf=time.time()
    #!!!此时浏览器已经打开可以搜索的微博页面
    browser.execute_script('window.scrollTo(0,0)')
    #搜索该话题
    searchInput=browser.find_element_by_tag_name('input')
    searchInput.clear()
    searchInput.send_keys('#'+topic+'#')
    time.sleep(random.randint(1,2))
    searchInput.send_keys(Keys.ENTER)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'.m-box'))
    )
    log(logger, 'SEARCHED TOPIC: #' + topic + '#')
    #滚动获取更多微博
    for i in range(scrollnum):
        rsleep=0.1
        log(logger, 'SCROLLING: '+str(i)+' WAIT: '+str(rsleep))
        browser.execute_script('window.scrollBy(0,window.innerHeight*14)')
        time.sleep(rsleep)
    time.sleep(1)
    #解析微博并保存（话题，内容，转发数，评论数，赞同数，以及计算得到的积极度）
    cards:list=[]
    words:list=[]
    cardList=browser.find_elements_by_css_selector('.card')
    log(logger,'WEIBO CARDS FOUND')
    i:int=0
    for card in cardList:
        try:
            c:dict = {}
            c['topic']=topic
            c['author'] = card.find_element_by_css_selector('.weibo-top .m-text-cut').text
            c['content'] = card.find_element_by_css_selector('.weibo-main .weibo-text').text
            ctrls:list = card.find_elements_by_css_selector('.m-ctrl-box .m-diy-btn')
            basei:int=1 if len(ctrls)>3 else 0
            c['reposts'] = parseCtrls(ctrls[basei+0].text)
            c['comments'] = parseCtrls(ctrls[basei+1].text)
            c['attitudes'] = parseCtrls(ctrls[basei+2].text)
            positive=calculatePositive(u''.join(c['content']))
            c['positive']=positive
            cards.append(c)
            log(logger,'PARSED: '+str(i)+' POSITIVE: '+str(positive))
            i+=1
            words.extend(jieba.cut(c['content']))#分词以便于生成词云
        except:
            log(logger,'PARSE ERROR: '+str(i))
            i+=1
            continue
    weibos:dict={'cards':cards,'topic':topic,'words':words}
    #保存该话题相关微博
    colname:str=str(hour)+'#'+str(rank)
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    mongoClear(client,'weiboTopics',colname)
    mongoSave(client,weibos,'weiboTopics',colname)
    client.close()
    etf=time.time()
    log(logger,'TOPIC: #'+topic+'# FETCHED TIME-USED: '+str(etf-stf))
    return weibos

#微博解析辅助函数
def parseCtrls(text:str) -> str:
    if text=='转发':
        return '0'
    elif text=='评论':
        return '0'
    elif text=='赞':
        return '0'
    if '万' in text:
        return str(float(text.split('万')[0])*10000)
    return text

#计算积极度
def calculatePositive(content:str) -> float:
    try:
        positive: float = Analysis(content)
    except:
        try:
            positive: float = SnowNLP(content).sentiments
        except:
            positive: float = 0.5
    return positive

#数据库操作，从外部传入client以便复用
def mongoSave(client,content,dbname:str,colname:str):
    db=client[dbname]
    col=db[colname]
    if type(content)==dict:
        col.insert_one(content)
    elif type(content)==list:
        col.insert_many(content)

def mongoClear(client,dbname:str,colname:str):
    db = client[dbname]
    col = db[colname]
    col.drop()

#从数据库中获取本地热搜榜
def fetchHotRankLocal(hour:int=time.localtime().tm_hour) -> dict:
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboHotRanks']
    col = db[str(hour)+'#rank']
    rank=col.find_one()
    client.close()
    return rank

#保存数据为json文件，用于测试
def jsonSave(content,fname:str):
    with open(fname,'w',encoding='utf-8') as f:
        f.write(json.dumps(content,indent=2,ensure_ascii=False))

#获取热搜榜主循环函数
def mainHotRank(wait,browser,mainlog:Logger,hourlog:Logger,hour:int) -> dict:
    log(mainlog, 'HOT-RANK NOT THERE YET HOUR: ' + str(hour))
    maxtry_rank: int = 5 #最大尝试次数
    succeeded:bool=False
    for i in range(maxtry_rank):
        try:
            hotRank(wait=wait,
                    browser=browser,
                    logger=hourlog,
                    hour=hour)
            succeeded=True
            break
        except:
            log(mainlog, 'FAILURE-LEFT: ' + str(maxtry_rank-i-1))
            time.sleep(2)
            continue
    if not succeeded:
        log(mainlog, 'HOT-RANK-FETCH-MAXTRY-EXCEEDED')
    hotrank:dict=fetchHotRankLocal(hour)
    return hotrank

#获取话题相关微博主循环函数
def mainTopic(wait,browser,hotrank:dict,mainlog:Logger,hourlog:Logger,hour:int):
    global scrollNum
    global currentRank

    #访问微博搜索页
    reachWeibo(wait, browser, hourlog)
    #依次获取热搜榜五十个话题的相关微博
    for rank in range(currentRank,50):
        log(mainlog, 'FETCHING-RANK: ' + str(rank))
        maxtry_topic: int = 3 #最大尝试次数
        succeeded:bool=False
        currenthour:int=time.localtime().tm_hour
        if currenthour!=hour:
            log(mainlog,'HOUR EXCEEDED - TIME FOR NEXT HOUR')
            break
        for i in range(maxtry_topic):
            try:
                topic = hotrank['rank'][str(rank)]
                fetchTopic(wait=wait,
                           browser=browser,
                           logger=hourlog,
                           topic=topic,
                           rank=rank,
                           scrollnum=scrollNum,
                           hour=hour)
                succeeded=True
                currentRank=rank
                gc.collect()
                break
            except:
                log(mainlog, 'FAILURE-FETCH-TOPIC LEFT: ' + str(maxtry_topic-i-1))
                #出现失败往往是被识别出来了，因此重新创建浏览器进行搜索
                browser.close()
                wait,browser=getBrowser()
                reachWeibo(wait,browser,hourlog)
        if not succeeded:
            log(mainlog, 'TOPIC-WEIBO-FETCH-MAXTRY-EXCEEDED')
    return browser

#主函数
def main():
    #主日志
    mainlogname='./logs/weiboloader.log'
    mainlog=getLogger(filename=mainlogname)
    #分时记录，以一天24小时为周期覆盖
    fetchcount:int=0
    fetched:dict={i:0 for i in range(24)}
    log(mainlog,'FETCH DICT INITIATED')
    #主循环
    while True:
        #获取当前小时数
        hour:int=time.localtime().tm_hour
        if fetchcount>23:
            fetchcount=0
            fetched= {i: 0 for i in range(24)}
            log(mainlog,'FETCH DICT RENEWED')
        #该小时数对应的热搜微博未获取则进行获取
        if fetched[hour]==0:
            #分时日志
            hourlogname='./logs/hourlogs/hour'+str(hour)+'.log'
            hourlog=getLogger(filename=hourlogname)
            st=time.time()
            #启动浏览器
            try:
                wait,browser=getBrowser()
            except:
                continue
            log(mainlog,'BROWSER AND CLIENT INITIATED')
            #获取热搜榜，进入主话题循环
            try:
                browser=mainTopic(wait=wait,
                                  browser=browser,
                                  hotrank=mainHotRank(wait=wait,
                                                      browser=browser,
                                                      mainlog=mainlog,
                                                      hourlog=hourlog,
                                                      hour=hour),
                                  mainlog=mainlog,
                                  hourlog=hourlog,
                                  hour=hour)
            except:
                continue
            et=time.time()
            log(mainlog,'FETCH-HOUR: '+str(hour)+' TIME-USED: '+str(et-st)+'s')
            fetched[hour]=1
            fetchcount+=1
            #关闭浏览器
            #因为浏览器在运行中可能由于运行时的错误已经非正常关闭，因此添加try...except...语句
            try:
                browser.close()
            except:
                pass
        else:
            #计算当前小时剩余时间，进行休眠以节约资源
            min:int=time.localtime().tm_min
            log(mainlog,'READY TO SLEEP FOR: '+str(60-min)+' min')
            gc.collect()
            time.sleep((60-min)*60)
            log(mainlog,'WAKE UP!')

if __name__ == '__main__':
    freeze_support()
