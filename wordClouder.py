#本模块为测试模块，实际程序中并未调用
from PIL import Image
from wordcloud import WordCloud, ImageColorGenerator
import matplotlib.pyplot as plt
import numpy as np
import jieba
import time
import pymongo
import json
import io
from pyecharts.charts import WordCloud
from weiboLoader import mongoClear,mongoSave
import pprint

def fetchTopicLocal(rank,hour=time.localtime().tm_hour):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['weiboTopics']
    col = db[str(hour) + '#'+str(rank)]
    topic=col.find_one()
    return topic

def setWordCloud(ranks,hour):
    words=[]
    for rank in ranks:
        weibos=fetchTopicLocal(rank,hour)
        for weibo in weibos['cards']:
            words.append(" ".join(jieba.cut(weibo['content'])))
    cut_text = " ".join(words)
    wordcloud = WordCloud(
        # 设置字体，不然会出现口字乱码，文字的路径是电脑的字体一般路径，可以换成别的
        font_path="C:/Windows/Fonts/simhei.ttf",
        background_color="rgba(128,128,128,0)",
        width=700,height=400,scale=1,margin=5,
        colormap="copper").generate(cut_text)
    wordcloud.to_file('frontend/wordcloud.png')
    """
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()
    """

def blank():
    cut_text = "稍等"
    wordcloud = WordCloud(
        # 设置字体，不然会出现口字乱码，文字的路径是电脑的字体一般路径，可以换成别的
        font_path="C:/Windows/Fonts/simhei.ttf",
        background_color="rgba(128,128,128,0)",
        width=700, height=400, scale=1, margin=5,
        colormap="copper",
        max_font_size=0).generate(cut_text)
    wordcloud.to_file('frontend/wordblank.png')

def echartCloud(ranks,hour):
    st=time.time()
    wc = WordCloud()
    words=[]
    for rank in ranks:
        weibos=fetchTopicLocal(rank,hour)
        for weibo in weibos['cards']:
            words.extend(list(jieba.cut(weibo['content'])))
    textdict={}
    for wd in words:
        try:
            textdict[wd]+=1
        except:
            textdict[wd]=0
    wordpair=list(textdict.items())
    mt=time.time()
    print('CUT TIME USED: ',mt-st)
    wc.add("", wordpair, word_size_range=[20, 100])
    #wc.render('wordcloud.html')
    option=wc.get_options()
    # pprint.pprint(option)
    # print(type(option))
    option['tooltip']['textStyle']=''
    mongoClear('weiboTopics', 'cloudoption')
    mongoSave(option, 'weiboTopics', 'cloudoption')
    et=time.time()
    print('TIME USED: ',et-st)


if __name__ == '__main__':
    echartCloud(range(50),26)