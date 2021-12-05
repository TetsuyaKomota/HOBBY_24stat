import os
import pandas as pd
import requests
import time
import yaml
from datetime import datetime
from glob import glob
import base64

from google.cloud import secretmanager
from google.cloud import storage as gcs
import tempfile

# GCS上に配置したファイルのディレクトリ名とファイル名の区切り
SEP = "@"

# チャンネルIDから以下を取得する
# - channel_name:     チャンネル名
# - subscriber_count: 登録者数
# - playlist_id:      アップロード動画リストID
def get_channel_info(conf, channel_id):
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    id_key = "id" if channel_id.startswith("UC") else "forUsername"
    param = {
        "key": conf["keys"]["youtube_data_api_key"],
        id_key: channel_id,
        "part": "snippet, contentDetails, statistics",
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
        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        param = {
            "key": conf["keys"]["youtube_data_api_key"],
            "playlistId": playlist_id,
            "part": "contentDetails",
            "maxResults": "50",
            "pageToken": pageToken,
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
        video_url = "https://www.googleapis.com/youtube/v3/videos"
        param = {
            "key": conf["keys"]["youtube_data_api_key"],
            "id": ",".join(video_id_list),
            "part": "snippet, statistics",
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

        for item in video_list_result.get("items", []):
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
    with open("secret.yaml", "rt", encoding="utf-8") as f:
        conf = yaml.safe_load(f.read())
    return conf

# Secret Manager から secret を読み込んで conf に追記する
def load_secret(conf):
    conf["keys"] = {}
    client = secretmanager.SecretManagerServiceClient()
    project_id  = conf["gcp"]["project_id"]
    for key in conf["gcp"]["secrets"].keys():
        secret_name = conf["gcp"]["secrets"][key]["name"]
        secret_ver  = conf["gcp"]["secrets"][key]["version"]
        name        = client.secret_version_path(project_id, secret_name, secret_ver)
        response    = client.access_secret_version(name=name)
        conf["keys"][key] = response.payload.data.decode('UTF-8')
    return conf

def main(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message     = base64.b64decode(event['data']).decode('utf-8')
    print(pubsub_message)
    data               = pubsub_message.split("-")
    begin_idx          = int(data[0])
    end_idx            = int(data[1]) if len(data) >= 1 and len(data[1]) > 0 else None
    for_local          = (len(data) >= 2 and data[2]=="local")

    # API KEY や対象のチャンネルIDリストを取得
    conf = load_config()
    conf = load_secret(conf)

    if for_local:
        client = gcs.Client.from_service_account_json(conf["gcp"]["credentials_path"])
    else:
        client = gcs.Client()
    bucket = client.bucket(conf["gcp"]["bucket"])

    with tempfile.TemporaryDirectory() as tempdir:

        os.makedirs(os.path.join(tempdir, conf["statistics_dir"]))
        os.makedirs(os.path.join(tempdir, conf["subscriber_count_dir"]))

        # GCS上のファイルをダウンロード
        for path in client.list_blobs(conf["gcp"]["bucket"]):
            if len(path.name.split(SEP)) != 2:
                continue
            dir_name, file_name = path.name.split(SEP)
            if dir_name not in ["statistics_dir", "subscriber_count_dir"]:
                continue
            blob = bucket.get_blob(path.name)
            blob.download_to_filename(os.path.join(tempdir, conf[dir_name], file_name))
            print("download: ", path.name, dir_name, file_name)

        current_date = datetime.now()

        # 全ての対象チャンネルに対して実行
        for channel_id in conf["channel_id_list"][begin_idx:end_idx]:
            print("execute ", channel_id)
            # 取得済みの統計情報を取得
            if os.path.exists(os.path.join(tempdir, conf["statistics_dir"], f"{channel_id}.tsv")):
                df = pd.read_csv(os.path.join(tempdir, conf["statistics_dir"], f"{channel_id}.tsv"), sep="\t")
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
            df.to_csv(os.path.join(tempdir, conf["statistics_dir"], f"{channel_id}.tsv"), sep="\t", index=None)
            blob = bucket.blob(SEP.join(["statistics_dir", f"{channel_id}.tsv"]))
            blob.upload_from_filename(os.path.join(tempdir, conf["statistics_dir"], f"{channel_id}.tsv"))

            # 登録者数更新
            path = os.path.join(tempdir, conf["subscriber_count_dir"], f"{channel_id}.tsv")
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
            blob = bucket.blob(SEP.join(["subscriber_count_dir", f"{channel_id}.tsv"]))
            blob.upload_from_filename(path)
    return "OK"

if __name__ == "__main__":
    main({"data": base64.b64encode(b"0-10-local")}, None)
