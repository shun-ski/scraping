from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import csv
import re

# ChromeDriverのパスと設定
chrome_path = "/usr/bin/chromedriver"
service = Service(executable_path=chrome_path)
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=service, options=options)

# 出力先
output_path = "job_details_cleaned.csv"

# CSVヘッダーの初回書き込み
with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "No", "求人タイトル", "サブタイトル", "仕事内容", "対象となる方", "勤務地",
        "給与", "初年度年収", "会社名", "住所", "電話番号", "企業HP", "詳細ページURL"
    ])

# スクレイピング対象ページ（1〜7ページ）
base_url = "https://tenshoku.mynavi.jp/list/o132/"
query = "?jobsearchType=14&searchType=18&refLoc=fnc_sra"
target_pages = list(range(1, 9))
count = 1

for page in target_pages:
    list_url = f"{base_url}pg{page}/{query}"
    print(f"[INFO] ページ{page}にアクセス中: {list_url}")
    driver.get(list_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    jobs = soup.select("div.cassetteRecruit")

    for job in jobs:
        title = job.select_one("h3.cassetteRecruit__name")
        subtitle_link = job.select_one("p.cassetteRecruit__copy a")

        title_text = title.get_text(strip=True) if title else ""
        subtitle_text = subtitle_link.get_text(strip=True) if subtitle_link else ""
        detail_url = "https:" + subtitle_link["href"] if subtitle_link and subtitle_link.has_attr("href") else ""
        detail_url = detail_url.replace("/msg/", "/")

        print(f"[INFO] 詳細ページアクセス中: {detail_url}")
        driver.get(detail_url)
        time.sleep(3)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

        # 求人の基本情報
        table = detail_soup.select_one("table.tableCondition")
        details = {
            "仕事内容": "", "対象となる方": "", "勤務地": "",
            "給与": "", "初年度年収": ""
        }
        if table:
            for row in table.select("tr"):
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td and th.text.strip() in details:
                    details[th.text.strip()] = td.get_text(strip=True)

        # 情報初期化
        company_name = ""
        address = ""
        phone = ""
        company_hp = ""

        # 「本社所在地」から住所を抽出
        hq_row = detail_soup.select_one("th.jobOfferTable__head:contains('本社所在地')")
        if hq_row:
            hq_td = hq_row.find_next_sibling("td")
            if hq_td:
                address = hq_td.get_text(strip=True).replace("地図を見る", "")

        # 問い合わせ情報も確認（会社名・電話番号・住所補完）
        contact_row = detail_soup.select_one("th.jobOfferTable__head:contains('問い合わせ')")
        if contact_row:
            contact_td = contact_row.find_next_sibling("td")
            if contact_td:
                divs = contact_td.select("div.text > div")
                for i, div in enumerate(divs):
                    text = div.get_text(strip=True)
                    if text == "住所" and i + 1 < len(divs):
                        zipcode = divs[i + 1].select_one("span.jobOfferTable__zipcode")
                        addr_text = divs[i + 1].get_text(strip=True)
                        alt_address = (zipcode.get_text(strip=True) + " " if zipcode else "") + addr_text
                        if not address:
                            address = alt_address
                    elif text == "電話番号" and i + 1 < len(divs):
                        phone = divs[i + 1].get_text(strip=True)
                    elif not company_name:
                        company_name = text

                link_tag = contact_td.select_one("a[href*='url-forwarder']")
                if link_tag and link_tag.has_attr("href"):
                    company_hp = "https:" + link_tag["href"]

        # 「企業ホームページ」セクションからも補完
        if not company_hp:
            corp_info_row = detail_soup.select_one("th.jobOfferTable__head:contains('企業ホームページ')")
            if corp_info_row:
                hp_link = corp_info_row.find_next_sibling("td").select_one("a")
                if hp_link and hp_link.has_attr("href"):
                    company_hp = hp_link.get_text(strip=True)

        # 重複郵便番号除去（例：〒104-0061〒104-0061…）
        address = re.sub(r"(〒\s*\d{3}-\d{4})\s*\1", r"\1", address)

        # 結果を1行ずつ書き込み（都度追記）
        with open(output_path, "a", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                count, title_text, subtitle_text,
                details["仕事内容"], details["対象となる方"], details["勤務地"],
                details["給与"], details["初年度年収"],
                company_name, address, phone, company_hp, detail_url
            ])
        count += 1

driver.quit()
print(f"[INFO] 全ページ（1〜7）の処理が完了しました（{count - 1}件）→ {output_path}")
