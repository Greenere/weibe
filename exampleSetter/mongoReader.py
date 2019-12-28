import json
import pymongo
import time

def fetchHotRankLocal(hour=time.localtime().tm_hour):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboHotRanks']
    col = db[str(hour)+'#rank']
    rank=col.find_one()
    return rank

def fetchTopicLocal(rank,hour=time.localtime().tm_hour):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboTopics']
    col = db[str(hour) + '#'+str(rank)]
    topic=col.find_one()
    return topic

def mongoToFiles():
    hour=27
    rank=fetchHotRankLocal(hour)
    rank.pop('_id')
    json.dump(rank,open('hotRank.json','w',encoding='utf-8'),ensure_ascii=False)
    topics=[]
    for r in range(50):
        topic=fetchTopicLocal(r,hour)
        topic.pop('_id')
        topics.append(topic)
    json.dump(topics,open('hotTopics.json','w',encoding='utf-8'),ensure_ascii=False)

if __name__ == '__main__':
    mongoToFiles()