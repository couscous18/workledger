# Versioning Policy

## Core schema

Core object schemas use semver-style versioning. Breaking field changes require a major version bump.

## Policy packs

Policy packs are versioned independently from code. Policy changes that alter classification semantics should increment the pack version.

## Extensions

Extension facets are namespaced and versionable by namespace owner. Core code should treat unknown facets as opaque.

