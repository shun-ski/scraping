import requests
from bs4 import BeautifulSoup
from gspread_util import Gspread_Util
import time
from setting import service_account_path, sheet_id, sheet_tab_name, list_url


# 実行時間計測
start_time = time.time()

# ヘッダー付きでリクエスト（Bot対策回避用）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

# 一覧ページ取得
print(f"[INFO] 一覧ページアクセス中: {list_url}")
response = requests.get(list_url, headers=headers)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

jobs = soup.select("div.cassetteRecruit")

rows = []
count = 1

for job in jobs:
    title_elem = job.select_one("h3.cassetteRecruit__name")
    subtitle_link = job.select_one("p.cassetteRecruit__copy a")

    title_text = title_elem.get_text(strip=True) if title_elem else ""
    subtitle_text = subtitle_link.get_text(strip=True) if subtitle_link else ""
    detail_url = "https:" + subtitle_link["href"] if subtitle_link and subtitle_link.has_attr("href") else ""

    work_content = ""
    company_name = ""

    # 詳細ページへアクセス
    if detail_url:
        print(f"[INFO] 詳細ページアクセス中: {detail_url}")
        detail_response = requests.get(detail_url, headers=headers)
        detail_response.encoding = detail_response.apparent_encoding
        detail_soup = BeautifulSoup(detail_response.text, "html.parser")

        # 仕事内容取得
        table = detail_soup.select_one("table.tableCondition")
        if table:
            for row_elem in table.select("tr"):
                th = row_elem.select_one("th")
                td = row_elem.select_one("td")
                if th and td and th.text.strip() == "仕事内容":
                    work_content = td.get_text(strip=True)
                    break

        # 会社名取得
        company_elem = detail_soup.select_one("h2.companyName")
        if company_elem:
            company_name = company_elem.get_text(strip=True)

    # データ追加
    rows.append([
        count, title_text, subtitle_text, work_content, company_name, detail_url
    ])
    count += 1

print(f"[INFO] データ抽出完了：{count - 1}件")

# スプレッドシートへ書き込み
gs_util = Gspread_Util(service_account_path)
workbook = gs_util.get_workbook_by_id(sheet_id)
worksheet = workbook.worksheet(sheet_tab_name)

header = ["No", "求人タイトル", "サブタイトル", "仕事内容", "会社名", "詳細ページURL"]
full_data = [header] + rows

worksheet.clear()
gs_util.list_2_spread(full_data, worksheet)

# 実行時間
end_time = time.time()
elapsed = end_time - start_time
print(f"[INFO] スプレッドシートへの書き込み完了")
print(f"[INFO] 実行時間: {elapsed:.2f} 秒")


# 54秒