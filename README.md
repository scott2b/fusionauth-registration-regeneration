# fusionauth-registration-regeneration

Minimal implementation to demonstrate the re-generation of administratively deleted
user-application registrations.

## Installation

```
pip install -r requirements.txt
```


## Running

```
flask --app main --debug run
```

Visit `http://localhost:5000`


## About

This minimal implementation of a Flask application that uses FusionAuth for authentication
was original built to better understand the workflows associated with FusionAuth's
tendency to regenerate deleted user-application registrations. As such, there are aspects
of this example that would probably need to be built out more for use in production. In
particular, I recommend:

- Do not attach the user object directly to the session. The user's info could change in FusionAuth during the session lifecycle, resulting in an out-of-sync user experience.

## Revealing the "re-spawning" of user-application registrations

From what I can tell, this tendency is primarily a side-effect of the self-service registration
configuration. When self-service registration is activated, there is an underlying assumption
that users are broadly authorized to register themselves. Thus, when an authenticated
user makes generally any kind of application-specific request against the FusionAuth
platform, that will result in either (a) re-generating a deleted registration for
previously registered users, or (b) iniitiating the "complete registration" process for
new users. I believe this is by design with respect to the self-service registration enabled
configuration.

To see this behavior in the current application, use the following process:

1. Admin enables application for self-service registration
2. User self-registers via the application Register link 
3. Admin deletes the user's application registration
4. User visits the application's login URL initiating a login (if needed) and re-generated registration
5. Admin will see the registration again in the user's details

The registration re-spawning occurs regardless of whether the user was still logged in
before re-visiting the login link.

Again, I believe this is by design. The only real fix to this that I am aware of is to
turn off self-service registration. If self-service is deactivated, new users will not
have a path to self-registration (obviously, I suppose) but also, deleted registrations
will not be re-created.


## What if I want self-registration but want to be able to disable users for an application?

My current workaround for this is not ideal, but does work: Add a "disabled" role to the
application. Check for the role in your application during authentication and reject any
users who have that role. Now, be sure not to delete deactivated users, but rather give
them the "deactivated" role.

This is not ideal simply because it requires admins to have specific knowledge and
resulting behavior, namely: don't delete users. It would be better if there was some
mechanism for policy enforcement to prevent user-deletion. A de-facto "active" flag on
the registration (as opposed to a role) would probably also be a better solution.


## Thanks

Thanks to @mooreds for the feedback as I pushed through understanding these workflow issues.
