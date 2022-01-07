from flask import Flask, request, abort

from linebot import(
    LineBotApi, WebhookHandler
)
from linebot.exceptions import(
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
import os, re, requests
from datetime import datetime, timedelta

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    dateday0 = datetime.today()
    dateday0 = dateday0 + timedelta(hours=9)
    dateday1 = dateday0 + timedelta(days=1)
    dateday2 = dateday0 + timedelta(days=2)
    usertext = event.message.text
    searchday0 = re.search("今日|今夜", usertext)
    searchday1 = re.search("明日", usertext)
    searchday2 = re.search("あさって|明後日", usertext)
    datecount = None
    date = None

    #datecountは「0」で今日、「1」で明日、「2」で明後日となる
    if searchday0:
        datecount = 0
    if searchday1:
        datecount = 1
    if searchday2:
        datecount = 2

    #ユーザーの打った文章に地域の単語が含まれているかを確認するブーリアン
    searchnagano = re.search("長野",usertext)
    searchmatsumoto = re.search("松本",usertext)
    searchueda = re.search("上田",usertext)
    searchina = re.search("伊那",usertext)
    searchsaku = re.search("佐久",usertext)
    searchida = re.search("飯田",usertext)
    searchiyama = re.search("飯山",usertext)
    global locationString, locationKey
    locationString = None
    locationKey = None
    def setlocation(Key,Region):
        global locationString, locationKey
        locationKey = str(Key)
        locationString = str(Region)
    
    #特定地域のlocationKeyをAccuWeatherの天気予報ページから取得
    if searchnagano:
        setlocation("224701","長野市")
    elif searchmatsumoto:
        setlocation("219098","松本市")
    elif searchueda:
        setlocation("219099","上田市")
    elif searchina:
        setlocation("219092","伊那市")
    elif searchsaku:
        setlocation("219093","佐久市")
    elif searchida:
        setlocation("219097","飯田市")
    elif searchiyama:
        setlocation("219105","飯山市")
    
    #ユーザーの打った文章に単語が含まれているかを確認するブーリアン
    searchwhatweather = re.search("天気|気象|天候|状況",usertext)
    searchwhensunrise = re.search("日の出",usertext)
    searchwhensunset = re.search("日の入り",usertext)
    searchwhenmoonrise = re.search("月の出",usertext)
    searchwhenmoonset = re.search("月の入り",usertext)
    searchwhatmoonage = re.search("月齢",usertext)
    convtype = None
    if searchwhatweather:
        convtype = "whatweather"
    elif searchwhensunrise:
        convtype = "whensunrise"
    elif searchwhensunset:
        convtype = "whensunset"
    elif searchwhenmoonrise:
        convtype = "whenmoonrise"
    elif searchwhenmoonset:
        convtype = "whenmoonset"
    elif searchwhatmoonage:
        convtype = "whatmoonage"
    if datecount == 0:
        date = dateday0
    elif datecount == 1:
        date = dateday1
    elif datecount == 2:
        date = dateday2
    datenextdayday = int((date + timedelta(days=1)).strftime("%d"))        #dateの次の日の「日」
    date = str(int(date.strftime("%Y"))) + "年" + str(int(date.strftime("%m"))) + "月" + str(int(date.strftime("%d"))) + "日"

    #AccuweatherのForecast APIにアクセス
    url = 'http://dataservice.accuweather.com/forecasts/v1/daily/5day/' + locationKey + '自分のAPIキーを入力してください'
    weather_data = requests.get(url)        #レスポンスデータをjson形式で入手
    weather_datajson =weather_data.json()   #pythonのディクショナリ型にデコード
    if weather_data.status_code == 503:     #問い合わせ回数が50回を超えた場合
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="エラー：今日の問い合わせ回数上限に達しました。")
        )
    
    weather_datajson = weather_datajson["DailyForecasts"][datecount]     #「今日」or「明日」or「明後日」
    maxtemp = str(weather_datajson["Temperature"]["Maximum"]["Value"])   #最高気温
    mintemp = str(weather_datajson["Temperature"]["Minimum"]["Value"])   #最低気温
    dayweather = weather_datajson["Day"]["IconPhrase"]
    dayrainpro = str(weather_datajson["Day"]["RainProbability"])         #日中の降水確率
    daycloudcover = str(weather_datajson["Day"]["CloudCover"])           #日中の雲量
    nightweather = weather_datajson["Night"]["IconPhrase"]               #夜間の天気
    nightrainpro = str(weather_datajson["Night"]["RainProbability"])     #夜間の降水確率
    nightcloudcover = str(weather_datajson["Night"]["CloudCover"])       #夜間の雲量
    def timeFix(time):              #時間を[~時~日]と表記させるモジュール
        return str(int(time[:2])) + "時" + str(int(time[4:6])) + "分"
    sunrise = timeFix(weather_datajson["Sun"]["Rise"][11:16])            #日の出時刻
    sunset = timeFix(weather_datajson["Sun"]["Set"][11:16])              #日の入り時刻
    moonrise = timeFix(weather_datajson["Moon"]["Rise"][11:16])          #月の出時刻
    moonset = weather_datajson["Moon"]["Set"]                            #月の入り時刻(timeFixではない)
    moonsetDay = int(moonset[8:10])                                      #月の入り時刻の「日」
    moonset = timeFix(moonset[11:16])                                    #月の入り時刻(timeFix)
    if moonsetDay == datenextdayday:                                     #もし月の入り時刻の「日」が次の日なら
        moonset = "翌日" + moonset                                       #月の入り時刻に「翌日」を加える
    moonage = str(weather_datajson["Moon"]["Age"])                       #月齢取得

    #返信メッセージの内容を決定
    if convtype == "whatweather":               #もし会話の種類が「天気」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の天気予報です。\n\n"
                                        "最高気温は" + maxtemp + "℃、最低気温は" + mintemp + "℃でしょう。\n\n"
                                        "日中は" + dayweather + "でしょう。降水確率は" + dayrainpro + "％、雲量は" + daycloudcover + "％でしょう。\n\n"
                                        "夜間は" + nightweather + "でしょう。降水確率は" + nightrainpro + "％、雲量は" + nightcloudcover + "％でしょう。\n\n"
                                        "日の出は" + sunrise + "に、日の入りは" + sunset + "にあります。\n\n"
                                        "月の出は" + moonrise + "に、月の入りは" + moonset + "にあります。また、月齢は" + moonage + "です。") #返事する
                                )
    elif convtype == "whensunrise":     #もし会話の種類が「日の出はいつ」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の日の出は" + sunrise + "にあります。") #返事する
                            )
    elif convtype == "whensunset":      #もし会話の種類が「日の入りはいつ」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の日の入りは" + sunset + "にあります。") #返事する
                            )
    elif convtype == "whenmoonrise":    #もし会話の種類が「月の出はいつ」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の月の出は" + moonrise + "にあります。") #返事する
                            )
    elif convtype == "whenmoonset":     #もし会話の種類が「月の入りはいつ」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の日の出は" + moonset + "にあります。") #返事する
                            )
    elif convtype == "whatmoonage":     #もし会話の種類が「月齢は何」なら
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=date + "の" + locationString + "の月齢は" + moonage + "です。") #返事する
                            )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)