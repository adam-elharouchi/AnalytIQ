"""
Integration tests — invariants the schema itself has to hold.

Deleting a user is the one operation that touches nearly every table, and what
happens to the rows pointing at that user is decided by the ``ON DELETE`` action
on each foreign key, not by either delete handler. PostgreSQL's default when no
action is written is ``NO ACTION``: the delete raises ForeignKeyViolation
instead of cascading. Both admin delete handlers wrap everything in
``except Exception`` and answer with a generic 500, so an FK added without an
``ON DELETE`` clause does not show up as a schema error -- it shows up as an
account that cannot be deleted, for no stated reason, but only for the users who
happen to have a row in that table.

These tests read the catalogue of the database the migrations built, so a new
table whose author forgot the clause fails here rather than in production.
"""

# The two deliberate policies for a foreign key into users:
#   CASCADE  — the row belongs to the user and goes with them (their profile,
#              their attempts, their conversations).
#   SET NULL — the row is the organisation's and merely records who made it
#              (an announcement, an SSO provider, an LTI config, a blocked IP);
#              it outlives the author and loses the attribution.
_DELETE_ACTIONS = {
    "a": "NO ACTION",
    "r": "RESTRICT",
    "c": "CASCADE",
    "n": "SET NULL",
    "d": "SET DEFAULT",
}

_FOREIGN_KEYS = """
    SELECT child.relname,
           (SELECT a.attname
              FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
             ORDER BY k.ord
             LIMIT 1),
           parent.relname,
           c.confdeltype
      FROM pg_constraint c
      JOIN pg_class child  ON child.oid  = c.conrelid
      JOIN pg_class parent ON parent.oid = c.confrelid
      JOIN pg_namespace n  ON n.oid = child.relnamespace
     WHERE c.contype = 'f' AND n.nspname = 'public'
     ORDER BY child.relname
"""


def _foreign_keys(conn):
    with conn.cursor() as cur:
        cur.execute(_FOREIGN_KEYS)
        return [
            (table, column, parent, _DELETE_ACTIONS.get(action, action))
            for table, column, parent, action in cur.fetchall()
        ]


def test_every_foreign_key_into_users_cascades_or_nulls(db_conn):
    """A user must be deletable whatever rows they left behind."""
    into_users = [fk for fk in _foreign_keys(db_conn) if fk[2] == "users"]

    # Guard against a query that silently matches nothing.
    assert len(into_users) > 10, "expected the schema to reference users from many tables"

    blocking = [fk for fk in into_users if fk[3] not in ("CASCADE", "SET NULL")]
    assert not blocking, "these foreign keys would make the user undeletable: " + ", ".join(
        f"{table}.{column} ON DELETE {action}" for table, column, _, action in blocking
    )


def test_no_foreign_key_is_left_on_the_default_no_action(db_conn):
    """Every foreign key states what a delete does, rather than inheriting the default."""
    defaulted = [fk for fk in _foreign_keys(db_conn) if fk[3] == "NO ACTION"]
    assert not defaulted, "these foreign keys have no ON DELETE clause: " + ", ".join(
        f"{table}.{column} -> {parent}" for table, column, parent, _ in defaulted
    )
