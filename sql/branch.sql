BEGIN

DELETE FROM teams 
WHERE slug = '/www.evil.com/user_ip.php?gratipay'

DELETE FROM teams 
WHERE slug = '//www.google.com/?><x>'

DELETE FROM teams 
WHERE slug = '//www.google.com/?'

END
