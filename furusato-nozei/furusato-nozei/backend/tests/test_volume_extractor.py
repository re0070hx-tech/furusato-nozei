"""volume_extractor のユニットテスト"""
import pytest
from lib.volume_extractor import extract_volume_g


@pytest.mark.parametrize("text, expected", [
    # kg 系
    ("ふるさと牛タン 1.5kg ねぎ塩", 1500.0),
    ("コシヒカリ 5kg", 5000.0),
    ("牛肉 2,5kg 切り落とし", 2500.0),
    # g 系
    ("容量：国産牛肩ロース 約900g", 900.0),
    ("ホタテ 400g（訳あり）", 400.0),
    ("訳あり 1,000g 小分け", 1000.0),
    # 乗算
    ("ホタテ 500g×3パック", 1500.0),
    ("牛肉 250g×6", 1500.0),
    ("小分け 200g x2", 400.0),
    # 抽出不能
    (None, None),
    ("ふるさと納税 体験チケット", None),
    ("", None),
    # 大文字単位
    ("サーモン 800G", 800.0),
    ("米 4KG", 4000.0),
])
def test_extract_volume_g(text, expected):
    result = extract_volume_g(text)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)
