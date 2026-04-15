import tempfile
import unittest
from http.cookiejar import Cookie
from http.cookiejar import CookieJar
from pathlib import Path

from app.sources.pku_reagent.auth import CachedPkuReagentAuthenticator
from app.sources.pku_reagent.auth import StaticPkuReagentAuthenticator
from app.sources.pku_reagent.auth import _build_cookie_header
from app.sources.pku_reagent.auth import _extract_route_query_params


def _make_cookie(*, name: str, value: str, domain: str) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


class PkuReagentAuthTestCase(unittest.TestCase):
    def test_cached_authenticator_reuses_saved_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "pku_reagent_session.json"
            authenticator = CachedPkuReagentAuthenticator(
                delegate=StaticPkuReagentAuthenticator(
                    username="CG17288",
                    token="session-token",
                    cookie_header="JWTUser=abc",
                ),
                store_path=cache_path,
            )

            first = authenticator.authenticate()
            second = authenticator.authenticate()

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertEqual(first.username, "CG17288")
            self.assertEqual(second.token, "session-token")
            self.assertTrue(cache_path.exists())

    def test_build_cookie_header_filters_domain(self) -> None:
        cookie_jar = CookieJar()
        cookie_jar.set_cookie(_make_cookie(name="JWTUser", value="abc", domain="reagent.pku.edu.cn"))
        cookie_jar.set_cookie(_make_cookie(name="8DbqJ99x4ZtLO", value="xyz", domain=".reagent.pku.edu.cn"))
        cookie_jar.set_cookie(_make_cookie(name="IAAA", value="ignore", domain="iaaa.pku.edu.cn"))

        header = _build_cookie_header(cookie_jar, "https://reagent.pku.edu.cn")

        self.assertIn("JWTUser=abc", header)
        self.assertIn("8DbqJ99x4ZtLO=xyz", header)
        self.assertNotIn("IAAA=ignore", header)

    def test_extract_route_query_params_reads_hash_query(self) -> None:
        params = _extract_route_query_params(
            "https://reagent.pku.edu.cn/index.html#/oauth?json=%7B%22name%22%3A%22yanghan%22%7D"
        )

        self.assertEqual(params["json"], '{"name":"yanghan"}')


if __name__ == "__main__":
    unittest.main()
