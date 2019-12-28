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

from snownlp import SnowNLP

flag=0
fetchMap=[0 for i in range(50)]
scrollNum:int=5

chrome_options = Options()
chrome_options.add_argument('--headless')

def hotRank(hour:int=time.localtime().tm_hour) -> dict:
    browser = webdriver.Chrome(chrome_options=chrome_options)
    browser.set_window_size(500, 700)
    browser.get('https://m.weibo.cn/')
    wait = WebDriverWait(browser, 10)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,'.m-font-search'))
    )
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
    texts=browser.find_elements_by_css_selector('.m-text-cut')
    hotList:list=[]
    for text in texts:
        hotList.append(text.text)
    print(hotList,len(hotList))
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
    colname:str=str(hour)+'#rank'
    mongoClear('weiboHotRanks',colname)
    mongoSave(hot,'weiboHotRanks',colname)
    browser.close()
    return hot

def fetchTopic(topic:str,rank:int=0,scrollnum:int=20,hour:int=time.localtime().tm_hour) -> dict:
    stf=time.time()
    browser = webdriver.Chrome(chrome_options=chrome_options)
    browser.set_window_size(500, 700)
    browser.get('https://m.weibo.cn/')
    wait = WebDriverWait(browser, 10)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.m-font-search'))
    )
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
    for i in range(scrollnum):
        rsleep=random.randint(1,3)
        print('SCROLLING: ',i,' WAIT: ',rsleep)
        browser.execute_script('window.scrollBy(0,window.innerHeight*14)')
        time.sleep(rsleep)
    time.sleep(2)
    cards:list=[]
    words:list=[]
    cardList=browser.find_elements_by_css_selector('.card')
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
            try:
                positive:float=SnowNLP(u''.join(c['content'])).sentiments
            except:
                positive:float=0.5
            print('CALCULATED POSITIVE: ',positive)
            c['positive']=positive#random.random()
            cards.append(c)
            print('PARSED: ',i,' ',len(ctrls))
            i+=1

            words.extend(list(jieba.cut(c['content'])))

        except:
            print('PARSE ERROR: ',i)
            i+=1
            continue
    #jsonSave(cards,'cards4.json')
    weibos:dict={}
    weibos['cards']=cards
    weibos['topic']=topic
    weibos['words']=words
    colname:str=str(hour)+'#'+str(rank)
    print('SAVING TO: ',colname)
    mongoClear('weiboTopics',colname)
    mongoSave(weibos,'weiboTopics',colname)
    etf=time.time()
    print('FETCHED: ',topic,' TIME-USED: ',etf-stf)
    return weibos

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

def main():
    fetched:dict={}
    fetchcount:int=0
    for i in range(24):
        fetched[i]=0
    while True:
        if fetchcount>23:
            for i in range(24):
                fetched[i]=0
            fetchcount=0
        hour:int=time.localtime().tm_hour
        if fetched[hour]==0:
            st=time.time()
            while True:
                hotrank=fetchHotRankLocal(hour)
                if True:
                    print('HOT-RANK NOT THERE YET HOUR: ',hour)
                    maxtry_rank:int=10
                    while True:
                        if maxtry_rank<1:
                            print('HOT-RANK-FETCH-MAXTRY-EXCEEDED')
                            break
                        try:
                            hotRank(hour)
                            break
                        except:
                            print('FAILURE-LEFT: ',maxtry_rank)
                            maxtry_rank-=1
                    hotrank:dict=fetchHotRankLocal(hour)
                for rank in range(50):
                    print('FETCHING-RANK: ',rank)
                    topic=hotrank['rank'][str(rank)]
                    maxtry_topic:int=10
                    while True:
                        if maxtry_topic < 1:
                            print('TOPIC-WEIBO-FETCH-MAXTRY-EXCEEDED')
                            break
                        try:
                            fetchTopic(topic, rank,scrollnum=scrollNum, hour=hour)
                            break
                        except:
                            print('FAILURE-FETCH-TOPIC LEFT: ',maxtry_topic)
                            maxtry_topic -= 1
                break
            et=time.time()
            print('FETCH-HOUR: ',hour,' TIME-USED: ',et-st,'s')
            fetched[hour]=1
            fetchcount+=1

if __name__ == '__main__':
    main()
