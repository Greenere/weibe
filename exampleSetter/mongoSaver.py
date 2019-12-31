#运行本程序可以将示例数据存入Mongodb数据库中

import json
import pymongo
import time

def filesToMongo(hour):
    rank=json.load(open('hotRank.json','r',encoding='utf-8'))
    topics=json.load(open('hotTopics.json','r',encoding='utf-8'))

    client = pymongo.MongoClient('mongodb://localhost:27017/')
    dbr = client['weiboHotRanks']
    colr= dbr[str(hour)+'#rank']
    colr.insert_one(rank)

    dbt=client['weiboTopics']
    for r,topic in zip(range(50),topics):
        colt=dbt[str(hour) + '#' + str(r)]
        colt.insert_one(topic)

if __name__ == '__main__':
    hour=27
    filesToMongo(hour)