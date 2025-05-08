from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import json

# ▼ Chrome起動設定（ヘッドレス）
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# ▼ 一覧ページを開く
list_url = "https://zcareer.com/job?jobCategory=3&jobCategory=7&jobCategory=6&jobCategory=11&jobCategory=2"
driver.get(list_url)
time.sleep(5)

# ▼ 最初の「この求人を見る」をクリック
try:
    detail_link = driver.find_element(By.XPATH, "//a[contains(@href, '/job/detail')]")
    detail_url = detail_link.get_attribute("href")
    driver.get(detail_url)
    time.sleep(5)
except Exception as e:
    print("詳細ページのリンク取得失敗:", e)
    driver.quit()
    exit()

# ▼ 詳細ページのHTMLを取得
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# ▼ 抽出先辞書
job_info = {"遷移先のURL": detail_url}

# ▼ 会社名（JSON-LD構造）
org_script = soup.find("script", type="application/ld+json")
if org_script:
    try:
        data = json.loads(org_script.string)
        job_info["会社名"] = data.get("hiringOrganization", {}).get("name", "")
    except:
        job_info["会社名"] = ""

# ▼ 共通関数群
def extract_labeled_value(label_text):
    for div in soup.find_all("div", class_="flex items-start justify-center"):
        label = div.find("p", string=label_text)
        if label:
            return div.find_all("div")[-1].get_text(strip=True)
    return ""

def extract_section_by_title(title):
    for h2 in soup.find_all("h2", string=title):
        wrapper = h2.find_parent("div", class_="bg-surface-primary")
        if wrapper:
            content = wrapper.find("div", class_="relative")
            return content.get_text(strip=True) if content else ""
    return ""

# ✅ 最新版：勤務地抽出（都道府県＋説明＋注釈）
def extract_location():
    section = soup.find("div", id="work-place-section")
    if not section:
        return ""

    result_lines = []

    # ▼ 各都道府県と説明文の組み合わせ
    for area_block in section.select(".space-y-4 > div"):
        area = area_block.find("p", class_="mb-2")
        detail = area_block.find_all("p")[-1]  # 最後の <p> を説明とする
        if area:
            result_lines.append(area.get_text(strip=True))
        if detail and detail != area:
            result_lines.append(detail.get_text(strip=True))
        result_lines.append("")  # 改行

    # ▼ 備考・注釈
    note = section.find("div", class_="mt-4")
    if note:
        note_p = note.find("p")
        if note_p:
            result_lines.append(note_p.get_text(strip=True))

    return "\n".join(result_lines).strip()

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
    return ""

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
    return "\n".join(results)

def extract_holidays():
    results = []
    for div in soup.find_all("div", class_="flex items-start justify-center"):
        label = div.find("p", string="年間休日")
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
    return "\n".join(results)

def extract_salary_details():
    for h2 in soup.find_all("h2", string="給与"):
        wrapper = h2.find_parent("div", class_="bg-surface-primary")
        if wrapper:
            content = wrapper.find("div", class_="relative")
            return content.get_text(strip=True) if content else ""
    return ""

# ▼ 各項目を抽出
h1 = soup.find("h1")
job_info["キャッチコピー"] = h1.get_text(strip=True) if h1 else ""

job_info["職種名"] = extract_labeled_value("職種")
job_info["雇用形態"] = extract_section_by_title("雇用形態")
job_info["勤務地"] = extract_location()
job_info["給与"] = extract_labeled_value("想定給与")
job_info["試用期間"] = extract_section_by_title("試用期間")
job_info["募集要項（仕事内容）"] = extract_section_by_title("仕事内容")
job_info["アピールポイント"] = extract_section_by_title("仕事の醍醐味")
job_info["求める人材"] = extract_requirements()
job_info["勤務時間"] = extract_work_time()
job_info["休暇・休日"] = extract_holidays()
job_info["給与の補足"] = extract_salary_details()
job_info["待遇・福利厚生"] = extract_section_by_title("福利厚生")

# ▼ 結果出力
print("\n【Zキャリア 求人情報】")
for k, v in job_info.items():
    print(f"{k}:\n{v if v else '（情報なし）'}\n")

driver.quit()
