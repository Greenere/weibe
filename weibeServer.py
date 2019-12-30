from flask import Flask, request,jsonify,send_from_directory,send_file
from pyecharts.charts import WordCloud

import json
import pymongo
import time
import math
import os
import threading
import gc

from weiboLoader import getLogger,log

#词云信号量
clouded:int=0
cloudseries:list=[]
discardwords:list=['#', '【', '】', ',', '，', '##','的','是','了','在']

exampleHour:int=27

client = pymongo.MongoClient('mongodb://localhost:27017/')

def fetchHotRankLocal(hour:int=time.localtime().tm_hour) -> dict:
    global client
    #client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboHotRanks']
    col = db[str(hour)+'#rank']
    rank=col.find_one()
    return rank

def fetchTopicLocal(rank,hour:int=time.localtime().tm_hour) -> dict:
    global client
    #client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboTopics']
    col = db[str(hour) + '#'+str(rank)]
    topic=col.find_one()
    return topic

def setWordCloud(ranks:list,hour:int) -> list:
    global clouded
    global cloudseries

    try:
        wc = WordCloud()
        words:list = []
        for rank in ranks:
            weibos = fetchTopicLocal(rank, hour)
            try:
                words.extend(weibos['words'])
            except:
                pass
        wordpair:list=[]
        for wd in set(words)-set(discardwords):
            wordpair.append((wd,words.count(wd)))
        wordpair.sort(key=lambda i:i[1],reverse=True)
        wc.add("", wordpair, word_size_range=[10, 100], rotate_step=1, word_gap=20)
        options = wc.get_options()
        options['tooltip']['textStyle'] = {"fontSize": 14}
        series = options['series']
        series[0]['rotationRange'] = [-2, 2]
        if len(series[0]['data'])>500:
            series[0]['data']=series[0]['data'][:500]
        cloudseries=series
    except:
        cloudseries=[]

    clouded=1

    return cloudseries

app = Flask(__name__)

servelog=getLogger('./logs/server.log')

@app.route('/')
def index():
    filename='./frontend/index.html'
    return send_file(filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/about.html')
def aboutPage():
    filename='./frontend/about.html'
    return send_file(filename)

@app.route('/data',methods=['GET'])
def dataServeAttemp():
    try:
        return dataServe()
    except:
        log(servelog,'DATA SERVE ERROR')
        return {}

def dataServe():
    global clouded
    global cloudseries

    gc.collect()

    reqs=request.args.get('request')
    log(servelog,'REQUEST RECIEVED: '+str(reqs))
    #print('RECIEVED REQUEST: ',reqs)
    reqs = json.loads(reqs)
    if reqs['example'] == 1:
        hour = exampleHour
    else:
        hour = time.localtime().tm_hour
    if reqs['require'] == 'hot-rank':
        response = fetchHotRankLocal(hour)
        if response is not None:
            response['_id'] = ''
            response['ready']=1
        #print('RESPONSE: ',str(response))
        if response is None:
            response = {
                'ready':0,
                'rank': {},
                'rise': {}
            }
        log(servelog,'RESPONSE SENDING: '+str(response))
    elif reqs['require'] == 'topic':
        st=time.time()
        #解析请求
        #hotrank:dict=reqs['hotrank']
        checkStatus:list = list(reqs['checkstatus'])
        ranks:list = [i for i,check in zip(range(50), checkStatus) if check==1]
        log(servelog,'RANKS REQUESTED: '+str(ranks))
        #print('RANKS REQUESTED: ', ranks)
        #构造回复
        response:dict = {}
        response['ranks']=[]
        response['ready'] = {}
        response['cloudseries']=[]
        #获取当时热搜榜，失败则回复均失败
        try:
            hotrank = fetchHotRankLocal(hour)
            hotrank = hotrank['rank']
        except:
            for rank in ranks:
                response['ready'][rank]=0
            return jsonify(response)
        #词云构造线程
        try:
            clouded=0
            threading.Thread(target=setWordCloud,args=(ranks,hour)).start()
        except:
            clouded=1
        #获取话题数据
        for rank in ranks:
            try:
                weibos = fetchTopicLocal(rank, hour=hour)
                if weibos['topic'] != hotrank[str(rank)]:
                    log(servelog,'TOPIC ERROR - IN TIME TOPIC NOT THERE YET')
                    response['ready'][rank] = 0
                    continue
            except:
                response['ready'][rank]=0
                continue
            weibes:list = weibos['cards']
            response['ready'][rank] = 0 if len(weibes) <1 else 1
            reps:list = []
            for weibe in weibes:
                rep = {
                    'author': weibe['author'],
                    'content': '',#weibe['content'],
                    'positive': weibe['positive'],
                    'reposts': weibe['reposts'],
                    'comments': weibe['comments'],
                    'attitudes': weibe['attitudes'],
                    'size': int(math.log(float(weibe['reposts']) + 1)),
                    'y': math.log(float(weibe['attitudes']) + 1),
                    'x': weibe['positive']
                }
                reps.append(rep)
            response[str(rank)] = reps
        response['ranks'] = ranks
        et=time.time()
        log(servelog,'TIME-USED-FOR-MAINRESPONSE: '+str(et-st)+'s')
        log(servelog,'WAITING FOR WORD CLOUDING')
        while True:
            if clouded == 1:
                response['cloudseries'] = cloudseries
                wt=time.time()
                log(servelog,'TIME-WAITED-FOR-WORDCLOUD: '+str(wt-et)+'s')
                break
    else:
        response = {}
    return jsonify(response)

if __name__ == '__main__':
    host='localhost'
    port=8880