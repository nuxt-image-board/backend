from flask import Blueprint, jsonify, g
from datetime import datetime

def recordApiRequest(issuerUserID,logType,message=None,param1=None,param2=None,param3=None):
    '''API使用履歴をログに残す'''
    logDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    g.db.edit(
        "INSERT INTO `data_log`(`userID`,`logType`,`logDate`,`logMessage`,`logParam1`,`logParam2`,`logParam3`) VALUES (?,?,?,?,?,?,?)",
        (issuerUserID,logType,logDate,message,param1,param2,param3)
    )