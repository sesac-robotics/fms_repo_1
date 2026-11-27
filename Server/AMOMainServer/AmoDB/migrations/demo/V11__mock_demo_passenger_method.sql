-- The built-in fictional passenger can exercise the mock payment.
UPDATE users
SET mock_payment_method_ref = 'demo-approved'
WHERE id = 1 AND contact = 'passenger@amo.test' AND mock_payment_method_ref IS NULL;
