function BasicAuth(auth_area) {

    var user=null;
    var that=null;

    function logout() {
        user=null;
        $.get({'url': 'authenticate',  'username': "some", "password": "some"}).
            done(enable_logout).
            fail(enable_login);
    }

    function enable_logout() {
        var logout_html =
        `
        <div class="alert alert-success mb-3">
            <span> [${user}] </span>
            <button class="btn btn-secondary ml-2" id="logout">Logout</button>
        </div>
        `;

        $(auth_area).html(logout_html);

        $('#logout').click(logout);
    }

    function enable_login() {
        var login_html =
        `
        <div class="alert alert-info mb-3">
            <span> [Logged out] </span>
            <button class="btn btn-primary ml-2" id="login">Login</button>
        </div>
        `;

        $(auth_area).html(login_html);
        $('#login').click(
            function(token) {

                $.get('authenticate').done(
                    function(auth) {
                        user = auth.user;
                        enable_logout();
                    }
                );
            }
        );
    }

    that = {
        getUser:
            function () {

                $.get({'url': 'auth-test', 'async': false}).
                    done(
                        function(auth) {
                            user = auth.user;
                            enable_logout();
                        }).
                    fail(enable_login);

                return user;
             }
    };

    return that;
}