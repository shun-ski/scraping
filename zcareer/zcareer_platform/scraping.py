# ======================================================================
# Project Name    : <scraping>
# File Name       : <scraping.py>
# Author          : <Shun Hoshina>      
# Creation Date   : <2025-05-23>
 
# Copyright © 2025 Shun Hoshina All rights reserved.
 
# This source code or any portion thereof must not be  
# reproduced or used in any manner whatsoever.
# ======================================================================
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from ips import EMAIL, PASSWORD  
from bs4 import BeautifulSoup
import time
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from selenium.common.exceptions import TimeoutException
from urllib.parse import urljoin

"""
スクレイピング先：https://agent-bank.com/service/job/list
"""

# 認証スコープとサービスアカウントの読み込み
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# スプレッドシートとワークシートを開く
spreadsheet_id = "xxxxxxxxx"  
worksheet = client.open_by_key(spreadsheet_id).worksheet("xxxxxxxx")  

# Chromeオプション設定（headlessモード）
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# ChromeDriver起動
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    # 初期化
    company_name = title = detail_url = job_type = employment_type = ""
    locations = []
    annual_income = job_description = required_qualifications = ""
    working_hours = holidays = salary_info = welfare = ""
    alert_elem = None

    # 1. ログインページへアクセス
    driver.get("https://agent-bank.com/service/job/list")

    # 2. ログイン情報入力
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
    driver.find_element(By.NAME, "email").send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)

    # 3. ログインボタンをクリック
    login_btn = driver.find_element(By.XPATH, '//button[contains(., "ログイン")]')
    login_btn.click()

    # 4. 「職種」の「選択」ボタンをクリック
    select_xpath = '//div[contains(text(), "職種")]/ancestor::div[contains(@class, "s-job__side-card-item")]//div[contains(text(), "選択")]'
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, select_xpath)))
    select_btn = driver.find_element(By.XPATH, select_xpath)
    driver.execute_script("arguments[0].click();", select_btn)
    print(" 『職種 > 選択』ボタンをクリックしました")

    # 「ITエンジニア関連」というカテゴリのボタンをクリック
    category_xpath = '//span[contains(text(), "ITエンジニア関連")]/ancestor::button'
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, category_xpath))
    )
    category_button = driver.find_element(By.XPATH, category_xpath)
    driver.execute_script("arguments[0].click();", category_button)
    print(" 『ITエンジニア関連』カテゴリボタンをクリックしました")

    # 「ITエンジニア関連すべて」のチェックボックスを探してチェックを入れる
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "ITエンジニア関連すべて")]'))
    )
    checkbox_xpath = '//span[contains(text(), "ITエンジニア関連すべて")]/ancestor::label'
    checkbox_label = driver.find_element(By.XPATH, checkbox_xpath)
    driver.execute_script("arguments[0].click();", checkbox_label)
    print("『ITエンジニア関連すべて』にチェックを入れました")

    # 「閉じる」ボタンをクリック
    close_button_xpath = '//span[text()="閉じる"]/ancestor::button'
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, close_button_xpath))
    )
    close_button = driver.find_element(By.XPATH, close_button_xpath)
    driver.execute_script("arguments[0].click();", close_button)
    print(" 『閉じる』ボタンをクリックしました")
    time.sleep(2)

    # 「絞り込む」ボタンをクリック
    filter_button_xpath = '//button[contains(text(), "絞り込む")]'
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, filter_button_xpath))
    )
    filter_button = driver.find_element(By.XPATH, filter_button_xpath)
    driver.execute_script("arguments[0].click();", filter_button)
    print("『絞り込む』ボタンをクリックしました")
    time.sleep(2)

    # #  114ページ目まで遷移
    # for i in range(1, 114):
    #     try:
    #         next_button = WebDriverWait(driver, 5).until(
    #             EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn-next:not(.disabled)'))
    #         )
    #         driver.execute_script("arguments[0].click();", next_button)
    #         print(f" {i + 1}ページ目へ遷移")
    #         time.sleep(2)
    #     except TimeoutException:
    #         print(f"{i + 1}ページ目への遷移に失敗しました。中断します。")
    #         driver.quit()
    #         exit(1)

    base_url = "https://agent-bank.com"

    while True:
        # 求人リンクをすべて取得
        first_job_link_xpath = '//a[contains(@href, "/service/job/") and contains(@class, "title")]'
        job_link_elems = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, first_job_link_xpath))
        )
        job_links = []
        for elem in job_link_elems:
            href = elem.get_attribute("href")
            if href and href.startswith("/"):
                href = urljoin(base_url, href)
            if href and href.startswith("http"):
                job_links.append(href)

        job_links = job_links[:15]  

        for detail_url in job_links:
           
            # href属性からURL取得
            # detail_url = first_job_link.get_attribute("href")
            print(" 詳細ページURL:", detail_url)
            driver.get(detail_url)

            # ページのHTMLを再度取得してパース
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # timeline-alert.warning 内のすべてのテキストを抽出
            alert_block = soup.select_one("div.timeline-alert.warning")
            alert_text = ""
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.timeline-alert.warning"))
                )
                # 描画完了後にHTMLを取得してパース
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")

                # 警告メッセージの抽出
                alert_block = soup.select_one("div.timeline-alert.warning")
                if alert_block:
                    alert_text = alert_block.get_text(separator="\n", strip=True)
                    print(" 集客利用不可メッセージを検出：", alert_text)
                else:
                    print(" timeline-alert.warning は検出されたが、内部要素が空です")

            except TimeoutException:
                print(" 集客制限メッセージは検出されませんでした")
                alert_text = ""

            # タイトルを取得
            title_xpath = '//div[contains(@class, "title") and contains(@class, "mb-4")]/p'

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, title_xpath))
            )
            title = driver.find_element(By.XPATH, title_xpath).text
            print(" 求人タイトル:", title)
       
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # 会社名の取得
            company_name_elem = soup.select_one('div.company > p.name')
            if company_name_elem:
                company_name = company_name_elem.text.strip()
                print(" 会社名:", company_name)
            else:
                print(" 会社名が見つかりませんでした")
           
            # 募集職種の<dd>要素を取得
            job_type_elem = soup.select_one('dt.head:contains("募集職種") + dd.content')
            if job_type_elem:
                job_type = job_type_elem.text.strip()
                print(" 募集職種:", job_type)
            else:
                print(" 募集職種が見つかりませんでした")

            # すべてのdlを走査して、dtが「雇用形態」のときにddを取得
            employment_type = None
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "雇用形態" in dt.text:
                    employment_type = dd.text.strip()
                    print(" 雇用形態:", employment_type)
                    break

            if not employment_type:
                print(" 雇用形態が見つかりませんでした")
           
            # 勤務地情報を格納するリスト
            locations = []

            # 「勤務地」セクションのdlを探す
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                if dt and "勤務地" in dt.text:
                    dd = dl.find('dd')
                    if dd:
                        for block in dd.select('div.title'):
                            # 勤務地タイトル（勤務地1、勤務地2など）
                            title = block.text.strip()
                            # 同じ階層にある address-container を取得
                            container = block.find_next_sibling("div", class_="address-container")
                            if container:
                                items = container.find_all("div", recursive=False)
                                parts = []
                                for item in items:
                                    text = item.get_text(separator="", strip=True)
                                    if text:
                                        parts.append(text)
                                address_info = "\n".join(parts)
                                locations.append(f"{title}\n{address_info}")
                    break  
                
            for loc in locations:
                print("勤務地情報:\n" + loc)
           
            annual_income = None
            # 「想定年収」の dl ブロックを探す
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "想定年収" in dt.text:
                    annual_income = dd.text.strip()
                    print("想定年収:", annual_income)
                    break
            if not annual_income:
                print(" 想定年収が見つかりませんでした")

            # 試用期間詳細を格納する変数
            trial_period_detail = None
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "試用期間詳細" in dt.text:
                    trial_period_detail = dd.text.strip()
                    break

            if trial_period_detail:
                print(" 試用期間詳細:", trial_period_detail)
            else:
                print(" 試用期間詳細が見つかりませんでした")

            job_description = None

            # 「仕事内容」を抽出
            soup = BeautifulSoup(driver.page_source, "html.parser")

            job_description = None
            for card in soup.select("div.s-card"):
                header = card.select_one("h1.s-card-header span")
                if header and "仕事内容" in header.text:
                    dd = card.select_one("dd.content")
                    if dd:
                        job_description = dd.get_text(separator="\n", strip=True)
                    break

            if job_description:
                print(" 仕事内容:\n" + job_description)
            else:
                print("仕事内容が見つかりませんでした")

            required_qualifications = None
            # 必須要件を取得
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "必須要件" in dt.text:
                    required_qualifications = dd.get_text(separator="\n", strip=True)
                    break

            if required_qualifications:
                print("必須要件:\n" + required_qualifications)
            else:
                print("必須要件が見つかりませんでした")

            working_hours = None
            # 「勤務時間」を探す
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "勤務時間" in dt.text:
                    working_hours = dd.get_text(separator="\n", strip=True)
                    break
            if working_hours:
                print("勤務時間:\n" + working_hours)
            else:
                print("勤務時間が見つかりませんでした")

            holidays = None
            # 年間休日
            for dl in soup.select('div.list dl'):
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd and "年間休日" in dt.text:
                    if holidays:
                        holidays += "\n年間休日：" + dd.text.strip()
                    else:
                        holidays = "年間休日：" + dd.text.strip()
                    break

            # 「休日・休暇」
            for dl in soup.select('div.list dl'):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if dt and dd and "休日・休暇" in dt.text:
                    if holidays:
                        holidays += "\n"  
                    holidays += dd.get_text(separator="\n", strip=True)
                    break
           
            salary_info = None
            # 「給与・待遇」を抽出
            for dl in soup.select("div.list dl"):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if dt and dd and "給与・待遇" in dt.text:
                    salary_info = dd.get_text(separator="\n", strip=True)
                    break

            if salary_info:
                print("給与・待遇:\n" + salary_info)
            else:
                print(" 給与・待遇が見つかりませんでした")

            welfare = None
            # 「福利厚生」を取得
            for dl in soup.select("div.list dl"):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if dt and dd and "福利厚生" in dt.text:
                    welfare = dd.get_text(separator="\n", strip=True)
                    break

            if welfare:
                print("福利厚生:\n" + welfare)
            else:
                print("福利厚生が見つかりませんでした")

            # 取得したデータを1行として記載（例）
            row = [
                detail_url,
                alert_text,
                company_name,
                # title,      
                job_type,
                employment_type,
                "\n".join(locations),
                annual_income,
                trial_period_detail,
                job_description,
                required_qualifications,
                working_hours,
                holidays,
                salary_info,
                welfare,
            ]
            worksheet.append_row(row, value_input_option="USER_ENTERED")
            print("スプレッドシートに書き込みました")

            # 検索結果ページに戻る
            driver.back()
            time.sleep(2)
   
        # 「次へ」ボタンのクリック
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn-next:not(.disabled)'))
            )
            driver.execute_script("arguments[0].click();", next_button)
            print("次のページへ遷移")
            time.sleep(2)  # ページ読み込み待機
        except TimeoutException:
            print("最後のページに到達しました")
            break

finally:
    driver.quit()

