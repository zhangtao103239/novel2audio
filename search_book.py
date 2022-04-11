import requests
from lxml import etree


def search_book(book_host_url, bookname):
    url = book_host_url + '/search/'
    body = {
        "searchkey": bookname,
        "searchtype": "all"
    }
    response = requests.post(url, data=body)
    if response.ok:
        res_html = response.text
        html = etree.HTML(res_html)
        results = html.xpath('//li[@class="searchresult"]')
        book_url = ''
        for result in results:
            searched_book_name = result.xpath('string(.//h3)')
            if searched_book_name == bookname:
                book_url = result.xpath('./div[1]/a[1]/@href')[0]
                break
        if book_url == '':
            print('未找到完全同名的书籍，请确认')
            return None
        print('已找到对应书籍，正在获取目录')
        return book_url


def get_chapters(book_host_url, book_url):
    r = requests.get(book_host_url + book_url)
    if r.ok:
        html = etree.HTML(r.text)
        chapters = html.xpath('//ul[@id="ul_all_chapters"]/li')
        for chapter in chapters:
            chapter_name = chapter.xpath('./a[1]/@title')[0]
            chapter_url = chapter.xpath('./a[1]/@href')[0]
            chapter_resp = requests.get(book_host_url + chapter_url)
            html = etree.HTML(chapter_resp.text)
            chapter_content = '\n'.join(html.xpath('//*[@id="article"]//text()'))
            yield chapter_name, chapter_content
