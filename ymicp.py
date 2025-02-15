'''
author     : Yiming
Creat time : 2023/9/8 16:53
Blog       : https://www.cnblogs.com/ymer
Github     : https://github.com/HG-ha
Home       : https://api.wer.plus
QQ group   : 376957298,1029212047
'''

import asyncio
import aiohttp
import cv2
import time
import hashlib
import re
import base64
import numpy as np
import ujson

class beian():
    def __init__(self):
        self.typj = {
            0:ujson.dumps(
                {'pageNum': '', 'pageSize': '', 'unitName': '',"serviceType":1}
                ), # 网站
            1:ujson.dumps(
                {"pageNum":"","pageSize":"","unitName":'',"serviceType":6}
                ), # APP
            2:ujson.dumps(
                {'pageNum': '', 'pageSize': '', 'unitName': '',"serviceType":7}
                ), # 小程序
            3:ujson.dumps(
                {'pageNum': '', 'pageSize': '', 'unitName': '',"serviceType":8}
                ) # 快应用
        }
        self.cookie_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32'}
        self.home = 'https://beian.miit.gov.cn/'
        self.url = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth'
        self.getCheckImage = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImage'
        self.checkImage = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/checkImage'
        self.queryByCondition = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition'

    async def _init_session(self):
        self.session = aiohttp.ClientSession()
    
    async def _close_session(self):
        if self.session is not None:
            await self.session.close()
    
    async def get_token(self):
        timeStamp = round(time.time()*1000)
        authSecret = 'testtest' + str(timeStamp)
        authKey = hashlib.md5(authSecret.encode(encoding='UTF-8')).hexdigest()
        self.auth_data = {'authKey': authKey, 'timeStamp': timeStamp}
        self.cookie = await self.get_cookie()
        self.base_header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32',
                'Origin': 'https://beian.miit.gov.cn',
                'Referer': 'https://beian.miit.gov.cn/',
                'Cookie': f'__jsluid_s={self.cookie}',
                'Accept': 'application/json, text/plain, */*'
            }
        try:
            async with self.session.post(self.url,data=self.auth_data,headers=self.base_header) as req:
                t = await req.json()
                return t['params']['bussiness']
        except Exception as e:
            return e

    async def get_cookie(self):
        async with self.session.get(self.home,headers=self.cookie_headers) as req:
            res = await req.text()
            for key,value in req.cookies.items():
                jsluid_s = re.compile('[0-9a-z]{32}').search(str(value))[0]
            return jsluid_s

    async def check_img(self):
        self.token = await self.get_token()
        self.base_header.update({'Content-Length': '0', 'Token': self.token})
        try:
            async with self.session.post(self.getCheckImage,data='',headers=self.base_header) as req:
                res = await req.json()
                self.p_uuid = res['params']['uuid']
                big_image = res['params']['bigImage']
                small_image = res['params']['smallImage']
                ibig = cv2.cvtColor(cv2.imdecode(np.frombuffer(base64.b64decode(big_image),np.uint8), cv2.COLOR_GRAY2RGB), cv2.IMREAD_GRAYSCALE)
                isma = cv2.cvtColor(cv2.imdecode(np.frombuffer(base64.b64decode(small_image),np.uint8), cv2.COLOR_GRAY2RGB), cv2.IMREAD_GRAYSCALE)
                mouse_length = await self.getvalue(ibig,isma)
                self.check_data = ujson.dumps({'key': self.p_uuid, 'value': str(mouse_length)})
                sign = await self.get_sign()
                return sign
        except Exception as e:
            print(e)
            print("过验证码失败,自动递归重试")
            return await self.check_img()
        
    async def get_sign(self):
        length = str(len(str(self.check_data).encode('utf-8')))
        self.base_header.update({'Content-Length': length,'Content-Type':'application/json'})
        try:
            async with self.session.post(self.checkImage, data=self.check_data, headers=self.base_header) as req:
                res = await req.json()
                return res['params']
        except Exception as e:
            print(e)
            return e

    async def getvalue(self,bigImage,smallImage):
        position_match = cv2.matchTemplate(bigImage, smallImage, cv2.TM_CCOEFF_NORMED)
        max_loc = cv2.minMaxLoc(position_match)[3][0]
        mouse_length = max_loc+1
        return mouse_length

    async def getbeian(self,name,sp,pageNum,pageSize,):
        info = ujson.loads(self.typj.get(sp))
        info['pageNum'] = pageNum
        info['pageSize'] = pageSize
        info['unitName'] = name
        sign = await self.check_img()
        length = str(len(str(ujson.dumps(info,ensure_ascii=False)).encode('utf-8')))
        self.base_header.update({'Content-Length': length, 'Uuid': self.p_uuid, 'Token': self.token, 'Sign': sign})
        async with self.session.post(self.queryByCondition, data=ujson.dumps(info,ensure_ascii=False), headers=self.base_header) as req:
            res = await req.text()
            return ujson.loads(res)

    async def autoget(self,name,sp,pageNum,pageSize):
        await self._init_session()
        try:
            data = await self.getbeian(name,sp,pageNum,pageSize)
        except Exception as e:
            print(e)
            return {"code":122,"msg":"查询失败"}
        finally:
            await self._close_session()

        if data['code'] == 500:
            return {"code":122,"msg":"工信部服务器异常"}
        return data

    # APP备案查询
    async def ymApp(self,name,pageNum='',pageSize=''):
        return await self.autoget(name,1,pageNum,pageSize)

    # 网站备案查询
    async def ymWeb(self,name,pageNum='',pageSize=''):
        return await self.autoget(name,0,pageNum,pageSize)

    # 小程序备案查询
    async def ymMiniApp(self,name,pageNum='',pageSize=''):
        return await self.autoget(name,2,pageNum,pageSize)

    # 快应用备案查询
    async def ymKuaiApp(self,name,pageNum='',pageSize=''):
        return await self.autoget(name,3,pageNum,pageSize)

if __name__ == '__main__':
    async def main():
        a = beian()
        # 官方单页查询pageSize最大支持26
        # 页面索引pageNum从1开始,第一页可以不写
        # 查询该公司的网站备案信息，每页10条数据，查询第二页
        data = await a.ymWeb("深圳市腾讯计算机系统有限公司",pageSize=10,pageNum=2)
        print(data)
        # 查询微信APP的备案信息
        data = await a.ymApp("微信")
        print(data)
        return data
    asyncio.run(main())

    '''
    在其他代码模块中调用（异步）

        from ymicp import beian

        icp = beian()
        data = await icp.ymApp("微信")
    
    '''
