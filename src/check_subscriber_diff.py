import pandas as pd
from glob import glob
import os
import yaml


def load_config():
    with open("tmp/secret.yaml", "rt", encoding="utf-8") as f:
        conf = yaml.safe_load(f.read())
    return conf



if __name__ == "__main__":

    # API KEY や対象のチャンネルIDリストを取得
    conf = load_config()

    for p in glob(os.path.join(conf["subscriber_count_dir"], "*.tsv")):
        df = pd.read_csv(p, sep="\t")
        sc = list(df.sort_values("dt").subscriber_count)
        if sc[-1] != sc[-2]:

            channel_name = df.iloc[0].channel_name
            diff         = sc[-1] - sc[-2]
            if diff > 0:
                diff = f"+{diff}"
            else:
                diff = f"{diff}"
            print(f"{df.iloc[0].channel_name}\t{diff}")
