from blog_tracker.rss import clean_html_text


def test_clean_html_text():
    assert clean_html_text("<p>삼성전자 <b>실적</b> 개선</p>") == "삼성전자 실적 개선"
