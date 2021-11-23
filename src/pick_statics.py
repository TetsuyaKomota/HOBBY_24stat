import os
import pandas as pd
import requests
import time
import yaml
from datetime import datetime

# チャンネルIDから以下を取得する
# - channel_name:     チャンネル名
# - subscriber_count: 登録者数
# - playlist_id:      アップロード動画リストID
def get_channel_info(conf, channel_id):
    channel_url = 'https://www.googleapis.com/youtube/v3/channels'
    param = {
        'key': conf["keys"]["youtube_data_api_key"], 
        'id': channel_id, 
        # 'forUsername': channel_id, 
        'part': 'snippet, contentDetails, statistics', 
    }

    req  = requests.get(channel_url, params=param)
    data =  req.json()
    if "items" not in data.keys():
        output = {}
        output["channel_name"]     = "ERROR"
        output["subscriber_count"] = 0
        output["playlist_id"]      = []
        return output

    data =  req.json()["items"][0]

    output = {}
    output["channel_name"]     = data["snippet"]["title"]
    output["subscriber_count"] = data["statistics"]["subscriberCount"]
    output["playlist_id"]      = data["contentDetails"]["relatedPlaylists"]["uploads"]
    return output


# アップロード動画リストIDから以下を取得する
# - video_id_list: アップロード動画IDのリスト
def get_video_id_list(conf, playlist_id, wait_time=0.1):
    def sub_get_playlist_info(playlist_id, pageToken):
        playlist_url = 'https://www.googleapis.com/youtube/v3/playlistItems'
        param = {
            'key': conf["keys"]["youtube_data_api_key"], 
            'playlistId': playlist_id, 
            'part': 'contentDetails', 
            'maxResults': '50', 
            'pageToken': pageToken, 
        }

        req = requests.get(playlist_url, params=param)
        return req.json()

    # 動画IDのリスト格納用の変数
    video_id_list = []

    # pageTokenに空文字列を渡すと何も指定していないのと同じになる
    res = {"nextPageToken": ""}
    while "nextPageToken" in res:
        pageToken = res["nextPageToken"]
        res = sub_get_playlist_info(playlist_id, pageToken)
        # 今までの結果と今回の結果をマージする
        video_id_list += [ item["contentDetails"]["videoId"] for item in res.get("items", []) ]
        time.sleep(wait_time)
    return video_id_list

# アップロード動画IDのリストから以下のDataFrameを取得する
# - video_id:     動画ID
# - video_name:   動画タイトル
# - publish_time: 投稿日時
# - view:         視聴回数
# - like:         高評価回数
# - dislike:      低評価回数
# - comment:      コメント数
def get_video_list(conf, video_id_list):
    def sub_get_video_list(video_id_list):
        video_url = 'https://www.googleapis.com/youtube/v3/videos'
        param = {
            'key': conf["keys"]["youtube_data_api_key"], 
            'id': ','.join(video_id_list), 
            # 'part': 'snippet, contentDetails, statistics', 
            'part': 'snippet, statistics', 
        }

        req = requests.get(video_url, params=param)
        return req.json()

    # 取得する動画について順番にAPIを叩いていく
    # uploaded_video_id_listにvideo IDが格納されている前提
    # maxResultsに合わせて50単位でループを回していく
    video_list = []
    while video_id_list:
        req_list = video_id_list[:50]
        video_id_list = video_id_list[50:]
        video_list_result = sub_get_video_list(req_list)

        for item in video_list_result["items"]:
            video = {}
            video["video_id"]     = item["id"]
            video["video_name"]   = item["snippet"]["title"]
            video["publish_time"] = datetime.strptime(item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
            video["view"]         = item["statistics"].get("viewCount", 0)
            video["like"]         = item["statistics"].get("likeCount", 0)
            video["dislike"]      = item["statistics"].get("dislikeCount", 0)
            video["comment"]      = item["statistics"].get("commentCount", 0)
            video_list.append(video)
    df = pd.DataFrame(video_list)
    if len(df) > 0:
        df = df.sort_values("publish_time")
    return df


def load_config():
    with open("tmp/secret.yaml", "rt", encoding="utf-8") as f:
        conf = yaml.safe_load(f.read())
    return conf

if __name__ == "__main__":

    # API KEY や対象のチャンネルIDリストを取得
    conf = load_config()

    os.makedirs(conf["statistics_dir"], exist_ok=True)
    os.makedirs(conf["subscriber_count_dir"], exist_ok=True)

    current_date = datetime.now()

    # 全ての対象チャンネルに対して実行
    for channel_id in conf["channel_id_list"]:
        print("execute ", channel_id)
        # 取得済みの統計情報を取得
        if os.path.exists(os.path.join(conf["statistics_dir"], f"{channel_id}.tsv")):
            df = pd.read_csv(os.path.join(conf["statistics_dir"], f"{channel_id}.tsv"), sep="\t")
        else:
            df = pd.DataFrame()

        # 最新情報を取得
        channel_info  = get_channel_info(conf, channel_id)
        video_id_list = get_video_id_list(conf, channel_info["playlist_id"])
        video_data    = get_video_list(conf, video_id_list)

        video_data["channel_id"]       = channel_id
        video_data["channel_name"]     = channel_info["channel_name"]
        video_data["subscriber_count"] = channel_info["subscriber_count"]

        # 最新情報に上書き
        df = pd.concat([df, video_data], sort=True)
        df = df.drop_duplicates("video_id", keep="last")

        # 保存
        if len(df) > 0:
            cols = [
                    "channel_id", 
                    "channel_name", 
                    "subscriber_count", 
                    "video_id", 
                    "video_name", 
                    "publish_time", 
                    "view", 
                    "like", 
                    "dislike", 
                    "comment", 
                    ]
            df = df[cols]
        df.to_csv(os.path.join(conf["statistics_dir"], f"{channel_id}.tsv"), sep="\t", index=None)

        # 登録者数更新
        path = os.path.join(conf["subscriber_count_dir"], f"{channel_id}.tsv")
        if not os.path.exists(path):
            with open(path, "wt", encoding="utf-8") as f:
                f.write("channel_id\tchannel_name\tdt\tsubscriber_count\n")
        with open(path, "at", encoding="utf-8") as f:
            o = [
                    channel_id, 
                    channel_info["channel_name"], 
                    current_date.strftime("%Y-%m-%d %H:%M:%S"), 
                    channel_info["subscriber_count"], 
                ]
            f.write("\t".join([str(d) for d in o]) + "\n")
