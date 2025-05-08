import requests
from bs4 import BeautifulSoup
import csv

base_url = "https://jobuddy.jp"
headers = {"User-Agent": "Mozilla/5.0"}

# 詳細ページ1件のデータを抽出
def extract_job_details(detail_url):
    res = requests.get(detail_url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    def extract_text(selector):
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else "記載なし"

    def extract_section_text(header_text):
        for item in soup.find_all("div", class_="item"):
            h3 = item.find("h3")
            if h3 and h3.get_text(strip=True) == header_text:
                contents = item.find("div", class_="contents")
                if contents:
                    return contents.get_text("\n", strip=True)
        return "記載なし"

    def extract_list_by_header(header_text):
        for item in soup.find_all("div", class_="item"):
            h3 = item.find("h3")
            if h3 and h3.get_text(strip=True) == header_text:
                contents = item.find("div", class_="contents")
                ul = contents.find("ul") if contents else None
                if ul:
                    return "\n".join(li.get_text(strip=True) for li in ul.find_all("li"))
        return "記載なし"

    return {
        "Indeed項目": detail_url,
        "会社名": extract_text(".company-name"),
        "職種名": extract_text("h1.kyujin-title"),
        "キャッチコピー": extract_text(".catch-copy p"),
        "雇用形態": extract_text(".kodawari li"),
        "勤務地": extract_text(".kinmuti p:nth-of-type(2)"),
        "給与": extract_section_text("給与"),
        "試用期間": extract_section_text("試用期間"),
        "募集要項（仕事内容）": extract_section_text("仕事内容"),
        "アピールポイント": extract_text(".recommend p"),
        "求める人材": extract_section_text("応募条件"),
        "勤務時間": extract_section_text("勤務時間"),
        "休暇・休日": extract_list_by_header("休日休暇"),
        "給与の補足": extract_section_text("初年度想定年収"),
        "待遇・福利厚生": extract_list_by_header("福利厚生"),
        "その他": extract_section_text("当社・部署について")
    }

# 全ページ処理
def scrape_all_pages(keyword="クリエイティブ", output_file="jobuddy_all_data.csv"):
    all_data = []
    page = 1

    while True:
        search_url = f"{base_url}/recruit/search?word={keyword}&page={page}"
        print(f"[INFO] ページ {page} 処理中...")
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        job_links = soup.select("div.apply a[href^='https://jobuddy.jp/recruit/detail/']")
        if not job_links:
            print("[INFO] 最後のページに到達または求人が見つかりません。")
            break

        for a_tag in job_links:
            detail_url = a_tag["href"]
            try:
                data = extract_job_details(detail_url)
                all_data.append(data)
                print(f"[OK] {detail_url} 抽出成功")
            except Exception as e:
                print(f"[ERROR] {detail_url} の処理失敗: {e}")

        page += 1

    if all_data:
        with open(output_file, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
        print(f"[DONE] {len(all_data)} 件のデータを {output_file} に保存しました。")
    else:
        print("[WARN] データが取得できませんでした。")

# 実行
if __name__ == "__main__":
    scrape_all_pages()
