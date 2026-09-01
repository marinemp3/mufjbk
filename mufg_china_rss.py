import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
import re
import os

# --- 1. 設定 ---
TARGET_URL = "https://www.bk.mufg.jp/report/inschimonth/" # 対象ページ
FEED_FILENAME = "feed.xml" # 出力するRSSファイル名
SITE_NAME = "MUFG BK Global Business Insight"
FEED_DESCRIPTION = "MUFG BK 中国月報 のRSSフィード"

# --- 2. データ取得と解析 ---
def fetch_and_parse_pdfs():
    """対象ページからPDFリンクと日付、タイトルを抽出する"""
    try:
        response = requests.get(TARGET_URL)
        response.raise_for_status() # エラーが発生したら例外を上げる
        response.encoding = response.apparent_encoding # 文字化け防止
    except requests.exceptions.RequestException as e:
        print(f"ページの取得に失敗しました: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_items = []

    # 全ての<a>タグを探し、PDFリンクを含むものを抽出
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        # リンク先がPDFで、かつ中国月報であることを確認
        if href and href.endswith('.pdf') and 'inschimonth' in href:
            # タイトルテキストを取得（例: "MUFG BK 中国月報 2026年8・9月 第244号"）
            title_text = link.get_text(strip=True)

            # 日付情報をタイトルから抽出（例: "2026年8・9月"）
            date_match = re.search(r'(\d{4})年(\d{1,2})・?(\d{1,2})?月', title_text)
            if date_match:
                year = int(date_match.group(1))
                month = int(date_match.group(2))
                # 日付はその月の1日として扱い、RSSの更新日時とする
                # 日本時間（JST, UTC+9）を設定
                jst = timezone(timedelta(hours=9))
                pub_date = datetime(year, month, 1, tzinfo=jst)
            else:
                # 日付が抽出できない場合は、現在日時を仮に設定（フォールバック）
                # 日本時間（JST, UTC+9）を設定
                jst = timezone(timedelta(hours=9))
                pub_date = datetime.now(jst)
                print(f"警告: 日付を抽出できませんでした。タイトル: {title_text}")

            # 絶対URLに変換
            if href.startswith('/'):
                pdf_url = f"https://www.bk.mufg.jp{href}"
            else:
                pdf_url = href

            pdf_items.append({
                'title': title_text,
                'link': pdf_url,
                'pub_date': pub_date,
                # 説明文はタイトルと同じか、空欄でも可
                'description': f"{title_text} のPDFファイルです。"
            })

    # 日付が新しい順にソート（オプション）
    pdf_items.sort(key=lambda x: x['pub_date'], reverse=True)
    return pdf_items

# --- 3. RSSフィード生成 ---
def generate_rss(items, filename):
    """抽出したアイテムからRSSフィードを生成する"""
    if not items:
        print("RSSに追加するアイテムが見つかりませんでした。")
        return

    fg = FeedGenerator()
    fg.title(SITE_NAME)
    fg.description(FEED_DESCRIPTION)
    fg.link(href=TARGET_URL, rel='alternate')
    # フィード自体の最終更新日時を設定（最新アイテムの日付を使用）
    # items[0]['pub_date'] には既にタイムゾーン情報（JST）が含まれている
    fg.lastBuildDate(items[0]['pub_date'])

    for item in items:
        fe = fg.add_entry()
        fe.title(item['title'])
        fe.link(href=item['link'])
        fe.pubDate(item['pub_date'])
        fe.description(item['description'])
        # GUID（各アイテムを一意に識別するID）としてリンクを使用
        fe.guid(item['link'], permalink=True)

    # RSS 2.0形式でファイルに出力
    rss_str = fg.rss_str(pretty=True) # pretty=Trueで整形
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(rss_str.decode('utf-8'))
    print(f"RSSフィード '{filename}' を生成しました。")

# --- 4. スクリプト実行 ---
if __name__ == "__main__":
    print("PDFリンクの取得を開始します...")
    pdf_data = fetch_and_parse_pdfs()
    if pdf_data:
        print(f"{len(pdf_data)} 件のアイテムを取得しました。")
        generate_rss(pdf_data, FEED_FILENAME)
    else:
        print("アイテムが取得できなかったため、処理を終了します。")
