import requests
from bs4 import BeautifulSoup
import csv

# --- 基本設定 ---
base_url = "https://jobuddy.jp"
search_url = f"{base_url}/recruit/search?word=クリエイティブ&page=1"
headers = {
    "User-Agent": "Mozilla/5.0"
}

# --- 詳細ページURL取得関数 ---
def get_first_job_detail_url():
    res = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # div.apply の中にある aタグ（詳細ページURL）
    apply_divs = soup.select("div.apply a[href^='https://jobuddy.jp/recruit/detail/']")
    if apply_divs:
        return apply_divs[0]["href"]
    return None

# --- 詳細ページ情報抽出 ---
def extract_job_details(detail_url):
    res = requests.get(detail_url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # ↓ ここに追加！
    def extract_section_text(header_text):
        for item in soup.find_all("div", class_="item"):
            h3 = item.find("h3")
            if h3 and h3.get_text(strip=True) == header_text:
                contents = item.find("div", class_="contents")
                if contents:
                    return contents.get_text("\n", strip=True)
        return "記載なし"

    # ↓ 既存の補助関数
    def extract_text(selector, tag="p"):
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else "記載なし"
    
    def extract_list_text(selector):
        ul = soup.select_one(selector)
        if ul:
            return "\n".join(li.get_text(strip=True) for li in ul.find_all("li"))
        return "記載なし"
    
    def extract_list_by_header(header_text):
        for item in soup.find_all("div", class_="item"):
            h3 = item.find("h3")
            if h3 and h3.get_text(strip=True) == header_text:
                contents = item.find("div", class_="contents")
                if contents:
                    ul = contents.find("ul")
                    if ul:
                        return "\n".join(li.get_text(strip=True) for li in ul.find_all("li"))
        return "記載なし"

    # ... 以降に job_data の構築


    job_data = {
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

    return job_data

# --- CSV保存関数 ---
def save_to_csv(data, filename="jobuddy_scraped_data.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writeheader()
        writer.writerow(data)

# --- メイン処理 ---
if __name__ == "__main__":
    detail_relative_url = get_first_job_detail_url()
    if detail_relative_url:
        # 絶対URLかどうかをチェックして適切に代入
        if detail_relative_url.startswith("http"):
            full_url = detail_relative_url
        else:
            full_url = base_url + detail_relative_url

        job_info = extract_job_details(full_url)
        save_to_csv(job_info)
        print("[OK] データをCSVに保存しました。")
    else:
        print("[ERROR] 詳細ページへのリンクが取得できませんでした。")

