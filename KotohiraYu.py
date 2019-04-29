#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kotohira Yu

YuzuRyo61 Presents

License: MIT License (See LICENSE)
"""

import threading
import sys
import os
import configparser

from mastodon import Mastodon

from Yu import Yu, KotohiraUtil, KotohiraMemory, local, home

config = configparser.ConfigParser()
config.read('config/config.ini')

mastodon = Mastodon(
    access_token='config/accesstoken.txt',
    api_base_url=config['instance']['address']
)

def main():
    # スレッド化するための初期化
    features = []
    # タイムライン系
    features.append( threading.Thread(target=local) )
    features.append( threading.Thread(target=home) )
    # cron系
    features.append( threading.Thread(target=KotohiraUtil.schedule, args=(Yu.timeReport,['**:00'])) )
    features.append( threading.Thread(target=KotohiraUtil.schedule, args=(Yu.meow_time, ['22:22'])) )

    try:
        # スレッド開始
        for ft in features:
            ft.start()
    except KeyboardInterrupt:
        # 動作する気はしない
        sys.exit()
    except:
        KotohiraUtil.PANIC()

if __name__ == '__main__':
    # 設定ファイルがあるかチェック。ない場合は弾く
    if os.path.isfile('config/config.ini') and os.path.isfile('config/accesstoken.txt'):
        # config.iniにあるIDと実際に取り寄せたIDが一致しない場合は弾く
        res = mastodon.account_verify_credentials()
        if config['user']['me'] != res.acct:
            print('＊設定したアカウントIDと一致しませんっ！！')
            sys.exit(1)

        # 問題なさそうであれば起動

        # データベース初期化
        km = KotohiraMemory(showLog=config['log'].getboolean('enable'))
        del km

        main()
    else:
        print('＊設定ファイルやアクセストークンがありませんっ！！')
        sys.exit(1)
