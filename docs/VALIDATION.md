# 実行結果 — 2026-10-03

- Python unittest 3テスト PASS：年越し/省略会期/無効日/年不明、重複統合/地区判定/危険URL/制限ソース除外、空データ/読み取り失敗時に既存出力を保護。
- Node 5アサーション PASS：7日・30日の両端、終了除外、今週の上限と中央区/すすきの、年越し、JST日付境界、空配列。
- Python構文検証 PASS。保存済み実DBから743件出力、489件が年付き日付を解析。これは有効な今週件数や情報源の再取得成功件数ではない。
- 既存collector、run_and_publish.bat、index.html、upcoming.htmlの差分なし。
- スマホ390px、設定保存、DOM入力、危険リンク、空データ、fetch失敗のPlaywrightテストをtests/browser.cjsに用意したが、ブラウザ実体が環境に無く実行できなかった。インストール取得も不完全ZIPで失敗。これらは未検証であり、表示検証完了とは報告しない。
- 通知配送・課金・実店舗需要確認は未実施。

ブラウザ環境が整ったら、ルートでHTTPサーバー8765を起動し、PlaywrightをインストールしたNode環境でtests/browser.cjsを実行する。CODEX_PRIMARY_RUNTIME_NODE_MODULESが無い環境ではrequire先を通常のplaywrightパッケージに変更する。
