# 飲食店PRO β — レビュー・試用手順

月額980円はβ価格案。課金、会員認証、通知送信は未実装。需要は実地検証待ち。

## 構成と公開との関係

確認日2026-10-03。基点 sapporo-events main 4f1dd6a45691cd549ff6706c4138969fbd0c6dc5。
AGENTS.mdは対象チェックアウトと作業ルートに無し。
sapporo-eventsは events.db（URL主キー、title/date_text/place/categories/first_seen/last_seen等）を読み、collectorがdata/index.htmlとupcoming.htmlを生成する。run_and_publish.batはPython3.14で収集後git add/commit/pushする。具体的なPages設定・URLはコードに無く、稼働公開先は未確認。
関連sapporo-inshokuのバッチには https://yasu1013siren-code.github.io/sapporo-inshoku/ が記載され、collector_ver72.pyとindex.html/news.jsonを利用する。両リポジトリの連携・コピー処理は確認できない。関連サイトを本件の公開先とは断定しない。
本変更はsapporo-eventsのみ。既存バッチ・collector・無料HTML・DBを変更せず、追加ページを直接試用できる構成。mainへマージ、本番公開は実施しない。

## ローカルで試用

リポジトリルートで `python pro/export.py` → `python -m http.server 8765` → http://localhost:8765/data/pro.html 。exportは標準ライブラリのみ、DBを読み取り専用で開く。新しい収集後にexportを再実行する。既存バッチに自動連動しないため、PROの更新は別操作が必要。
今週は日本時間の月〜日で終了分を除く。7〜30日先は両端含み、会期の重なりを表示。日付は年明記のみ解析し、年省略は日時不明へ。開催時刻の解析や来客・影響スコアは行わない。
中央区は明記住所と一部の特定会場、すすきのは名称表記で判定。収集元の「中央区」ラベルだけでは地区を確定しない。住所不明の取りこぼしはあり、全地区でも確認する。
重複は正規化タイトル・会期・会場が一致するものを統合し、最終収集日が新しい根拠を採用。表記ゆれ/会場違いの重複は残り得る。記事公開日を開催日に流用しない。last_seenは収集日であり、情報源自体の更新時刻ではない。出力更新日時は別に表示。
サツイベは転載禁止の記載を確認したため追加PRO出力から除外。既存無料サイトは変更しない。他ソースも販売前に二次利用条件を確認する必要がある。PROは本文要約を出力せず、タイトル・日付・会場・根拠リンク中心。
店舗設定は同一ブラウザのlocalStorageに保存。別端末同期なし。通知は表示条件のテキストプレビューとダウンロードのみ。送信契約・認証・送信処理なし。

## 検証コマンド

`python -m unittest discover -s tests -v` / `node tests/filter.mjs`。
年越し、省略会期、無効日付、年不明、重複、誤った収集元地区、危険URL、空DB、DB取得失敗時の出力保持、7日/30日境界、今週、終了済み、中央区とすすきの、日本時間の境界を検証。
上流収集はこの実行では再巡回していない。保存済みDBの最終収集日を画面に出す。通知配送・実際の決済・Windowsバッチ実行はテスト対象外。
