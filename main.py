import os
import urllib
from flask import Flask, redirect, request, render_template, session, url_for
from fusionauth.fusionauth_client import FusionAuthClient
import pkce


app = Flask(__name__)
app.secret_key = os.urandom(24)

API_KEY = os.environ["FUSIONAUTH_API_KEY"]
CLIENT_ID = os.environ["FUSIONAUTH_CLIENT_ID"]
CLIENT_SECRET = os.environ["FUSIONAUTH_CLIENT_SECRET"]
FUSIONAUTH_HOST_IP = os.environ.get("FUSIONAUTH_HOST_IP", "localhost")
FUSIONAUTH_HOST_PORT = os.environ.get("FUSIONAUTH_HOST_PORT", "9011")


client = FusionAuthClient(API_KEY, f"http://{FUSIONAUTH_HOST_IP}:{FUSIONAUTH_HOST_PORT}")

### User object

UNAUTHENTICATED_USER = { "is_authenticated": False }

def User(**kwargs):
    kwargs.update({ "is_authenticated": True })
    return kwargs
    

### Helpers

"""
Any callback / redirect URLs must be specified in the "Authorized Redirect URLs" for the
application OAuth config in FusionAuth.

Be aware of trailing slash issues when configuring these URLs. E.g. Flask's url_for
will include a trailing slash here on `url_for("index")`
"""

#def fusionauth_register_url(code_challenge, scope="offline_access"):
def fusionauth_register_url(code_challenge):
    """offline_access scope is specified in order to recieve a refresh token."""
    callback = urllib.parse.quote_plus(url_for("oauth_callback", _external=True))
    #return f"http://{FUSIONAUTH_HOST_IP}:{FUSIONAUTH_HOST_PORT}/oauth2/register?client_id={CLIENT_ID}&response_type=code&code_challenge={code_challenge}&code_challenge_method=S256&scope={scope}&redirect_uri={callback}"
    return f"http://{FUSIONAUTH_HOST_IP}:{FUSIONAUTH_HOST_PORT}/oauth2/register?client_id={CLIENT_ID}&response_type=code&code_challenge={code_challenge}&code_challenge_method=S256&redirect_uri={callback}"


#def fusionauth_login_url(code_challenge, scope="offline_access"):
def fusionauth_login_url(code_challenge):
    """offline_access scope is specified in order to recieve a refresh token."""
    callback = urllib.parse.quote_plus(url_for("oauth_callback", _external=True))
    return f"http://{FUSIONAUTH_HOST_IP}:{FUSIONAUTH_HOST_PORT}/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&code_challenge={code_challenge}&code_challenge_method=S256&redirect_uri={callback}"


def fusionauth_logout_url():
    """
    Alternatively to specifying the `post_logout_redirect_uri`, set the Logout URL in
    the application configuration OAuth tab.
    """
    redir = urllib.parse.quote_plus(url_for("index", _external=True))
    return f"http://{FUSIONAUTH_HOST_IP}:{FUSIONAUTH_HOST_PORT}/oauth2/logout?client_id={CLIENT_ID}&post_logout_redirect_uri={redir}"


def user_is_registered(registrations, app_id=CLIENT_ID):
    return all([
        registrations is not None,
        len(registrations) > 0,
        any(r["applicationId"] == app_id for r in registrations)])
        #any(r["applicationId"] == app_id and not "deactivated" in r["roles"] for r in registrations)])


### Handlers

@app.before_request
def load_user():
    """It is not recommended to directly set the user in the session due to the fact that
    user info may be modified in FusionAuth, including administrative deactivation or
    deletion during the session lifecycle. 

    The current approach of setting the user in the session is intended to demonstrate
    minimal utilzation and to isolate the registration re-spawning behavior that
    occurs due to the lingering FusionAuth session (not the application session).
    """
    request.user = session.get("user")


### Routes

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/oauth-callback")
def oauth_callback():
    session["user"] = UNAUTHENTICATED_USER
    if not request.args.get("code"):
        return render_template(
            "error.html",
            msg="Failed to get auth token.",
            reason=request.args["error_reason"],
            description=request.args["error_description"]
        )
    uri = url_for("oauth_callback", _external=True),
    tok_resp = client.exchange_o_auth_code_for_access_token_using_pkce(
        request.args.get("code"),
        uri,
        session['code_verifier'],
        CLIENT_ID,
        CLIENT_SECRET,
    )
    if not tok_resp.was_successful():
        return render_template(
            "error.html",
            msg="Failed to get auth token.",
            reason=tok_resp.error_response["error_reason"],
            description=tok_resp.error_response["error_description"],
        )
    access_token = tok_resp.success_response["access_token"]
    user_resp = client.retrieve_user_using_jwt(access_token)
    if not user_resp.was_successful():
        return render_template(
            "error.html",
            msg="Failed to get user info.",
            reason=tok_resp.error_response["error_reason"],
            description=tok_resp.error_response["error_description"],
        )
    registrations = user_resp.success_response["user"]["registrations"]
    if not user_is_registered(registrations):
        return render_template(
            "error.html",
            msg="User not registered for this application.",
            reason="Application id not found in user object.",
            description="Did you create a registration for this user and this application?"
        )
    session["user"] = User(**user_resp.success_response["user"])
    return redirect("/")


@app.route("/register")
def register():
    """To use registration, enable self-service registration in the Registration tab of
    the application configuration in FusionAuth. You may also want to enable specific
    registration properties such as First Name and Last Name to be passed into the
    User constructor.
    """
    code_verifier, code_challenge = pkce.generate_pkce_pair()
    session['code_verifier'] = code_verifier
    return redirect(fusionauth_register_url(code_challenge))


@app.route("/login")
def login():
    code_verifier, code_challenge = pkce.generate_pkce_pair()
    session['code_verifier'] = code_verifier
    return redirect(fusionauth_login_url(code_challenge))


@app.route("/logout")
def logout():
    if "user" in session:
        del session["user"]
    return redirect(fusionauth_logout_url())
