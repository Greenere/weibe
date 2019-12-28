import pymongo
import jieba

def wordsExtend():
    hour = 26
    for rank in range(50):
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client['weiboTopics']
        col = db[str(hour) + '#' + str(rank)]
        hotrank = client['weiboHotRanks'][str(hour) + '#rank'].find_one()['rank']
        weibo = col.find_one()
        weibe = {}
        weibe['topic'] = hotrank[str(rank)]
        weibe['cards'] = weibo['cards']
        words = []
        for wb in weibo['cards']:
            words.extend(list(jieba.cut(wb['content'])))
        weibe['words'] = words
        col.drop()
        col.insert_one(weibe)

def migrateHour(hour0,hour1):
    client=pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboTopics']
    for rank in range(50):
        col0=db[str(hour0) + '#' + str(rank)]
        col1=db[str(hour1) + '#' + str(rank)]
        weibe=col0.find_one()
        weibe.pop('_id')
        col1.insert_one(weibe)

def migrateHotRanks(hour0,hour1):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboHotRanks']
    col0=db[str(hour0) + '#rank']
    col1=db[str(hour1) + '#rank']
    hotrank=col0.find_one()
    col1.insert_one(hotrank)

if __name__ == '__main__':
    #migrateHour(19,27)
    migrateHotRanks(19,27)
