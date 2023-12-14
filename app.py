import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse
import re

def get_soup_from_url(session, url):
    response = session.get(url)
    return BeautifulSoup(response.text, 'html.parser')

def remove_query_string(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

def safe_file_name(url):
    """URL에서 안전한 파일 이름을 생성합니다."""
    unquoted_url = unquote(url)
    base_name, ext = os.path.splitext(os.path.basename(unquoted_url))

    # 비-ASCII 및 파일 이름으로 사용 불가능한 문자 제거
    safe_base_name = re.sub(r'[<>:"/\\|?*\x00-\x1F\x7F-\xFF]', '', base_name)

    # 쿼리 파라미터의 시작을 나타내는 문자를 안전한 문자로 대체
    safe_ext = ext.replace('?', '_').replace('&', '_')

    # 확장자에서 '_' 이후의 문자열 제거
    safe_ext = safe_ext.split('_')[0]

    return safe_base_name + safe_ext  # 원래의 확장자를 유지하면서 안전한 파일 이름 반환

def check_url_exist(session, url):
    """주어진 URL이 존재하는지 404 상태 코드를 기준으로 확인합니다."""
    try:
        response = session.head(url, timeout=5)
        return response.status_code != 404
    except requests.RequestException:
        return False

def save_images_from_blog(url, save_path):
    print(f"Processing URL: {url}")
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        try:
            soup = get_soup_from_url(session, url)

            # iframe 태그 처리
            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                soup = get_soup_from_url(session, urljoin(url, iframe['src']))
                print("iframe 태그 처리 완료")

            # HTML 전체에서 img 태그 찾기
            images = soup.find_all('img')

            if not images:
                print("이미지를 찾지 못하였습니다.")
                return

            for img in images:
                if img.has_attr('src') and 'postfiles.pstatic.net' in img['src']:
                    img_url = urljoin(url, img['src'])
                    img_url = unquote(img_url)  # URL 디코드
                    print(f"이미지 URL: {img_url}")

                    # 쿼리 파라미터 중 type=w80_blur를 type=w966로 대체
                    img_url = img_url.replace('type=w80_blur', 'type=w966')
                    print(f"쿼리 파라미터 대체 후 이미지 URL: {img_url}")

                    # 먼저 type=w966로 시도
                    img_name = os.path.join(save_path, safe_file_name(os.path.basename(img_url)))
                    if not check_url_exist(session, img_url):
                        # 다음으로 type=w2로 시도
                        img_url = img_url.replace('type=w966', 'type=w2')
                        print(f"type=w2로 대체 후 이미지 URL: {img_url}")
                        img_name = os.path.join(save_path, safe_file_name(os.path.basename(img_url)))
                        if not check_url_exist(session, img_url):
                            # 쿼리 파라미터 제거 후 시도
                            img_url = img_url.split('?')[0]
                            print(f"쿼리 파라미터 제거 후 이미지 URL: {img_url}")
                            img_name = os.path.join(save_path, safe_file_name(os.path.basename(img_url)))
                            if not check_url_exist(session, img_url):
                                print(f"이미지를 다운로드 할 수 없습니다. ({img_url})")
                                continue

                    try:
                        img_data = session.get(img_url).content
                        with open(img_name, 'wb') as file:
                            file.write(img_data)
                        print(f"이미지 저장됨 ({img_name})")
                    except Exception as e:
                        print(f"다운로드 오류 ({img_url}: {e})")
        except Exception as e:
            print(f"접근실패 {url}: {e}")

def process_blog_urls(file_path, save_directory):
    if not os.path.isfile(file_path):
        print(f"{file_path} 파일을 찾지 못하였습니다. 파일을 확인해주세요.")
        return

    with open(file_path, 'r') as file:
        urls = file.readlines()

    if not urls:
        print("블로그 URL을 찾지 못하였습니다. URL을 확인해 주세요.")
        return

    for url in urls:
        url = url.strip()
        if url:
            # URL에 http:// 또는 https://가 포함되어 있지 않은 경우 https:// 추가
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            save_images_from_blog(url, save_directory)
        else:
            print("URL이 비어있습니다.")

# 사용 예시
blog_urls_file = 'blog-urls.txt'  # 네이버 블로그 URL이 저장된 텍스트 파일
save_directory = 'result-file'  # 현재 디렉토리에 저장될 하위 폴더 이름
process_blog_urls(blog_urls_file, save_directory)
