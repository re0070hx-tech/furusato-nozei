"""
affiliate.py のユニットテスト
環境変数は monkeypatch で注入し、外部依存ゼロで実行できる。
"""
import pytest
import lib.affiliate as aff_mod


@pytest.fixture(autouse=True)
def clear_site_cache():
    """各テスト前後にモジュールキャッシュをリセット"""
    aff_mod._SITES.clear()
    yield
    aff_mod._SITES.clear()


# ─── generate_affiliate_link ────────────────────────────────────

class TestGenerateAffiliateLink:
    def test_rakuten_encodes_product_url(self, monkeypatch):
        monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "TESTID123")
        result = aff_mod.generate_affiliate_link(
            "rakuten", "https://item.rakuten.co.jp/shop/item/"
        )
        assert result is not None
        assert "TESTID123" in result
        # クエリパラメータ値として URL エンコードされていること
        assert "https%3A%2F%2F" in result

    def test_a8_encodes_product_url(self, monkeypatch):
        monkeypatch.setenv("A8_FURUNAVI_ID", "A8TESTID")
        result = aff_mod.generate_affiliate_link(
            "furunavi", "https://furunavi.jp/product/detail?pid=12345"
        )
        assert result is not None
        assert "A8TESTID" in result
        assert "https%3A%2F%2F" in result

    def test_amazon_does_not_encode_product_url(self, monkeypatch):
        monkeypatch.setenv("AMAZON_ASSOCIATES_TAG", "mytag-22")
        result = aff_mod.generate_affiliate_link(
            "amazon", "https://www.amazon.co.jp/dp/B0XXXXXXXX"
        )
        assert result is not None
        assert "mytag-22" in result
        # Amazon は URL エンコードしない
        assert "https://www.amazon.co.jp/dp/B0XXXXXXXX" in result
        assert "https%3A%2F%2F" not in result

    def test_valuecommerce_sid_pid_replaced(self, monkeypatch):
        monkeypatch.setenv("VC_SATOFULL_SID", "SID001")
        monkeypatch.setenv("VC_SATOFULL_PID", "PID999")
        result = aff_mod.generate_affiliate_link(
            "satofull", "https://www.satofull.jp/products/detail.php?product_id=42"
        )
        assert result is not None
        assert "SID001" in result
        assert "PID999" in result

    def test_missing_env_var_returns_none(self, monkeypatch):
        monkeypatch.delenv("RAKUTEN_AFFILIATE_ID", raising=False)
        result = aff_mod.generate_affiliate_link(
            "rakuten", "https://item.rakuten.co.jp/shop/item/"
        )
        assert result is None

    def test_unknown_site_returns_none(self):
        result = aff_mod.generate_affiliate_link("nonexistent_site", "https://example.com")
        assert result is None

    def test_direct_asp_does_not_encode(self, monkeypatch):
        monkeypatch.setenv("ANA_AFF_ID", "ANATEST")
        result = aff_mod.generate_affiliate_link(
            "ana", "https://furusato.ana.co.jp/products/detail/12345"
        )
        assert result is not None
        assert "https://furusato.ana.co.jp/products/detail/12345" in result
        assert "ANATEST" in result


# ─── get_active_sites ───────────────────────────────────────────

class TestGetActiveSites:
    def test_returns_only_active_sites(self):
        sites = aff_mod.get_active_sites()
        assert all(s["is_active"] for s in sites)

    def test_sorted_by_sort_order(self):
        sites = aff_mod.get_active_sites()
        orders = [s["sort_order"] for s in sites]
        assert orders == sorted(orders)

    def test_active_sites_include_amazon(self):
        sites = aff_mod.get_active_sites()
        ids = [s["id"] for s in sites]
        assert "amazon" in ids

    def test_rakuten_furunavi_satofull_active(self):
        ids = [s["id"] for s in aff_mod.get_active_sites()]
        for expected in ("rakuten", "furunavi", "satofull", "amazon"):
            assert expected in ids


# ─── get_site_config ────────────────────────────────────────────

class TestGetSiteConfig:
    def test_returns_config_dict(self):
        cfg = aff_mod.get_site_config("rakuten")
        assert cfg is not None
        assert cfg["id"] == "rakuten"
        assert "affiliate_template" in cfg

    def test_unknown_site_returns_none(self):
        assert aff_mod.get_site_config("does_not_exist") is None
