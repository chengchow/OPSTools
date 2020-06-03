# -*- coding: utf-8 -*-
"""
邮件发送脚本:
1. 支持有附件和无附件格式.
2. 支持smtp类型有ssl ,tls, smtp.
3. smtp配置参考配置文件config.ini.
4. 发送信息传参优先级: 函数传参-->命令传参-->配置文件传参.
"""

import os
import sys
import smtplib
import argparse
import logging
import logging.config
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formatdate

from configparser import ConfigParser as cf

## 获取根路径
homePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')

## 配置日志格式
logging.config.fileConfig(os.path.join(homePath, 'conf/logging.ini'))

## 获取临时文件存储路径
tmpPath = os.path.join(homePath, 'tmp')

## 读取配置文件
conFile = os.path.join(homePath, 'conf/config.ini')
conf = cf(allow_no_value=True)
conf.read(conFile)

#设置默认字符集为UTF8 不然有些时候转码会出问题
unixCode = 'utf-8'
winCode  = 'gbk'
if sys.getdefaultencoding() != unixCode:
    reload(sys)
    sys.setdefaultencoding(unixCode)

## 定义参数
def args():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-e', '--email', action='store', dest='email', 
        help="接收邮件地址"
    )
    parser.add_argument('-t', '--title', action='store', dest='title',
        help='接收邮件标题'
    )
    parser.add_argument('-c', '--context', action='store', dest='context',
        help='接收邮件内容'
    )
    parser.add_argument('-f', '--file', action='store', dest='attech_file', default=None,
        help='接收邮件附件文件名, 该文件必须存放在tmp目录下'
    )

    return parser.parse_args()

## 主程序
def main(**kwargs):
    ## 邮件标题和内容
    if __name__ == '__main__':
        ## 命令传参
        parser = args()

        mailTo = parser.email
        sub = parser.title
        text = parser.context
        attFile = parser.attech_file
    else:
        ## 函数传参
        mailTo = kwargs.get('toMail')
        sub = kwargs.get('sub')
        text = kwargs.get('context')
        attFile = kwargs.get('xlsFile')

    ## 设置邮件发送地址
    mailFrom = conf.get('mail', 'from_mail') or mailTo
    
    ## SMTP相关配置
    smtpHost = conf.get('smtp', 'smtp_host')
    smtpUser = conf.get('smtp', 'smtp_user')
    smtpPass = conf.get('smtp', 'smtp_pass')
    smtpPort = conf.get('smtp', 'smtp_port')
    
    ## 定义SMTP类型
    smtpType = conf.get('smtp', 'smtp_type')

    ## 判断smtp端口
    if smtpType == 'ssl' and not smtpPort:
        smtpPort = 465
    elif not smtpPort:
        smtpPort = 25

    ## 初始化邮件标题和内容
    mail = MIMEMultipart('related')
    msg  = MIMEText(text.encode(unixCode),'html',unixCode)
    mail.attach(msg)

    mail['Subject'] = Header(sub, unixCode)
    mail['From']    = mailFrom
    mail['To']      = mailTo
    mail['Date']    = formatdate()

    ## 给邮件添加附件
    if attFile:
        ## excel, 图片为base64未加密文本.
        att = MIMEText(open(attFile, 'rb').read(), 'base64', winCode)
        att['Content-Type'] = 'application/octet-stream'
        att['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(attFile))
        mail.attach(att)

    ## 发送邮件
    try:
        if smtpType == 'ssl' :
            ## ssl的连接
            smtp = smtplib.SMTP_SSL(smtpHost,smtpPort)
            smtp.set_debuglevel(False)
            smtp.ehlo()
            smtp.login(smtpUser,smtpPass)
        else :
            ## smtp和tls的连接
            smtp = smtplib.SMTP(smtpHost,smtpPort)
            smtp.set_debuglevel(False)
    
            if smtpType == 'tls' :
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
    
            smtp.login(smtpUser,smtpPass)
    
        smtp.sendmail(mailFrom, mailTo, mail.as_string())
        smtp.close()
        logging.info(
            'SUCCESS. mailFrom={}, mailTo={}'.format(
            mailFrom, mailTo))
    except Exception as e:
        logging.error(
            'FAILURE. mailFrom={}, mailTo={}'.format(
            mailFrom, mailTo))
        logging.error(e)

## 运行函数
if __name__ == '__main__':
    main()
