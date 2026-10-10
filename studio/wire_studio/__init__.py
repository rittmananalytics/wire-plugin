"""Wire Studio 4.x: a local, read-only director console for a Wire release.

Studio reads a client repository's `.wire/` record and the Wire framework's
release-type graph, and shows what the release director needs: what can run,
what is waiting on a decision, what the lanes are doing, and the record.

It never writes the record. The orchestrating session is the single writer of
`status.md` and `execution_log.md` (specs/utils/director_operating_model.md,
rule 6), so every action in Studio produces a directive for the director to
paste into that session.
"""

__version__ = "4.2.1-studio.2"
