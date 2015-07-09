BEGIN;
    UPDATE participants
       SET notifications = array_remove(notifications, 'ba_withdrawal_failed')
     WHERE 'ba_withdrawal_failed' = ANY(notifications);
END;
