from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import csv

#https://tenshoku.mynavi.jp/list/o132/?jobsearchType=14&searchType=18&refLoc=fnc_sra

# ChromeDriverパス
chrome_path = "/usr/bin/chromedriver"
service = Service(executable_path=chrome_path)

# オプション設定
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# ドライバー起動
driver = webdriver.Chrome(service=service, options=options)

# ページ設定
base_url = "https://tenshoku.mynavi.jp/list/o132/"
query = "?jobsearchType=14&searchType=18&refLoc=fnc_sra"

# 保存先
output_path = "job_full_info_with_dates.csv"
count = 1

with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "No", "求人タイトル", "サブタイトル",
        "仕事内容", "対象となる方", "勤務地", "給与", "初年度年収",
        "情報更新日", "掲載終了予定日"
    ])

    for page in range(1, 8):
        url = f"{base_url}pg{page}/{query}" if page != 1 else base_url + query
        print(f"[INFO] アクセス中: {url}")
        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        jobs = soup.select("div.cassetteRecruit")

        for job in jobs:
            title = job.select_one("h3.cassetteRecruit__name")
            subtitle = job.select_one("p.cassetteRecruit__copy a")

            title_text = title.get_text(strip=True) if title else ""
            subtitle_text = subtitle.get_text(strip=True) if subtitle else ""

            # 詳細情報のtableから取得
            table = job.select_one("table.tableCondition")
            details = {
                "仕事内容": "", "対象となる方": "", "勤務地": "",
                "給与": "", "初年度年収": ""
            }

            if table:
                for row in table.select("tr"):
                    head = row.select_one("th")
                    body = row.select_one("td")
                    if head and body and head.text.strip() in details:
                        details[head.text.strip()] = body.get_text(strip=True)

            # 情報更新日・掲載終了予定日
            update = job.select_one("p.cassetteRecruit__updateDate span")
            end = job.select_one("p.cassetteRecruit__endDate span")
            update_text = update.get_text(strip=True) if update else ""
            end_text = end.get_text(strip=True) if end else ""

            writer.writerow([
                count, title_text, subtitle_text,
                details["仕事内容"], details["対象となる方"], details["勤務地"],
                details["給与"], details["初年度年収"],
                update_text, end_text
            ])
            count += 1

driver.quit()
print(f"[INFO] 全データ保存完了（{count - 1}件） → {output_path}")
