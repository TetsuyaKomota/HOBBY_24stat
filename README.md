# 24分析ツール

## 概要
- youtube とか twitter とかいじって分析ごっこするリポジトリ

### pick_statistics
- 指定したチャンネルの以下の情報を取得し，tsvにまとめる
    - チャンネル名
    - 登録者数
    - 直近の投稿動画
        - 投稿日時
        - 視聴回数
        - 高評価数
        - 低評価数
        - コメント数

- GCPで稼働させている
    - Cloud Scheduler -> Cloud Pub/Sub -> Cloud Funstions で定期実行
    - Cloud Storage に tsv を読み書き
    - Cloud Secret Manager から YoutubeAPIKey を取得
    - Cloud Build に連携してCICD

## 参考
- youtube api key の取得方法
    - https://qiita.com/iroiro_bot/items/1016a6a439dfb8d21eca
- Cloud Storage
    - https://sleepless-se.net/2018/05/22/googlecloudstorage%E3%81%A7python%E3%81%8B%E3%82%89%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%82%92%E3%82%84%E3%82%8A%E3%81%A8%E3%82%8A%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/
- Cloud Storage の python API
    - https://qiita.com/Hyperion13fleet/items/594c15ac24f149ab73c9
- Cloud Functions と Cloud Storage の連携
    - https://dev.classmethod.jp/articles/try-cloud-functions-scheduler-pubsub/
    - https://www.isoroot.jp/blog/2132/
- CloudSecretManager
    - https://cloud.google.com/secret-manager/docs/reference/libraries#client-libraries-install-python
    - https://www.apps-gcp.com/sm-with-gcf/
    - https://qiita.com/chun37/items/7e844ad982486705c32b

