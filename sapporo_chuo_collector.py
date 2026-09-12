# -*- coding: utf-8 -*-
r"""
sapporo_chuo_collector(10).py
==========================
札幌市中央区の「飲食・アニメ・ポップアップ・音楽ライブ・映画」情報を毎日自動収集するツール。

【できること】
  - 複数の情報サイト＋商業施設公式サイトを巡回し、イベント/ライブ/ポップアップ情報を取得
  - 飲食・アニメ・音楽ライブに関係する情報だけに自動で絞り込み
  - 環境変数 GEMINI_API_KEY を設定していれば、Gemini AI(無料枠)がキーワードだけ
    では判断しづらいケースも判定し、SNS/ブログにそのまま使える紹介文も生成する
    （未設定の場合はこれまで通りキーワードのみで判定、動作に支障なし）
  - これまでに集めた情報を SQLite DB に蓄積し、重複を自動で排除（URL単位）
  - 実行するたびに data/index.html を更新 → ブラウザで見やすく確認できる
  - 通知（メール/LINE/Slack等）は一切送信しない。ファイル更新のみ。

【対象サイト（初期設定）】
  1. サツイベ（札幌イベント情報マガジン）中央区ページ　※中央区限定
     https://sapporo.magazine.events/area/chuou-ku
     さっぽろオータムフェストのような大通公園の大型フェスも、開催が近づき
     このサイトに掲載されればここで自動的に拾われます。
  2. チ・カ・ホ（札幌駅前通地下広場）イベント一覧　※会場自体が中央区
     https://www.sapporo-chikamichi.jp/event/
  3. cube garden（中央区北2東3のライブハウス）LIVEスケジュール　※中央区限定
     https://www.cube-garden.com/live.php
  4. ウォーカープラス　札幌市の「ライブ・音楽イベント」　※市内広域
     https://www.walkerplus.com/event_list/ar0101100/sapporo/eg0109/
     ラルクアンシエルのようなメジャーアーティストの公演は、hitaru・Zepp
     Sapporo・きたえーるなど中央区外の大規模会場で行われることが多いため、
     この情報源だけは「札幌市内」全体を対象にしています。
     ただし「音楽ライブ」カテゴリへの採用は、きたえーる/hitaru/Zepp Sapporo等の
     大型会場名、または「全国ツアー」「ワンマン」等メジャー公演を示す語句を
     含むものだけに絞っています（小規模ライブは対象外）。
  5. ウォーカープラス　札幌市の「アニメ・ゲーム」イベント　※市内広域
     https://www.walkerplus.com/event_list/ar0101100/sapporo/eg0127/
     採用は「原画展」「POP UP」「コラボカフェ」等の展示・物販系のみに絞り、
     声優イベント・上映会・舞台挨拶などは除外しています。
  6. 札幌三越（中央区南1条西3）公式サイトの催事情報
     https://www.mitsukoshi.mistore.jp/sapporo.html
  7. 丸井今井札幌本店（中央区南1条西2）公式サイトの催事情報
     https://www.maruiimai.mistore.jp/sapporo.html
  7.5 サッポロファクトリー（中央区北2条東4丁目、大型複合商業施設）公式サイトの
      イベント情報。デパートと同様「デパート催事」として扱う。
     https://sapporofactory.jp/event/
  8. 札幌市内の主要映画館（ユナイテッド・シネマ札幌/札幌シネマフロンティア/
     シアターキノ/TOHOシネマズすすきの。いずれも中央区）の上映中アニメ映画
     https://press.moviewalker.jp/theater/108/
  9. 札幌PARCO／札幌ステラプレイス／アピア　各公式サイトのポップアップ・
     期間限定ショップ情報（ジャンル不問。POP UP/期間限定ショップ等と確認できるもの）
  10. 大丸札幌店　公式SHOP BLOG（テナント各店のお知らせ記事一覧）
      https://shopblog.dmdepart.jp/sapporo/
      （大丸札幌店本体の「イベントカレンダー」はJavaScriptで動的生成されるため
       引き続き取得できないが、SHOP BLOGは静的HTMLのため取得可能）
  11. 狸小路商店街（moyuk SAPPORO含む）公式サイトの「ニュース&イベント」
      https://tanukikoji.or.jp/news-event/

  必要に応じて SOURCES 辞書に情報源を追加/削除してください。
  カテゴリ判定の基準は CATEGORY_INCLUDE / CATEGORY_EXCLUDE で調整できます。

【セットアップ】
    py -m pip install requests beautifulsoup4 lxml

【AI判定を使う場合（任意）】
    環境変数 GEMINI_API_KEY にAPIキーを設定してください（クレジットカード不要の
    無料枠で利用可能）。取得方法: https://aistudio.google.com/ → 「Get API key」
    Windowsでの設定例:
        setx GEMINI_API_KEY "取得したキー"
    設定後はコマンドプロンプトを開き直してください。
    設定しない場合は、これまで通りキーワードのみの判定で動作します。

【実行】
    py sapporo_chuo_collector.py

  実行するたびに以下が更新されます:
    - data/events.db      … 蓄積データベース（重複排除済み全件）
    - data/index.html     … ★ブラウザで開いて確認するレポート（最新状態に上書き）
    - data/new_YYYY-MM-DD.csv … その日新しく見つかった対象情報（Excel用）
    - collector.log       … 実行ログ

【毎日自動実行する方法】

  ■ Windows（コマンド1つで登録・タスクスケジューラ）
    コマンドプロンプトで以下を実行（パスは自分の環境に合わせて変更）。
    毎朝7時に自動実行されるようになります。

      schtasks /create /tn "SapporoChuoCollector" ^
        /tr "py -3.14 C:\Users\user\Downloads\sapporo_chuo_collector.py" ^
        /sc daily /st 07:00

    確認:   schtasks /query /tn "SapporoChuoCollector"
    削除:   schtasks /delete /tn "SapporoChuoCollector" /f

  ■ Linux / macOS (cron)
    crontab -e で以下を1行追加（毎朝7時の例）
      0 7 * * * /usr/bin/python3 /path/to/sapporo_chuo_collector.py >> /path/to/collector.log 2>&1

  自動実行後は、いつでも data/index.html をダブルクリックして
  ブラウザで最新のイベント一覧を確認できます（通知は出ません）。
"""

import csv
import json
import logging
import os
import re
import sqlite3
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "events.db"
LOG_PATH = BASE_DIR / "collector.log"
HTML_PATH = DATA_DIR / "index.html"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SapporoChuoCollector/1.0; +personal-use-script)"
}
REQUEST_TIMEOUT = 60
REQUEST_INTERVAL_SEC = 1.5  # 相手サーバーへの配慮（連続アクセスの間隔）

# 収集後にどのカテゴリに分類するか（かなり絞り込んだ基準）
# CATEGORY_INCLUDE: これらの語句を含んでいれば、そのカテゴリの候補にする
# CATEGORY_EXCLUDE: これらの語句を含んでいたら、候補から除外する
CATEGORY_INCLUDE = {
    "🍜 飲食": [
        "グルメフェス", "フードフェス", "マルシェ", "物産展", "食べ歩き", "食べ比べ",
        "スイーツイベント", "スイーツフェス", "デザートフェス", "ラーメンフェス", "肉フェス",
        "餃子フェス", "ビアガーデン", "日本酒", "ワイン", "クラフトビール", "オータムフェスト", "雪まつり",
        "コーヒーフェス", "コーヒーイベント", "コーヒーフェスティバル", "コーヒーペアリング", "カフェイベント", "カフェコラボ",
        "期間限定カフェ", "ラテアート",
    ],
    "🎮 アニメ": [
        "アニメ展示会", "アニメ原画展", "原画展", "複製原画展", "コラボカフェ",
    ],
    "🛍️ ポップアップストア": [
        "POP UP", "POP-UP", "ポップアップ", "ポップアップストア",
        "期間限定ショップ", "期間限定店", "期間限定ストア",
        "POP UP SHOP", "POPUP SHOP", "POP UP STORE", "POPUP STORE",
    ],
    "🎵 音楽ライブ": [
        "きたえーる", "hitaru", "Zepp Sapporo", "札幌ドーム", "真駒内セキスイハイムアイスアリーナ",
        "全国ツアー", "アリーナツアー", "ドームツアー", "JAPAN TOUR", "TOUR", "ワンマン",
    ],
    "🎬 映画": ["映画上映中"],  # 中央区内の主要映画館で上映中の全作品（collect_movie_theaters()がタグ付け）
    "🍿 公開予定映画": ["公開予定映画"],  # 2ヶ月以内に公開予定の映画（collect_upcoming_movies()がタグ付け）
}

CATEGORY_EXCLUDE = {
    "🍜 飲食": ["レストラン", "居酒屋"],  # 普通の飲食店の宣伝は除外（"カフェ"は単体では除外しない。"カフェイベント"等の
                                       # 具体的なイベント名だけを拾うようにしているため、単なるカフェの宣伝はそもそも
                                       # INCLUDE側に一致しない設計）
    "🎮 アニメ": ["声優イベント", "アニメライブ"],
    "🛍️ ポップアップストア": [],
    "🎵 音楽ライブ": [
        "オーケストラ", "クラシック", "交響楽団", "交響曲", "室内楽", "オペラ", "バレエ",
        "吹奏楽", "合唱", "アンサンブル", "フィルハーモニー",
    ],  # 邦楽・洋楽（ポップス/ロック等）のみを対象にし、クラシック系は除外
}
# デパート催事は内容キーワードではなく「情報源」で自動判定するカテゴリ（下のclassify()参照）
DEPARTMENT_CATEGORY = "🏬 デパート催事"
CATEGORY_ORDER = list(CATEGORY_INCLUDE.keys()) + [DEPARTMENT_CATEGORY]

# ----------------------------------------------------------------------------
# AI判定（Gemini API）設定
# ----------------------------------------------------------------------------
# 環境変数 GEMINI_API_KEY が設定されていれば自動的に有効になる。
# 設定されていない場合は、これまで通りキーワードだけの判定で動作する
# （AI無しでも問題なく使える設計）。
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.5-flash"  # 安定版(GA)モデルを直接指定。
# 以前は "gemini-flash-latest" というエイリアスを使っていたが、このエイリアスは
# Google側の更新で中身が入れ替わることがあり、一時的にプレビュー版（レート制限が
# 厳しく503/429エラーが出やすい）を指す期間があったため、個別の安定版モデル名を
# 直接指定する方式に変更した。将来このモデルが廃止された場合は、Google公式の
# モデル一覧 https://ai.google.dev/gemini-api/docs/models で後継の安定版
# （Stableと明記されているもの）を確認し、ここを書き換えてください。
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
AI_ENABLED = bool(GEMINI_API_KEY)
AI_REQUEST_INTERVAL_SEC = 4.5  # 無料枠のレート制限(1分あたりのリクエスト数)に配慮した間隔
AI_TIMEOUT = 60
AI_MAX_RETRIES = 2  # タイムアウト/一時的なエラー時の再試行回数

AI_SYSTEM_PROMPT = """あなたは札幌市中央区の地域情報まとめサイト向けに、イベント情報を判定するアシスタントです。
以下のイベント情報を読み、次のカテゴリのうち当てはまるものだけを選んでください（複数可、0個も可）。

- 🍜 飲食: グルメフェス、フードフェス、マルシェ、物産展、食べ歩き・食べ比べイベント、スイーツイベント、
  ラーメン/肉/餃子フェス、ビアガーデン、日本酒・ワイン・クラフトビール系イベントなど。
  普通のレストラン・カフェ・居酒屋の宣伝は含めない。
- 🎮 アニメ: アニメの原画展、企画展、特別展、コラボカフェ、複製原画展、物販イベントなど。
  声優イベント、アニメライブ、上映会、映画、舞台挨拶は含めない。
- 🛍️ ポップアップストア: ジャンルを問わず、POP UP/ポップアップストア/期間限定ショップ/
  期間限定店/POP UP SHOP/LIMITED SHOP等の期間限定物販・ブランドショップ。
  「札幌PARCO」「札幌ステラプレイス」「アピア」「大丸札幌店」「狸小路商店街」などのポップアップ専用・
  ショップニュース情報源から取得した項目は、通常店舗の営業情報ではなく、期間限定販売・期間限定
  ショップであることが確認できる場合に採用する。
- 🎵 音楽ライブ: きたえーる、hitaru、Zepp Sapporo、札幌ドーム、真駒内セキスイハイムアイスアリーナ等の
  大型会場、または「全国ツアー」「ワンマン」等メジャー公演を示すもの。ジャンルは邦楽・洋楽(ポップス/ロック等)
  のみ。オーケストラ・クラシック・吹奏楽・合唱・オペラ・バレエなどは含めない。小規模なライブハウス公演も含めない。

必ず以下のJSON形式のみで回答してください（説明文や```は一切不要）:
{"categories": ["🍜 飲食"], "blurb": "30文字程度の魅力が伝わる紹介文"}

該当するカテゴリが無い場合は {"categories": [], "blurb": ""} としてください。
blurbは、SNSやブログでそのまま使えるような、親しみやすい日本語の一文にしてください。"""


def call_gemini(user_content: str) -> Optional[str]:
    """Gemini APIを呼び出し、テキスト応答を返す。失敗時はNone（タイムアウト等は自動で再試行する）。"""
    if not AI_ENABLED:
        return None
    last_error = None
    for attempt in range(1, AI_MAX_RETRIES + 2):  # 初回 + 再試行
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": user_content}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1024,
                        # gemini-3.5-flash は既定で「思考」が有効で、思考に使うトークンも
                        # maxOutputTokensの上限を共有するため、思考を無効化しないと
                        # 肝心の回答本文が出力される前に上限に達して途中で切れてしまう。
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
                timeout=AI_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_error = e
            if attempt <= AI_MAX_RETRIES:
                # 429(リクエスト過多)/503(サーバー混雑)は一時的な混雑が原因のことが多いため、
                # 通常のタイムアウト等より長めに待ってから再試行する。
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                wait_sec = 20 if status_code in (429, 503) else 3
                log.warning(f"Gemini API 呼び出し失敗(試行{attempt}回目、{wait_sec}秒待って再試行します): {e}")
                time.sleep(wait_sec)
            continue
        finally:
            time.sleep(AI_REQUEST_INTERVAL_SEC)
    log.warning(f"Gemini API 呼び出し失敗(再試行含め断念): {last_error}")
    return None


def ai_judge(item: "EventItem"):
    """AIにイベントを判定させ、(カテゴリ一覧, 紹介文) を返す。失敗時は (None, None)。"""
    user_content = (
        f"タイトル: {item.title}\n"
        f"開催日: {item.date_text}\n"
        f"場所: {item.place}\n"
        f"情報源: {item.source}"
    )
    raw = call_gemini(user_content)
    if raw is None:
        return None, None
    # ```json ... ``` で囲まれて返ってくることがあるため除去してからパース
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
        cats = [c for c in parsed.get("categories", []) if c in CATEGORY_INCLUDE]
        blurb = str(parsed.get("blurb", ""))[:60]
        return cats, blurb
    except Exception as e:
        log.warning(f"Gemini応答のJSON解析に失敗: {e} / 応答内容: {raw[:200]!r}")
        return None, None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


@dataclass
class EventItem:
    source: str
    title: str
    url: str
    date_text: str = ""
    place: str = ""
    fee: str = ""
    tags: list = field(default_factory=list)
    categories: list = field(default_factory=list)  # 判定後にセットされる
    blurb: str = ""  # AI判定が有効な場合、紹介文がここに入る（副業での発信素材として利用可）
    links: list = field(default_factory=list)  # 複数リンクがある場合(例:同じ映画が複数の映画館で上映)
                                                 # [{"label": "劇場名", "url": "..."}, ...] の形式。
                                                 # 空リストなら urlひとつだけをリンクとして扱う。


# ----------------------------------------------------------------------------
# 共通ユーティリティ
# ----------------------------------------------------------------------------

def fetch(url: str, retries: int = 2) -> Optional[BeautifulSoup]:
    """URLを取得してBeautifulSoupオブジェクトを返す。失敗時はNone。
    サーバー側の一時的なエラー(タイムアウトや500番台)に備え、自動で再試行する。"""
    last_error = None
    for attempt in range(1, retries + 2):  # 初回 + 再試行
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            last_error = e
            if attempt <= retries:
                time.sleep(3)
            continue
        finally:
            time.sleep(REQUEST_INTERVAL_SEC)
    log.warning(f"取得失敗(再試行含め断念): {url} ({last_error})")
    return None


def clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize(text: str) -> str:
    """全角英数字を半角に正規化（"Ｓａｐｐｏｒｏ" → "Sapporo" 等）"""
    return unicodedata.normalize("NFKC", text or "")


# 中央区外の会場でも「札幌市内」なら音楽ライブ/アニメ枠では許可する
# （メジャーアーティストの公演は中央区外の大ホールで行われることが多いため）
SAPPORO_VENUE_HINTS = [
    "札幌", "sapporo", "cube garden", "zepp", "hitaru", "きたえーる",
    "penny lane", "ペニーレーン", "つどーむ", "きょうどーサッポロ",
]


def is_sapporo_venue(venue_text: str) -> bool:
    v = normalize(venue_text).lower()
    return any(hint in v for hint in SAPPORO_VENUE_HINTS)


def classify(item: EventItem) -> list:
    """タイトル＋会場名＋タグから、飲食/音楽ライブ/アニメ/ポップアップ のどれに該当するか判定
    （かなり絞り込んだキーワード基準。デパート催事はタグで別途判定）"""
    haystack = normalize(f"{item.title} {item.place} {' '.join(item.tags)}")
    haystack_lower = haystack.lower()
    matched = []
    for label, includes in CATEGORY_INCLUDE.items():
        # 専用コレクターが「ポップアップ」と明示した情報は、
        # タイトルにPOP UP等の文字がなくてもポップアップカテゴリへ入れる。
        forced_popup = (
            label == "🛍️ ポップアップストア"
            and any(t in item.tags for t in ["ポップアップストア", "POPUP専用ソース"])
        )
        if forced_popup or any(normalize(inc).lower() in haystack_lower for inc in includes):
            excludes = CATEGORY_EXCLUDE.get(label, [])
            if any(exc in haystack for exc in excludes):
                continue
            matched.append(label)
    if "デパート催事" in item.tags:
        matched.append(DEPARTMENT_CATEGORY)
    return matched


# ----------------------------------------------------------------------------
# 情報源ごとの取得処理
# ----------------------------------------------------------------------------

def get_nearby_category_tags(anchor) -> list:
    """イベントカードの近くにあるカテゴリタグ（/category/xxx へのリンク）を拾う。
    ページ下部のカテゴリ一覧ナビ（数十件）を誤って拾わないよう、
    近い階層で見つかった小さめのリンク集合だけを採用する。"""
    depth = 0
    node = anchor
    while node is not None and depth < 6:
        node = node.parent
        depth += 1
        if node is None:
            break
        cat_links = node.find_all("a", href=re.compile(r"/category/[\w-]+/?$"))
        if 0 < len(cat_links) <= 6:
            return [clean(c.get_text()) for c in cat_links]
    return []


def collect_satsuibe(max_pages: int = 6) -> Iterable[EventItem]:
    """サツイベ 中央区ページを巡回して取得"""
    base = "https://sapporo.magazine.events/area/chuou-ku"
    seen_urls = set()

    for page in range(1, max_pages + 1):
        url = base if page == 1 else f"{base}/page/{page}"
        soup = fetch(url)
        if soup is None:
            break

        links = soup.find_all("a", href=re.compile(r"/(area|category)/[\w-]+/\d+\.html$"))
        if not links:
            log.info(f"サツイベ: {page}ページ目でリンクが見つからず終了")
            break

        found_this_page = 0
        for a in links:
            href = a.get("href", "")
            if href in seen_urls:
                continue
            seen_urls.add(href)

            title = clean(a.get("title")) or clean(a.get_text(" ", strip=True))[:80]
            block_text = clean(a.get_text(" ", strip=True))

            date_m = re.search(r"開催日\s*([^\s].*?)(?=場所|参加料|$)", block_text)
            place_m = re.search(r"場所\s*([^\s].*?)(?=参加料|$)", block_text)
            fee_m = re.search(r"参加料\s*([^\s].*?)(?=$)", block_text)
            tags = get_nearby_category_tags(a)

            item = EventItem(
                source="サツイベ(中央区)",
                title=title,
                url=href,
                date_text=clean(date_m.group(1))[:60] if date_m else "",
                place=clean(place_m.group(1))[:60] if place_m else "",
                fee=clean(fee_m.group(1))[:40] if fee_m else "",
                tags=tags,
            )
            found_this_page += 1
            yield item

        log.info(f"サツイベ: {page}ページ目 {found_this_page}件")
        if found_this_page == 0:
            break


def collect_chikaho() -> Iterable[EventItem]:
    """チ・カ・ホ（札幌駅前通地下広場）イベント一覧。会場自体が中央区。"""
    url = "https://www.sapporo-chikamichi.jp/event/"
    soup = fetch(url)
    if soup is None:
        return

    links = soup.find_all("a", href=True)
    count = 0
    for a in links:
        href = a["href"]
        title = clean(a.get_text(" ", strip=True))
        if not title or len(title) < 4:
            continue
        if not re.search(r"/event/.+", href):
            continue
        if href.rstrip("/").endswith("/event"):
            continue
        full_url = href if href.startswith("http") else f"https://www.sapporo-chikamichi.jp{href}"
        count += 1
        yield EventItem(
            source="チ・カ・ホ",
            title=title[:80],
            url=full_url,
            place="チ・カ・ホ（札幌駅前通地下広場）",
        )
    log.info(f"チ・カ・ホ: {count}件")


def collect_cube_garden() -> Iterable[EventItem]:
    """cube garden（中央区のライブハウス）のLIVEスケジュール。
    小規模ライブハウスのため、タイトルに全国ツアー等メジャー公演を示す語句が
    含まれる場合のみ後段のclassify()で音楽ライブ扱いになる（強制タグ付けはしない）。"""
    url = "https://www.cube-garden.com/live.php"
    soup = fetch(url)
    if soup is None:
        return

    count = 0
    candidates = soup.find_all(["a", "h2", "h3", "dt", "li"])
    for el in candidates:
        text = clean(el.get_text(" ", strip=True))
        if not text or len(text) < 4 or len(text) > 120:
            continue
        if not re.search(r"\d{1,2}[/月.\-]\d{1,2}", text):
            continue
        href = el.get("href") if el.name == "a" else None
        full_url = href if (href and href.startswith("http")) else url
        count += 1
        yield EventItem(
            source="cube garden(ライブ)",
            title=text[:80],
            url=full_url,
            place="cube garden（札幌市中央区）",
        )
    log.info(f"cube garden: {count}件（日付らしき記載がある行のみ抽出。要目視確認）")


def parse_walkerplus_listing(soup: BeautifulSoup):
    """ウォーカープラスのイベント一覧ページを解析し、(タイトル, URL, 公演日, 会場) のリストを返す。
    DOMのクラス名には依存せず、「タイトル → 日付 → … → "北海道" → 区名 → 会場名」
    というテキストの並び順だけを頼りに抽出する。"""
    date_re = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日\([月火水木金土日]\)(?:[・〜~][0-9]{1,2}日\([月火水木金土日]\))?")
    # イベント詳細へのリンク（タイトル→URL の対応づけ用）
    event_links = {}
    for a in soup.find_all("a", href=re.compile(r"/event/ar\d+e\d+/?$")):
        t = clean(a.get_text())
        if t and t not in event_links:
            event_links[t] = a["href"]

    strings = list(soup.stripped_strings)
    n = len(strings)
    results = []
    for i, s in enumerate(strings):
        if s != "北海道" or i + 2 >= n:
            continue
        ward = strings[i + 1]
        venue = strings[i + 2]
        title, date_text = "", ""
        for back in range(1, 5):
            idx = i - back
            if idx < 0:
                break
            m = date_re.search(strings[idx])
            if m:
                date_text = m.group(0)
                if idx - 1 >= 0:
                    title = strings[idx - 1]
                break
        if title and date_text and len(title) <= 100:
            href = event_links.get(title, "")
            results.append((title, href, date_text, f"{ward} {venue}"))
    return results


def collect_walkerplus_live(max_pages: int = 3) -> Iterable[EventItem]:
    """ウォーカープラス 札幌市の「ライブ・音楽イベント」。
    メジャー会場名／全国ツアー等の語句を含むものだけ、後段のclassify()で採用される。"""
    base = "https://www.walkerplus.com/event_list/ar0101100/sapporo/eg0109/"
    count = 0
    for page in range(1, max_pages + 1):
        url = base if page == 1 else f"{base}{page}.html"
        soup = fetch(url)
        if soup is None:
            break
        items = parse_walkerplus_listing(soup)
        if not items:
            break
        for title, href, date_text, place in items:
            full_url = f"https://www.walkerplus.com{href}" if href.startswith("/") else (href or url)
            count += 1
            yield EventItem(
                source="ウォーカープラス(音楽)",
                title=clean(title)[:80],
                url=full_url,
                date_text=clean(date_text)[:40],
                place=clean(place)[:60],
            )
    log.info(f"ウォーカープラス(音楽): {count}件チェック（メジャー会場/ツアー語句一致のみ後で採用）")


def collect_walkerplus_anime(max_pages: int = 3) -> Iterable[EventItem]:
    """ウォーカープラス 札幌市の「アニメ・ゲーム」イベント。
    原画展/POP UP等の展示・物販系語句を含むものだけ、後段のclassify()で採用される。"""
    base = "https://www.walkerplus.com/event_list/ar0101100/sapporo/eg0127/"
    count = 0
    for page in range(1, max_pages + 1):
        url = base if page == 1 else f"{base}{page}.html"
        soup = fetch(url)
        if soup is None:
            break
        items = parse_walkerplus_listing(soup)
        if not items:
            break
        for title, href, date_text, place in items:
            full_url = f"https://www.walkerplus.com{href}" if href.startswith("/") else (href or url)
            count += 1
            yield EventItem(
                source="ウォーカープラス(アニメ)",
                title=clean(title)[:80],
                url=full_url,
                date_text=clean(date_text)[:40],
                place=clean(place)[:60],
            )
    log.info(f"ウォーカープラス(アニメ): {count}件チェック（原画展/POP UP等の語句一致のみ後で採用）")


def parse_department_store_top_page(soup: BeautifulSoup):
    """百貨店公式サイトのトップページから「タイトル＋開催期間」の並びを抽出する。
    例: "秋はじめ スイーツ&グルメ 第1弾" の直後に "8月19日(水) ～ 8月31日(月)" が続く、
    という並び順だけを頼りに、DOM構造に依存せず抽出する。"""
    strings = list(soup.stripped_strings)
    date_pattern = re.compile(r"\d{1,2}月\d{1,2}日")
    items = []
    for i, s in enumerate(strings):
        if date_pattern.search(s) and len(s) <= 40 and i >= 1:
            title = strings[i - 1]
            if title and 3 <= len(title) <= 60 and not date_pattern.search(title):
                items.append((title, s))
    return items


def collect_mitsukoshi() -> Iterable[EventItem]:
    """札幌三越（中央区南1条西3）公式サイトの催事情報"""
    url = "https://www.mitsukoshi.mistore.jp/sapporo.html"
    soup = fetch(url)
    if soup is None:
        return
    count = 0
    for title, date_text in parse_department_store_top_page(soup):
        count += 1
        yield EventItem(
            source="札幌三越(催事)",
            title=clean(title)[:80],
            url=url,
            date_text=clean(date_text)[:40],
            place="札幌三越",
            tags=["デパート催事"],
        )
    log.info(f"札幌三越(催事): {count}件")


def collect_maruiimai() -> Iterable[EventItem]:
    """丸井今井札幌本店（中央区南1条西2）公式サイトの催事情報"""
    url = "https://www.maruiimai.mistore.jp/sapporo.html"
    soup = fetch(url)
    if soup is None:
        return
    count = 0
    for title, date_text in parse_department_store_top_page(soup):
        count += 1
        yield EventItem(
            source="丸井今井札幌本店(催事)",
            title=clean(title)[:80],
            url=url,
            date_text=clean(date_text)[:40],
            place="丸井今井札幌本店",
            tags=["デパート催事"],
        )
    log.info(f"丸井今井札幌本店(催事): {count}件")


def collect_sapporo_factory() -> Iterable[EventItem]:
    """サッポロファクトリー（中央区北2条東4丁目、大型複合商業施設）公式サイトの
    イベント情報。ページ末尾に「カテゴリ 日付 タイトル」を1本のテキストにまとめた
    リンク一覧があるため、そこから正規表現で日付部分とタイトル部分を切り分けて抽出する。
    デパート同様、情報源そのものを「デパート催事」として扱う（催事場に限らずアトリウムや
    館内各所でのイベント・ポップアップショップ・キャンペーン等をまとめて対象にする）。"""
    url = "https://sapporofactory.jp/event/"
    soup = fetch(url)
    if soup is None:
        return
    # 日付らしき文字（数字・年月日・曜日・区切り記号）が続く限り「日付」とみなし、
    # それ以外の文字（かな漢字等）が現れた時点をタイトルの開始位置とする簡易パーサー。
    date_run = re.compile(r"[0-9年月日祝土日火水木金/\-\(\)（）～〜・:.\u3000 ]+")
    seen_urls = set()
    count = 0
    for a in soup.select('a[href*="/event/detail/"]'):
        href = a.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"https://sapporofactory.jp{href}"
        if full_url in seen_urls:
            continue
        text = clean(a.get_text(" ", strip=True))
        # 「2026年」「2026/9/12」のような本物の日付の始まりだけを対象にする。
        # ページ内にはカレンダー表側（タイトルのみで日付情報を持たないリンク）と
        # 下部一覧側（カテゴリ+日付+タイトルがまとまったリンク）の2種類が同じURLで
        # 存在するため、単に「最初の数字」で判定すると表側の方を誤って拾ってしまう
        # （例:タイトル中の「第20回」の「20」を日付と誤認する）ことがあるための対策。
        m = re.search(r"\d{4}[年/]", text)
        if not m:
            continue
        date_start = m.start()
        date_match = date_run.match(text[date_start:])
        if not date_match:
            continue
        date_text = text[date_start:date_start + date_match.end()].strip()
        title = text[date_start + date_match.end():].strip()
        if not title or len(title) < 3:
            continue
        seen_urls.add(full_url)
        count += 1
        yield EventItem(
            source="サッポロファクトリー(催事)",
            title=title[:80],
            url=full_url,
            date_text=date_text[:40],
            place="サッポロファクトリー",
            tags=["デパート催事"],
        )
    log.info(f"サッポロファクトリー(催事): {count}件")



def _parse_popup_date_text(text: str) -> str:
    """ポップアップ本文から開催期間らしい日付文字列を抽出する。"""
    text = clean(text)
    patterns = [
        r"\d{4}[年/.\-]\d{1,2}[月/.\-]\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?\s*(?:[～〜~\-]\s*\d{4}[年/.\-]?\d{1,2}[月/.\-]\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?)?",
        r"\d{4}年\d{1,2}月\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?\s*(?:[～〜~\-]\s*\d{1,2}月\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?)?",
        r"\d{1,2}月\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?\s*(?:[～〜~\-]\s*\d{1,2}月\d{1,2}日?(?:\s*[（(][月火水木金土日祝][）)])?)?",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(0)[:60]
    return ""


# PARCO/ステラプレイス/アピアの各ポップアップ収集関数に共通する、
# 「イベントではなくサイト内ナビゲーション（言語切替・フロア案内等）のリンクを
# 誤って拾ってしまう」問題への対策。<a>タグの祖先にnav/header/footerが
# あるか、あるいはタイトル自体が既知のナビゲーション文言と一致する場合は除外する。
_POPUP_NAV_EXCLUDE_TITLES = {
    "日本語", "english", "简体中文", "繁體中文", "繁体字", "简体字", "한국어",
    "ภาษาไทย", "tax free", "フロア一覧", "レストラン・カフェ", "ショップを探す",
    "ショップからのお知らせ", "パルコからのお知らせ", "parcoメンバーズ",
    "イベント・ポップアップ", "サイトマップ", "お問い合わせ", "アクセス",
    "営業時間", "フロアガイド", "ニュース一覧", "お知らせ一覧", "店舗一覧",
}


def _is_nav_or_utility_link(a) -> bool:
    if a.find_parent(["nav", "header", "footer"]) is not None:
        return True
    title_norm = clean(a.get_text(" ", strip=True)).strip().lower()
    return title_norm in _POPUP_NAV_EXCLUDE_TITLES


def collect_sapporo_parco_popup(max_items: int = 40) -> Iterable[EventItem]:
    """札幌PARCO公式「イベント・ポップアップ」ページからPOPUP項目だけを取得。"""
    url = "https://sapporo.parco.jp/event/?page=1"
    soup = fetch(url)
    if soup is None:
        return

    seen = set()
    count = 0

    for a in soup.find_all("a", href=True):
        title = clean(a.get_text(" ", strip=True))
        if not title:
            continue
        if _is_nav_or_utility_link(a):
            continue

        block = a
        block_text = title
        # 親要素を数段たどって、一覧カードに表示されている開催日・会場も取得
        for _ in range(4):
            if block.parent is None:
                break
            block = block.parent
            candidate = clean(block.get_text(" ", strip=True))
            if len(candidate) > len(block_text):
                block_text = candidate
            if len(block_text) > 500:
                break

        popup_text = normalize(block_text).lower()
        if not any(k.lower() in popup_text for k in [
            "popup", "pop-up", "ポップアップ", "期間限定ショップ", "期間限定店", "limited shop"
        ]):
            continue

        href = a.get("href", "")
        if not href or href.startswith("#"):
            continue
        full_url = href if href.startswith("http") else f"https://sapporo.parco.jp{href}"
        if full_url in seen:
            continue

        # 一覧のタイトルに日付が混ざる場合を除去
        clean_title = re.sub(
            r"^\s*(?:POPUP|POP-UP|ポップアップ|POPUP / [^ ]+)\s*(?:予告|開催中)?\s*",
            "",
            title,
            flags=re.I,
        ).strip()
        if len(clean_title) < 3:
            clean_title = title

        date_text = _parse_popup_date_text(block_text)
        if not date_text:
            # detailページの取得は負荷を抑えるため、日付が一覧にない場合のみ実施
            detail = fetch(full_url)
            if detail is not None:
                date_text = _parse_popup_date_text(clean(" ".join(detail.stripped_strings)))

        seen.add(full_url)
        count += 1
        yield EventItem(
            source="札幌PARCO(ポップアップ)",
            title=clean_title[:100],
            url=full_url,
            date_text=date_text[:60],
            place="札幌PARCO",
            tags=["ポップアップストア", "POPUP専用ソース"],
        )
        if count >= max_items:
            break

    log.info(f"札幌PARCO(ポップアップ): {count}件")


def collect_stellarplace_popup(max_items: int = 50) -> Iterable[EventItem]:
    """札幌ステラプレイス公式トピックス＋ショップニュースからPOPUP/LIMITED SHOPだけを取得。"""
    urls = [
        "https://www.stellarplace.net/topics",
        "https://www.stellarplace.net/",
        "https://www.jr-tower.jp/open_renewal_stellar",
    ]
    seen = set()
    count = 0

    for url in urls:
        soup = fetch(url)
        if soup is None:
            continue

        for a in soup.find_all("a", href=True):
            title = clean(a.get_text(" ", strip=True))
            if not title:
                continue
            if _is_nav_or_utility_link(a):
                continue

            node = a
            block_text = title
            for _ in range(4):
                if node.parent is None:
                    break
                node = node.parent
                candidate = clean(node.get_text(" ", strip=True))
                if len(candidate) > len(block_text):
                    block_text = candidate
                if len(block_text) > 600:
                    break

            normalized = normalize(block_text).lower()
            if not any(k in normalized for k in [
                "popup", "pop-up", "ポップアップ", "limited shop", "期間限定ショップ", "期間限定店"
            ]):
                continue

            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            full_url = href if href.startswith("http") else (
                "https://www.stellarplace.net" + href
                if url.startswith("https://www.stellarplace.net")
                else "https://www.jr-tower.jp" + href
            )
            if full_url in seen:
                continue

            date_text = _parse_popup_date_text(block_text)
            clean_title = re.sub(
                r"^\s*(?:POPUP|POP-UP|ポップアップ|LIMITED SHOP)\s*",
                "",
                title,
                flags=re.I,
            ).strip() or title

            seen.add(full_url)
            count += 1
            yield EventItem(
                source="札幌ステラプレイス(ポップアップ)",
                title=clean_title[:100],
                url=full_url,
                date_text=date_text[:60],
                place="札幌ステラプレイス",
                tags=["ポップアップストア", "POPUP専用ソース"],
            )
            if count >= max_items:
                log.info(f"札幌ステラプレイス(ポップアップ): {count}件")
                return

    log.info(f"札幌ステラプレイス(ポップアップ): {count}件")


def collect_apia_popup(max_items: int = 50) -> Iterable[EventItem]:
    """アピア公式ショップニュースからPOPUP/期間限定ショップだけを取得。
    セール等の通常ショップニュースは対象外。"""
    url = "https://www.apiadome.com/shopnews"
    soup = fetch(url)
    if soup is None:
        return

    seen = set()
    count = 0

    for a in soup.find_all("a", href=True):
        title = clean(a.get_text(" ", strip=True))
        if not title:
            continue
        if _is_nav_or_utility_link(a):
            continue

        node = a
        block_text = title
        for _ in range(4):
            if node.parent is None:
                break
            node = node.parent
            candidate = clean(node.get_text(" ", strip=True))
            if len(candidate) > len(block_text):
                block_text = candidate
            if len(block_text) > 600:
                break

        normalized = normalize(block_text).lower()
        if not any(k in normalized for k in [
            "popup", "pop-up", "ポップアップ", "limited shop", "期間限定ショップ", "期間限定店"
        ]):
            continue

        href = a.get("href", "")
        if not href or href.startswith("#"):
            continue
        full_url = href if href.startswith("http") else f"https://www.apiadome.com{href}"
        if full_url in seen:
            continue

        seen.add(full_url)
        count += 1
        yield EventItem(
            source="アピア(ポップアップ)",
            title=title[:100],
            url=full_url,
            date_text=_parse_popup_date_text(block_text)[:60],
            place="アピア",
            tags=["ポップアップストア", "POPUP専用ソース"],
        )
        if count >= max_items:
            break

    log.info(f"アピア(ポップアップ): {count}件")


def collect_daimaru_sapporo_popup(max_pages: int = 3, max_items: int = 60) -> Iterable[EventItem]:
    """大丸札幌店公式SHOP BLOG（テナント各店のお知らせ記事一覧）からアニメ・ゲーム・
    漫画関連のPOPUP/期間限定ショップ/コラボカフェ等だけを取得する。
    大丸札幌店本体の「イベントカレンダー」はJavaScriptで動的生成されるため取得できないが、
    こちらのSHOP BLOGは静的HTMLで一覧が出力されるため取得可能。"""
    seen = set()
    count = 0
    for page in range(1, max_pages + 1):
        url = "https://shopblog.dmdepart.jp/sapporo/" if page == 1 else f"https://shopblog.dmdepart.jp/sapporo/?p={page}"
        soup = fetch(url)
        if soup is None:
            continue
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/sapporo/detail/" not in href:
                continue
            title = clean(a.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue
            normalized = normalize(title).lower()
            if not any(k.lower() in normalized for k in [
                "popup", "pop-up", "ポップアップ", "期間限定ショップ", "期間限定店", "limited shop", "コラボ"
            ]):
                continue
            full_url = href if href.startswith("http") else f"https://shopblog.dmdepart.jp{href}"
            if full_url in seen:
                continue
            date_text = ""
            m = re.search(r"\d{4}\.\d{1,2}\.\d{1,2}", title)
            if m:
                date_text = m.group(0)
            seen.add(full_url)
            count += 1
            yield EventItem(
                source="大丸札幌店(SHOP BLOG)",
                title=title[:100],
                url=full_url,
                date_text=date_text,
                place="大丸札幌店",
                tags=["ポップアップストア", "POPUP専用ソース"],
            )
            if count >= max_items:
                log.info(f"大丸札幌店(SHOP BLOG): {count}件チェック（アニメ/ゲーム/漫画関連の絞り込みは後でclassify()が行う）")
                return
        time.sleep(REQUEST_INTERVAL_SEC)
    log.info(f"大丸札幌店(SHOP BLOG): {count}件チェック（アニメ/ゲーム/漫画関連の絞り込みは後でclassify()が行う）")


def collect_tanukikoji_popup(max_pages: int = 3, max_items: int = 60) -> Iterable[EventItem]:
    """狸小路商店街（moyuk SAPPORO等を含む）公式サイトの「ニュース&イベント」一覧から
    アニメ・ゲーム・漫画関連のPOPUP/期間限定ショップ等だけを取得する。"""
    seen = set()
    count = 0
    for page in range(1, max_pages + 1):
        url = "https://tanukikoji.or.jp/news-event/" if page == 1 else f"https://tanukikoji.or.jp/news-event/page/{page}/"
        soup = fetch(url)
        if soup is None:
            continue
        for h in soup.find_all(["h2", "h3"]):
            a = h.find("a", href=True)
            if a is None:
                continue
            href = a.get("href", "")
            if "/news-event/" not in href or href.rstrip("/").endswith("news-event"):
                continue
            title = clean(a.get_text(" ", strip=True))
            if not title:
                continue

            # 見出しの後ろに続く説明文＋日付らしき行も合わせて拾う（同じ記事ブロック内）
            block_text = title
            node = h
            for _ in range(4):
                nxt = node.find_next_sibling()
                if nxt is None:
                    break
                candidate = clean(nxt.get_text(" ", strip=True))
                block_text += " " + candidate
                node = nxt
                if len(block_text) > 400:
                    break

            normalized = normalize(block_text).lower()
            if not any(k.lower() in normalized for k in [
                "popup", "pop-up", "ポップアップ", "期間限定ショップ", "期間限定店", "limited shop", "コラボ"
            ]):
                continue

            full_url = href if href.startswith("http") else f"https://tanukikoji.or.jp{href}"
            if full_url in seen:
                continue

            seen.add(full_url)
            count += 1
            yield EventItem(
                source="狸小路商店街(ニュース&イベント)",
                title=re.sub(r"^\s*【終了しました】\s*", "", title)[:100],
                url=full_url,
                date_text=_parse_popup_date_text(block_text)[:60],
                place="狸小路商店街",
                tags=["ポップアップストア", "POPUP専用ソース"],
            )
            if count >= max_items:
                log.info(f"狸小路商店街(ニュース&イベント): {count}件チェック（アニメ/ゲーム/漫画関連の絞り込みは後でclassify()が行う）")
                return
        time.sleep(REQUEST_INTERVAL_SEC)
    log.info(f"狸小路商店街(ニュース&イベント): {count}件チェック（アニメ/ゲーム/漫画関連の絞り込みは後でclassify()が行う）")




def collect_manual_events() -> Iterable[EventItem]:
    """自動収集が難しい大型の年次フェス等を手動で登録しておく場所。
    ここに追加した項目も、他の情報源と同じくclassify()でカテゴリ判定される
    （タイトルにCATEGORY_INCLUDEの語句が含まれていれば自動的に採用される）。
    URLは重複判定のキーにもなるので、年ごとに変えるなどして使い回さないこと。

    映画の場合は "release_date"（公開日）を指定しておくと、実行日がその日を
    迎えたかどうかで自動的に「🍿 公開予定映画」→「🎬 映画」へタグが切り替わる
    （公開日を過ぎたら手動で書き換える必要がない）。"""
    manual_events = [
        {
            "title": "2026さっぽろオータムフェスト",
            "date_text": "2026年9月11日(金)〜10月3日(土)",
            "place": "大通公園（中央区）",
            "url": "https://www.sapporo.travel/autumnfest/",
        },
        {
            "title": "桑田佳祐 夏祭りツアー 2026 supported by カンロ 北海道公演",
            "date_text": "2026年8月27日(木)・28日(金)",
            "place": "真駒内セキスイハイムアイスアリーナ",
            "url": "https://southernallstars.jp/feature/kuwata2026live#sapporo2026",
        },
        {
            "title": "Coffee Pairing Festival 2026（コーヒーペアリングフェスティバル2026）",
            "date_text": "2026年9月30日(水)〜10月6日(火)",
            "place": "大丸札幌店 7階催事場（中央区）",
            "url": "https://www.daimaru.co.jp/sapporo/coffeepairingfestival/",
        },
        {
            "title": "映画『超かぐや姫！』特別フォーマット版＆通常版 復活上映",
            "date_text": "2026年9月18日(金)〜",
            "place": "札幌市内の映画館（中央区）",
            "url": "https://www.cho-kaguyahime.com/theater/",
            "release_date": date(2026, 9, 18),  # この日を迎えると自動的に「映画上映中」に切り替わる
        },
        # 他の年次フェスもここに追加できます。例:
        # {
        #     "title": "さっぽろ雪まつり2027",
        #     "date_text": "2027年2月上旬",
        #     "place": "大通公園（中央区）ほか",
        #     "url": "https://www.snowfes.com/#2027",
        # },
    ]
    today = datetime.now().date()
    for ev in manual_events:
        tags = list(ev.get("tags", []))
        release_date = ev.get("release_date")
        if release_date:
            if today >= release_date:
                tags = [t for t in tags if t != "公開予定映画"]
                if "映画上映中" not in tags:
                    tags.append("映画上映中")
            else:
                tags = [t for t in tags if t != "映画上映中"]
                if "公開予定映画" not in tags:
                    tags.append("公開予定映画")
        yield EventItem(
            source="手動登録(年次フェス)",
            title=ev["title"],
            url=ev["url"],
            date_text=ev.get("date_text", ""),
            place=ev.get("place", ""),
            tags=tags,
        )
    log.info(f"手動登録イベント: {len(manual_events)}件")


def parse_eventernote_listing(soup: BeautifulSoup):
    """イベンターノートの会場別イベント一覧を解析し、(タイトル, URL, 開催日) のリストを返す。
    日付見出し（YYYY-MM-DD (曜)）とイベント詳細リンク（/events/数字）が
    ページ内に同じ順番で1対1に並んでいる、という構造だけを頼りに抽出する。"""
    date_re = re.compile(r"\d{4}-\d{2}-\d{2} \([月火水木金土日]\)")
    dates_in_order = date_re.findall(soup.get_text())

    seen = set()
    events = []
    for a in soup.find_all("a", href=re.compile(r"/events/\d+$")):
        href = a["href"]
        if href in seen:
            continue
        seen.add(href)
        title = clean(a.get_text())
        if title:
            events.append((title, href))

    results = []
    for i, (title, href) in enumerate(events):
        date_text = dates_in_order[i] if i < len(dates_in_order) else ""
        results.append((title, href, date_text))
    return results


# イベンターノートで確認できた、中央区内外の主要会場のID
EVENTERNOTE_VENUES = {
    650: "cube garden",  # 参考: 既にcube_garden個別ソースがあるため未使用（重複防止のためコメントのみ）
    13: "Zepp Sapporo",
    654: "北海きたえーる",
    9869: "札幌文化芸術劇場hitaru",
    10: "大和ハウスプレミストドーム（札幌ドーム）",
    950: "真駒内セキスイハイムアイスアリーナ",
}


def collect_eventernote_major_venues(max_pages: int = 2) -> Iterable[EventItem]:
    """イベンターノートで、メジャーアーティストの公演が多い主要会場（中央区外含む）の
    直近イベントを取得する。会場名自体がCATEGORY_INCLUDEの語句になっているため、
    後段のclassify()で自動的に音楽ライブとして採用される（クラシック等は引き続き除外）。"""
    count = 0
    for place_id, venue_name in EVENTERNOTE_VENUES.items():
        if place_id == 650:
            continue  # cube gardenは別ソースで収集済みのためスキップ
        for page in range(1, max_pages + 1):
            url = f"https://www.eventernote.com/places/{place_id}/events?limit=30&page={page}"
            soup = fetch(url)
            if soup is None:
                break
            items = parse_eventernote_listing(soup)
            if not items:
                break
            for title, href, date_text in items:
                full_url = href if href.startswith("http") else f"https://www.eventernote.com{href}"
                count += 1
                yield EventItem(
                    source=f"イベンターノート({venue_name})",
                    title=clean(title)[:80],
                    url=full_url,
                    date_text=clean(date_text)[:20],
                    place=venue_name,
                )
    log.info(f"イベンターノート(主要会場): {count}件チェック")


SAPPORO_MOVIE_THEATERS = {
    "th220": "ローソン・ユナイテッドシネマ札幌",
    "th592": "札幌シネマフロンティア",
    "th828": "TOHOシネマズすすきの",
    # "th533": "シアターキノ",  # ご要望により映画カテゴリの対象から除外（ミニシアター系のため）
}

# 現在上映中の映画一覧には「アニメかどうか」の情報が付いていないため、
# タイトルに含まれる語句で簡易的にアニメ映画かどうかを判定する。
# 新作アニメ映画のタイトルが拾えない場合は、ここにキーワードを追加してください。
ANIME_MOVIE_HINTS = [
    "アニメ", "劇場版", "ちいかわ", "クレヨンしんちゃん", "ポケモン", "ドラえもん",
    "名探偵コナン", "鬼滅の刃", "呪術廻戦", "ワンピース", "ガンダム", "五等分の花嫁",
    "推しの子", "スパイファミリー", "スパイ×ファミリー", "ヒーローアカデミア", "チェンソーマン",
    "薬屋のひとりごと", "プリキュア", "ウルトラマン", "幻想水滸伝", "パウ・パトロール",
    "ミニオンズ", "まどか", "マギカ",
]

def _extract_title_from_schedule_page(url: str) -> Optional[str]:
    """個別の上映スケジュールページの<title>タグから、正確な映画タイトルだけを取り出す。
    例: "映画ちいかわ 人魚の島のひみつ TOHOシネマズ すすきの(札幌) の上映時間・上映スケジュール | MOVIE WALKER PRESS 映画"
        → "映画ちいかわ 人魚の島のひみつ"
    一覧ページ周辺のDOM構造を辿る方式は、サイト内の無関係な要素（ランキング等）を
    誤って拾ってしまい不安定だったため、この方式に切り替えている。"""
    soup = fetch(url)
    if soup is None or not soup.title or not soup.title.string:
        return None
    raw = clean(soup.title.string)
    raw = re.sub(r"\s*[^\s]*\(.*?\)\s*の上映時間.*$", "", raw)
    raw = re.sub(r"\s*\|\s*MOVIE WALKER PRESS.*$", "", raw)
    raw = raw.strip()
    return raw or None


def collect_movie_theaters() -> Iterable[EventItem]:
    """札幌市内の主要映画館（ユナイテッド・シネマ札幌/札幌シネマフロンティア/シアターキノ/
    TOHOシネマズすすきの。いずれも中央区）で現在上映中の映画を全件取得する（🎬映画）。
    タイトルにANIME_MOVIE_HINTSの語句が含まれるものは、あわせて🎮アニメにも表示されるよう
    タグを追加する。同じ映画が複数の映画館で上映されている場合は1件にまとめつつ、
    それぞれの映画館の上映スケジュールページへのリンクを個別に持たせる。

    まとめページ(theater/108等)は注目記事中心で全作品が載らないため、
    映画館ごとの個別スケジュールページを1館ずつ巡回して対象の映画IDを集め、
    そのあと各映画の個別ページを開いて正確なタイトルを取得する2段階方式にしている。"""
    # movie_id -> [(theater_id, schedule_url), ...]（上映している映画館すべてを記録）
    movie_theater_map: dict[str, list] = {}
    for theater_id, theater_name in SAPPORO_MOVIE_THEATERS.items():
        url = f"https://press.moviewalker.jp/{theater_id}/schedule/"
        soup = fetch(url)
        if soup is None:
            continue
        for a in soup.find_all("a", href=re.compile(rf"/mv\d+/schedule/{theater_id}/?$")):
            href = a["href"]
            m = re.search(r"/mv(\d+)/schedule/", href)
            if not m:
                continue
            movie_id = m.group(1)
            full_url = href if href.startswith("http") else f"https://press.moviewalker.jp{href}"
            entries = movie_theater_map.setdefault(movie_id, [])
            if not any(tid == theater_id for tid, _ in entries):
                entries.append((theater_id, full_url))

    count = 0
    anime_count = 0
    all_titles = []
    for movie_id, theater_entries in movie_theater_map.items():
        first_theater_id, first_url = theater_entries[0]
        title = _extract_title_from_schedule_page(first_url)
        if not title:
            continue

        tags = ["映画上映中"]
        if any(hint in title for hint in ANIME_MOVIE_HINTS):
            tags.append("劇場版")
            anime_count += 1

        links = [
            {"label": SAPPORO_MOVIE_THEATERS[tid], "url": url}
            for tid, url in theater_entries
        ]
        theater_names = "・".join(SAPPORO_MOVIE_THEATERS[tid] for tid, _ in theater_entries)

        count += 1
        all_titles.append(title)
        yield EventItem(
            source="映画館(上映中)",
            title=title[:80],
            url=f"https://press.moviewalker.jp/mv{movie_id}/",
            place=f"{theater_names}（中央区）で上映中",
            tags=tags,
            links=links,
        )
    log.info(f"映画館(上映中): {count}件（うちアニメ映画と判定: {anime_count}件）")
    log.info(f"映画館(上映中) 取得タイトル一覧: {all_titles}")


_COMING_SOON_INFO_RE = re.compile(
    r"^(\d{4})年(\d{1,2})月(\d{1,2})日(?:公開|再上映|再上映開始|上映開始|復活上映)(?:、\d+分)?(?:、(.+))?$"
)


def _parse_coming_soon_page(soup: BeautifulSoup):
    """MOVIE WALKER PRESSの「公開予定」月別ページから (タイトル, href, 年, 月, 日, ジャンル文字列) を抽出する。
    ページの並び順（タイトル文字列の直後に「YYYY年M月D日公開、上映時間、ジャンル」の行が続く）
    だけを頼りにしているため、DOMのクラス名変更にはある程度強い。"""
    href_by_title = {}
    for a in soup.find_all("a", href=re.compile(r"^/mv\d+/?$")):
        t = clean(a.get_text())
        if t and t not in href_by_title:
            href_by_title[t] = a["href"]

    strings = list(soup.stripped_strings)
    results = []
    for i, s in enumerate(strings):
        m = _COMING_SOON_INFO_RE.match(s)
        if not m or i < 1:
            continue
        title = strings[i - 1]
        if not title or len(title) > 80:
            continue
        y, mo, d, genre = m.groups()
        href = href_by_title.get(title)
        results.append((title, href, int(y), int(mo), int(d), genre or ""))
    return results


def collect_upcoming_movies() -> Iterable[EventItem]:
    """今後2ヶ月以内に全国で公開予定の映画（🍿 公開予定映画）。
    MOVIE WALKER PRESSの月別「公開予定」ページ（例: /list/coming/2026/09/）を、
    対象期間が含まれる月×ページ送りぶんだけ巡回する。このページにはジャンル情報が
    明記されているため、タイトルのキーワード判定に加えてジャンルに「アニメ」が
    含まれるかどうかでもアニメ判定を行う（キーワード判定より確実）。
    全国版のリストのため、必ずしも札幌の劇場での上映が確定しているとは限らない点に注意。"""
    today = datetime.now().date()
    window_end = today + timedelta(days=60)

    # 対象期間をカバーする年月を列挙（当月から、window_endの月まで）
    months = []
    y, m = today.year, today.month
    while date(y, m, 1) <= window_end:
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    upcoming: dict[str, dict] = {}  # title -> {"date": date, "genre": str, "url": str}
    all_found_before_filter = []

    for y, m in months:
        for page in range(1, 6):  # ページ送り。空振りが続いたら打ち切る
            page_url = (
                f"https://press.moviewalker.jp/list/coming/{y}/{m:02d}/"
                if page == 1
                else f"https://press.moviewalker.jp/list/coming/{y}/{m:02d}/p{page}/"
            )
            soup = fetch(page_url)
            if soup is None:
                break
            entries = _parse_coming_soon_page(soup)
            if not entries:
                break
            for title, href, ey, em, ed, genre in entries:
                all_found_before_filter.append((title, f"{ey}年{em}月{ed}日", genre))
                try:
                    release_date = date(ey, em, ed)
                except Exception:
                    continue
                if release_date < today or release_date > window_end:
                    continue
                if title in upcoming:
                    continue
                url = f"https://press.moviewalker.jp{href}" if href else page_url
                upcoming[title] = {"date": release_date, "genre": genre, "url": url}

    count = 0
    anime_count = 0
    for title, info in upcoming.items():
        tags = ["公開予定映画"]
        is_anime = "アニメ" in info["genre"] or any(hint in title for hint in ANIME_MOVIE_HINTS)
        if is_anime:
            tags.append("劇場版")
            anime_count += 1

        date_text = f"{info['date'].year}年{info['date'].month}月{info['date'].day}日公開"
        genre_text = f"（{info['genre']}）" if info["genre"] else ""

        count += 1
        yield EventItem(
            source="映画館(公開予定・全国版)",
            title=title[:80],
            url=info["url"],
            date_text=date_text,
            place=f"全国公開予定{genre_text}　※札幌での上映は劇場発表をご確認ください",
            tags=tags,
        )
    log.info(f"映画館(公開予定): {count}件（うちアニメ映画と判定: {anime_count}件）")
    log.info(f"映画館(公開予定) フィルタ前の全件({len(all_found_before_filter)}件): {all_found_before_filter[:30]}...")


SOURCES = {
    "satsuibe": collect_satsuibe,
    "chikaho": collect_chikaho,
    "cube_garden": collect_cube_garden,
    "walkerplus_live": collect_walkerplus_live,
    "walkerplus_anime": collect_walkerplus_anime,
    "eventernote_major": collect_eventernote_major_venues,
    "mitsukoshi": collect_mitsukoshi,
    "maruiimai": collect_maruiimai,
    "sapporo_factory": collect_sapporo_factory,
    "sapporo_parco_popup": collect_sapporo_parco_popup,
    "stellarplace_popup": collect_stellarplace_popup,
    "apia_popup": collect_apia_popup,
    "daimaru_sapporo_popup": collect_daimaru_sapporo_popup,
    "tanukikoji_popup": collect_tanukikoji_popup,
    "movie_theaters": collect_movie_theaters,
    "upcoming_movies": collect_upcoming_movies,
    "manual": collect_manual_events,
}


# ----------------------------------------------------------------------------
# データベース
# ----------------------------------------------------------------------------

def cleanup_stale_manual_urls(conn: sqlite3.Connection) -> None:
    """手動登録イベントはURLを変更することがあるため、現在のmanual_eventsに
    含まれないURLパターン（手動登録ソースなのに一致しないもの）は
    重複表示を防ぐため削除しておく。"""
    current_urls = {ev["url"] for ev in [
        {"url": item.url} for item in collect_manual_events()
    ]}
    cur = conn.execute("SELECT url FROM events WHERE source = ?", ("手動登録(年次フェス)",))
    stale = [row[0] for row in cur.fetchall() if row[0] not in current_urls]
    for url in stale:
        conn.execute("DELETE FROM events WHERE url = ?", (url,))
    if stale:
        conn.commit()
        log.info(f"手動登録イベントの古いURL {len(stale)}件を削除しました")


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            url TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            date_text TEXT,
            place TEXT,
            fee TEXT,
            categories TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
        """
    )
    # 旧バージョン(列が無い)で作られたDBを引き続き使えるよう自動マイグレーション
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    if "categories" not in existing_cols:
        conn.execute("ALTER TABLE events ADD COLUMN categories TEXT DEFAULT ''")
        log.info("DBを新バージョン形式にマイグレーションしました（categories列を追加）")
    if "blurb" not in existing_cols:
        conn.execute("ALTER TABLE events ADD COLUMN blurb TEXT DEFAULT ''")
        log.info("DBを新バージョン形式にマイグレーションしました（blurb列を追加）")
    if "links" not in existing_cols:
        conn.execute("ALTER TABLE events ADD COLUMN links TEXT DEFAULT ''")
        log.info("DBを新バージョン形式にマイグレーションしました（links列を追加）")
    conn.commit()


def upsert_event(conn: sqlite3.Connection, item: EventItem, today: str) -> bool:
    """新規なら True（新着）、既存なら内容(タイトル等)とlast_seenを更新して False を返す。
    タイトルや日付/場所も毎回上書きするのは、情報源側の表記が後から変わったり、
    以前のバグ等で誤った内容が保存されてしまった場合でも、再取得時に自動的に
    最新の正しい内容へ直るようにするため。"""
    cur = conn.execute("SELECT url FROM events WHERE url = ?", (item.url,))
    row = cur.fetchone()
    cats = ",".join(item.categories)
    links_json = json.dumps(item.links, ensure_ascii=False) if item.links else ""
    if row is None:
        conn.execute(
            """
            INSERT INTO events (url, source, title, date_text, place, fee, categories, blurb, links, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item.url, item.source, item.title, item.date_text, item.place, item.fee, cats, item.blurb,
             links_json, today, today),
        )
        return True
    else:
        # 紹介文(blurb)は新しく判定できた時だけ上書きする（AI無効時に空で消してしまわないため）
        blurb_clause = ", blurb = ?" if item.blurb else ""
        params = [today, item.title, item.date_text, item.place, item.fee, cats, links_json]
        if item.blurb:
            params.append(item.blurb)
        params.append(item.url)
        conn.execute(
            f"""
            UPDATE events SET last_seen = ?, title = ?, date_text = ?, place = ?, fee = ?,
                               categories = ?, links = ?{blurb_clause}
            WHERE url = ?
            """,
            params,
        )
        return False


def fetch_all_current(conn: sqlite3.Connection) -> list:
    """DB内の全件を、表示用にカテゴリ別へ振り分けて返す"""
    cur = conn.execute(
        "SELECT source, title, date_text, place, fee, categories, url, first_seen, blurb, links "
        "FROM events ORDER BY date_text ASC, first_seen DESC"
    )
    rows = cur.fetchall()
    return rows


# ----------------------------------------------------------------------------
# 開催日フィルタ（更新日から1か月分だけを表示）
# ----------------------------------------------------------------------------

_FULL_DATE_RE = re.compile(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})")
_SHORT_DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")
_SHORT_SLASH_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)")


def parse_date_range(date_text: str, today: date):
    """date_text（形式は情報源ごとにバラバラ）から開催期間の (開始日, 終了日) を推定する。
    範囲表記（〜, ～, ・ 等で複数日付を含む）の場合は最初と最後の日付を採用。
    年が書かれていない場合は、今日から60日以上前になってしまうなら翌年とみなす
    （年末年始をまたぐケースへの対応）。
    解析できない場合は (None, None) を返す。"""
    if not date_text:
        return None, None

    # 「2026年9月30日〜10月6日」のように、2つ目以降の日付だけ年が省略される
    # 表記に対応するため、フル表記(年あり)・短縮表記(年なし)の両方を必ず探す。
    # フル表記の範囲と重なる短縮表記(例:"9月30日"の一部としての"30日"由来の誤検出)は
    # 除外しつつ、フル表記の外側にある短縮表記(例:後半の"10月6日")だけを追加する。
    matches = []
    full_spans = []
    for m in _FULL_DATE_RE.finditer(date_text):
        matches.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        full_spans.append(m.span())

    def _inside_full_span(pos: int) -> bool:
        return any(start <= pos < end for start, end in full_spans)

    for m in _SHORT_DATE_RE.finditer(date_text):
        if _inside_full_span(m.start()):
            continue  # フル表記の一部として既に拾っている日付なので重複させない
        matches.append((None, int(m.group(1)), int(m.group(2))))

    # 「2026/9/11〜9/22」のように、範囲の後半が年省略のスラッシュ形式（9/22）で
    # 書かれるケースにも対応する（"月","日"を使わないため上のSHORT_DATE_REでは拾えない）。
    for m in _SHORT_SLASH_DATE_RE.finditer(date_text):
        if _inside_full_span(m.start()):
            continue
        matches.append((None, int(m.group(1)), int(m.group(2))))

    dates = []
    for y, mo, d in matches:
        yy = y if y else today.year
        try:
            dt = date(yy, mo, d)
        except ValueError:
            continue
        if y is None and dt < today - timedelta(days=60):
            dt = date(yy + 1, mo, d)
        dates.append(dt)

    if not dates:
        return None, None
    return min(dates), max(dates)


def filter_within_month(rows: list, today: date, days: int = 30) -> list:
    """開催日が「今日 〜 今日+days日」に重なるものだけを残す。
    日付が読み取れなかった項目は、情報を落とさないよう念のため残す。"""
    window_end = today + timedelta(days=days)
    kept = []
    for row in rows:
        date_text = row[2]
        start, end = parse_date_range(date_text, today)
        if start is None:
            kept.append(row)  # 日付不明はフィルタしない
            continue
        if end is None:
            end = start
        if end >= today and start <= window_end:
            kept.append(row)
    return kept


def infer_tags_from_source(source: str) -> list:
    """DBには生のtags(カテゴリタグ)は保存していないため、再分類時はsource名から推測する。
    （百貨店の催事情報は情報源そのものが「デパート催事」の証拠になる）"""
    if source and "催事" in source:
        return ["デパート催事"]
    return []


def reclassify_all(conn: sqlite3.Connection) -> None:
    """保存済みの全イベントを、現在のCATEGORY_INCLUDE/EXCLUDE基準で再判定し直す。
    基準（キーワード）を変更するたびに、過去に保存済みのデータにも新基準が
    反映されるようにするための処理。"""
    cur = conn.execute("SELECT url, source, title, place FROM events")
    rows = cur.fetchall()
    updated = 0
    for url, source, title, place in rows:
        tmp = EventItem(source=source or "", title=title or "", url=url, place=place or "",
                         tags=infer_tags_from_source(source))
        cats = classify(tmp)
        conn.execute("UPDATE events SET categories = ? WHERE url = ?", (",".join(cats), url))
        updated += 1
    conn.commit()
    log.info(f"既存データ {updated} 件を最新の分類基準で再判定しました")


# ----------------------------------------------------------------------------
# 表示順
# ----------------------------------------------------------------------------

def sort_key_for_display(row, today: date):
    """開催開始日が早い順に並べる。日付を解析できない情報は最後へ。"""
    date_text = row[2] or ""
    start, _ = parse_date_range(date_text, today)
    return (start is None, start or date.max, (row[1] or "").lower())


# ----------------------------------------------------------------------------
# HTMLレポート生成（ブラウザで確認する用）
# ----------------------------------------------------------------------------

def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_html(rows, today: str, new_count: int) -> str:
    # カテゴリごとにグループ化
    grouped = {label: [] for label in CATEGORY_ORDER}
    for source, title, date_text, place, fee, cats, url, first_seen, blurb, links_json in rows:
        cat_list = cats.split(",") if cats else []
        for c in cat_list:
            if c in grouped:
                grouped[c].append((source, title, date_text, place, fee, url, first_seen, blurb, links_json))

    sections_html = ""
    today_date = datetime.strptime(today, "%Y-%m-%d").date()

    for label in CATEGORY_ORDER:
        items = grouped[label]
        if not items:
            sections_html += f'<h2>{label}</h2><p class="empty">現在、該当する情報はありません。</p>'
            continue

        # ★開催日順（開催開始日が早いもの→日付不明は最後）
        items.sort(key=lambda row: sort_key_for_display(row, today_date))

        sections_html += f'<h2>{label} <span class="count">({len(items)}件)</span></h2><div class="cards">'
        for source, title, date_text, place, fee, url, first_seen, blurb, links_json in items:
            is_new = " new" if first_seen == today else ""
            badge = '<span class="badge">NEW</span>' if first_seen == today else ""

            try:
                links = json.loads(links_json) if links_json else []
            except Exception:
                links = []
            if not links:
                links = [{"label": source, "url": url}]
            links_html = "".join(
                f'<a class="card-link" href="{escape_html(l.get("url", url))}" target="_blank" rel="noopener">'
                f'{escape_html(l.get("label", source))} ↗</a>'
                for l in links
            )

            sections_html += f"""
            <div class="card{is_new}">
              {badge}
              <div class="card-title">{escape_html(title)}</div>
              {'<div class="card-blurb">✨ ' + escape_html(blurb) + '</div>' if blurb else ''}
              <div class="card-meta">
                {'📅 ' + escape_html(date_text) + '<br>' if date_text else ''}
                {'📍 ' + escape_html(place) + '<br>' if place else ''}
                {'💰 ' + escape_html(fee) + '<br>' if fee else ''}
                <span class="source">{escape_html(source)}</span>
              </div>
              <div class="card-links">{links_html}</div>
            </div>
            """
        sections_html += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>札幌市中央区 情報収集レポート</title>
<style>
  :root {{
    --bg: #12131a;
    --panel: #1b1d29;
    --accent: #ff6b6b;
    --accent2: #4ecdc4;
    --text: #eaeaf0;
    --muted: #9a9ab0;
    --border: #2a2c3d;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
  }}
  header {{
    max-width: 980px;
    margin: 0 auto 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }}
  h1 {{
    font-size: 22px;
    margin: 0 0 6px;
  }}
  .updated {{
    color: var(--muted);
    font-size: 13px;
  }}
  main {{
    max-width: 980px;
    margin: 0 auto;
  }}
  h2 {{
    font-size: 18px;
    margin: 28px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .count {{
    color: var(--muted);
    font-size: 13px;
    font-weight: normal;
  }}
  .empty {{
    color: var(--muted);
    font-size: 14px;
  }}
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }}
  .card {{
    position: relative;
    display: block;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    color: var(--text);
    transition: border-color 0.15s;
  }}
  .card.new {{
    border-color: var(--accent);
  }}
  .card-links {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }}
  .card-link {{
    display: inline-block;
    font-size: 11.5px;
    color: var(--accent2);
    text-decoration: none;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 4px 10px;
    transition: border-color 0.15s, color 0.15s;
  }}
  .card-link:hover {{
    border-color: var(--accent2);
    color: #fff;
  }}
  .badge {{
    position: absolute;
    top: -8px;
    right: 10px;
    background: var(--accent);
    color: #fff;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: bold;
    letter-spacing: 0.05em;
  }}
  .card-title {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
    line-height: 1.4;
  }}
  .card-blurb {{
    font-size: 12.5px;
    color: var(--accent2);
    margin-bottom: 8px;
    line-height: 1.5;
  }}
  .card-meta {{
    font-size: 12px;
    color: var(--muted);
    line-height: 1.7;
  }}
  .source {{
    display: inline-block;
    margin-top: 4px;
    color: var(--accent2);
    font-size: 11px;
  }}
</style>
</head>
<body>
<header>
  <h1>🏙️ 札幌市中央区 情報収集レポート</h1>
  <div class="updated">最終更新: {today}　/　表示期間: 今日から2ヶ月(60日)以内に開催・公開のもの　/　今回の新着: {new_count}件　/　このページはスクリプト実行のたびに自動更新されます</div>
</header>
<main>
{sections_html}
</main>
</body>
</html>
"""
    return html


# ----------------------------------------------------------------------------
# メイン処理
# ----------------------------------------------------------------------------

def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    log.info("=== 札幌市中央区 情報収集 開始 ===")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cleanup_stale_manual_urls(conn)  # URLを変更した手動登録イベントの古い重複を削除
    reclassify_all(conn)  # 分類基準が更新されている場合に備え、既存データも最新基準で判定し直す

    new_items: list[EventItem] = []
    total_checked = 0
    total_matched = 0
    ai_calls = 0

    for name, collector_fn in SOURCES.items():
        log.info(f"--- 情報源: {name} ---")
        try:
            for item in collector_fn():
                total_checked += 1
                item.categories = classify(item)  # まずキーワードで一次判定（AI無効時/失敗時の土台にもなる）
                if AI_ENABLED:
                    ai_cats, ai_blurb = ai_judge(item)
                    if ai_cats is not None:
                        item.categories = ai_cats  # AIの判定を優先して採用
                        item.blurb = ai_blurb or ""
                        ai_calls += 1
                if not item.categories:
                    continue  # 飲食/音楽ライブ/アニメ/デパート催事 のどれにも該当しない情報は除外
                total_matched += 1
                if upsert_event(conn, item, today):
                    new_items.append(item)
        except Exception as e:
            log.error(f"{name} の収集中にエラー: {e}")

    conn.commit()

    # 今回の新着分だけをCSVに保存
    if new_items:
        out_path = DATA_DIR / f"new_{today}.csv"
        with out_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["categories", "source", "title", "date_text", "place", "fee", "url"])
            for it in new_items:
                writer.writerow([
                    "/".join(it.categories), it.source, it.title, it.date_text, it.place, it.fee, it.url
                ])
        log.info(f"新着 {len(new_items)} 件を保存しました → {out_path}")
    else:
        log.info("新着情報はありませんでした。")

    # HTMLレポートを常に最新化（開催日が今日から60日以内のものだけ表示）
    rows = fetch_all_current(conn)
    today_date = datetime.now().date()
    rows = filter_within_month(rows, today_date, days=60)  # 公開予定映画等も見えるよう2ヶ月分表示
    html = build_html(rows, today, len(new_items))
    HTML_PATH.write_text(html, encoding="utf-8")
    log.info(f"HTMLレポートを更新しました → {HTML_PATH}")

    conn.close()

    log.info(f"チェック件数(延べ): {total_checked} / 対象カテゴリ一致: {total_matched} / 新着: {len(new_items)} / AI判定利用: {ai_calls}件{'(有効)' if AI_ENABLED else '(無効:GEMINI_API_KEY未設定)'}")
    log.info("=== 完了 ===")


if __name__ == "__main__":
    main()
