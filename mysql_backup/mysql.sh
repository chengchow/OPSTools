#!/bin/bash

SIGN=mysql
HOME=/data/software/mysql
DATA_DIR=/data/database/mysql3306
BACKUP_BASE=/data/backup/$SIGN
DEFAULT_FILE=/etc/my.cnf
ADMIN_USER=root
ADMIN_GROUP=root
INNOBACKUPEX_FILE=/usr/bin/innobackupex
BINLOG_PREFIX=mysql-bin
LOG_PATH=/data/logs

BACKUP_USER=net100_backup   ##需要权限select, reload, process, supper, replication client
BACKUP_PASS=ahAaFtDt6NL8i
BACKUP_HOST=localhost
SOCKET_FILE=/tmp/mysql.sock

FULL_BASE=$BACKUP_BASE/full
INCREMENT_BASE=$BACKUP_BASE/increment

NOW_WEEKLY=$(date +%Y)_$(date +%W)
DAY_OF_THE_WEEK=$(date +%u)
EXPIRATION_TIME=14

FULL_PATH=$FULL_BASE/$NOW_WEEKLY
INCREMENT_PATH=$INCREMENT_BASE/$NOW_WEEKLY/$DAY_OF_THE_WEEK

if [ ! -x $INNOBACKUPEX_FILE ];then
    [ -x /usr/bin/innobackupex ] && INNOBACKUPEX_FILE=/usr/bin/innobackupex
fi

if [ ! -x $INNOBACKUPEX_FILE ];then
    echo -e "系统没有检测到Percona Xtrabackup安装文件."
    exit 1
fi

sudo mkdir -p $LOG_PATH/backup/$SIGN && sudo chown -R $ADMIN_USER:$ADMIN_PASS $LOG_PATH/backup/$SIGN
sudo mkdir -p $BACKUP_BASE && sudo chown -R $ADMIN_USER:$ADMIN_PASS $BACKUP_BASE

if [ -x "$HOME/bin/mysql" ];then
    MYSQL=$HOME/bin/mysql
else
    MYSQL=mysql
fi

binary_log_clean () {
    MYSQL_LOGN="$MYSQL -u$BACKUP_USER -p$BACKUP_PASS -S$SOCKET_FILE -h$BACKUP_HOST"
    PURGE_SIGN=$(sudo /bin/find $DATA_DIR -type f -mtime +$EXPIRATION_TIME -name "$BINLOG_PREFIX*" ! -name "*.index" | awk -F '.' '{if($NF>last){last=$NF}}END{print last}')
    if [ ! -z $PURGE_SIGN ];then
        PURGE_FILE=${BINLOG_PREFIX}.${PURGE_SIGN}
        $MYSQL_LOGN -e "purge binary logs to \"$PURGE_FILE\""
    fi

}

full_backup () {
    if [ ! -d $FULL_PATH ];then
        echo -e "开始完整备份, `date +%Y-%m-%d`"
        sudo /bin/mkdir -p $FULL_PATH
        sudo /bin/chown -R $ADMIN_USER:$ADMIN_GROUP $FULL_PATH
        sudo $INNOBACKUPEX_FILE --defaults-file=$DEFAULT_FILE --user=$BACKUP_USER --password=$BACKUP_PASS --socket=$SOCKET_FILE \
                                --no-timestamp $FULL_PATH
        sudo chown -R $ADMIN_USER:$ADMIN_GROUP $BACKUP_BASE
        RETAVL=$?
        [ $RETAVL = 0 ] && /bin/find $BACKUP_BASE -type f -mtime +$EXPIRATION_TIME -exec /bin/rm -rf {} \;
        [ $RETAVL = 0 ] && binary_log_clean
    fi
    /bin/rm -rf $(du -sh $FULL_BASE * | awk '$1==0{print $2}')
    /bin/rm -rf $(du -sh $INCREMENT_BASE * | awk '$1==0{print $2}')
    echo;echo
}

increment_backup () {
    if [ -d $FULL_PATH ] && [ ! -d $INCREMENT_PATH ];then
        echo -e "开始增量备份, `date +%Y-%m-%d`"
        sudo /bin/mkdir -p $INCREMENT_PATH
        sudo /bin/chown -R $ADMIN_USER:$ADMIN_GROUP $INCREMENT_PATH
        sudo $INNOBACKUPEX_FILE --defaults-file=$DEFAULT_FILE --user=$BACKUP_USER --password=$BACKUP_PASS  --socket=$SOCKET_FILE \
                                --incremental --no-timestamp --incremental-basedir=$FULL_PATH $INCREMENT_PATH
        sudo chown -R $ADMIN_USER:$ADMIN_GROUP $BACKUP_BASE
        RETAVL=$?
    elif [ ! -d $FULL_PATH ] && [ ! -d $INCREMENT_PATH ];then
        echo -e "首次完整备份, `date +%Y-%m-%d`"
        sudo /bin/mkdir -p $INCREMENT_PATH
        sudo /bin/chown -R $ADMIN_USER:$ADMIN_GROUP $INCREMENT_PATH
        sudo $INNOBACKUPEX_FILE --defaults-file=$DEFAULT_FILE --user=$BACKUP_USER --password=$BACKUP_PASS --socket=$SOCKET_FILE \
                                --no-timestamp $FULL_PATH
        sudo chown -R $ADMIN_USER:$ADMIN_GROUP $BACKUP_BASE
        RETAVL=$?
        [ $RETAVL = 0 ] && binary_log_clean
    fi
    echo;echo
}

let TYPE=$DAY_OF_THE_WEEK%7

if [ $TYPE = 1 ];then
    full_backup >> $LOG_PATH/backup/$SIGN/${SIGN}.log 2>&1
else
    increment_backup >>$LOG_PATH/backup/$SIGN/${SIGN}.log 2>&1
fi

[ -f "$LOG_PATH/backup/$SIGN/${SIGN}.log" ] && sed -ri '/1000000/,$d' $LOG_PATH/backup/$SIGN/${SIGN}.log

exit 0
