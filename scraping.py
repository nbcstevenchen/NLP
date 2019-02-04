# -!- coding: utf-8 -!-
"""
Author: Yuhao Chen
语法参照文档：https://ltp.readthedocs.io/zh_CN/latest/appendix.html#id3
依存句法关系语法和解释：1. https://blog.csdn.net/weixin_40899194/article/details/79808276
                     2. http://www.ltp-cloud.com/intro
关系三元组:
因为中文语法过于的庞大，所以目前只支持主谓宾的格式，也曾尝试添加过定语后置关系，做出的效果不是很好，所以就没有加入。
其他语法格式用主谓宾相似的思路也可以实现。

关于人名，机构，技术：
我用的是thulac的库的默认字典识别
   1. 部分公司被当做了人名，公司名称与人名过于相似，机构名称并没有出现在默认字典中。
      （我尝试过导入自定义字典，但是thulac对自定义词语的词性定义都是uw，无法更改，所以我就放弃了这个想法，
         我也尝试过用jieba这个库，但是jieba的默认字典对人名和机构的识别在此例子中大幅度不如thulac，如果添加自定义
         字典的话没有意义）
   2.对技术的识别，只用到了对html tag进行识别。如果想要对更多技术的识别，可以用添加字典的方式实现。
"""
from bs4 import BeautifulSoup
import urllib.request
import re
import sys
import os
from pyltp import Segmentor, Postagger, Parser
import thulac

final = {'technologies': set(), 'institutions':set(), 'name':set()}
output = open('result.txt', 'a')

def getHtml(url):
    html = urllib.request.urlopen(url).read()
    return html


def getSome():
    '''
    从文中给出的标签，提取部分科技和机构的名称
    '''
    html_doc = getHtml("https://www.jiqizhixin.com/articles/2018-10-25-8")
    html = BeautifulSoup(html_doc,'html.parser')
    for sub in html.find_all('mark'):
        #print(sub['data-type'])
        if sub['data-type'] == 'technologies':
           # print(sub.contents[0])
            final[sub['data-type']].add(sub.contents[0])
        if sub['data-type'] == 'institutions':
            final[sub['data-type']].add(sub.contents[0])
    #print(final)


def get_content():
    '''
    :return: the splited content of website
    '''
    string = ''
    html_doc = getHtml("https://www.jiqizhixin.com/articles/2018-10-25-8")
    html = BeautifulSoup(html_doc, 'html.parser')
    #print(html.find_all('p'))
    for i in range(0, len(html.find_all('p'))):
        reg = re.compile('<[^>]*>')
        for sub in html.find_all('p')[i].contents:
            content = reg.sub('', str(sub)).replace('\n', '').replace(' ', '')
            string += content
    t = thulac.thulac()
    result = t.cut(string)
    #print(result)
    for sub in result:
        if sub[1] == 'nz':
           # print(sub[1], sub[0], '\n')
            final['institutions'].add(sub[0])
        elif sub[1] == 'np':
            #print(sub[1], sub[0], '\n')
            final['name'].add(sub[0])
    getSome()
    final_list = re.split('。|？|!',string)
    return final_list


def load_ltp_model():
    LTP_DATA_DIR = ""
    print("Loading LTP Model... ...")

    segmentor = Segmentor()
    segmentor.load(os.path.join(LTP_DATA_DIR, "cws.model"))

    postagger = Postagger()
    postagger.load(os.path.join(LTP_DATA_DIR, "pos.model"))

    parser = Parser()
    parser.load(os.path.join(LTP_DATA_DIR, "parser.model"))

    print("Success")
    return segmentor, postagger, parser


def relation_triple_tuple(sentence, segmentor, postagger, parser):
    words = segmentor.segment(sentence)  # 分词列表
    #print(list(words))
    postags = postagger.postag(words)    #a list of (verb, punctuation, general noun...)
    #print(list(postags))
    arcs = parser.parse(words, postags)  #依存句法关系列表（主谓关系，动宾关系...）
    #print("\t".join("%d:%s" % (arc.head, arc.relation) for arc in arcs))
    relation = relation_dict(words, arcs)
    for i in range(0, len(postags)):
        if postags[i] == 'v':  #寻找谓语动词
            sub_relation = relation[i] #根据index定位谓语动词
            #定位主谓宾关系
            if 'SBV' in sub_relation and 'VOB' in sub_relation: # 'SBV': 主谓关系, 'VOB' :谓宾关系
                first = word_connection(words, postags, relation, sub_relation['SBV'][0])
                second = words[i]
                last = word_connection(words, postags, relation, sub_relation['VOB'][0])
                print((first, second, last))
                output.write("关系三元组： (%s, %s, %s)\n" % (first, second, last))






def relation_dict(words, arcs):
    """
    :param words: 分词列表
    :param arcs: 依存句法关系列表（主谓关系，动宾关系...）
    :return: 罗列出每个依存句法关系的起始点和结束点（分词的index是起始点，arcs的index是结束点）
    """
    final_list = []
    for index in range(0, len(words)):
        sub_dict = {}
        for i in range(0, len(arcs)):
            if arcs[i].head == index + 1:
                if arcs[i].relation not in sub_dict:
                    sub_dict[arcs[i].relation] = [i]
                else:
                    sub_dict[arcs[i].relation].append(i)
        final_list.append(sub_dict)
    return final_list

def word_connection(words, postags, relation_list, index):
    """
    加上修饰等词语，让句子更完整
    """
    before = ''
    after = ''

    if 'ATT' in relation_list[index]:
        for i in range(0, len(relation_list[index]['ATT'])):
            before += word_connection(words, postags, relation_list, relation_list[index]['ATT'][i])

    if postags[index] == 'v':
        if 'SBV' in relation_list[index]:
            before = word_connection(words, postags, relation_list, relation_list[index]['SBV'][0]) + before
        if 'VOB' in relation_list[index]:
            after += word_connection(words, postags, relation_list, relation_list[index]['VOB'][0])
    return before + words[index] + after


if __name__ == '__main__':
    alist = get_content()

    for key in final:   #循环字典，并输出文件
        out = key + ': ' + str(final[key]) + '\n'
        output.write(out)

    segmentor, postagger, parser = load_ltp_model()  #load model

    for sub in alist:  # 循环列表中的每句话，得到关系三元组
        relation_triple_tuple(sub, segmentor, postagger, parser)

    print(final)



