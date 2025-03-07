# -*- coding: utf-8 -*-
import configparser
import re

from mastodon import Mastodon, StreamListener

from Yu import KotohiraMemory, KotohiraUtil, YuChan

config = configparser.ConfigParser()
config.read('config/config.ini')

mastodon = Mastodon(
    access_token='config/accesstoken.txt',
    api_base_url=config['instance']['address']
)

# ホームタイムラインのリスナー(主に通知リスナー)
class user_listener(StreamListener):
    def on_update(self, status):
        try:
            # 公開範囲が「公開」であればここのリスナーでは無視する
            if status['visibility'] == 'public':
                return
            
            # 連合アカウントである場合(@が含まれている)は無視する
            if status['account']['acct'].find('@') != -1:
                return

            # Botアカウントは応答しないようにする
            if status['account']['bot'] == True:
                return

            # 自分のトゥートは無視
            if config['user']['me'] == status['account']['acct']:
                return

            # トゥート内のHTMLタグを除去
            txt = KotohiraUtil.h2t(status['content'])

            # 自分宛てのメンションはここのリスナーでは無視する（ユーザー絵文字の場合は例外）
            isMeMention = re.search('(?!.*:)@({}+)(?!.*:)'.format(config['user']['me']), txt)
            if isMeMention:
                return
            
            # データベース初期化
            memory = KotohiraMemory(showLog=config['log'].getboolean('enable'))

            calledYuChan = re.search(r'(琴平|ことひら|コトヒラ|ｺﾄﾋﾗ|れい|れぃ|レイ|レィ|ﾚｲ|ﾚｨ|:@' + config['user']['me'] + ':)', txt)

            # レイちゃん etc... とか呼ばれたらふぁぼる
            if calledYuChan:
                print('呼ばれたっ！：@{0} < {1}'.format(status['account']['acct'], txt))
                mastodon.status_favourite(status['id'])
                # 好感度ちょいアップ
                memory.update('fav_rate', 1, status['account']['id'])

        except Exception as e:
            # Timelines.pyの方へエラーを送出させる
            raise e
        finally: # 必ず実行
            try:
                del memory # データベースロック防止策、コミットする
            except NameError: # 定義されていなくてもエラーを出さない
                pass

    def on_notification(self, notification):
        try:
            # bot属性のアカウントの場合は無視する
            if notification['account']['bot'] == True:
                return

            # 連合アカウントである場合(@が含まれている)は無視する
            if notification['account']['acct'].find('@') != -1:
                return

            # 代入してちょっと見栄え良く
            notifyType = notification['type']
            if notifyType == 'mention':
                # 返信とか

                memory = KotohiraMemory(showLog=config['log'].getboolean('enable'))

                # 知っているユーザーであるか
                # 知らないユーザーの場合はここで弾く
                if len(memory.select('fav_rate', notification['account']['id'])) == 0:
                    return

                # テキスト化
                txt = KotohiraUtil.h2t(notification['status']['content'])

                # 口頭のメンションを除去
                txt = re.sub('^(@[a-zA-Z0-9_]+)?(\s|\n)*', '', txt)

                # とりあえずふぁぼる
                print('お手紙っ！：@{0} < {1}'.format(notification['account']['acct'], txt))
                mastodon.status_favourite(notification['status']['id'])

                # NGワードを検知した場合は弾いて好感度下げ
                if YuChan.ngWordHook(txt):
                    print('変なこと言っちゃダメ～！！(*`ω´*): @{0}'.format(notification['account']['acct']))
                    memory.update('fav_rate', -5, notification['account']['id'])
                    time.sleep(0.5)
                    mastodon.status_post('@{}\n変なこと言っちゃダメ～！！(*`ω´*)'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                    YuChan.unfollow_attempt(notification['account']['id'])
                    return

                # 好感度を少し上げる
                memory.update('fav_rate', 1, notification['account']['id'])

                # 正規表現とか
                followReq = re.search(r'(フォロー|[Ff]ollow|ふぉろー)(して|.?頼(む|みたい|もう)|.?たの(む|みたい|もう)|お願い|おねがい)?', txt)
                fortune = re.search(r'(占|うらな)(って|い)', txt)
                showNick = re.search(r'(ぼく|ボク|僕|わたし|ワタシ|私|俺|おれ|オレ|うち|わし|あたし|あたい)の(ニックネーム|あだな|あだ名|名前|なまえ)', txt)
                deleteNick = re.search(r'^(ニックネーム|あだ名)を?(消して|削除|けして|さくじょ)', txt)
                otherNick = re.search(r'^:@([a-zA-Z0-9_]+):\sの(あだ名|あだな|ニックネーム)[:：は]\s?(.+)', txt)
                nick = re.search(r'^(あだ(名|な)|ニックネーム)[:：は]\s?', txt)
                rspOtt = re.search(r'じゃんけん\s?(グー|✊|👊|チョキ|✌|パー|✋)', txt)
                isPing = re.search(r'[pP][iI][nN][gG]', txt)
                love = re.search(r'(すき|好き|しゅき|ちゅき)', txt)

                # メンションでフォローリクエストされたとき
                if followReq:
                    reqRela = mastodon.account_relationships(notification['account']['id'])[0]
                    # フォローしていないこと
                    if reqRela['following'] == False:
                        if reqRela['followed_by'] == True: # フォローされていること
                            reqMem = memory.select('fav_rate', notification['account']['id'])[0]
                            if int(reqMem[2]) >= int(config['follow']['condition_rate']): # 設定で決めた好感度レート以上だったら合格
                                print('フォローっ！：@{}'.format(notification['account']['acct']))
                                mastodon.account_follow(notification['account']['id'])
                                mastodon.status_post('@{}\nフォローしだよっ！これからもよろしくねっ！'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                            else: # 不合格の場合はレスポンスして終了
                                print('もうちょっと仲良くなってからっ！：@{}'.format(notification['account']['acct']))
                                mastodon.status_post('@{}\nもうちょっと仲良くなってからっ！'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                        else:
                            print('先にフォローしてっ！:@{}'.format(notification['account']['acct']))
                            mastodon.status_post('@{}\n私をフォローしてくれたら考えるねっ！'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                    else: # フォローしている場合は省く
                        print('フォロー済みっ！：@{}'.format(notification['account']['acct']))
                        mastodon.status_post('@{}\nもうフォローしてるよっ！'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                
                # 占いのリクエストがされたとき
                elif fortune:
                    YuChan.fortune(notification['status']['id'], notification['account']['acct'], notification['status']['visibility'])
                    # 更に４つ加算
                    memory.update('fav_rate', 4, notification['account']['id'])

                # ニックネームの照会
                elif showNick:
                    YuChan.show_nickname(notification['status']['id'], notification['account']['id'], notification['account']['acct'], notification['status']['visibility'], memory)

                # ニックネームの削除
                elif deleteNick:
                    YuChan.del_nickname(notification['status']['id'], notification['account']['id'], notification['account']['acct'], notification['status']['visibility'], memory)

                # 他人のニックネームの設定
                elif otherNick:
                    YuChan.set_otherNickname(txt, notification['status']['id'], notification['account']['id'], notification['account']['acct'], notification['status']['visibility'], memory)

                # ニックネームの設定
                elif nick:
                    YuChan.set_nickname(txt, notification['status']['id'], notification['account']['id'], notification['account']['acct'], notification['status']['visibility'], memory)

                # レイちゃんとじゃんけんっ！
                elif rspOtt:
                    YuChan.rsp(txt, notification)
                    # 更に４つ加算
                    memory.update('fav_rate', 4, notification['account']['id'])

                # 応答チェッカー
                elif isPing:
                    print('PINGっ！：@{}'.format(notification['account']['acct']))
                    mastodon.status_post('@{}\nPONG!'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])

                elif love:
                    reqMem = memory.select('fav_rate', notification['account']['id'])[0]
                    if int(reqMem[2]) >= int(config['follow']['condition_rate']):
                        print('❤：@{}'.format(notification['account']['acct']))
                        mastodon.status_post('@{}\nレイちゃんも好きっ！❤'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
                    elif int(reqMem[2]) < 0:
                        print('...: @{}'.format(notification['account']['acct']))
                    else:
                        print('//：@{}'.format(notification['account']['acct']))
                        mastodon.status_post('@{}\nは、恥ずかしいよっ・・・//'.format(notification['account']['acct']), in_reply_to_id=notification['status']['id'], visibility=notification['status']['visibility'])
            
            elif notifyType == 'favourite':
                # ふぁぼられ
                print('ふぁぼられたっ！：@{0}'.format(notification['account']['acct']))
                # ふぁぼ連対策
                memory = KotohiraMemory(showLog=config['log'].getboolean('enable'))
                favInfo = memory.select('recent_favo', notification['account']['id'])
                if len(favInfo) == 0:
                    # データがない場合は追加して好感度アップ
                    memory.insert('recent_favo', notification['account']['id'], notification['status']['id'])
                    memory.update('fav_rate', 1, notification['account']['id'])
                else:
                    # 最後にふぁぼったトゥートが同じものでないこと
                    if notification['status']['id'] != favInfo[0][2]:
                        memory.update('recent_favo', notification['status']['id'], notification['account']['id'])
                        memory.update('fav_rate', 1, notification['account']['id'])

            
            elif notifyType == 'reblog':
                # ブーストされ
                print('ブーストされたっ！：@{0}'.format(notification['account']['acct']))
                # ふぁぼられと同様な機能とか
            
            elif notifyType == 'follow':
                # フォローされ
                print('フォローされたっ！：@{0}'.format(notification['account']['acct']))
        except Exception as e:
            # Timelines.pyの方へエラーを送出させる
            raise e
        finally: # 必ず実行
            try:
                del memory # データベースロック防止策、コミットする
            except NameError: # 定義されていなくてもエラーを出さない
                pass
