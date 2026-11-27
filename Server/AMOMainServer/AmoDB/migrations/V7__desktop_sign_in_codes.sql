-- Short-lived codes that transfer a staff browser identity to a native session.
CREATE TABLE amo_desktop_codes (
    code_digest bytea PRIMARY KEY CHECK (octet_length(code_digest) = 32),
    challenge text NOT NULL CHECK (challenge ~ '^[A-Za-z0-9_-]{43}$'),
    callback_port integer NOT NULL CHECK (callback_port BETWEEN 1024 AND 65535),
    source_session_id uuid NOT NULL REFERENCES amo_sessions(id) ON DELETE CASCADE,
    account_id bigint NOT NULL REFERENCES amo_accounts(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL
);

CREATE INDEX ix_amo_desktop_codes_expires_at ON amo_desktop_codes (expires_at);
