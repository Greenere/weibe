import json
import pymongo
import time
import math
import os

from threading import Thread
from weiboLoader import main
import gc

from functools import reduce
from flask import Flask, request,jsonify,send_from_directory,send_file
from pyecharts.charts import WordCloud
from weiboLoader import getLogger,log,crawling

discardwords:list=['#', '【', '】', ',', '，', '##','的','是','了','在'] #词云构建时的弃用词
exampleHour:int=27 #示例小时（虚拟时间）

#从数据库获取热搜榜和相应话题的微博数据，外部传入client以便复用
def fetchHotRankLocal(client,hour:int=time.localtime().tm_hour) -> dict:
    db = client['weiboHotRanks']
    col = db[str(hour)+'#rank']
    rank=col.find_one()
    return rank

def fetchTopicLocal(client,rank,hour:int=time.localtime().tm_hour) -> dict:
    db = client['weiboTopics']
    col = db[str(hour) + '#'+str(rank)]
    topic=col.find_one()
    return topic

#词云构建函数
def setWordCloud(ranks:list,hour:int) -> list:
    try:
        #获取词语列表
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        wc = WordCloud()
        words:list = []
        list(map(lambda x:words.extend(x),
                 [fetchTopicLocal(client,rank, hour)['words']
                  for rank in ranks]))
        client.close()
        #词频统计
        textdict:dict={}
        for wd in filter(lambda wd:wd not in discardwords,words):
            textdict[wd]=textdict.get(wd,0)+1
        wordpair:list=list(textdict.items())
        wordpair.sort(key=lambda i:i[1],reverse=True)
        wc.add("", wordpair, word_size_range=[10, 100], rotate_step=1, word_gap=20)
        options = wc.get_options()
        options['tooltip']['textStyle'] = {"fontSize": 14}
        series = options['series']
        series[0]['rotationRange'] = [-2, 2]
        #在词语过多时只取前500项
        if len(series[0]['data'])>500:
            series[0]['data']=series[0]['data'][:500]
        cloudseries=series
    except:
        cloudseries=[]
    return cloudseries

if not crawling:
    Thread(target=main,args=(False,),name='weibeloader',daemon=True).start()
    crawling=True

app = Flask(__name__)

#服务日志
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

#数据请求服务
@app.route('/data',methods=['GET'])
def dataServe():
    #获取请求
    reqs=request.args.get('request')
    log(servelog,'REQUEST RECIEVED: '+str(reqs))
    reqs = json.loads(reqs)
    hour = exampleHour if reqs['example']==1 else time.localtime().tm_hour
    if reqs['require'] == 'hot-rank':
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        response = fetchHotRankLocal(client,hour)
        if response is not None:
            response['_id'] = ''
            response['ready']=1
        else:
            response = {
                'ready':0,
                'rank': {},
                'rise': {}
            }
        log(servelog,'RESPONSE SENDING: '+str(response))
        client.close()
        return jsonify(response)
    elif reqs['require'] == 'topic':
        st=time.time()
        #解析请求
        allMode:int=int(reqs['allmode'])
        checkStatus:list = list(reqs['checkstatus'])
        ranks:list = [i for i,check in zip(range(50), checkStatus) if check==1]
        log(servelog,'RANKS REQUESTED: '+str(ranks))
        #构造回复
        response:dict = {}
        response['ranks']=[]
        response['ready'] = {}
        response['cloudseries']=[]
        #获取当时热搜榜，失败则回复均失败
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        try:
            hotrank = fetchHotRankLocal(client,hour)['rank']
        except:
            for rank in ranks:
                response['ready'][rank]=0
            return jsonify(response)
        #获取话题数据
        for rank in ranks:
            try:
                weibos = fetchTopicLocal(client,rank, hour=hour)
                if weibos['topic'] != hotrank[str(rank)]:
                    log(servelog,'TOPIC ERROR - IN TIME TOPIC NOT THERE YET')
                    response['ready'][rank] = 0
                    continue
            except:
                response['ready'][rank]=0
                continue
            response['ready'][rank] = 0 if len(weibos['cards']) <1 else 1
            #allMode为1时，放弃所有计算得到的记录点大小小于1的数据点
            reps:list = [
                {
                    'author': weibe['author'],
                    'positive': weibe['positive'],
                    'reposts': weibe['reposts'],
                    'comments': weibe['comments'],
                    'attitudes': weibe['attitudes'],
                    'size': int(math.log(float(weibe['reposts']) + 1)),
                    'y': math.log(float(weibe['attitudes']) + 1),
                    'x': weibe['positive']
                } for weibe in weibos['cards'] if not (allMode==1 and int(math.log(float(weibe['reposts']) + 1))<1)
            ]
            response[str(rank)] = reps
        response['ranks'] = ranks
        et=time.time()
        log(servelog,'TIME-USED-FOR-MAINRESPONSE: '+str(et-st)+'s')
        client.close()
        return jsonify(response)
    elif reqs['require']=='wordcloud':
        #获取应该用于生成词云的词语对应的话题的标号（即热搜榜排名）列表readyranks
        ranks: list = list(reqs['ranks'])
        ready: dict = dict(reqs['ready'])
        readyranks:list=[rank for rank in ranks if ready[str(rank)]]
        #生成词云，构造回复
        log(servelog, 'WAITING FOR WORD CLOUDING')
        response: dict = {'cloudseries':setWordCloud(readyranks, hour)}
        log(servelog, 'WORD CLOUDING FINISHED')
        return jsonify(response)
    else:
        response = {}
        return jsonify(response)

if __name__ == '__main__':
    host='localhost'
    port=8880