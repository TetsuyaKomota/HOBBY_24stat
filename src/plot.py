import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
import re
import time
import yaml
import numpy as np
from datetime import datetime
from pyti.triangular_moving_average import triangular_moving_average

plt.rcParams["font.family"] = "MS Gothic"

labels = {
        "view": "視聴回数", 
        "like": "高評価数", 
        "dislike": "低評価数", 
        "comment": "コメント数", 
        }

def tma(data, l):
    d = list(triangular_moving_average(data, l))
    return d[l:-l]

def plot(data, label, video_name=None, B=5):
    l = max(len(data)//40, 1)
    tma1 = tma(data, l)
    tma2 = tma(data, 2*l)
    tma4 = tma(data, 4*l)
    plt.plot(data, color="skyblue")
    plt.ylabel(label)

    if video_name is not None:
        # idx = [i for i in range(len(tma4)) if data[i+4*l] > tma4[i]*10]
        idx = sorted(range(len(tma4)), key=lambda x: data[x+4*l] / tma4[x] if tma4[x] > 0 else 0)
        idx = idx[::-1][:B]
        for i in idx:
            plt.text(i+4*l, data[i+4*l], video_name[i+4*l])

    r = range(0, len(data), 2*l)
    t = [datetime.strptime(df.iloc[i].publish_time, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d") for i in r]
    plt.xticks(r, t, rotation=90, fontsize=7)

    ax = plt.twinx()
    ax.plot(tma1, color="blue")
    ax.plot(tma2, color="darkblue")


def load_config():
    with open("tmp/secret.yaml", "rt", encoding="utf-8") as f:
        conf = yaml.safe_load(f.read())
    return conf

if __name__ == "__main__":

    # API KEY や対象のチャンネルIDリストを取得
    conf = load_config()

    os.makedirs(conf["plot_dir"], exist_ok=True)

    
    for channel_id in conf["channel_id_list"]:
        print("execute ", channel_id)

        df = pd.read_csv(f"tmp/statistics/{channel_id}.tsv", sep="\t")

        if len(df) < 10:
            print("continue...")
            continue

        plt.figure(figsize=(20, 15))

        for i, l in enumerate(labels):
            plt.subplot(len(labels), 2, 2*i+1)
            plot(df[l], labels[l], list(df.video_name))
            
            if l == "view":
                continue
            plt.subplot(len(labels), 2, 2*i+2)
            plot(df[l] / df["view"], labels[l] + "/視聴回数")
            # plot(df[l] / df["view"], labels[l] + "/視聴回数", list(df.video_name))


        plt.subplot(4, 2, 2)
        plot(df.dislike / (df.like + df.dislike), "低評価率")

        # plt.subplot(4, 2, 1)
        # plt.title(df.iloc[0].channel_name, fontsize=18)

        # plt.savefig(os.path.join(conf["plot_dir"], f"{channel_id}.png"), bbox_inches='tight', pad_inches=0)
        title = re.sub("/", "／", df.iloc[0].channel_name)
        title = re.sub(r"\\", "", title)
        title = re.sub("\*", "", title)
        plt.savefig(os.path.join(conf["plot_dir"], f"{title}.png"), bbox_inches='tight', pad_inches=0.5)
        plt.close()
