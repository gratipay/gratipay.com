BEGIN;

    INSERT INTO tips (tipper, tippee, amount, ctime)
        SELECT tipper, tippee, 0
             , ( SELECT ctime
                   FROM tips
                  WHERE tipper=tipper
                    AND tippee=tippee
                  LIMIT 1
               )
          FROM current_tips
         WHERE (tipper LIKE 'deactivated-%' OR tippee LIKE 'deactivated-%')
           AND amount > 0;

    UPDATE participants
       SET username = substring(username from 13)
         , username_lower = lower(substring(username from 13))
         , is_closed = true
         , statement = ''
         , goal = NULL
         , anonymous_giving = False
         , anonymous_receiving = False
         , number = 'singular'
         , avatar_url = NULL
         , email = NULL
         , giving = 0
         , pledging = 0
         , receiving = 0
     WHERE username LIKE 'deactivated-%';

END;
