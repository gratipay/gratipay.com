Gratipay.signUp = {};

Gratipay.signUp.wireUp = function() {
	$('.signup-form').submit(function(e) {
		e.preventDefault();
		jQuery.ajax({
            url: '/auth/signup.json',
            type: 'POST',
            data: {
                'email': $(this).find('input[name="email"]').val(),
                'username': $(this).find('input[name="username"]').val(),
                'nonce': $(this).find('input[name="nonce"]').val(),
            },
            success: function(data) {
                Gratipay.notification(data.message, 'success');

                // Let's reload the verification page, so that the
                // user is signed in
                setTimeout(function() { window.location.reload() }, 1000);
            },
            error: Gratipay.error
        });
	})
}
