# -*- coding: utf-8 -*-
"""
参考<<Python Linux系统管理与运维自动化>>11.3章节(p388)范例改写.
运用到以下知识:
1. 参数管理(argprase)
2. 多线程并发处理, 线程传参(threading)
3. 上下文管理(with)
4. MySQL数据库增改查操作(pymysql)
5. 配置文件管理(configparser)
6. 日志管理
"""

## 导入模块
from __future__ import print_function
import os
import sys
import string
import argparse
import random
import threading
import time
import logging
import logging.config
## 读取配置文件函数
from configparser import ConfigParser as cf
## 装饰上下文函数
from contextlib import contextmanager
## mysql连接模块
import pymysql

## 获取根目录路径
homePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')

## 配置日志格式
logging.config.fileConfig(os.path.join(homePath, 'conf/logging.ini'))

## 读取配置文件
conFile = os.path.join(homePath, 'conf/config.ini')
content = cf(allow_no_value=True)
content.read(conFile)

## 压测数据库名及表名
dbName = content.get('db', 'db_name')
tbName = content.get('db', 'db_table')

## 创建压测数据库命令
dropDBCommand = "DROP DATABASE IF EXISTS {}".format(dbName)
dropTBCommand = "DROP TABLE {}".format(tbName)
createDBCommand = "CREATE DATABASE {}".format(dbName)
useDBCommand = "USE {}".format(dbName)

## show库表命令
showDBCommand = "SHOW DATABASES"
showTBCommand = "SHOW TABLES"

## 创建压测表命令
createTBCommand="""
CREATE TABLE {0} (
    id INT(10) PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL, 
    datetime DOUBLE NOT NULL
)
""".format(tbName)

## 插入语句格式
inertFormat  = "INSERT INTO {}(name, datetime) values ('{}', {})"

## 修改语句格式
modifyFormat = "UPDATE {} SET name = '{}',datetime={} WHERE id = {}" 

## 查询语句格式
queryFormat = "SELECT name from {} WHERE id = {}" 

## 随机抽取1000个索引语句
queryIndexCommand = "SELECT id from {} order by rand() limit 1000".format(tbName)

## 定义帮助文档
def args():
    desc="""
        MySQL压测工具, 修改和查询测试必须有数据, 
        结合参数(-t)向测试表追加数据.
    """
    parser=argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '-H', '--host', action='store', dest='host', default='localhost',
        help='MySQL连接主机名称(默认: localhost)' 
    )
    parser.add_argument(
        '-u', '--user', action='store', dest='user', default='root',
        help='MySQL连接用户(默认: root)'
    )
    parser.add_argument(
        '-p', '--password', action='store', dest='password', required=True,
        help='MySQL连接密码(必须)'
    )
    parser.add_argument(
        '-P', '--port', action='store', dest='port', type=int, default=3306, 
        help='MySQL连接端口(默认: 3306)'
    )
    ## 压测类型为插入, 修改还是查询
    parser.add_argument(
        '-t', '--type', action='store', dest='_type', type=int, default=0,
        help="压测类型(默认: 0), 0=插入, 1=修改, 2=查询"
    )
    ## 压测结束是否删除压测数据库
    parser.add_argument(
        '-d', '--delete', action='store_true', default=False, dest='deleted', 
        help="删除压测数据库(默认: False)"
    )
    ## 压测前是否初始化数据库
    parser.add_argument(
        '-i', '--init', action='store_true', default=False, dest='init',
        help="重置数据库(默认: False, 需结合结合参数-t使用)"
    )
    ## 并发数
    parser.add_argument(
        '-r', '--row', action='store', dest='row', type=int, default=5,
        help='并发进程数(默认: 5, 请求次数=并发进程数*执行次数)'
    )
    ## 执行次数(总插入次数==并发数*执行次数)
    parser.add_argument(
        '-c', '--col', action='store', dest='col', type=int, default=2000,
        help='执行次数(默认: 2000, 请求次数=并发进程数*执行次数)'
    )

    return parser.parse_args()

## 连接数据库, 并构建为上下文结构
@contextmanager
def db_conn(**kwargs):
    conn = pymysql.connect(**kwargs)
    ## 返回数据后保留状态, 并关闭数据库连接
    try:
        yield conn
    finally:
        conn.close()

## 创建10位字母数字组合
def random_string(length=10):
    s = string.ascii_letters + string.digits
    return "".join(random.sample(s, length))

## 查询索引执行语句
def index_row(cursor):
    sql = queryIndexCommand
    cursor.execute(sql)

## 添加数据执行语句
def insert_row(cursor):
    sql = inertFormat.format(
        tbName,
        random_string(),
        time.time()
    )
    cursor.execute(sql)

## 查询数据执行语句
def query_row(cursor, index):
    sql = queryFormat.format(
        tbName,
        index
    )
    cursor.execute(sql)

## 修改数据执行语句
def modify_row(cursor, index):
    sql = modifyFormat.format(
        tbName,
        random_string(),
        time.time(),
        index
    )
    cursor.execute(sql)

## 插入数据
def insert_data(connArgs, col):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            for x in range(col):
                insert_row(c)
                conn.commit()

## 修改数据
def modify_data(connArgs, col, index):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            for x in range(col):
                modify_row(c, index)
                conn.commit()

## 查询数据
def query_data(connArgs, col, index):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            for x in range(col):
                query_row(c, index)

## 查询索引
def index_data(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            index_row(c)
            re = c.fetchall()
            result = map(lambda x:x[0], re)
            return list(result)

## 删除压测库
def del_db(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(dropDBCommand)

## 删除压测表
def del_tb(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            c.execute(dropTBCommand)

## 创建压测库和表
def create_db(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(createDBCommand)

## 创建数据表
def create_tb(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(useDBCommand)
            c.execute(createTBCommand)

## 判断数据库或者数据表是否存在
def object_is_exist(connArgs):
    with db_conn(**connArgs) as conn:
        with conn.cursor() as c:
            c.execute(showDBCommand)
            showDB = c.fetchall()
            re = map(lambda x:x[0], showDB)
             
            if dbName in re:
                c.execute(useDBCommand)
                c.execute(showTBCommand)
                showTB = c.fetchall()
                re = map(lambda x:x[0], showTB)
                return tbName in re
            else:
                return 2

## 主程序
def main(**kwargs):
    if __name__ == '__main__':
        ## 命令传参
        parser = args()

        connArgs = dict(
            host     = parser.host, 
            user     = parser.user,
            password = parser.password,
            port     = parser.port,
        )
    
        row = parser.row
        col = parser.col
        _type = parser._type
        _del = parser.deleted
        _init = parser.init

    else:
        ## 函数传参
        connArgs = dict(
            host     = kwargs.get('host'),
            user     = kwargs.get('user'),
            password = kwargs.get('password'),
            port     = kwargs.get('port')
        )

        row = kwargs.get('row')
        col = kwargs.get('col')
        _type = kwargs.get('_type')
        _del = kwargs.get('_del')
        _init = kwargs.get('_init')


    ## 插入数据测试并且添加了-d参数
    if object_is_exist(connArgs) == 2:
        create_db(connArgs)
        create_tb(connArgs)
    elif object_is_exist(connArgs) == 0:
        create_tb(connArgs)
    elif _type == 0 and _init:
        del_tb(connArgs)
        create_tb(connArgs)
    elif _type in (1,2):
        if _init == False:
            index = index_data(connArgs)
        else:
            logging.error(
                '插入和修改测试不支持重置数据库, 当前type=={}'.format(
                _type))
            return None

    ## 压测开始时间
    beginTime = time.time()

    ## 多线程并发测试
    threads = []
    for x in range(row):
        if _type == 0:
            t = threading.Thread(
                target=insert_data, args=(
                    connArgs, col
                )
            )
        elif _type == 1:
            try:
                t = threading.Thread(
                    target=modify_data, args=(
                        connArgs, col, random.choice(
                            index
                        )
                    )
                )
            except IndexError:
                logging.error(
                    '查询结果为空, 目标数据库或者表不存在, 当前index=={}'.format(
                    index))
                return None
        elif _type == 2:
            try: 
                t = threading.Thread(
                    target=query_data, args=(
                        connArgs, col, random.choice(
                           index
                        )
                    )
                )
            except IndexError:
                logging.error(
                    '查询结果为空, 目标数据库或者表不存在, 当前index=={}'.format(
                    index))
                return None
        else:
            logging.error(
                'type参数只能是(0|1|2), 当前type=={}'.format(
                _type))
            return None

        threads.append(t)
        t.start()

    ## 阻塞方式运行
    for x in threads:
        t.join()

    ## 压测结束时间
    endTime = time.time()

    ## 等待进程连接关闭(???)
    time.sleep(1)

    ## 删除压测库
    if _del == True:
        del_db(connArgs)

    ## 返回压测时间
    return round(endTime-beginTime, 4)

## 本地运行
if __name__ == '__main__':
    print(main())
