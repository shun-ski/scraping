from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import csv

# ChromeDriverのパス
chrome_path = "/usr/bin/chromedriver"
service = Service(executable_path=chrome_path)

# オプション
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# ドライバー起動
driver = webdriver.Chrome(service=service, options=options)

# 出力ファイル
output_path = "job_details_with_contact_and_hp.csv"
count = 1

# URL構成
base_url = "https://tenshoku.mynavi.jp/list/o132/"
query = "?jobsearchType=14&searchType=18&refLoc=fnc_sra"

with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "No", "求人タイトル", "サブタイトル", "仕事内容", "対象となる方", "勤務地", "給与", "初年度年収",
        "会社名", "住所", "電話番号", "企業HP", "詳細ページURL"
    ])

    for page in range(1, 8):
        list_url = f"{base_url}pg{page}/{query}" if page != 1 else base_url + query
        print(f"[INFO] 一覧ページアクセス中: {list_url}")
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

            print(f"[INFO] 詳細ページアクセス中: {detail_url}")
            driver.get(detail_url)
            time.sleep(3)

            detail_soup = BeautifulSoup(driver.page_source, "html.parser")

            # 求人情報
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

            # 問い合わせ情報
            company_name = ""
            address = ""
            phone = ""
            company_hp = ""

            contact_row = detail_soup.select_one("th.jobOfferTable__head:contains('問い合わせ')")
            if contact_row:
                contact_td = contact_row.find_next_sibling("td")
                if contact_td:
                    contact_divs = contact_td.select("div.text > div")
                    for i, div in enumerate(contact_divs):
                        text = div.get_text(strip=True)
                        if text == "住所" and i + 1 < len(contact_divs):
                            zipcode = contact_divs[i + 1].select_one("span.jobOfferTable__zipcode")
                            addr_text = contact_divs[i + 1].get_text(strip=True)
                            address = (zipcode.get_text(strip=True) + " " if zipcode else "") + addr_text
                        elif text == "電話番号" and i + 1 < len(contact_divs):
                            phone = contact_divs[i + 1].get_text(strip=True)
                        elif not company_name:
                            company_name = text
                    # 企業HPリンクがこのブロック内にある場合
                    link_tag = contact_td.select_one("a[href*='url-forwarder']")
                    if link_tag and link_tag.has_attr("href"):
                        company_hp = "https:" + link_tag["href"]

            # 会社情報ブロックからもHP確認
            if not company_hp:
                corp_info_row = detail_soup.select_one("th.jobOfferTable__head:contains('企業ホームページ')")
                if corp_info_row:
                    hp_link = corp_info_row.find_next_sibling("td").select_one("a")
                    if hp_link and hp_link.has_attr("href"):
                        company_hp = hp_link.get_text(strip=True)

            writer.writerow([
                count, title_text, subtitle_text,
                details["仕事内容"], details["対象となる方"], details["勤務地"],
                details["給与"], details["初年度年収"],
                company_name, address, phone, company_hp, detail_url
            ])
            count += 1

driver.quit()
print(f"[INFO] 保存完了：{count - 1}件 → {output_path}")
