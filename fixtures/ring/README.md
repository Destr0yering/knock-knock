# Sanitized Ring contract fixtures

These JSON files mirror Ring webhook v1.1 examples from the official Partner API
documentation. Identifiers are synthetic and no customer payload or media is stored here.

Media contract tests use synthetic byte sequences labelled as watermarked content and assert that
the adapter returns those bytes unchanged. Knock Knock does not crop, mask, or alter the mandatory
Ring watermark. Real Ring media and captured Playground payloads must stay outside Git.
