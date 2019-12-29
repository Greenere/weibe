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

from logging import INFO
from logging import Formatter
from logging.handlers import RotatingFileHandler
from logging import Logger

try:
    from Analysis import Analysis
    print('ANALYSIS IMPORTED')
except:
    print('ANALYSIS NOT FOUND')
    pass

from snownlp import SnowNLP

scrollNum:int=10

chrome_options = Options()
chrome_options.add_argument('--headless')
browser = webdriver.Chrome(chrome_options=chrome_options)
browser.set_window_size(500, 700)

def getLogger(filename='weiboloader.log'):
    logger = Logger(filename.split('.')[0])
    logger.setLevel(level=INFO)
    maxsize=5*1024*1024
    handler=RotatingFileHandler(filename=filename,encoding='utf-8',maxBytes=maxsize)
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def log(logger, info):
    logger.info(info)

def hotRank(logger,hour:int=time.localtime().tm_hour) -> dict:
    browser.get('https://m.weibo.cn/')
    wait = WebDriverWait(browser, 10)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'.m-font-search'))
    )
    log(logger, 'REACH WEIBO')
    search=browser.find_element_by_css_selector('.m-font-search')
    search.click()
    wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR,'.m-text-cut'))
    )
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
    texts=browser.find_elements_by_css_selector('.m-text-cut')
    hotList:list=[]
    for text in texts:
        hotList.append(text.text)
    log(logger,'FETCH HOTLIST WITH LENGTH: '+str(len(hotList)))
    rankDict:dict={}
    for i in range(50):
        rankDict[str(i)]=hotList[i]
    riseDict:dict={}
    for text,i in zip(hotList[50:],range(len(hotList[50:]))):
        riseDict[str(i)]=text
    hot:dict={}
    hot['rank']=rankDict
    hot['rise']=riseDict
    hot['hour']=hour
    log(logger, 'HOT RANK PARSED')
    colname:str=str(hour)+'#rank'
    mongoClear('weiboHotRanks',colname)
    mongoSave(hot,'weiboHotRanks',colname)
    log(logger, 'HOT RANK SAVED TO MONGODB')
    return hot

def fetchTopic(logger,topic:str,rank:int=0,scrollnum:int=20,hour:int=time.localtime().tm_hour) -> dict:
    stf=time.time()
    browser.get('https://m.weibo.cn/')
    wait = WebDriverWait(browser, 10)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.m-font-search'))
    )
    log(logger, 'REACH WEIBO')
    search = browser.find_element_by_css_selector('.m-font-search')
    search.click()
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'input'))
    )
    searchInput=browser.find_element_by_tag_name('input')
    searchInput.send_keys('#'+topic+'#')
    searchInput.send_keys(Keys.ENTER)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'.m-box'))
    )
    log(logger, 'SEARCHED TOPIC: #' + topic + '#')
    for i in range(scrollnum):
        rsleep=0.1
        log(logger, 'SCROLLING: '+str(i)+' WAIT: '+str(rsleep))
        browser.execute_script('window.scrollBy(0,window.innerHeight*14)')
        time.sleep(rsleep)
    time.sleep(1)
    cards:list=[]
    words:list=[]
    cardList=browser.find_elements_by_css_selector('.card')
    log(logger,'WEIBO CARDS FOUND')
    i:int=0
    for card in cardList:
        try:
            c = {}
            c['topic']=topic
            c['author'] = card.find_element_by_css_selector('.weibo-top .m-text-cut').text
            c['content'] = card.find_element_by_css_selector('.weibo-main .weibo-text').text
            ctrls = card.find_elements_by_css_selector('.m-ctrl-box .m-diy-btn')
            basei=1 if len(ctrls)>3 else 0
            c['reposts'] = parseCtrls(ctrls[basei+0].text)
            c['comments'] = parseCtrls(ctrls[basei+1].text)
            c['attitudes'] = parseCtrls(ctrls[basei+2].text)
            positive=calculatePositive(u''.join(c['content']))
            c['positive']=positive
            cards.append(c)
            log(logger,'PARSED: '+str(i)+' POSITIVE: '+str(positive))
            i+=1
            words.extend(list(jieba.cut(c['content'])))
        except:
            log(logger,'PARSE ERROR: '+str(i))
            i+=1
            continue
    weibos:dict={}
    weibos['cards']=cards
    weibos['topic']=topic
    weibos['words']=words
    colname:str=str(hour)+'#'+str(rank)
    mongoClear('weiboTopics',colname)
    mongoSave(weibos,'weiboTopics',colname)
    etf=time.time()
    log(logger,'TOPIC: #'+topic+'# FETCHED TIME-USED: '+str(etf-stf))
    return weibos

def calculatePositive(content):
    try:
        positive: float = Analysis(content)
    except:
        try:
            positive: float = SnowNLP(content).sentiments
        except:
            positive: float = 0.5
    return positive

def mongoSave(content,dbname:str,colname:str):
    client=pymongo.MongoClient('mongodb://localhost:27017/')
    db=client[dbname]
    col=db[colname]
    if type(content)==type({}):
        col.insert_one(content)
    elif type(content)==type([]):
        col.insert_many(content)
    client.close()

def mongoClear(dbname:str,colname:str):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client[dbname]
    col = db[colname]
    col.drop()
    client.close()

def mongoReadOne(dbname:str,colname:str) -> dict:
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client[dbname]
    col = db[colname]
    one=col.find_one()
    client.close()
    return one

def fetchHotRankLocal(hour:int=time.localtime().tm_hour) -> dict:
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboHotRanks']
    col = db[str(hour)+'#rank']
    rank=col.find_one()
    return rank

def jsonSave(content,fname:str):
    with open(fname,'w',encoding='utf-8') as f:
        f.write(json.dumps(content,indent=2,ensure_ascii=False))

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

def mainHotRank(mainlog,hourlog,hour) -> dict:
    log(mainlog, 'HOT-RANK NOT THERE YET HOUR: ' + str(hour))
    maxtry_rank: int = 3
    while True:
        if maxtry_rank < 1:
            log(mainlog, 'HOT-RANK-FETCH-MAXTRY-EXCEEDED')
            break
        try:
            hotRank(logger=hourlog, hour=hour)
            break
        except:
            log(mainlog, 'FAILURE-LEFT: ' + str(maxtry_rank))
            maxtry_rank -= 1
            time.sleep(2)
    hotrank: dict = fetchHotRankLocal(hour)
    return hotrank

def mainTopic(hotrank,mainlog,hourlog,hour):
    global scrollNum

    for rank in range(50):
        log(mainlog, 'FETCHING-RANK: ' + str(rank))
        maxtry_topic: int = 3
        while True:
            if maxtry_topic < 1:
                log(mainlog, 'TOPIC-WEIBO-FETCH-MAXTRY-EXCEEDED')
                break
            try:
                topic = hotrank['rank'][str(rank)]
                fetchTopic(logger=hourlog, topic=topic, rank=rank, scrollnum=scrollNum, hour=hour)
                break
            except:
                log(mainlog, 'FAILURE-FETCH-TOPIC LEFT: ' + str(maxtry_topic))
                maxtry_topic -= 1
                time.sleep(2)

def main():
    mainlogname='./logs/weiboloader.log'
    mainlog=getLogger(filename=mainlogname)
    fetched:dict={}
    fetchcount:int=0
    for i in range(24):
        fetched[i]=0
    log(mainlog,'FETCH DICT INITIATED')
    while True:
        hour:int=time.localtime().tm_hour
        if fetchcount>23:
            for i in range(24):
                fetched[i]=0
            fetchcount=0
            log(mainlog,'FETCH DICT RENEWED')
        if fetched[hour]==0:
            hourlogname='./logs/hourlogs/hour'+str(hour)+'.log'
            hourlog=getLogger(filename=hourlogname)
            st=time.time()
            hotrank:dict=mainHotRank(mainlog,hourlog,hour)
            mainTopic(hotrank,mainlog,hourlog,hour)
            et=time.time()
            print('FETCH-HOUR: ',hour,' TIME-USED: ',et-st,'s')
            fetched[hour]=1
            fetchcount+=1
        else:
            min:int=time.localtime().tm_min
            log(mainlog,'READY TO SLEEP FOR: '+str(60-min)+' min')
            time.sleep((60-min)*60)
            log(mainlog,'WAKE UP!')

if __name__ == '__main__':
    main()
