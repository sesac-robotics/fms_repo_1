-- Allow one separately approved, Google-only operating account for a passenger identity.
ALTER TABLE amo_accounts
    ADD COLUMN google_passenger_id bigint UNIQUE REFERENCES amo_accounts(id),
    ADD CONSTRAINT ck_amo_google_operator
        CHECK (google_passenger_id IS NULL OR
               (role IN ('ADMIN', 'OPERATOR') AND password_hash IS NULL
                AND google_passenger_id <> id));

CREATE UNIQUE INDEX ux_amo_primary_account_email
    ON amo_accounts (email) WHERE google_passenger_id IS NULL;

ALTER TABLE amo_accounts DROP CONSTRAINT amo_accounts_email_key;
