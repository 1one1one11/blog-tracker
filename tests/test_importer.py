from blog_tracker.importer import parse_followings_dump


def test_parse_followings_dump():
    sample = """
    주식
    이웃
    pokara61|포카라의 실전투자
    26.03.30. 25.12.17.

    부동산
    서로이웃
    리얼점프부동산lap|'인생'을 'Jump-Up'하는 부동산
    26.03.30. 25.06.13.
    """
    rows = parse_followings_dump(sample)
    assert [row["blog_id"] for row in rows] == ["pokara61", "리얼점프부동산lap"]
    assert rows[0]["group_name"] == "주식"
    assert rows[1]["relationship"] == "서로이웃"
