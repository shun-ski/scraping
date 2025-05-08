import time
import json
import gspread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from google.oauth2.service_account import Credentials
import re

# --- Google Sheets 認証設定 ---
SERVICE_ACCOUNT_FILE = "gas.json"
SPREADSHEET_NAME = "みらいずスクレイピング"
SHEET_TITLE = "Zキャリアスクレイピング"

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open(SPREADSHEET_NAME)

try:
    worksheet = sh.worksheet(SHEET_TITLE)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_TITLE, rows="100", cols="20")

# --- Selenium Chromeドライバ ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# --- ラベル名で値を抽出 ---
def extract_labeled_value(label_text, soup):
    for div in soup.find_all("div", class_="flex items-start justify-center"):
        label = div.find(["p", "span"], string=label_text)
        if label:
            parent = label.find_parent("div", class_="flex items-start justify-center")
            if parent:
                next_sibling = parent.find_next_sibling("div")
                if next_sibling:
                    return next_sibling.get_text(strip=True)
                strong_text = parent.find("div", class_="text-text-primary")
                if strong_text:
                    return strong_text.get_text(strip=True)
            divs = div.find_all("div")
            for d in divs[::-1]:
                if d.get_text(strip=True):
                    return d.get_text(strip=True)
    return "記載なし"

# --- 求人詳細ページの情報抽出関数 ---
def extract_job_detail(url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    job_info = {"遷移先のURL": url}

    org_script = soup.find("script", type="application/ld+json")
    if org_script:
        try:
            data = json.loads(org_script.string)
            job_info["会社名"] = data.get("hiringOrganization", {}).get("name", "")
        except:
            job_info["会社名"] = ""
    else:
        job_info["会社名"] = ""

    def extract_section_by_title(title):
    # 通常の構造
        for h2 in soup.find_all("h2"):
            if h2.get_text(strip=True) == title:
                wrapper = h2.find_parent("div", class_="bg-surface-primary")
                if wrapper:
                    content = wrapper.find("div", class_="relative")
                    if content:
                        return content.get_text(separator="\n", strip=True)
        # fallback: タイトルが微妙に違うケースに対応（例：「仕事の内容」→「仕事内容」）
        if title == "仕事内容":
            for h2 in soup.find_all("h2"):
                if "仕事の内容" in h2.get_text(strip=True):
                    wrapper = h2.find_parent("div", class_="bg-surface-primary")
                    if wrapper:
                        content = wrapper.find("div", class_="relative")
                        if content:
                            return content.get_text(separator="\n", strip=True)
        return "記載なし"


    def extract_location():
        section = soup.find("div", id="work-place-section")
        if not section:
            return extract_labeled_value("勤務地", soup)

        result_lines = []

        # 通常のパターン
        area_blocks = section.select(".space-y-4 > div")
        if area_blocks:
            for area_block in area_blocks:
                area = area_block.find("p", class_="mb-2")
                detail = area_block.find_all("p")[-1]
                if area:
                    result_lines.append(area.get_text(strip=True))
                if detail and detail != area:
                    result_lines.append(detail.get_text(strip=True))
        else:
            # 新パターン（pやdivを直に見る）
            location_container = section.find("div", class_="text-[13px] leading-[175%] whitespace-pre-wrap")
            if location_container:
                for elem in location_container.find_all(["p", "div"], recursive=False):
                    text = elem.get_text(strip=True)
                    if text and "入力した勤務地情報" not in text:
                        result_lines.append(text)

        return "\n".join(result_lines).strip() or "記載なし"



    def extract_requirements():
        for h2 in soup.find_all("h2", string="対象となる方"):
            wrapper = h2.find_parent("div", class_="bg-surface-primary")
            if wrapper:
                content_div = wrapper.find("div", class_="relative")
                if content_div:
                    sections = content_div.find_all("div", recursive=False)
                    texts = []
                    for sec in sections:
                        title = sec.find("p", class_="font-bold")
                        body = sec.find_all("p")[1:] if title else sec.find_all("p")
                        text_block = (title.get_text(strip=True) + "\n" if title else "")
                        text_block += "\n".join(p.get_text(strip=True) for p in body)
                        texts.append(text_block)
                    return "\n\n".join(texts)
        return "記載なし"

    def extract_work_time():
        results = []
        for h2 in soup.find_all("h2", string="勤務時間"):
            wrapper = h2.find_parent("div", class_="bg-surface-primary")
            if wrapper:
                content = wrapper.find("div", class_="relative")
                if content:
                    results.append(content.get_text(strip=True))
        for div in soup.find_all("div", class_="text-text-primary"):
            p = div.find("p")
            if p and "勤務時間帯" in p.text:
                results.append(p.get_text(strip=True))
        return "\n".join(results) if results else extract_labeled_value("勤務時間", soup)

    def extract_holidays():
        results = []
        for div in soup.find_all("div", class_="flex items-start justify-center"):
            label = div.find(["p", "span"], string="年間休日")
            if label:
                value_div = div.find_all("div")[-1]
                if value_div:
                    results.append(value_div.get_text(strip=True))
        for h2 in soup.find_all("h2", string="休日・休暇"):
            wrapper = h2.find_parent("div", class_="bg-surface-primary")
            if wrapper:
                content = wrapper.find("div", class_="relative")
                if content:
                    results.append(content.get_text(strip=True))
        return "\n".join(results) if results else extract_labeled_value("休暇・休日", soup)

    def extract_salary(soup):
        keywords = ["想定給与", "月給", "年収", "時給", "給料", "給与"]
        text_blocks = []

        for container in soup.find_all("div"):
            if container.get_text(strip=True) and any(k in container.get_text() for k in keywords):
                for tag in container.find_all(["p", "span"], recursive=True):
                    text = tag.get_text(strip=True)
                    if any(re.search(rf"{kw}", text) for kw in keywords) and re.search(r"\d", text):
                        text_blocks.append(text)

        for t in text_blocks:
            if re.search(r"[万千円]", t) and re.search(r"\d", t):
                return t

        return "記載なし"





    h1 = soup.find("h1")
    job_info["キャッチコピー"] = h1.get_text(strip=True) if h1 else ""
    job_info["職種名"] = extract_labeled_value("職種", soup)
    job_info["雇用形態"] = extract_section_by_title("雇用形態")
    job_info["勤務地"] = extract_location()
    job_info["給与"] = extract_salary(soup)
    job_info["試用期間"] = extract_section_by_title("試用期間")
    job_info["募集要項（仕事内容）"] = extract_section_by_title("仕事内容")
    job_info["アピールポイント"] = extract_section_by_title("仕事の醍醐味")
    job_info["求める人材"] = extract_requirements()
    job_info["勤務時間"] = extract_work_time()
    job_info["休暇・休日"] = extract_holidays()
    job_info["給与の補足"] = extract_section_by_title("給与")
    job_info["待遇・福利厚生"] = extract_section_by_title("福利厚生")

    return job_info

# --- ページネーション ---
def scrape_pages_from(start_page=5, start_row=151):
    base_url = "https://zcareer.com"
    base_search = "/job?jobCategory=3&jobCategory=7&jobCategory=6&jobCategory=11&jobCategory=2"

    current_page = start_page
    current_row = start_row

    while True:
        print(f"[INFO] ページ {current_page} を処理中...")

        page_url = f"{base_url}{base_search}&page={current_page}"
        driver.get(page_url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        job_links = soup.select("a[href^='/job/detail']")
        job_urls = list({base_url + link["href"] for link in job_links})

        if not job_urls:
            print("[INFO] 求人情報が見つかりません。終了します。")
            break

        for url in job_urls:
            try:
                job_info = extract_job_detail(url)
                if current_row == start_row:
                    worksheet.update(f"A{start_row}", [list(job_info.keys())])
                    current_row += 1
                worksheet.update(f"A{current_row}", [list(job_info.values())])
                print(f"[OK] {url} を行 {current_row} に書き込み完了")
                current_row += 1
            except Exception as e:
                print(f"[ERROR] {url} の処理で失敗: {e}")
                continue

        next_button = soup.find("a", attrs={"aria-label": "次のページへ移動"})
        if next_button and "href" in next_button.attrs:
            current_page += 1
        else:
            print("[INFO] 最後のページに到達しました。")
            break

    driver.quit()
    print("[DONE] 完了")

if __name__ == "__main__":
    scrape_pages_from(start_page=33, start_row=992)
