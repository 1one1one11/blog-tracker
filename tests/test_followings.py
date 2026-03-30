from blog_tracker.followings import _extract_blog_id


def test_extract_blog_id_from_direct_url():
    assert _extract_blog_id("https://blog.naver.com/pokara61") == "pokara61"


def test_extract_blog_id_from_post_list_url():
    assert (
        _extract_blog_id("https://blog.naver.com/PostList.naver?blogId=pokara61&from=postList")
        == "pokara61"
    )
