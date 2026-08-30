# -*- coding: utf-8 -*-
r"""
sapporo_chuo_collector.py (Ver.6.2)
==================================
札幌市中央区の「飲食・アニメ・音楽ライブ」情報を毎日自動収集するツール。

【できること】
  - 複数の情報サイトを巡回し、イベント/ライブ情報を取得
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
     （大丸札幌店は催事ページがJavaScriptで動的生成されるため、今回は
      静的HTMLを取得するこのスクリプトでは対応できていません）
  8. 映画情報（公式優先）
     - ローソン・ユナイテッドシネマ札幌 公式「公開予定作品」
       https://www.unitedcinemas.jp/sapporo/movie.php
     - TOHOシネマズすすきの 公式「前売券情報」
       https://www.tohotheater.jp/theater/089/info/advanceticket.html
     - MOVIE WALKER PRESS（バックアップ）
       https://press.moviewalker.jp/theater/108/
     公式情報を優先し、1サイトが取得できなくても他の情報源から補完します。

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
# Ver.6: サイトごとにタイムアウトを設定し、応答しないサイトを自動スキップする。
# 全体を止めないことを最優先に、短めのタイムアウト＋少回数リトライで運用。
REQUEST_TIMEOUT = 15  # 未登録ドメインの標準タイムアウト（秒）
REQUEST_RETRIES = 1   # 初回＋1回だけ再試行
REQUEST_INTERVAL_SEC = 1.5  # 相手サーバーへの配慮（連続アクセスの間隔）
RETRY_BACKOFF_SEC = 2.0

# 情報源ごとのタイムアウト。特に止まりやすかったサイトは短めに設定。
SITE_TIMEOUTS = {
    "sapporo.magazine.events": 12,
    "www.sapporo-chikamichi.jp": 12,
    "www.cube-garden.com": 10,
    "www.walkerplus.com": 15,
    "www.eventernote.com": 12,
    "www.mitsukoshi.mistore.jp": 15,
    "www.maruiimai.mistore.jp": 15,
    "press.moviewalker.jp": 12,
    "www.unitedcinemas.jp": 12,
    "www.tohotheater.jp": 12,
}

# 再試行するHTTPステータス。404等の恒久エラーは無駄に再試行しない。
RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}

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
        "アニメ展示会", "アニメ原画展", "原画展", "複製原画展", "POP UP", "ポップアップ",
        "期間限定ショップ", "コラボカフェ",
        "アニメ映画", "劇場版",
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
    "🎮 アニメ": ["声優イベント", "アニメライブ"],  # 映画/上映会/舞台挨拶は今回対象に含めるため除外しない
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
GEMINI_MODEL = "gemini-flash-latest"  # 常に最新の安定版Flashモデルを指すエイリアス（個別モデル名の廃止に強い）
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
AI_ENABLED = bool(GEMINI_API_KEY)
AI_REQUEST_INTERVAL_SEC = 4.5  # 無料枠のレート制限(1分あたりのリクエスト数)に配慮した間隔
AI_TIMEOUT = 20
AI_MAX_RETRIES = 1  # Ver.6: AIも長時間停止させない（初回＋1回）

AI_SYSTEM_PROMPT = """あなたは札幌市中央区の地域情報まとめサイト向けに、イベント情報を判定するアシスタントです。
以下のイベント情報を読み、次のカテゴリのうち当てはまるものだけを選んでください（複数可、0個も可）。

- 🍜 飲食: グルメフェス、フードフェス、マルシェ、物産展、食べ歩き・食べ比べイベント、スイーツイベント、
  ラーメン/肉/餃子フェス、ビアガーデン、日本酒・ワイン・クラフトビール系イベントなど。
  普通のレストラン・カフェ・居酒屋の宣伝は含めない。
- 🎮 アニメ: アニメの原画展、企画展、特別展、POP UPストア、期間限定ショップ、コラボカフェ、複製原画展、
  物販イベントなど。声優イベント、アニメライブ、上映会、映画、舞台挨拶は含めない。
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
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200},
                },
                timeout=AI_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_error = e
            if attempt <= AI_MAX_RETRIES:
                log.warning(f"Gemini API 呼び出し失敗(試行{attempt}回目、再試行します): {e}")
                time.sleep(3)
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


# ----------------------------------------------------------------------------
# 共通ユーティリティ
# ----------------------------------------------------------------------------

def _site_config(url: str) -> tuple[int, int]:
    """URLからサイト別のタイムアウト秒数と再試行回数を決める。"""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    timeout = SITE_TIMEOUTS.get(host, REQUEST_TIMEOUT)
    return timeout, REQUEST_RETRIES


def fetch(url: str) -> Optional[BeautifulSoup]:
    """
    URLを取得してBeautifulSoupオブジェクトを返す。

    Ver.5の重要ポイント:
      - サイト別タイムアウトで「1サイト待ち続ける」を防止
      - タイムアウト/接続エラー/一時的HTTPエラーだけ1回再試行
      - 最終的に失敗したらNoneを返し、呼び出し側が次の情報源へ進める
      - 500系エラーでもスクリプト全体を停止させない
    """
    timeout, max_retries = _site_config(url)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=timeout,
            )

            # 500/502/503/504等は一時的な障害の可能性があるため再試行。
            if resp.status_code in RETRY_STATUS_CODES and attempt < max_retries:
                log.warning(
                    f"一時HTTPエラー: {url} ({resp.status_code}) "
                    f"→ {RETRY_BACKOFF_SEC:.1f}秒後に再試行"
                )
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue

            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return BeautifulSoup(resp.text, "lxml")

        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                log.warning(
                    f"取得タイムアウト/接続失敗: {url} "
                    f"({timeout}秒) → {RETRY_BACKOFF_SEC:.1f}秒後に再試行"
                )
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            break

        except requests.HTTPError as e:
            last_error = e
            # ここまで来たHTTPエラーは、再試行しても改善しにくいものとして即スキップ。
            break

        except Exception as e:
            last_error = e
            break

    log.warning(
        f"取得失敗・スキップ: {url} "
        f"(timeout={timeout}s, retries={max_retries}, error={last_error})"
    )
    time.sleep(REQUEST_INTERVAL_SEC)
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
    """タイトル＋会場名＋タグから、飲食/音楽ライブ/アニメ のどれに該当するか判定
    （かなり絞り込んだキーワード基準。デパート催事はタグで別途判定）"""
    haystack = normalize(f"{item.title} {item.place} {' '.join(item.tags)}")
    haystack_lower = haystack.lower()
    matched = []
    for label, includes in CATEGORY_INCLUDE.items():
        if any(normalize(inc).lower() in haystack_lower for inc in includes):
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


def collect_manual_events() -> Iterable[EventItem]:
    """自動収集が難しい大型の年次フェス等を手動で登録しておく場所。
    ここに追加した項目も、他の情報源と同じくclassify()でカテゴリ判定される
    （タイトルにCATEGORY_INCLUDEの語句が含まれていれば自動的に採用される）。
    URLは重複判定のキーにもなるので、年ごとに変えるなどして使い回さないこと。"""
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
        # 他の年次フェスもここに追加できます。例:
        # {
        #     "title": "さっぽろ雪まつり2027",
        #     "date_text": "2027年2月上旬",
        #     "place": "大通公園（中央区）ほか",
        #     "url": "https://www.snowfes.com/#2027",
        # },
    ]
    for ev in manual_events:
        yield EventItem(
            source="手動登録(年次フェス)",
            title=ev["title"],
            url=ev["url"],
            date_text=ev.get("date_text", ""),
            place=ev.get("place", ""),
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
    "th533": "シアターキノ",
    "th828": "TOHOシネマズすすきの",
}

# 現在上映中の映画一覧には「アニメかどうか」の情報が付いていないため、
# タイトルに含まれる語句で簡易的にアニメ映画かどうかを判定する。
# 新作アニメ映画のタイトルが拾えない場合は、ここにキーワードを追加してください。
ANIME_MOVIE_HINTS = [
    "アニメ", "劇場版", "ちいかわ", "クレヨンしんちゃん", "ポケモン", "ドラえもん",
    "名探偵コナン", "鬼滅の刃", "呪術廻戦", "ワンピース", "ガンダム", "五等分の花嫁",
    "推しの子", "スパイファミリー", "スパイ×ファミリー", "ヒーローアカデミア", "チェンソーマン",
    "薬屋のひとりごと", "プリキュア", "ウルトラマン", "幻想水滸伝", "パウ・パトロール",
    "ミニオンズ", "まどか", "マギカ", "超かぐや姫", "かぐや姫",
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
    タグを追加する。同じ映画が複数の映画館で上映されていても1件にまとめる。

    まとめページ(theater/108等)は注目記事中心で全作品が載らないため、
    映画館ごとの個別スケジュールページを1館ずつ巡回して対象の映画IDを集め、
    そのあと各映画の個別ページを開いて正確なタイトルを取得する2段階方式にしている。"""
    seen_movie_ids: dict[str, str] = {}  # movie_id -> href（最初に見つかったもの）
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
            if movie_id not in seen_movie_ids:
                seen_movie_ids[movie_id] = href if href.startswith("http") else f"https://press.moviewalker.jp{href}"

    count = 0
    anime_count = 0
    all_titles = []
    for movie_id, schedule_url in seen_movie_ids.items():
        title = _extract_title_from_schedule_page(schedule_url)
        if not title:
            continue

        tags = ["映画上映中"]
        if any(hint in title for hint in ANIME_MOVIE_HINTS):
            tags.append("劇場版")
            anime_count += 1

        count += 1
        all_titles.append(title)
        yield EventItem(
            source="映画館(上映中)",
            title=title[:80],
            url=f"https://press.moviewalker.jp/mv{movie_id}/",
            place="札幌市内の映画館（中央区）で上映中",
            tags=tags,
        )
    log.info(f"映画館(上映中): {count}件（うちアニメ映画と判定: {anime_count}件）")
    log.info(f"映画館(上映中) 取得タイトル一覧: {all_titles}")


def _parse_release_date(text: str) -> Optional[date]:
    """日本語/スラッシュ表記の公開日からdateを作る。"""
    text = normalize(clean(text))
    patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if not m:
            continue
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _in_upcoming_window(release_date: Optional[date], today: date) -> bool:
    return bool(release_date and today <= release_date <= today + timedelta(days=60))


def _make_upcoming_movie(title: str, release_date: date, url: str, source: str, place: str) -> EventItem:
    tags = ["公開予定映画"]
    if any(hint in title for hint in ANIME_MOVIE_HINTS):
        tags.append("劇場版")
    return EventItem(
        source=source,
        title=title[:80],
        url=url,
        date_text=f"{release_date.year}年{release_date.month}月{release_date.day}日公開",
        place=place,
        tags=tags,
    )


def _collect_unitedcinemas_upcoming(today: date) -> Iterable[EventItem]:
    """ローソン・ユナイテッドシネマ札幌の公式「公開予定作品」から取得。"""
    url = "https://www.unitedcinemas.jp/sapporo/movie.php"
    soup = fetch(url)
    if soup is None:
        return

    # 公式ページは「公開日 → 作品名」の順で掲載されるため、日付行の直後から
    # 作品名らしい文字列を探す。作品情報/予告編などのナビ文言は除外する。
    lines = [clean(x) for x in soup.stripped_strings if clean(x)]
    date_re = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}(?:（.*?）)?(?:公開|上映)?$")
    skip = {"作品情報", "予告編", "作品情報・上映スケジュール", "公開予定作品", "上映作品のご案内"}
    count = 0

    for i, line in enumerate(lines):
        if not date_re.fullmatch(line):
            continue
        release_date = _parse_release_date(line)
        if not _in_upcoming_window(release_date, today):
            continue

        title = ""
        for candidate in lines[i + 1:i + 8]:
            if candidate in skip or date_re.fullmatch(candidate):
                continue
            if len(candidate) < 2 or len(candidate) > 120:
                continue
            # 作品名に続く出演者・監督情報などを拾わないよう、明らかな説明文を除外。
            if candidate.startswith(("©", "監督", "出演", "声の出演", "Image", "字幕", "吹替")):
                continue
            title = candidate
            break
        if not title:
            continue

        count += 1
        yield _make_upcoming_movie(
            title=title,
            release_date=release_date,
            url=url,
            source="ローソン・ユナイテッドシネマ札幌(公式・公開予定)",
            place="ローソン・ユナイテッドシネマ札幌（札幌市中央区）",
        )

    log.info(f"ユナイテッドシネマ公式(公開予定): {count}件")


def _collect_toho_susukino_upcoming(today: date) -> Iterable[EventItem]:
    """TOHOシネマズすすきの公式の前売券情報から、公開予定作品を補完取得。"""
    url = "https://www.tohotheater.jp/theater/089/info/advanceticket.html"
    soup = fetch(url)
    if soup is None:
        return

    # TOHO公式ページは作品名 → 「公開日」 → 日付 の構造。
    # 見出し(h2/h3)を中心に探索し、ページ全体の文字列でも保険をかける。
    count = 0
    seen = set()
    headings = soup.find_all(["h2", "h3", "h4"])
    for heading in headings:
        title = clean(heading.get_text(" ", strip=True))
        if not title or len(title) > 120:
            continue
        if title in {"TOHOシネマズすすきの前売券情報", "前売券情報"}:
            continue

        parent_text = clean(heading.parent.get_text(" ", strip=True)) if heading.parent else ""
        release_date = _parse_release_date(parent_text)
        if not _in_upcoming_window(release_date, today):
            continue
        if title in seen:
            continue

        seen.add(title)
        count += 1
        yield _make_upcoming_movie(
            title=title,
            release_date=release_date,
            url=url,
            source="TOHOシネマズすすきの(公式・公開予定)",
            place="TOHOシネマズすすきの（札幌市中央区）",
        )

    # 見出し構造が変わった場合のフォールバック。
    if count == 0:
        strings = [clean(x) for x in soup.stripped_strings if clean(x)]
        for i, s in enumerate(strings):
            if s != "公開日" or i + 1 >= len(strings):
                continue
            release_date = _parse_release_date(strings[i + 1])
            if not _in_upcoming_window(release_date, today):
                continue
            title = ""
            for candidate in reversed(strings[max(0, i - 5):i]):
                if 2 <= len(candidate) <= 120 and candidate not in {"公開日", "価格", "発売日", "特典"}:
                    title = candidate
                    break
            if title and title not in seen:
                seen.add(title)
                count += 1
                yield _make_upcoming_movie(
                    title=title,
                    release_date=release_date,
                    url=url,
                    source="TOHOシネマズすすきの(公式・公開予定)",
                    place="TOHOシネマズすすきの（札幌市中央区）",
                )

    log.info(f"TOHOシネマズすすきの公式(公開予定): {count}件")


def _collect_moviewalker_upcoming(today: date) -> Iterable[EventItem]:
    """MOVIE WALKER PRESSの公開予定情報。公式情報の取りこぼしを補うバックアップ。"""
    date_re = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日公開")

    for theater_id in SAPPORO_MOVIE_THEATERS:
        url = f"https://press.moviewalker.jp/{theater_id}/schedule/"
        soup = fetch(url)
        if soup is None:
            continue

        href_by_text = {}
        for a in soup.find_all("a", href=re.compile(r"^/mv\d+/?$")):
            t = clean(a.get_text())
            if t:
                href = a["href"]
                href_by_text[t] = href if href.startswith("http") else f"https://press.moviewalker.jp{href}"

        strings = list(soup.stripped_strings)
        for i, s in enumerate(strings):
            if not date_re.fullmatch(s) or i < 1:
                continue
            title = strings[i - 1]
            if not title or not (2 <= len(title) <= 60) or date_re.fullmatch(title):
                continue

            release_date = _parse_release_date(s)
            if not _in_upcoming_window(release_date, today):
                continue

            yield _make_upcoming_movie(
                title=title,
                release_date=release_date,
                url=href_by_text.get(title, url),
                source="映画館(MOVIE WALKER・公開予定)",
                place="札幌市内の映画館（中央区）で公開予定",
            )


def collect_upcoming_movies() -> Iterable[EventItem]:
    """今後2ヶ月以内の公開予定映画を、映画館公式＋MOVIE WALKERの多重取得で集める。

    優先順位:
      1. ローソン・ユナイテッドシネマ札幌 公式「公開予定作品」
      2. TOHOシネマズすすきの 公式「前売券情報」
      3. MOVIE WALKER PRESS（バックアップ）

    同一タイトルはタイトル正規化で重複除去するため、公式とMOVIE WALKERの両方に
    掲載されていても1件にまとめる。1サイトが落ちても他の情報源は継続する。
    """
    today = datetime.now().date()
    # 「作品タイトル本体＋公開日」で同一作品をまとめる。
    # 劇場ごとの「復活上映」「特別フォーマット版」などの表記差も吸収する。
    seen_titles = set()
    count = 0
    anime_count = 0

    collectors = [
        _collect_unitedcinemas_upcoming,
        _collect_toho_susukino_upcoming,
        _collect_moviewalker_upcoming,
    ]

    for collector in collectors:
        try:
            for item in collector(today):
                key = f"{_normalize_movie_title(item.title)}|{_movie_release_key(item.date_text)}"
                if key in seen_titles:
                    # 同一作品が別劇場から来た場合でも、ここでは別EventItemを捨てず、
                    # DB側のevent_key統合処理で会場情報を集約するためyieldする。
                    pass
                else:
                    seen_titles.add(key)
                    count += 1
                if "劇場版" in item.tags:
                    anime_count += 1
                yield item
        except Exception as e:
            log.error(f"公開予定映画の取得中にエラー: {collector.__name__}: {e} → 次の情報源へ続行")
            continue

    log.info(f"映画館(公開予定・公式優先): {count}件（うちアニメ映画と判定: {anime_count}件）")


SOURCES = {
    "satsuibe": collect_satsuibe,
    "chikaho": collect_chikaho,
    "cube_garden": collect_cube_garden,
    "walkerplus_live": collect_walkerplus_live,
    "walkerplus_anime": collect_walkerplus_anime,
    "eventernote_major": collect_eventernote_major_venues,
    "mitsukoshi": collect_mitsukoshi,
    "maruiimai": collect_maruiimai,
    "movie_theaters": collect_movie_theaters,
    "upcoming_movies": collect_upcoming_movies,
    "manual": collect_manual_events,
}


# ----------------------------------------------------------------------------
# データベース
# ----------------------------------------------------------------------------

def consolidate_movie_duplicates(conn: sqlite3.Connection) -> int:
    """既存DBに残っている「同じ映画の表記違い」重複を1件へ統合する。

    Ver.6.2ではタイトルが完全一致する場合のみ統合されていたため、
    「超かぐや姫！復活上映」と「超かぐや姫！特別フォーマット版」のような
    表記差が別レコードになり得る。起動時に既存データも自動修正する。
    """
    rows = conn.execute(
        "SELECT id,event_key,url,source,title,date_text,place,fee,categories,first_seen,last_seen,blurb "
        "FROM events WHERE event_key LIKE 'movie|%' ORDER BY id"
    ).fetchall()
    groups = {}
    for row in rows:
        key = f"{_normalize_movie_title(row[4])}|{_movie_release_key(row[5])}"
        groups.setdefault(key, []).append(row)

    merged = 0
    for group_key, items in groups.items():
        if len(items) <= 1:
            continue
        # 代表レコードは公式優先、同順位なら最初のレコード。
        items = sorted(items, key=lambda r: (_movie_source_priority(r[3]), r[0]))
        keep = items[0]
        keep_id = keep[0]
        canonical_title = _canonical_movie_title(keep[4])

        places = []
        sources = []
        cats = []
        first_seen = keep[9]
        last_seen = keep[10]
        blurb = keep[11] or ""
        best_url = keep[2]
        best_source = keep[3]
        best_priority = _movie_source_priority(best_source)

        for row in items:
            if row[6] and clean(row[6]) not in places:
                places.append(clean(row[6]))
            if row[3] and row[3] not in sources:
                sources.append(row[3])
            for c in (row[8] or "").split(","):
                c = clean(c)
                if c and c not in cats:
                    cats.append(c)
            if row[9] and (not first_seen or row[9] < first_seen):
                first_seen = row[9]
            if row[10] and row[10] > last_seen:
                last_seen = row[10]
            if not blurb and row[11]:
                blurb = row[11]
            priority = _movie_source_priority(row[3])
            if priority < best_priority:
                best_priority = priority
                best_url = row[2]
                best_source = row[3]

        merged_place = " / ".join(places)
        # sourceは代表の公式ソースを残しつつ、複数ソースがあることも分かるようにする。
        merged_source = best_source
        for src in sources:
            if src != merged_source and src not in merged_source:
                merged_source += " / " + src

        conn.execute(
            "UPDATE events SET event_key=?,url=?,source=?,title=?,date_text=?,place=?,categories=?,first_seen=?,last_seen=?,blurb=? WHERE id=?",
            (
                f"movie|{_normalize_movie_title(canonical_title)}|{_movie_release_key(keep[5])}",
                best_url, merged_source, canonical_title, keep[5], merged_place, ",".join(cats),
                first_seen, last_seen, blurb, keep_id,
            ),
        )
        for row in items[1:]:
            conn.execute("DELETE FROM events WHERE id=?", (row[0],))
            merged += 1

    if merged:
        conn.commit()
        log.info(f"公開予定映画の既存重複を統合: {merged}件削除")
    return merged


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


def _canonical_movie_title(title: str) -> str:
    """映画タイトルを表示用の基本タイトルへ正規化する。

    劇場ごとに「復活上映」「特別フォーマット版」などの販売/上映形態が付く
    場合があるため、それらをタイトル本体から切り離して同一作品として扱う。
    """
    t = clean(title or "")
    # 全角/半角・前後空白・先頭の装飾括弧を吸収
    t = normalize(t).strip()
    t = re.sub(r"[【】\[\]]", "", t).strip()

    # 先頭/末尾に付く劇場・販売上の補足表現を除去
    # 例: 「超かぐや姫！ 復活上映」「超かぐや姫！ 特別フォーマット版」
    patterns = [
        r"\s*(?:復活上映|再上映|リバイバル上映|アンコール上映)\s*$",
        r"\s*(?:特別フォーマット版|特別上映版|特別版)\s*$",
        r"\s*(?:通常版|通常上映)\s*$",
    ]
    for pattern in patterns:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE).strip()

    # 末尾の括弧内が上映形態だけなら除去
    t = re.sub(r"[（(](?:復活上映|再上映|特別フォーマット版|特別上映版|特別版|通常版|通常上映)[）)]\s*$", "", t).strip()
    return t or clean(title or "")


def _normalize_movie_title(title: str) -> str:
    """映画の重複判定用タイトル。上映形態の違いは同一作品として扱う。"""
    t = _canonical_movie_title(title).lower()
    t = re.sub(r"\s+", "", t)
    return t


def _movie_release_key(date_text: str) -> str:
    """公開日を重複判定用のISO日付へ変換する。"""
    dt = _parse_release_date(date_text or "")
    return dt.isoformat() if dt else normalize(clean(date_text or ""))


def _is_upcoming_movie_item(item: EventItem) -> bool:
    """公開予定映画として扱うべきイベントか判定する。"""
    return (
        "公開予定映画" in (item.tags or [])
        or "公開予定" in (item.source or "")
        or "🍿 公開予定映画" in (item.categories or [])
    )


def _event_key(item: EventItem) -> str:
    """DB上の論理キー。

    通常イベントはURLをキーにするが、公開予定映画だけは
    「映画タイトル＋公開日」をキーにする。これにより、同じ劇場の公式ページURLを
    複数作品が共有していても、作品ごとに別レコードとして保存できる。
    """
    if _is_upcoming_movie_item(item):
        return f"movie|{_normalize_movie_title(item.title)}|{_movie_release_key(item.date_text)}"
    return f"url|{normalize(clean(item.url or ''))}"


def _is_movie_source(source: str) -> bool:
    return "公開予定" in (source or "")


def _movie_source_priority(source: str) -> int:
    """公開予定映画の情報源優先度。数字が小さいほど優先。"""
    source = source or ""
    if "ユナイテッドシネマ公式" in source:
        return 10
    if "TOHOシネマズすすきの公式" in source:
        return 20
    if "MOVIE WALKER" in source:
        return 30
    return 50


def _merge_movie_place(old_place: str, new_place: str) -> str:
    """同一作品が複数劇場から取得された場合、劇場情報を重複なく統合する。"""
    vals = []
    for text in (old_place or "", new_place or ""):
        text = clean(text)
        if text and text not in vals:
            vals.append(text)
    return " / ".join(vals)


def init_db(conn: sqlite3.Connection) -> None:
    """DB初期化/マイグレーション。

    Ver.6.2ではURLを物理的な主キーにせず、idを主キー、event_keyを論理一意キーにする。
    映画だけevent_keyを「タイトル＋公開日」にすることで、劇場公式ページの共通URLによる
    大量の作品消失を防ぐ。
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}

    if not cols:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                source TEXT,
                title TEXT,
                date_text TEXT,
                place TEXT,
                fee TEXT,
                categories TEXT,
                first_seen TEXT,
                last_seen TEXT,
                blurb TEXT DEFAULT ''
            )
            """
        )
        conn.commit()
        return

    # Ver.6以前は url TEXT PRIMARY KEY だったため、event_key方式へ一度だけ移行。
    if "id" not in cols or "event_key" not in cols:
        log.info("DBをVer.6.2形式へ移行します（URL主キー → id主キー＋event_key）")
        old_name = "events_old_v61"
        conn.execute(f"DROP TABLE IF EXISTS {old_name}")
        conn.execute(f"ALTER TABLE events RENAME TO {old_name}")
        conn.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                source TEXT,
                title TEXT,
                date_text TEXT,
                place TEXT,
                fee TEXT,
                categories TEXT,
                first_seen TEXT,
                last_seen TEXT,
                blurb TEXT DEFAULT ''
            )
            """
        )

        old_cols = {row[1] for row in conn.execute(f"PRAGMA table_info({old_name})")}
        select_cols = [c for c in ["url", "source", "title", "date_text", "place", "fee", "categories", "first_seen", "last_seen", "blurb"] if c in old_cols]
        rows = conn.execute(f"SELECT {', '.join(select_cols)} FROM {old_name}").fetchall()
        migrated = 0
        skipped = 0
        seen_keys = set()
        for row in rows:
            d = dict(zip(select_cols, row))
            item = EventItem(
                source=d.get("source") or "",
                title=d.get("title") or "",
                url=d.get("url") or "",
                date_text=d.get("date_text") or "",
                place=d.get("place") or "",
                fee=d.get("fee") or "",
                categories=[x for x in (d.get("categories") or "").split(",") if x],
                blurb=d.get("blurb") or "",
            )
            key = _event_key(item)
            if key in seen_keys:
                # 旧DBで同じ映画URLにまとめられていたレコードが複数ある場合の安全策。
                # 次回の公式取得で正しい作品データが復元されるため、重複は1件だけ残す。
                skipped += 1
                continue
            seen_keys.add(key)
            conn.execute(
                """
                INSERT INTO events
                    (event_key, url, source, title, date_text, place, fee, categories, first_seen, last_seen, blurb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key, item.url, item.source, item.title, item.date_text, item.place,
                    item.fee, ",".join(item.categories), d.get("first_seen") or "", d.get("last_seen") or "", item.blurb,
                ),
            )
            migrated += 1

        conn.execute(f"DROP TABLE {old_name}")
        conn.commit()
        log.info(f"DB移行完了: {migrated}件を移行 / 重複スキップ: {skipped}件")
        return

    # event_key方式になっているDBに、旧バージョン由来の列が不足していれば補う。
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    if "categories" not in existing_cols:
        conn.execute("ALTER TABLE events ADD COLUMN categories TEXT DEFAULT ''")
    if "blurb" not in existing_cols:
        conn.execute("ALTER TABLE events ADD COLUMN blurb TEXT DEFAULT ''")
    conn.commit()


def upsert_event(conn: sqlite3.Connection, item: EventItem, today: str) -> bool:
    """event_keyで新規/更新を判定する。

    通常イベント: URLベース
    公開予定映画: タイトル＋公開日ベース

    同一映画を複数の公式劇場/情報源から取得した場合は1件に統合し、
    劇場情報をplaceへ追記する。公式情報をMOVIE WALKERより優先して残す。
    """
    key = _event_key(item)
    cur = conn.execute(
        "SELECT id, url, source, title, date_text, place, fee, categories, blurb FROM events WHERE event_key = ?",
        (key,),
    )
    row = cur.fetchone()
    cats = ",".join(item.categories)
    display_title = _canonical_movie_title(item.title) if _is_upcoming_movie_item(item) else item.title

    if row is None:
        conn.execute(
            """
            INSERT INTO events
                (event_key, url, source, title, date_text, place, fee, categories, blurb, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (key, item.url, item.source, display_title, item.date_text, item.place, item.fee, cats, item.blurb, today, today),
        )
        return True

    event_id, old_url, old_source, old_title, old_date_text, old_place, old_fee, old_categories, old_blurb = row

    new_url = item.url
    new_source = item.source
    new_place = item.place

    if _is_upcoming_movie_item(item) or _is_movie_source(old_source):
        # 同じ映画が複数劇場/情報源に存在する場合は統合。
        new_place = _merge_movie_place(old_place, item.place)
        # 公式URLを優先。既存が公式ならMOVIE WALKERで上書きしない。
        if _movie_source_priority(item.source) > _movie_source_priority(old_source):
            new_url = old_url
            new_source = old_source
        elif _movie_source_priority(item.source) < _movie_source_priority(old_source):
            new_url = item.url
            new_source = item.source
        else:
            new_url = old_url or item.url
            new_source = old_source or item.source

    if item.blurb:
        conn.execute(
            """
            UPDATE events
               SET last_seen = ?, url = ?, source = ?, title = ?, date_text = ?, place = ?, fee = ?, categories = ?, blurb = ?
             WHERE id = ?
            """,
            (today, new_url, new_source, display_title, item.date_text, new_place, item.fee, cats, item.blurb, event_id),
        )
    else:
        conn.execute(
            """
            UPDATE events
               SET last_seen = ?, url = ?, source = ?, title = ?, date_text = ?, place = ?, fee = ?, categories = ?
             WHERE id = ?
            """,
            (today, new_url, new_source, item.title, item.date_text, new_place, item.fee, cats, event_id),
        )
    return False


def fetch_all_current(conn: sqlite3.Connection) -> list:
    """DB内の全件を、表示用にカテゴリ別へ振り分けて返す"""
    cur = conn.execute(
        "SELECT source, title, date_text, place, fee, categories, url, first_seen, blurb "
        "FROM events ORDER BY first_seen DESC, date_text ASC"
    )
    rows = cur.fetchall()
    return rows


# ----------------------------------------------------------------------------
# 開催日フィルタ（更新日から1か月分だけを表示）
# ----------------------------------------------------------------------------

_FULL_DATE_RE = re.compile(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})")
_SHORT_DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")


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
    cur = conn.execute("SELECT id, url, source, title, place FROM events")
    rows = cur.fetchall()
    updated = 0
    for event_id, url, source, title, place in rows:
        tmp = EventItem(source=source or "", title=title or "", url=url, place=place or "",
                         tags=infer_tags_from_source(source))
        cats = classify(tmp)
        conn.execute("UPDATE events SET categories = ? WHERE id = ?", (",".join(cats), event_id))
        updated += 1
    conn.commit()
    log.info(f"既存データ {updated} 件を最新の分類基準で再判定しました")


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
    for source, title, date_text, place, fee, cats, url, first_seen, blurb in rows:
        cat_list = cats.split(",") if cats else []
        for c in cat_list:
            if c in grouped:
                grouped[c].append((source, title, date_text, place, fee, url, first_seen, blurb))

    sections_html = ""
    for label in CATEGORY_ORDER:
        items = grouped[label]
        if not items:
            sections_html += f'<h2>{label}</h2><p class="empty">現在、該当する情報はありません。</p>'
            continue
        sections_html += f'<h2>{label} <span class="count">({len(items)}件)</span></h2><div class="cards">'
        for source, title, date_text, place, fee, url, first_seen, blurb in items:
            is_new = " new" if first_seen == today else ""
            badge = '<span class="badge">NEW</span>' if first_seen == today else ""
            sections_html += f"""
            <a class="card{is_new}" href="{escape_html(url)}" target="_blank" rel="noopener">
              {badge}
              <div class="card-title">{escape_html(title)}</div>
              {'<div class="card-blurb">✨ ' + escape_html(blurb) + '</div>' if blurb else ''}
              <div class="card-meta">
                {'📅 ' + escape_html(date_text) + '<br>' if date_text else ''}
                {'📍 ' + escape_html(place) + '<br>' if place else ''}
                {'💰 ' + escape_html(fee) + '<br>' if fee else ''}
                <span class="source">{escape_html(source)}</span>
              </div>
            </a>
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
    text-decoration: none;
    color: var(--text);
    transition: border-color 0.15s, transform 0.15s;
  }}
  .card:hover {{
    border-color: var(--accent2);
    transform: translateY(-2px);
  }}
  .card.new {{
    border-color: var(--accent);
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
    consolidate_movie_duplicates(conn)
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
            # Ver.6: 1情報源の異常で全体を止めない。
            log.error(f"{name} の収集中にエラー: {e} → この情報源をスキップして続行")
            continue

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

    # HTMLレポートを常に最新化（開催日が今日から1か月以内のものだけ表示）
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
