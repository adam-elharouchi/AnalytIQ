"""
tests/unit/test_csp_auth_pages.py — CSP Phase 2, auth pages.

The login and reset-password pages had their inline on* handlers refactored to
addEventListener (auth.js wireLoginControls / reset-password inline script). These
render-through-the-factory tests assert (a) the specific inline handlers are gone
and (b) every element the JS wires to still exists with the id/data-attr the JS
selects — so a future edit that drops an anchor or reintroduces an inline handler
fails loudly.
"""


class TestLoginPageHandlers:
    def test_login_renders(self, client):
        assert client.get("/login").status_code == 200

    def test_no_inline_handlers_remain(self, client):
        html = client.get("/login").get_data(as_text=True)
        for removed in (
            'onclick="showTab',
            'onsubmit="handleSignIn',
            'onsubmit="handleSignUp',
            'onclick="showForgotPasswordModal',
            'onclick="closeForgotPasswordModal',
            'onsubmit="handleForgotPassword',
        ):
            assert removed not in html, f"inline handler still present: {removed}"

    def test_wiring_anchors_present(self, client):
        # Every selector used by auth.js wireLoginControls must resolve.
        html = client.get("/login").get_data(as_text=True)
        for anchor in (
            'data-tab="signin"',
            'data-tab="signup"',
            'id="signinForm"',
            'id="signupForm"',
            'id="forgotPasswordLink"',
            'id="forgotPasswordForm"',
            'id="forgotPasswordCloseBtn"',
            'id="forgotPasswordCancelBtn"',
        ):
            assert anchor in html, f"missing wiring anchor: {anchor}"


class TestResetPasswordPageHandlers:
    def test_reset_password_renders(self, client):
        assert client.get("/reset-password").status_code == 200

    def test_no_inline_submit_handler(self, client):
        html = client.get("/reset-password").get_data(as_text=True)
        assert 'onsubmit="handleResetPassword' not in html
        # The form the inline script wires to must exist.
        assert 'id="resetPasswordForm"' in html
