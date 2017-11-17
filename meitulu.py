# coding:utf-8
import requests
import re
import os
import time
import threading
import random
import sys
import queue as q

class retry():
    def __init__(self,max_attempt_number=None,delay=None):
        self.max_attempt_number = max_attempt_number
        self.delay = delay

    def __call__(self,func):
        def call(*args,**kwargs):
            attempt_number = 1
            while True:
                try:
                    return func(*args,**kwargs)
                except Exception:
                    if self.max_attempt_number:
                        if attempt_number >= self.max_attempt_number:
                            raise Exception
                        else:
                            attempt_number += 1
                    if self.delay:
                        time.sleep(self.delay)
        return call


class Meitulu():
    def __init__(self):
        self.item_url_compile = re.compile(r'https://www.meitulu.com/item/\d+\.html') 
        self.head = {'User-Agent': 'User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) \
                    AppleWebKit/537.36 (KHTML,like Gecko) Chrome/56.0.2924.87 Safari/537.36'}
        
        self.issuer_blacklist = ['其他','Bomb.TV','WPB-net','日本美女','DGC','BWH套图','@misty','@crepe,',
                                'YSWeb','WBGC','Minisuka.tv','Sabra','H!P Digital Books','H!P','NS-Eyes',
                                'Image.tv','RQ-STAR写真套图','For-side','Minisuka.tv','VYJ']
        
        self.model_blacklist = ['傅雅慧']
        
        self.timeout = 10
        self.path = None
        self.queue = q.Queue()
        self.threading_num = 10


    @retry(max_attempt_number=10)
    def get(self,url):
        res = requests.get(url,headers=self.head,timeout=self.timeout)
        res.encoding = 'utf-8'
        return res


 
    def fetch_img(self):
        while True:
            try:
                url = self.queue.get_nowait()
                i = self.queue.qsize()
            except:
                break
            try:
                res = self.get(url)
            except Exception as e:
                print('%s 下载失败。\n%s' % (url, e))
                continue
            if(res.status_code == 200):
                pic_name = re.match(r'^http.+/(\d+\.jpg)$', url).group(1)
                filename = '{0}{1}{2}.jpg'.format(self.path,os.sep,i+1)
                try:
                    with open(filename, 'wb') as fs:
                        for chunk in res.iter_content(1024):
                            fs.write(chunk)
                        print('{0} 下载成功。'.format(url),end='\r')
                except Exception as e:
                    print(e)
                    exit()
            else:
                pass


    @retry(max_attempt_number=10,delay=60)
    def parse_html(self,url):
        """解析图集HTML页面获取所有图片URL下载保存， 随机返回下一个相册链接，递归执行。"""
        print('open {0}...'.format(url))
        try:            
            resp = self.get(url)
        except:
            raise UserWarning

        if(resp.status_code != 200):
            raise UserWarning
        
        item_num = re.match(r'https://www.meitulu.com/item/(\d+)\.html',url).group(1)
        urls = self.item_url_compile.findall(resp.text, re.S)
        next_link = random.choice(urls)

        model_name = re.search(r'<p>模特姓名(：|:)\s*(.+?)</p>', resp.text, re.S).group(2)
        model_name = re.sub(r'<[^>]+>', '', model_name)
        issuer = re.search(r'<p>发行机构(：|:)\s*(.+?)</p>', resp.text, re.S).group(2)
        issuer = re.sub(r'<[^>]+>', '', issuer)
        issuer = str.split(issuer)[0]
        match = re.search(r'<p>发行时间(：|:)\s*(\d.+?)\s*</p>', resp.text, re.S)
        issue_date = match.group(2) if match else None
        img_amount = re.search(r'<p>图片数量.+?(\d+).*?</p>', resp.text, re.S).group(1)
        album_name = issue_date if issue_date else item_num


        self.path = 'meitulu{sep}{model_name}{sep}{album_name}-{img_amount}P'.format(
            model_name=model_name,album_name=album_name,img_amount=img_amount,sep=os.sep)

        print('模特：{model_name} 发行日期：{issue_date} 发行机构：{issuer} 图片数量：{img_amount}张 '.format(
            model_name=model_name, issue_date=issue_date, issuer=issuer,img_amount=img_amount))

        if(issuer in self.issuer_blacklist):
            print('发行机构黑名单中，跳过。\n')
            return self.parse_html(next_link)
        if(model_name in self.model_blacklist):
            print('模特黑名单中，跳过。\n')
            return self.parse_html(next_link)

        if (os.path.exists(self.path)):
            print('{0}/{1}相册已存在，跳过。\n'.format(model_name, issue_date))
            return self.parse_html(next_link)
        else:
            os.makedirs(self.path, 0o777, True)

        #根据图片数量及URL规则批量生成图片下载URL
        for i in range(1, int(img_amount) + 1):
            pic_url = 'http://mtl.ttsqgs.com/images/img/{0}/{1}.jpg'.format(item_num, i)
            self.queue.put(pic_url)

        threads = []
        for _ in range(self.threading_num): 
            t = threading.Thread(target=self.fetch_img)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print('%s下载完成。                    \n' % (self.path))

        return self.parse_html(next_link)

    def run(self):
        res = self.get('https://www.meitulu.com')
        urls = self.item_url_compile.findall(res.text, re.S)
        self.parse_html(random.choice(urls))


if __name__ == '__main__':
    sys.setrecursionlimit(99999)
    mtl = Meitulu()
    mtl.run()
    
